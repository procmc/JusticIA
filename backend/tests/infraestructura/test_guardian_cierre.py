"""Pruebas de T8 (spec 002, RA-02.6 d) del marcador `infraestructura`: el guardián de las unitarias falla al cerrarse.

Una prueba que debe fallar al cerrarse no puede dejar en rojo la suite de verdad ni marcarse `xfail` (el fallo ocurre
en el cierre de la fixture, que pytest informa como error, no como fallo esperado): por eso se comprueba con una
corrida hija (plan, decisión 10b). La hija vive en una carpeta temporal con su propio `pytest.ini` y su propio
`conftest.py`, que importa la fixture REAL `guardian_servicios` de `tests/unitarias/conftest.py`. No usa el
`conftest.py` de la raíz de `backend/`, así que no crea, migra ni elimina `servia_pruebas` ni toca la colección, y
su fallo no suma al resumen de esta corrida (aquí pasa). Todas las direcciones de la hija son `.invalid`.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.soporte import entorno
from tests.soporte.nombres import NOMBRE_PRUEBAS

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

CONFTEST_DE_LA_HIJA = """\
# Importa la fixture REAL (automática) que usan las unitarias de la suite.
from tests.unitarias.conftest import guardian_servicios  # noqa: F401
"""

PRUEBA_QUE_ATRAPA_EL_ERROR = """\
def test_el_codigo_atrapa_el_error_de_qdrant():
    try:
        from qdrant_client import QdrantClient

        QdrantClient(url="http://qdrant-hijo.invalid:6333")
    except Exception:
        pass  # como el código del sistema: sin el guardián, esta prueba pasaría
"""

PRUEBA_INOCENTE = """\
def test_no_usa_ningun_servicio():
    assert 1 + 1 == 2
"""


def _correr_hija(carpeta: Path, codigo_de_la_prueba: str):
    """Corre `pytest` sobre `carpeta` con su propio `pytest.ini`, fuera de la raíz del backend, con todo apuntando a `.invalid`."""
    (carpeta / "pytest.ini").write_text("[pytest]\naddopts = -p no:cacheprovider\n", encoding="utf-8")
    (carpeta / "conftest.py").write_text(CONFTEST_DE_LA_HIJA, encoding="utf-8")
    (carpeta / "test_hija.py").write_text(codigo_de_la_prueba, encoding="utf-8")
    entorno_hijo = {**os.environ, "PYTHONPATH": str(RAIZ_BACKEND), "QDRANT_URL": "http://qdrant-hijo.invalid:6333"}
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-c", str(carpeta / "pytest.ini"), "--rootdir", str(carpeta), str(carpeta)],
        cwd=carpeta, env=entorno_hijo, capture_output=True, text=True, timeout=180,
    )


def test_d_una_prueba_que_atrapa_el_error_de_un_servicio_real_falla_al_cerrarse_nombrandolo(tmp_path):
    """RA-02.6 (d): la hija termina con código distinto de cero, con una prueba fallida AL CERRARSE y Qdrant nombrado."""
    hija = _correr_hija(tmp_path, PRUEBA_QUE_ATRAPA_EL_ERROR)
    salida = hija.stdout + hija.stderr

    assert hija.returncode != 0, salida[-2000:]
    assert "1 passed" in salida  # el cuerpo de la prueba pasó: el error estaba atrapado
    assert "1 error" in salida  # y aun así falla: el error ocurre en el cierre de la fixture, no en el cuerpo
    assert "teardown" in salida
    assert "test_el_codigo_atrapa_el_error_de_qdrant" in salida
    assert "La prueba unitaria intentó usar servicios reales (Qdrant)" in salida

    # Sin tocar `servia_pruebas`: la hija no usó el `conftest.py` de la raíz y la base de esta sesión sigue ahí.
    assert "Base de pruebas:" not in salida
    assert entorno.base_existe(NOMBRE_PRUEBAS)


def test_d_una_prueba_que_no_usa_servicios_no_falla_al_cerrarse(tmp_path):
    """Control de la anterior: el guardián no hace fallar a una prueba que no intentó usar ningún servicio real."""
    hija = _correr_hija(tmp_path, PRUEBA_INOCENTE)
    salida = hija.stdout + hija.stderr

    assert hija.returncode == 0, salida[-2000:]
    assert "1 passed" in salida
    assert "error" not in salida and "failed" not in salida
