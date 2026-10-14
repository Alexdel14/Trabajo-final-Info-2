"""Comprobaciones básicas de separación de consola y datos por instancia."""
import ast
import inspect
from pathlib import Path
import parque


def test_sin_input_en_clases():
    for cls in (parque.Aerogenerador, parque.Area, parque.ParqueEolico):
        arbol = ast.parse(inspect.getsource(cls))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Call):
                fn = nodo.func
                es_input = isinstance(fn, ast.Name) and fn.id == "input"
                es_input |= isinstance(fn, ast.Attribute) and fn.attr == "input"
                assert not es_input, f"No uses input() dentro de {cls.__name__}"


def test_listas_independientes_entre_areas():
    a = parque.Area("A", 1, 1)
    b = parque.Area("B", 1, 1)
    assert isinstance(a.aerogeneradores, list)
    assert isinstance(b.aerogeneradores, list)
    assert a.aerogeneradores is not b.aerogeneradores
    a.anadir_aerogenerador(parque.Aerogenerador("X", "ACTIVO", "N", 0, 5))
    assert b.aerogeneradores == []


def test_parques_independientes():
    p, q = parque.ParqueEolico(), parque.ParqueEolico()
    assert isinstance(p.areas, list) and isinstance(q.areas, list)
    assert p.areas is not q.areas
    ruta = Path(__file__).resolve().parents[1] / "escenarios" / "parque_inicial.txt"
    p.cargar_configuracion(str(ruta))
    assert q.areas == []
    q.cargar_configuracion(str(ruta))
    assert p.buscar_aerogenerador("N1") is not q.buscar_aerogenerador("N1")
