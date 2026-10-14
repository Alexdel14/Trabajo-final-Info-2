"""Clases del parque. Completa los TODO y conserva avanzar_paso del aerogenerador.

Puedes añadir métodos y atributos auxiliares. No uses input() en estas clases.
Los NotImplementedError señalan trabajo pendiente; no son errores que debas
capturar con try/except. Sustitúyelos por tu implementación.
"""
from __future__ import annotations


class Aerogenerador:
    def __init__(self, identificador: str, estado: str, orientacion: str,
                 desgaste: int, umbral: int):

        # Guardamos los datos del aerogenerador.

        self.identificador = identificador
        self.estado = estado
        self.orientacion = orientacion
        self.desgaste = desgaste
        self.umbral = umbral

        # Y los datos relacionados con las averías y reparaciones.
        self.codigo_averia = ""
        self.averias_acumuladas = 0
        self.pasos_reparacion = 0

    def consultar_estado(self) -> str:
        return self.estado

    def activar(self) -> bool:
        # Solo se puede activar en el caso de que esté DESACTIVADO.
        if self.estado != "DESACTIVADO":
            return False

        self.estado = "ACTIVO"
        return True

    def desactivar(self) -> bool:
        # Solo se puede desactivar en el caso de que esté ACTIVO.
        if self.estado != "ACTIVO":
            return False

        self.estado = "DESACTIVADO"
        return True

    def orientar(self, orientacion: str) -> bool:
        # Solo se puede orientar si está DESACTIVADO.
        if self.estado != "DESACTIVADO":
            return False

        # Las únicas orientaciones válidas son N (de norte), E (de este), S (de sur) y O (de oeste).
        if orientacion not in ("N", "E", "S", "O"):
            return False

        self.orientacion = orientacion
        return True

    def iniciar_reparacion(self) -> bool:
        # La disponibilidad de técnicos se comprueba en la clase ParqueEolico.
        if self.estado != "AVERIADO":
            return False

        # La duración depende del tipo de que tarde la avería.
        if self.codigo_averia == "E1":
            self.pasos_reparacion = 1
        elif self.codigo_averia == "E2":
            self.pasos_reparacion = 2
        else:
            return False

        self.estado = "EN_REPARACION"
        return True

    def avanzar_paso(self, exigencia: int) -> str:
        """PROPORCIONADO: no modificar. Actualiza exactamente un paso.

        exigencia es el entero positivo del área. La rama se elige según
        el estado al empezar: terminar una reparación no añade desgaste.
        """
        if self.estado == "ACTIVO":
            self.desgaste = min(self.umbral, self.desgaste + exigencia)
            if self.desgaste >= self.umbral:
                self.averias_acumuladas += 1
                self.codigo_averia = "E1" if self.averias_acumuladas % 2 else "E2"
                self.estado = "AVERIADO"
                return f"{self.identificador}: nueva avería {self.codigo_averia}"
        elif self.estado == "EN_REPARACION":
            self.pasos_reparacion -= 1
            if self.pasos_reparacion == 0:
                self.estado = "DESACTIVADO"
                self.desgaste = 0
                self.codigo_averia = ""
                return f"{self.identificador}: reparación terminada"
        return ""


class Area:
    def __init__(self, nombre: str, exigencia: int, minimo_activos: int):
        self.nombre = nombre
        self.exigencia = exigencia
        self.minimo_activos = minimo_activos
        self.aerogeneradores = []

    def anadir_aerogenerador(self, aerogenerador: Aerogenerador) -> None:
        self.aerogeneradores.append(aerogenerador)

    def contar_activos(self) -> int:
        contador = 0

        for aerogenerador in self.aerogeneradores:
            if aerogenerador.consultar_estado() == "ACTIVO":
                contador += 1

        return contador

    def cumple_servicio(self) -> bool:
        return self.contar_activos() >= self.minimo_activos


class ParqueEolico:
    def __init__(self):
        self.areas = []
        self.total_tecnicos = 0
        self.paso_actual = 0

    def cargar_configuracion(self, ruta: str) -> None:
        # Al cargar una configuración nueva se reinicia el parque.
        self.areas = []
        self.total_tecnicos = 0
        self.paso_actual = 0

        # Creamos un diccionario auxiliar para localizar rápidamente las áreas.
        areas_por_nombre = {}

        with open(ruta, "r", encoding="utf-8") as fichero:
            for linea in fichero:
                partes = linea.rstrip("\n").split(";")

                if partes[0] == "TECNICOS":
                    self.total_tecnicos = int(partes[1])

                elif partes[0] == "AREA":
                    nombre = partes[1]
                    exigencia = int(partes[2])
                    minimo_activos = int(partes[3])

                    area = Area(
                        nombre,
                        exigencia,
                        minimo_activos
                    )

                    self.areas.append(area)
                    areas_por_nombre[nombre] = area

                elif partes[0] == "AEROGENERADOR":
                    identificador = partes[1]
                    nombre_area = partes[2]
                    estado = partes[3]
                    orientacion = partes[4]
                    desgaste = int(partes[5])
                    umbral = int(partes[6])

                    aerogenerador = Aerogenerador(
                        identificador,
                        estado,
                        orientacion,
                        desgaste,
                        umbral
                    )

                    areas_por_nombre[nombre_area].anadir_aerogenerador(
                        aerogenerador
                    )

    def buscar_aerogenerador(
        self,
        identificador: str
    ) -> Aerogenerador | None:

        for area in self.areas:
            for aerogenerador in area.aerogeneradores:
                if aerogenerador.identificador == identificador:
                    return aerogenerador

        return None

    def activar_aerogenerador(self, identificador: str) -> bool:
        aerogenerador = self.buscar_aerogenerador(identificador)

        if aerogenerador is None:
            return False

        return aerogenerador.activar()

    def desactivar_aerogenerador(self, identificador: str) -> bool:
        aerogenerador = self.buscar_aerogenerador(identificador)

        if aerogenerador is None:
            return False

        return aerogenerador.desactivar()

    def orientar_aerogenerador(
        self,
        identificador: str,
        orientacion: str
    ) -> bool:

        aerogenerador = self.buscar_aerogenerador(identificador)

        if aerogenerador is None:
            return False

        return aerogenerador.orientar(orientacion)

    def reparar_aerogenerador(self, identificador: str) -> bool:
        aerogenerador = self.buscar_aerogenerador(identificador)

        if aerogenerador is None:
            return False

        # Antes de iniciar la reparación comprobamos que haya al menos un técnico disponible.
        if self.tecnicos_disponibles() <= 0:
            return False

        return aerogenerador.iniciar_reparacion()

    def tecnicos_disponibles(self) -> int:
        tecnicos_ocupados = 0

        for area in self.areas:
            for aerogenerador in area.aerogeneradores:
                if aerogenerador.estado == "EN_REPARACION":
                    tecnicos_ocupados += 1

        return self.total_tecnicos - tecnicos_ocupados

    def cumple_servicio(self) -> bool:
        # Si no hay ninguna área, el parque no cumple el servicio.
        if not self.areas:
            return False

        # El parque cumple su función únicamentesi todas sus áreas cumplen.
        for area in self.areas:
            if not area.cumple_servicio():
                return False

        return True

    def avanzar_paso(self) -> list[str]:
        self.paso_actual += 1

        avisos = []

        # Se recorren las áreas y los aerogeneradores en el mismo orden en que fueron cargados.
        for area in self.areas:
            for aerogenerador in area.aerogeneradores:
                aviso = aerogenerador.avanzar_paso(area.exigencia)

                if aviso != "":
                    avisos.append(aviso)

        return avisos