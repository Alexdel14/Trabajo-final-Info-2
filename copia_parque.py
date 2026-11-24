
import socket
import sys
import threading
from parque import ParqueEolico

clientes_conectados = {}  # {identificador: socket_cliente}
confirmaciones = {}       # {identificador: mensaje recibido}
eventos_confirmacion = {} # {identificador: evento}
lock_clientes = threading.Lock()


def enviar_linea(sock: socket.socket, mensaje: str):
    """Envía un mensaje UTF-8 terminado en salto de línea."""
    try:
        sock.sendall((mensaje + "\n").encode("utf-8"))
    except OSError:
        pass


def recibir_linea(sock: socket.socket) -> str:
    """Recibe datos acumulando hasta el salto de línea."""
    buffer = b""
    while not buffer.endswith(b"\n"):
        chunk = sock.recv(1024)
        if not chunk:
            break
        buffer += chunk
    return buffer.decode("utf-8").strip()


def preparar_confirmacion(identificador: str) -> bool:
    """Prepara el evento antes de enviar una orden."""
    with lock_clientes:
        evento = eventos_confirmacion.get(identificador)

        if evento is None:
            return False

        confirmaciones.pop(identificador, None)
        evento.clear()

        return True


def esperar_confirmacion(identificador: str, timeout=10):
    """Espera la confirmación sin leer directamente del socket."""
    with lock_clientes:
        evento = eventos_confirmacion.get(identificador)

    if evento is None:
        return None

    if not evento.wait(timeout):
        return None

    with lock_clientes:
        return confirmaciones.pop(identificador, None)


def enviar_orden_y_esperar(sock, identificador, orden):
    """Envía una orden y espera a que llegue su confirmación."""
    if not preparar_confirmacion(identificador):
        print("No se ha podido preparar la confirmación.")
        return None

    try:
        enviar_linea(sock, "ORDEN " + orden)
    except OSError:
        print("No se ha podido enviar la orden.")
        return None

    return esperar_confirmacion(identificador)


def manejar_cliente(sock_cliente: socket.socket, addr, parque: ParqueEolico):
    """Atiende de forma concurrente a un aerogenerador conectado."""
    id_aerog = None

    try:
        linea = recibir_linea(sock_cliente)

        if not linea.startswith("CONECTAR "):
            enviar_linea(sock_cliente, "RECHAZADO")
            sock_cliente.close()
            return

        id_aerog = linea.split(" ", 1)[1].strip()

        if not parque.buscar_aerogenerador(id_aerog):
            enviar_linea(sock_cliente, f"RECHAZADO {id_aerog} desconocido")
            sock_cliente.close()
            return

        with lock_clientes:
            if id_aerog in clientes_conectados:
                enviar_linea(
                    sock_cliente,
                    f"RECHAZADO {id_aerog} ya conectado"
                )
                sock_cliente.close()
                return

            clientes_conectados[id_aerog] = sock_cliente
            confirmaciones.pop(id_aerog, None)
            eventos_confirmacion[id_aerog] = threading.Event()

        enviar_linea(sock_cliente, "ACEPTADO")
        print(f"\n{id_aerog} conectado correctamente.")

        # Este hilo es el único que recibe mensajes del aerogenerador.
        while True:
            msg = recibir_linea(sock_cliente)

            if not msg or msg == "DESCONECTAR":
                break

            if msg.startswith("CONFIRMADO "):
                with lock_clientes:
                    evento = eventos_confirmacion.get(id_aerog)

                    if evento is not None:
                        confirmaciones[id_aerog] = msg
                        evento.set()

                print(f"\nConfirmación recibida de {id_aerog}.\n")

    except (OSError, UnicodeDecodeError):
        pass

    finally:
        if id_aerog:
            with lock_clientes:
                if clientes_conectados.get(id_aerog) == sock_cliente:
                    del clientes_conectados[id_aerog]

                    confirmaciones.pop(id_aerog, None)

                    evento = eventos_confirmacion.pop(id_aerog, None)

                    # Despierta al menú si el cliente se desconecta
                    # mientras el servidor está esperando.
                    if evento is not None:
                        evento.set()

            print(f"\n{id_aerog} se ha desconectado.")

        try:
            sock_cliente.close()
        except OSError:
            pass


def aceptar_conexiones(server_socket: socket.socket, parque: ParqueEolico):
    """Hilo para aceptar conexiones entrantes en bucle."""
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
    print("\nÁreas disponibles:")

    for i, area in enumerate(parque.areas, start=1):
        print(f"{i}) {area.nombre}")

    sel = input("Seleccione un área: ").strip()

    if not sel.isdigit() or not (1 <= int(sel) <= len(parque.areas)):
        print("Selección no válida")
        return None

    return parque.areas[int(sel) - 1]


def seleccionar_aerogenerador(parque: ParqueEolico):
    print("\nAerogeneradores disponibles:")

    aerogs = []

    for area in parque.areas:
        for ag in area.aerogeneradores:
            aerogs.append(ag)

            with lock_clientes:
                remoto = (
                    "CONTROL REMOTO DISPONIBLE"
                    if ag.identificador in clientes_conectados
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


def main():
    if len(sys.argv) != 3:
        print("Uso: python3 servidor.py <puerto> <fichero_configuracion>")
        sys.exit(1)

    puerto = int(sys.argv[1])
    parque = ParqueEolico()

    try:
        parque.cargar_configuracion(sys.argv[2])
    except Exception as e:
        print(f"Error al cargar el escenario: {e}")
        sys.exit(1)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind(("0.0.0.0", puerto))
        server_socket.listen(5)
    except Exception as e:
        print(f"No se pudo iniciar el servidor: {e}")
        sys.exit(1)

    print(f"Centro de control iniciado en el puerto {puerto}.")

    threading.Thread(
        target=aceptar_conexiones,
        args=(server_socket, parque),
        daemon=True
    ).start()

    while True:
        print("\n=== Centro de control del parque eólico ===")
        print(f"Paso: {parque.paso_actual}")

        with lock_clientes:
            num_remotos = len(clientes_conectados)

        total_aerog = sum(len(a.aerogeneradores) for a in parque.areas)

        print(
            f"Control remoto disponible: "
            f"{num_remotos}/{total_aerog} aerogeneradores"
        )

        print(f"Técnicos disponibles: {parque.tecnicos_disponibles()}")
        print(
            "Servicio:",
            "CUMPLE" if parque.cumple_servicio() else "INSUFICIENTE"
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

        opcion = input("> ").strip()

        if opcion == "0":
            with lock_clientes:
                conexiones = list(clientes_conectados.items())

            for ident, sock in conexiones:
                try:
                    enviar_linea(sock, "SERVIDOR_CIERRA")
                    sock.close()
                except OSError:
                    pass

            server_socket.close()
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
                    "CUMPLE" if area.cumple_servicio() else "INSUFICIENTE"
                )

                for ag in area.aerogeneradores:
                    with lock_clientes:
                        remoto = (
                            "CONTROL REMOTO DISPONIBLE"
                            if ag.identificador in clientes_conectados
                            else "SIN CONEXIÓN REMOTA"
                        )

                    print(
                        f"  {ag.identificador} | {ag.estado} | {remoto} | "
                        f"orientación {ag.orientacion} | "
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
                    "CUMPLE" if area.cumple_servicio() else "INSUFICIENTE"
                )

                for ag in area.aerogeneradores:
                    with lock_clientes:
                        remoto = (
                            "CONTROL REMOTO DISPONIBLE"
                            if ag.identificador in clientes_conectados
                            else "SIN CONEXIÓN REMOTA"
                        )

                    print(
                        f"  {ag.identificador} | {ag.estado} | {remoto} | "
                        f"orientación {ag.orientacion} | "
                        f"desgaste {ag.desgaste}/{ag.umbral}"
                    )

        elif opcion == "3":
            ag = seleccionar_aerogenerador(parque)

            if ag:
                with lock_clientes:
                    remoto = (
                        "CONTROL REMOTO DISPONIBLE"
                        if ag.identificador in clientes_conectados
                        else "SIN CONEXIÓN REMOTA"
                    )

                print(f"\n--- Aerogenerador {ag.identificador} ---")
                print(f"Estado: {ag.estado}")
                print(f"Control remoto: {remoto}")
                print(f"Orientación: {ag.orientacion}")
                print(f"Desgaste: {ag.desgaste}/{ag.umbral}")

        elif opcion in ("4", "5", "6", "7"):
            ag = seleccionar_aerogenerador(parque)

            if not ag:
                continue

            # Comprobar si tiene control remoto conectado.
            with lock_clientes:
                sock = clientes_conectados.get(ag.identificador)

            if not sock:
                print(
                    f"Orden rechazada: {ag.identificador} "
                    "no tiene conexión remota."
                )
                continue

            # Mapeo de órdenes.
            if opcion == "4":
                resp = enviar_orden_y_esperar(
                    sock,
                    ag.identificador,
                    "ACTIVAR"
                )

                if resp in (
                    "CONFIRMADO ORDEN ACTIVAR",
                    "CONFIRMADO ACTIVAR"
                ):
                    if parque.activar_aerogenerador(ag.identificador):
                        print(f"{ag.identificador}: activado.")
                    else:
                        print("No se pudo activar según las reglas.")
                else:
                    print("El cliente no confirmó la orden correctamente.")

            elif opcion == "5":
                resp = enviar_orden_y_esperar(
                    sock,
                    ag.identificador,
                    "DESACTIVAR"
                )

                if resp in (
                    "CONFIRMADO ORDEN DESACTIVAR",
                    "CONFIRMADO DESACTIVAR"
                ):
                    if parque.desactivar_aerogenerador(ag.identificador):
                        print(f"{ag.identificador}: desactivado.")
                    else:
                        print("No se pudo desactivar según las reglas.")
                else:
                    print("El cliente no confirmó la orden.")

            elif opcion == "6":
                print("Orientaciones: 1) N, 2) E, 3) S, 4) O")

                d_sel = input("Seleccione orientación: ").strip()
                dirs = {"1": "N", "2": "E", "3": "S", "4": "O"}

                if d_sel not in dirs:
                    print("Orientación no válida")
                    continue

                d = dirs[d_sel]

                resp = enviar_orden_y_esperar(
                    sock,
                    ag.identificador,
                    f"ORIENTAR {d}"
                )

                if resp in (
                    f"CONFIRMADO ORDEN ORIENTAR {d}",
                    f"CONFIRMADO ORIENTAR {d}"
                ):
                    if parque.orientar_aerogenerador(ag.identificador, d):
                        print(f"{ag.identificador} orientado a {d}.")
                    else:
                        print("No se pudo orientar.")
                else:
                    print("El cliente no confirmó la orden.")

            elif opcion == "7":
                if ag.estado != "AVERIADO":
                    print("El aerogenerador no está averiado.")
                    continue

                if parque.tecnicos_disponibles() <= 0:
                    print("No hay técnicos disponibles.")
                    continue

                resp = enviar_orden_y_esperar(
                    sock,
                    ag.identificador,
                    "INICIAR_REPARACION"
                )

                if resp in (
                    "CONFIRMADO ORDEN INICIAR_REPARACION",
                    "CONFIRMADO INICIAR_REPARACION"
                ):
                    if parque.reparar_aerogenerador(ag.identificador):
                        print(f"{ag.identificador}: reparación iniciada.")
                    else:
                        print("No se pudo iniciar la reparación.")
                else:
                    print("El cliente no confirmó la orden.")

        elif opcion == "8":
            avisos = parque.avanzar_paso()
            print(f"\nPaso {parque.paso_actual} completado")

            if avisos:
                for aviso in avisos:
                    print(f"AVISO: {aviso}")

                    ident = aviso.split(":")[0].strip()

                    with lock_clientes:
                        sock = clientes_conectados.get(ident)

                    if sock:
                        enviar_linea(sock, f"AVISO {aviso}")
            else:
                print("No se han producido nuevas incidencias.")


if __name__ == "__main__":
    main()
