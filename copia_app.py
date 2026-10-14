import sys
from parque import ParqueEolico


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
    nombre = input("Nombre del área: ").strip()

    area_encontrada = None

    for area in parque.areas:
        if area.nombre == nombre:
            area_encontrada = area
            break

    if area_encontrada is None:
        print("Área inexistente")
        return

    area = area_encontrada

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
    identificador = input(
        "Identificador del aerogenerador: "
    ).strip()

    aerogenerador = parque.buscar_aerogenerador(identificador)

    if aerogenerador is None:
        print("Aerogenerador inexistente")
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
    identificador = input(
        "Identificador del aerogenerador: "
    ).strip()

    aerogenerador = parque.buscar_aerogenerador(identificador)

    if aerogenerador is None:
        print("Aerogenerador inexistente")
        return

    if parque.activar_aerogenerador(identificador):
        print(f"{identificador} activado correctamente")
    else:
        print(
            f"No se puede activar {identificador}. "
            f"Estado actual: {aerogenerador.estado}"
        )


def desactivar_aerogenerador(parque: ParqueEolico) -> None:
    """Intenta desactivar un aerogenerador."""
    identificador = input(
        "Identificador del aerogenerador: "
    ).strip()

    aerogenerador = parque.buscar_aerogenerador(identificador)

    if aerogenerador is None:
        print("Aerogenerador inexistente")
        return

    if parque.desactivar_aerogenerador(identificador):
        print(f"{identificador} desactivado correctamente")
    else:
        print(
            f"No se puede desactivar {identificador}. "
            f"Estado actual: {aerogenerador.estado}"
        )


def orientar_aerogenerador(parque: ParqueEolico) -> None:
    """Intenta cambiar la orientación de un aerogenerador."""
    identificador = input(
        "Identificador del aerogenerador: "
    ).strip()

    orientacion = input(
        "Nueva orientación (N, E, S u O): "
    ).strip()

    aerogenerador = parque.buscar_aerogenerador(identificador)

    if aerogenerador is None:
        print("Aerogenerador inexistente")
        return

    if parque.orientar_aerogenerador(
        identificador,
        orientacion
    ):
        print(
            f"{identificador} orientado hacia "
            f"{orientacion}"
        )
    else:
        if orientacion not in ("N", "E", "S", "O"):
            print("Orientación no válida")
        else:
            print(
                f"No se puede orientar {identificador}. "
                "Debe estar DESACTIVADO"
            )


def reparar_aerogenerador(parque: ParqueEolico) -> None:
    """Intenta iniciar la reparación de un aerogenerador."""
    identificador = input(
        "Identificador del aerogenerador: "
    ).strip()

    aerogenerador = parque.buscar_aerogenerador(identificador)

    if aerogenerador is None:
        print("Aerogenerador inexistente")
        return

    if aerogenerador.estado != "AVERIADO":
        print(
            "El aerogenerador no está averiado"
        )
        return

    if parque.tecnicos_disponibles() == 0:
        print("No hay técnicos libres")
        return

    if parque.reparar_aerogenerador(identificador):
        print(
            f"{identificador} pasa a EN_REPARACION"
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
