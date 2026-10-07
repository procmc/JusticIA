"""Guardianes de las pruebas unitarias (spec 002, RA-02.6).

Una prueba unitaria no usa SQL Server, Qdrant, Tika ni el modelo de embeddings reales. Esta fixture
automática los bloquea (la prueba falla nombrando el servicio, aunque el código del sistema atrape
la excepción) y deja el modelo de embeddings en un falso de tamaño `DIM`. Este archivo no importa
`app` al cargarse (regla del plan, decisión 3).
"""
import pytest

from tests.soporte import entorno, simulados


@pytest.fixture(autouse=True)
def guardian_servicios():
    """Instala los guardianes antes de cada prueba unitaria y los quita al terminar.

    Si el código intentó usar un servicio real y la prueba no lo esperaba (`reconocer`), la prueba
    falla al cerrarse aunque alguien haya atrapado la excepción.
    """
    guardian = simulados.instalar_guardianes()
    try:
        yield guardian
    finally:
        guardian.desinstalar()
    guardian.exigir_sin_intentos()


@pytest.fixture(autouse=True)
def sin_la_coleccion_de_la_sesion(monkeypatch):
    """Las unitarias no ven la colección de pruebas que la integración creó para la sesión.

    En una corrida completa la fixture `entorno_integracion` (de sesión) sigue activa mientras corren las
    unitarias. Sin esto, una unitaria que llame a `entorno.cerrar()` intentaría eliminar la colección real
    por Qdrant y lo frenaría el guardián. Al terminar cada prueba el estado de la sesión se restaura.
    """
    monkeypatch.setitem(entorno._estado, "coleccion_creada", False)
