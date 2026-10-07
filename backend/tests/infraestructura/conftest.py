"""Fixtures compartidas de las pruebas del marcador `infraestructura` (spec 002; plan, decisión 14b).

Las pruebas de esta carpeta que lanzan una corrida hija completa de `pytest` comparten el nombre de la base y de la
colección de pruebas con la sesión que las lanza: el hijo las reemplaza y las elimina al terminar. Por eso la
fixture `entorno_para_hijos` entrega el control de ambas a la prueba y las restaura al final. Este archivo no
importa `app` al cargarse (regla del plan, decisión 3).
"""
import pytest

from tests.soporte import entorno, proteccion
from tests.soporte.nombres import NOMBRE_PRUEBAS


@pytest.fixture
def entorno_para_hijos():
    """Entrega a la prueba el control de la base y de la colección de pruebas; las deja como estaban al terminar.

    La base de la sesión se cierra antes (el hijo usa el mismo nombre) y se restaura al final; la colección de
    pruebas no existe al empezar y se elimina al terminar, aunque la prueba falle.
    """
    entorno.cerrar()
    assert not entorno.base_existe(NOMBRE_PRUEBAS)
    proteccion.eliminar_coleccion(NOMBRE_PRUEBAS, entorno.cliente_qdrant)
    yield
    proteccion.eliminar_coleccion(NOMBRE_PRUEBAS, entorno.cliente_qdrant)
    if not entorno.base_existe(NOMBRE_PRUEBAS):
        entorno.preparar()
