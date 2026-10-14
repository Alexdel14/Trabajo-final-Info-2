"""Contrato público: firmas, atributos y tipos reales en llamadas básicas.

No comprueba todas las reglas funcionales ni exige un texto de salida exacto.
Ejecutar desde la raíz con python3 -m pytest tests/test_estructura.py -q
"""
import inspect
from pathlib import Path
from typing import get_type_hints, get_origin, get_args
import pytest
import parque


CONTRATOS = {
    "Aerogenerador": {
        "__init__": ([str, str, str, int, int], None),
        "consultar_estado": ([], str),
        "activar": ([], bool), "desactivar": ([], bool),
        "orientar": ([str], bool), "iniciar_reparacion": ([], bool),
        "avanzar_paso": ([int], str),
    },
    "Area": {
        "__init__": ([str, int, int], None),
        "anadir_aerogenerador": ([parque.Aerogenerador], type(None)),
        "contar_activos": ([], int), "cumple_servicio": ([], bool),
    },
    "ParqueEolico": {
        "__init__": ([], None),
        "cargar_configuracion": ([str], type(None)),
        "buscar_aerogenerador": ([str], parque.Aerogenerador | None),
        "activar_aerogenerador": ([str], bool),
        "desactivar_aerogenerador": ([str], bool),
        "orientar_aerogenerador": ([str, str], bool),
        "reparar_aerogenerador": ([str], bool),
        "tecnicos_disponibles": ([], int),
        "cumple_servicio": ([], bool), "avanzar_paso": ([], list[str]),
    },
}


def normalizar(tipo):
    """Acepta equivalentes como List[str] y list[str]."""
    return (get_origin(tipo), tuple(normalizar(t) for t in get_args(tipo))) if get_origin(tipo) else tipo


@pytest.mark.parametrize("nombre,metodo", [
    (nombre, metodo) for nombre, metodos in CONTRATOS.items() for metodo in metodos
])
def test_firmas(nombre, metodo):
    cls = getattr(parque, nombre, None)
    assert inspect.isclass(cls), f"Falta la clase {nombre}"
    fn = getattr(cls, metodo, None)
    assert callable(fn), f"Falta {nombre}.{metodo}"
    parametros, retorno = CONTRATOS[nombre][metodo]
    firma = list(inspect.signature(fn).parameters.values())
    assert firma and firma[0].name == "self", f"{nombre}.{metodo}: falta self"
    assert len(firma) - 1 == len(parametros), f"{nombre}.{metodo}: número de parámetros incorrecto (sin self)"
    hints = get_type_hints(fn)
    for param, esperado in zip(firma[1:], parametros):
        assert param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD)
        assert normalizar(hints.get(param.name)) == normalizar(esperado), f"{nombre}.{metodo}: revisa el tipo de {param.name}"
    if metodo != "__init__":
        assert normalizar(hints.get("return")) == normalizar(retorno), f"{nombre}.{metodo}: revisa el tipo de retorno"


def comprobar_atributos(objeto, tipos):
    for nombre, tipo in tipos.items():
        assert hasattr(objeto, nombre), f"Falta {type(objeto).__name__}.{nombre}"
        assert type(getattr(objeto, nombre)) is tipo, f"Tipo incorrecto de {nombre}"


def test_atributos_aerogenerador():
    m = parque.Aerogenerador("X", "DESACTIVADO", "N", 0, 10)
    comprobar_atributos(m, dict(identificador=str, estado=str, orientacion=str,
        desgaste=int, umbral=int, codigo_averia=str, averias_acumuladas=int, pasos_reparacion=int))
    assert (m.identificador, m.estado, m.orientacion, m.desgaste, m.umbral) == ("X", "DESACTIVADO", "N", 0, 10)
    assert (m.codigo_averia, m.averias_acumuladas, m.pasos_reparacion) == ("", 0, 0)


def test_atributos_area():
    a = parque.Area("Zona", 2, 1)
    comprobar_atributos(a, dict(nombre=str, exigencia=int, minimo_activos=int, aerogeneradores=list))
    assert (a.nombre, a.exigencia, a.minimo_activos) == ("Zona", 2, 1)
    assert a.aerogeneradores == []


def test_atributos_parque():
    p = parque.ParqueEolico()
    comprobar_atributos(p, dict(areas=list, total_tecnicos=int, paso_actual=int))
    assert (p.areas, p.total_tecnicos, p.paso_actual) == ([], 0, 0)


@pytest.mark.parametrize("metodo,args", [
    ("consultar_estado", ()), ("activar", ()), ("desactivar", ()),
    ("orientar", ("E",)), ("iniciar_reparacion", ()), ("avanzar_paso", (1,)),
])
def test_tipos_reales_aerogenerador(metodo, args):
    m = parque.Aerogenerador("X", "DESACTIVADO", "N", 0, 10)
    esperado = CONTRATOS["Aerogenerador"][metodo][1]
    assert type(getattr(m, metodo)(*args)) is esperado


def test_tipos_reales_area():
    a = parque.Area("Zona", 1, 1)
    m = parque.Aerogenerador("X", "ACTIVO", "N", 0, 10)
    assert a.anadir_aerogenerador(m) is None
    assert type(a.contar_activos()) is int
    assert type(a.cumple_servicio()) is bool


@pytest.fixture
def cargado():
    p = parque.ParqueEolico()
    ruta = Path(__file__).resolve().parents[1] / "escenarios" / "parque_inicial.txt"
    assert p.cargar_configuracion(str(ruta)) is None
    return p


def test_objetos_cargados(cargado):
    assert cargado.areas, "La carga debe crear las áreas"
    assert all(isinstance(a, parque.Area) for a in cargado.areas)
    assert all(isinstance(m, parque.Aerogenerador) for a in cargado.areas for m in a.aerogeneradores)
    assert isinstance(cargado.buscar_aerogenerador("N1"), parque.Aerogenerador)
    assert cargado.buscar_aerogenerador("NO_EXISTE") is None


@pytest.mark.parametrize("metodo,args,tipo", [
    ("activar_aerogenerador", ("S2",), bool),
    ("desactivar_aerogenerador", ("N1",), bool),
    ("orientar_aerogenerador", ("S2", "E"), bool),
    ("reparar_aerogenerador", ("N1",), bool),
    ("tecnicos_disponibles", (), int), ("cumple_servicio", (), bool),
    ("avanzar_paso", (), list),
])
def test_tipos_reales_parque(cargado, metodo, args, tipo):
    resultado = getattr(cargado, metodo)(*args)
    assert type(resultado) is tipo
    if tipo is list:
        assert all(type(aviso) is str for aviso in resultado)
