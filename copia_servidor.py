import socket
import sys
import threading
from parque import ParqueEolico

clientes_conectados = {}
confirmaciones = {}
eventos_confirmacion = {}
ordenes_pendientes = {}
notificaciones = []

lock_clientes = threading.Lock()

TIEMPO_ESPERA = 10


def enviar_linea(sock: socket.socket, mensaje: str) -> bool:
    """Envía un mensaje UTF-8 terminado en salto de línea."""
    try:
        sock.sendall((mensaje + "\n").encode("utf-8"))
        return True
    except OSError:
        return False


def recibir_linea(flujo):
    """Recibe una línea completa conservando los datos posteriores."""
    linea = flujo.readline()

    if not linea:
        return None

    return linea.rstrip("\r\n")


def anadir_notificacion(mensaje: str):
    """Añade una notificación para que la muestre el hilo principal."""
    with lock_clientes:
        notificaciones.append(mensaje)


def mostrar_notificaciones():
    """Muestra las notificaciones pendientes sin interrumpir el menú."""
    with lock_clientes:
        pendientes = list(notificaciones)
        notificaciones.clear()

    for mensaje in pendientes:
        print(f"\n{mensaje}")


def esperar_confirmacion(identificador: str, orden: str) -> bool:
    """Espera la confirmación exacta de una orden."""
    with lock_clientes:
        evento = eventos_confirmacion.get(identificador)

    if evento is None:
        return False

    recibida = evento.wait(TIEMPO_ESPERA)

    with lock_clientes:
        confirmacion = confirmaciones.pop(identificador, None)

        if ordenes_pendientes.get(identificador) == orden:
            ordenes_pendientes.pop(identificador, None)

    if not recibida:
        return False

    return confirmacion == f"CONFIRMADO {orden}"


def enviar_orden_y_esperar(identificador: str, orden: str) -> bool:
    """Envía una orden al cliente y espera su confirmación."""
    with lock_clientes:
        sock = clientes_conectados.get(identificador)
        evento = eventos_confirmacion.get(identificador)

        if sock is None or evento is None:
            return False

        confirmaciones.pop(identificador, None)
        ordenes_pendientes[identificador] = orden
        evento.clear()

    if not enviar_linea(sock, f"ORDEN {orden}"):
        with lock_clientes:
            if ordenes_pendientes.get(identificador) == orden:
                ordenes_pendientes.pop(identificador, None)
        return False

    return esperar_confirmacion(identificador, orden)


def cliente_conectado(identificador: str) -> bool:
    """Comprueba si un aerogenerador tiene un cliente conectado."""
    with lock_clientes:
        return identificador in clientes_conectados


def manejar_cliente(sock_cliente: socket.socket, addr, parque: ParqueEolico):
    """Atiende a un cliente remoto."""
    id_aerog = None
    flujo = None

    try:
        flujo = sock_cliente.makefile("r", encoding="utf-8")

        linea = recibir_linea(flujo)

        if linea is None or not linea.startswith("CONECTAR "):
            enviar_linea(sock_cliente, "RECHAZADO")
            return

        id_aerog = linea.split(" ", 1)[1].strip()

        if not parque.buscar_aerogenerador(id_aerog):
            enviar_linea(
                sock_cliente,
                f"RECHAZADO {id_aerog} desconocido"
            )
            return

        with lock_clientes:
            if id_aerog in clientes_conectados:
                enviar_linea(
                    sock_cliente,
                    f"RECHAZADO {id_aerog} ya conectado"
                )
                return

            clientes_conectados[id_aerog] = sock_cliente
            confirmaciones.pop(id_aerog, None)
            eventos_confirmacion[id_aerog] = threading.Event()

        if not enviar_linea(sock_cliente, "ACEPTADO"):
            return

        anadir_notificacion(
            f"{id_aerog} conectado correctamente."
        )

        while True:
            msg = recibir_linea(flujo)

            if msg is None or msg == "DESCONECTAR":
                break

            if msg.startswith("CONFIRMADO "):
                with lock_clientes:
                    orden_esperada = ordenes_pendientes.get(id_aerog)
                    evento = eventos_confirmacion.get(id_aerog)

                    if (
                        orden_esperada is not None
                        and msg == f"CONFIRMADO {orden_esperada}"
                        and evento is not None
                    ):
                        confirmaciones[id_aerog] = msg
                        evento.set()

    except (OSError, UnicodeDecodeError, ValueError):
        pass

    finally:
        if flujo is not None:
            try:
                flujo.close()
            except OSError:
                pass

        if id_aerog is not None:
            with lock_clientes:
                if clientes_conectados.get(id_aerog) == sock_cliente:
                    del clientes_conectados[id_aerog]
                    notificaciones.append(
                        f"{id_aerog} se ha desconectado."
                    )

                confirmaciones.pop(id_aerog, None)
                ordenes_pendientes.pop(id_aerog, None)

                evento = eventos_confirmacion.pop(id_aerog, None)

                if evento is not None:
                    evento.set()

        try:
            sock_cliente.close()
        except OSError:
            pass


def aceptar_conexiones(server_socket: socket.socket, parque: ParqueEolico):
    """Hilo encargado de aceptar conexiones entrantes."""
    while True:
        try:
            client_socket, addr = server_socket.accept()

            hilo = threading.Thread(
                target=manejar_cliente,
                args=(client_socket, addr, parque),
                daemon=True
            )

            hilo.start()

        except OSError:
            break


def seleccionar_area(parque: ParqueEolico):
    """Permite seleccionar un área del parque."""
    print("\nÁreas disponibles:")

    for i, area in enumerate(parque.areas, start=1):
        print(f"{i}) {area.nombre}")

    sel = input("Seleccione un área: ").strip()

    if not sel.isdigit() or not (1 <= int(sel) <= len(parque.areas)):
        print("Selección no válida")
        return None

    return parque.areas[int(sel) - 1]


def seleccionar_aerogenerador(parque: ParqueEolico):
    """Permite seleccionar un aerogenerador del parque."""
    print("\nAerogeneradores disponibles:")

    aerogs = []

    for area in parque.areas:
        for ag in area.aerogeneradores:
            aerogs.append(ag)

            remoto = (
                "CONTROL REMOTO DISPONIBLE"
                if cliente_conectado(ag.identificador)
                else "SIN CONEXIÓN REMOTA"
            )

            print(
                f"{len(aerogs)}) {ag.identificador} "
                f"- Área {area.nombre} - {remoto}"
            )

    sel = input("Seleccione un aerogenerador: ").strip()

    if not sel.isdigit() or not (1 <= int(sel) <= len(aerogs)):
        print("Selección no válida")
        return None

    return aerogs[int(sel) - 1]


def ejecutar_operacion_remota(
    ag,
    orden: str,
    condicion,
    operacion,
    mensaje_exito: str
):
    """Comprueba las reglas, espera confirmación y modifica el parque."""
    identificador = ag.identificador

    if not cliente_conectado(identificador):
        print(
            f"{identificador}: operación rechazada. "
            "SIN CONEXIÓN REMOTA."
        )
        return

    if not condicion():
        print("No se puede realizar la operación según las reglas.")
        return

    if not enviar_orden_y_esperar(identificador, orden):
        print(
            f"{identificador}: operación fallida. "
            "No se ha recibido una confirmación válida."
        )
        return

    print(f"Confirmación recibida de {identificador}.")

    if operacion():
        print(mensaje_exito)
    else:
        print(
            f"{identificador}: no se pudo aplicar la operación "
            "en el parque."
        )


def cerrar_servidor(server_socket: socket.socket):
    """Cierra ordenadamente las conexiones y el servidor."""
    with lock_clientes:
        conexiones = list(clientes_conectados.items())

    for identificador, sock in conexiones:
        enviar_linea(sock, "SERVIDOR_CIERRA")

        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

        try:
            sock.close()
        except OSError:
            pass

        with lock_clientes:
            if clientes_conectados.get(identificador) == sock:
                del clientes_conectados[identificador]
                notificaciones.append(
                    f"{identificador} se ha desconectado."
                )

            confirmaciones.pop(identificador, None)
            ordenes_pendientes.pop(identificador, None)

            evento = eventos_confirmacion.pop(identificador, None)

            if evento is not None:
                evento.set()

    mostrar_notificaciones()

    try:
        server_socket.close()
    except OSError:
        pass


def main():
    if len(sys.argv) != 3:
        print(
            "Uso: python3 servidor.py "
            "<puerto> <fichero_configuracion>"
        )
        sys.exit(1)

    try:
        puerto = int(sys.argv[1])

        if not 1 <= puerto <= 65535:
            print("Error: el puerto debe estar entre 1 y 65535.")
            sys.exit(1)

    except ValueError:
        print("Error: el puerto debe ser un número entero.")
        sys.exit(1)

    parque = ParqueEolico()

    try:
        parque.cargar_configuracion(sys.argv[2])
    except Exception as e:
        print(f"Error al cargar el escenario: {e}")
        sys.exit(1)

    server_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    try:
        server_socket.bind(("0.0.0.0", puerto))
        server_socket.listen(5)

    except OSError as e:
        print(f"No se pudo iniciar el servidor: {e}")
        server_socket.close()
        sys.exit(1)

    print(
        f"Centro de control iniciado en el puerto {puerto}."
    )

    threading.Thread(
        target=aceptar_conexiones,
        args=(server_socket, parque),
        daemon=True
    ).start()

    while True:
        mostrar_notificaciones()

        print("\n=== Centro de control del parque eólico ===")
        print(f"Paso: {parque.paso_actual}")

        with lock_clientes:
            num_remotos = len(clientes_conectados)

        total_aerog = sum(
            len(area.aerogeneradores)
            for area in parque.areas
        )

        print(
            f"Control remoto disponible: "
            f"{num_remotos}/{total_aerog} aerogeneradores"
        )

        print(
            f"Técnicos disponibles: "
            f"{parque.tecnicos_disponibles()}"
        )

        print(
            "Servicio:",
            "CUMPLE"
            if parque.cumple_servicio()
            else "INSUFICIENTE"
        )

        print("1) Consultar parque")
        print("2) Consultar área")
        print("3) Consultar aerogenerador")
        print("4) Activar aerogenerador")
        print("5) Desactivar aerogenerador")
        print("6) Orientar aerogenerador")
        print("7) Iniciar reparación")
        print("8) Avanzar al siguiente paso")
        print("0) Cerrar centro de control")

        try:
            opcion = input("> ").strip()

        except KeyboardInterrupt:
            print("\nCtrl+C recibido. Cerrando el centro de control...")

            cerrar_servidor(server_socket)

            print("Servidor cerrado correctamente.")
            break

        mostrar_notificaciones()

        if opcion == "0":
            cerrar_servidor(server_socket)
            print("\nApagando servidor...")
            break

        elif opcion == "1":
            print("\n--- Estado del parque ---")

            for area in parque.areas:
                print(f"\nÁrea {area.nombre}")
                print(f"  Exigencia: {area.exigencia}")

                print(
                    f"  Activos: {area.contar_activos()}/"
                    f"{area.minimo_activos} requeridos"
                )

                print(
                    "  Servicio:",
                    "CUMPLE"
                    if area.cumple_servicio()
                    else "INSUFICIENTE"
                )

                for ag in area.aerogeneradores:
                    remoto = (
                        "CONTROL REMOTO DISPONIBLE"
                        if cliente_conectado(ag.identificador)
                        else "SIN CONEXIÓN REMOTA"
                    )

                    print(
                        f"  {ag.identificador} | {ag.estado} | "
                        f"{remoto} | orientación {ag.orientacion} | "
                        f"desgaste {ag.desgaste}/{ag.umbral}"
                    )

        elif opcion == "2":
            area = seleccionar_area(parque)

            if area:
                print(f"\n--- Área {area.nombre} ---")
                print(f"Exigencia: {area.exigencia}")

                print(
                    f"Activos: {area.contar_activos()}/"
                    f"{area.minimo_activos} requeridos"
                )

                print(
                    "Servicio:",
                    "CUMPLE"
                    if area.cumple_servicio()
                    else "INSUFICIENTE"
                )

                for ag in area.aerogeneradores:
                    remoto = (
                        "CONTROL REMOTO DISPONIBLE"
                        if cliente_conectado(ag.identificador)
                        else "SIN CONEXIÓN REMOTA"
                    )

                    print(
                        f"  {ag.identificador} | {ag.estado} | "
                        f"{remoto} | orientación {ag.orientacion} | "
                        f"desgaste {ag.desgaste}/{ag.umbral}"
                    )

        elif opcion == "3":
            ag = seleccionar_aerogenerador(parque)

            if ag:
                remoto = (
                    "CONTROL REMOTO DISPONIBLE"
                    if cliente_conectado(ag.identificador)
                    else "SIN CONEXIÓN REMOTA"
                )

                print(
                    f"\n--- Aerogenerador {ag.identificador} ---"
                )
                print(f"Estado: {ag.estado}")
                print(f"Control remoto: {remoto}")
                print(f"Orientación: {ag.orientacion}")
                print(f"Desgaste: {ag.desgaste}/{ag.umbral}")

        elif opcion in ("4", "5", "6", "7"):
            ag = seleccionar_aerogenerador(parque)

            if not ag:
                continue

            identificador = ag.identificador

            if opcion == "4":
                ejecutar_operacion_remota(
                    ag,
                    "ACTIVAR",
                    lambda: ag.estado == "DESACTIVADO",
                    lambda: parque.activar_aerogenerador(identificador),
                    f"{identificador}: activado."
                )

            elif opcion == "5":
                ejecutar_operacion_remota(
                    ag,
                    "DESACTIVAR",
                    lambda: ag.estado == "ACTIVO",
                    lambda: parque.desactivar_aerogenerador(identificador),
                    f"{identificador}: desactivado."
                )

            elif opcion == "6":
                print(
                    "Orientaciones: "
                    "1) N, 2) E, 3) S, 4) O"
                )

                d_sel = input(
                    "Seleccione orientación: "
                ).strip()

                dirs = {
                    "1": "N",
                    "2": "E",
                    "3": "S",
                    "4": "O"
                }

                if d_sel not in dirs:
                    print("Orientación no válida")
                    continue

                d = dirs[d_sel]

                ejecutar_operacion_remota(
                    ag,
                    f"ORIENTAR {d}",
                    lambda: (
                        ag.estado == "DESACTIVADO"
                        and d in ("N", "E", "S", "O")
                    ),
                    lambda: parque.orientar_aerogenerador(
                        identificador,
                        d
                    ),
                    f"{identificador} orientado a {d}."
                )

            elif opcion == "7":
                if ag.estado != "AVERIADO":
                    print("El aerogenerador no está averiado.")
                    continue

                if parque.tecnicos_disponibles() <= 0:
                    print("No hay técnicos disponibles.")
                    continue

                if ag.codigo_averia not in ("E1", "E2"):
                    print("No se puede reparar esta avería.")
                    continue

                ejecutar_operacion_remota(
                    ag,
                    "INICIAR_REPARACION",
                    lambda: (
                        ag.estado == "AVERIADO"
                        and parque.tecnicos_disponibles() > 0
                        and ag.codigo_averia in ("E1", "E2")
                    ),
                    lambda: parque.reparar_aerogenerador(identificador),
                    f"{identificador}: reparación iniciada."
                )

        elif opcion == "8":
            avisos = parque.avanzar_paso()

            print(
                f"\nPaso {parque.paso_actual} completado"
            )

            if avisos:
                for aviso in avisos:
                    print(f"AVISO: {aviso}")

                    ident = aviso.split(":")[0].strip()

                    with lock_clientes:
                        sock = clientes_conectados.get(ident)

                    if sock is not None:
                        if not enviar_linea(sock, f"AVISO {aviso}"):
                            try:
                                sock.shutdown(socket.SHUT_RDWR)
                            except OSError:
                                pass

            else:
                print("No se han producido nuevas incidencias.")

        else:
            print("Opción no válida.")


if __name__ == "__main__":
    main()