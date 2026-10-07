"""Cinco pruebas de ejemplo para verificar el resumen de la suite (spec 002, RA-02.1).

Producen A PROPÓSITO cada situación que el resumen debe contar. Solo corren con
`docker compose exec backend pytest -m infraestructura` (el marcador `infraestructura` se asigna
por la carpeta y queda fuera del comando por omisión). Resultado esperado de ese comando:

    1 fallo esperado, 1 XPASS, 1 omitida, 1 error de preparación y 1 fallo

con código de salida distinto de cero. Cualquier otro resumen indica que el informe no cuenta
bien. Las pruebas de infraestructura que se sumen en otras tareas aparecen como «pasan».
No uses estas pruebas como modelo de nada más: no prueban ningún comportamiento del sistema.
"""
import pytest


@pytest.mark.xfail(reason="RA-02.1: ejemplo de fallo esperado que falla (no cuenta como fallo)", strict=True)
def test_ejemplo_fallo_esperado_que_falla():
    assert 1 == 2


@pytest.mark.xfail(reason="RA-02.1: ejemplo de fallo esperado que pasa (XPASS estricto)", strict=True)
def test_ejemplo_xpass():
    assert 1 == 1


@pytest.mark.skip(reason="RA-02.1: ejemplo de prueba omitida con su motivo")
def test_ejemplo_omitida_con_motivo():
    raise AssertionError("no debe ejecutarse")


@pytest.fixture
def preparacion_que_falla():
    raise RuntimeError("RA-02.1: ejemplo de error de preparación")


def test_ejemplo_error_de_preparacion(preparacion_que_falla):
    raise AssertionError("no debe ejecutarse: la preparación falla antes")


def test_ejemplo_fallo():
    assert "ejemplo" == "fallo", "RA-02.1: ejemplo de fallo a propósito"
