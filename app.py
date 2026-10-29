
import sys
from parque import ParqueEolico


def seleccionar_area(parque: ParqueEolico):
    print("\nÁreas disponibles:")

    for numero, area in enumerate(parque.areas, start=1):
        print(f"{numero}) {area.nombre}")

    seleccion = input("Seleccione un área: ").strip()

    if not seleccion.isdigit():
        print("Selección no válida")
        return None

    indice = int(seleccion) - 1

    if indice < 0 or indice >= len(parque.areas):
        print("Selección no válida")
        return None

    return parque.areas[indice]


def seleccionar_aerogenerador(parque: ParqueEolico):
    print("\nAerogeneradores disponibles:")

    aerogeneradores = []

    for area in parque.areas:
        for aerogenerador in area.aerogeneradores:
            aerogeneradores.append(aerogenerador)

            print(
                f"{len(aerogeneradores)}) "
                f"{aerogenerador.identificador} - Área {area.nombre}"
            )

    seleccion = input("Seleccione un aerogenerador: ").strip()

    if not seleccion.isdigit():
        print("Selección no válida")
        return None

    indice = int(seleccion) - 1

    if indice < 0 or indice >= len(aerogeneradores):
        print("Selección no válida")
        return None

    return aerogeneradores[indice]


def mostrar_aerogenerador(aerogenerador) -> None:
    """Muestra la información de un aerogenerador."""
    print(
        f"  {aerogenerador.identificador} | "
        f"Estado: {aerogenerador.estado} | "
        f"Orientación: {aerogenerador.orientacion} | "
        f"Desgaste: {aerogenerador.desgaste}/{aerogenerador.umbral}",
        end=""
    )

    if aerogenerador.estado in ("AVERIADO", "EN_REPARACION"):
        print(
            f" | Código: {aerogenerador.codigo_averia}",
            end=""
        )

    if aerogenerador.estado == "EN_REPARACION":
        print(
            f" | Pasos pendientes: "
            f"{aerogenerador.pasos_reparacion}",
            end=""
        )

    print()


def consultar_parque(parque: ParqueEolico) -> None:
    """Muestra el estado completo del parque."""
    print("\n--- Estado del parque ---")

    for area in parque.areas:
        activos = area.contar_activos()

        print(f"\nÁrea: {area.nombre}")
        print(f"  Exigencia: {area.exigencia}")
        print(f"  Activos: {activos}")
        print(f"  Mínimo requerido: {area.minimo_activos}")
        print(
            "  Servicio:",
            "CUMPLE" if area.cumple_servicio() else "INSUFICIENTE"
        )

        for aerogenerador in area.aerogeneradores:
            mostrar_aerogenerador(aerogenerador)


def consultar_area(parque: ParqueEolico) -> None:
    """Consulta un área concreta."""
    area = seleccionar_area(parque)

    if area is None:
        return

    print(f"\n--- Área: {area.nombre} ---")
    print(f"Exigencia: {area.exigencia}")
    print(f"Activos: {area.contar_activos()}")
    print(f"Mínimo requerido: {area.minimo_activos}")
    print(
        "Servicio:",
        "CUMPLE" if area.cumple_servicio() else "INSUFICIENTE"
    )

    print("\nAerogeneradores:")

    for aerogenerador in area.aerogeneradores:
        mostrar_aerogenerador(aerogenerador)


def consultar_aerogenerador(parque: ParqueEolico) -> None:
    """Consulta un aerogenerador concreto."""
    aerogenerador = seleccionar_aerogenerador(parque)

    if aerogenerador is None:
        return

    print("\n--- Aerogenerador ---")
    print(f"Identificador: {aerogenerador.identificador}")
    print(f"Estado: {aerogenerador.estado}")
    print(f"Orientación: {aerogenerador.orientacion}")
    print(
        f"Desgaste: "
        f"{aerogenerador.desgaste}/{aerogenerador.umbral}"
    )

    if aerogenerador.estado in ("AVERIADO", "EN_REPARACION"):
        print(f"Código: {aerogenerador.codigo_averia}")

    if aerogenerador.estado == "EN_REPARACION":
        print(
            f"Pasos pendientes: "
            f"{aerogenerador.pasos_reparacion}"
        )


def activar_aerogenerador(parque: ParqueEolico) -> None:
    """Intenta activar un aerogenerador."""
    aerogenerador = seleccionar_aerogenerador(parque)

    if aerogenerador is None:
        return

    identificador = aerogenerador.identificador

    if parque.activar_aerogenerador(identificador):
        print(f"{identificador} activado correctamente")
    else:
        print(
            f"No se puede activar {identificador}. "
            f"Estado actual: {aerogenerador.estado}"
        )


def desactivar_aerogenerador(parque: ParqueEolico) -> None:
    """Intenta desactivar un aerogenerador."""
    aerogenerador = seleccionar_aerogenerador(parque)

    if aerogenerador is None:
        return

    identificador = aerogenerador.identificador

    if parque.desactivar_aerogenerador(identificador):
        print(f"{identificador} desactivado correctamente")
    else:
        print(
            f"No se puede desactivar {identificador}. "
            f"Estado actual: {aerogenerador.estado}"
        )


def orientar_aerogenerador(parque: ParqueEolico) -> None:
    """Intenta cambiar la orientación de un aerogenerador."""
    aerogenerador = seleccionar_aerogenerador(parque)

    if aerogenerador is None:
        return

    identificador = aerogenerador.identificador

    print("\nOrientaciones disponibles:")
    print("1) Norte (N)")
    print("2) Este (E)")
    print("3) Sur (S)")
    print("4) Oeste (O)")

    seleccion = input("Seleccione una orientación: ").strip()

    orientaciones = {
        "1": "N",
        "2": "E",
        "3": "S",
        "4": "O"
    }

    if seleccion not in orientaciones:
        print("Orientación no válida")
        return

    orientacion = orientaciones[seleccion]

    if parque.orientar_aerogenerador(
        identificador,
        orientacion
    ):
        print(
            f"{identificador} orientado hacia "
            f"{orientacion}"
        )
    else:
        print(
            f"No se puede orientar {identificador}. "
            "Debe estar DESACTIVADO"
        )


def reparar_aerogenerador(parque: ParqueEolico) -> None:
    """Intenta iniciar la reparación de un aerogenerador."""
    aerogenerador = seleccionar_aerogenerador(parque)

    if aerogenerador is None:
        return

    identificador = aerogenerador.identificador

    if aerogenerador.estado != "AVERIADO":
        print("El aerogenerador no está averiado")
        return

    if parque.tecnicos_disponibles() == 0:
        print("No hay técnicos libres")
        return

    if parque.reparar_aerogenerador(identificador):
        print(
            f"{identificador}: reparación iniciada"
        )
        print(
            f"Pasos pendientes: "
            f"{aerogenerador.pasos_reparacion}"
        )
    else:
        print("No se ha podido iniciar la reparación")


def avanzar_paso(parque: ParqueEolico) -> None:
    """Avanza un paso de simulación."""
    avisos = parque.avanzar_paso()

    print(f"\n--- Paso {parque.paso_actual} ---")

    if avisos:
        print("Avisos:")
        for aviso in avisos:
            print(aviso)
    else:
        print("No se han producido nuevas incidencias")

    print(
        f"Técnicos disponibles: "
        f"{parque.tecnicos_disponibles()}"
    )

    print(
        "Servicio:",
        "CUMPLE" if parque.cumple_servicio()
        else "INSUFICIENTE"
    )


def ejecutar_opcion(parque: ParqueEolico, opcion: str) -> None:
    """Implementa las consultas y órdenes del menú. Puedes añadir funciones."""

    if opcion == "1":
        consultar_parque(parque)

    elif opcion == "2":
        consultar_area(parque)

    elif opcion == "3":
        consultar_aerogenerador(parque)

    elif opcion == "4":
        activar_aerogenerador(parque)

    elif opcion == "5":
        desactivar_aerogenerador(parque)

    elif opcion == "6":
        orientar_aerogenerador(parque)

    elif opcion == "7":
        reparar_aerogenerador(parque)

    elif opcion == "8":
        avanzar_paso(parque)


def main():
    if len(sys.argv) != 2:
        print("Uso: python3 app.py escenarios/parque_inicial.txt")
        return
    parque = ParqueEolico()
    parque.cargar_configuracion(sys.argv[1])
    while True:
        print("\n=== Parque eólico ===")
        print(f"Paso: {parque.paso_actual}")
        print(f"Técnicos disponibles: {parque.tecnicos_disponibles()}")
        print("Servicio:", "CUMPLE" if parque.cumple_servicio() else "INSUFICIENTE")
        print("1) Consultar parque")
        print("2) Consultar área")
        print("3) Consultar aerogenerador")
        print("4) Activar aerogenerador")
        print("5) Desactivar aerogenerador")
        print("6) Orientar aerogenerador")
        print("7) Iniciar reparación")
        print("8) Avanzar al siguiente paso")
        print("0) Salir")
        opcion = input("> ").strip()
        if opcion == "0":
            print("Hasta luego")
            break
        if opcion not in ("1", "2", "3", "4", "5", "6", "7", "8"):
            print("Opción no válida")
            continue
        ejecutar_opcion(parque, opcion)


if __name__ == "__main__":
    main()
    