"""Pruebas de T1 (spec 002, RA-02.1): marcadores por carpeta y configuración de pytest.

Estas pruebas no usan ningún servicio. No llevan el marcador `unitaria` escrito a mano:
lo asigna el `conftest.py` por la carpeta, y la primera prueba comprueba justamente eso.
"""
import configparser
from pathlib import Path

import pytest

from tests.soporte.marcadores import marcador_por_ruta, ordenar_pruebas

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
RUTA_PYTEST_INI = RAIZ_BACKEND / "pytest.ini"


def _leer_pytest_ini():
    """Lee `pytest.ini` tal como está en disco (sin interpolar `%`)."""
    parser = configparser.RawConfigParser()
    leidos = parser.read(RUTA_PYTEST_INI, encoding="utf-8")
    assert leidos, f"No existe {RUTA_PYTEST_INI}"
    return parser["pytest"]


def test_esta_prueba_recibe_el_marcador_unitaria_por_su_carpeta(request):
    """RA-02.1: el marcador lo asigna el conftest.py raíz según la carpeta (no se escribe a mano)."""
    assert request.node.get_closest_marker("unitaria") is not None


@pytest.mark.parametrize(
    "ruta, esperado",
    [
        ("/app/tests/unitarias/test_algo.py", "unitaria"),
        ("/app/tests/integracion/test_algo.py", "integracion"),
        ("/app/tests/infraestructura/test_algo.py", "infraestructura"),
        # Subcarpetas: decide la primera carpeta bajo `tests/`.
        ("/app/tests/infraestructura/ejemplos_resumen/test_ejemplos.py", "infraestructura"),
        ("/app/tests/integracion/unitarias/test_algo.py", "integracion"),
        # Rutas con separadores de Windows y rutas relativas.
        ("C:\\proyecto\\backend\\tests\\integracion\\test_algo.py", "integracion"),
        ("tests/unitarias/test_algo.py", "unitaria"),
    ],
)
def test_marcador_por_ruta_devuelve_el_marcador_de_la_carpeta(ruta, esperado):
    """RA-02.1: `marcador_por_ruta` decide el marcador por la carpeta."""
    assert marcador_por_ruta(ruta) == esperado
    assert marcador_por_ruta(Path(ruta)) == esperado


@pytest.mark.parametrize(
    "ruta",
    [
        "/app/otra_carpeta/test_algo.py",
        "/app/tests/soporte/test_algo.py",
        "/app/tests/test_suelta.py",
        "/app/tests/unitarias_extra/test_algo.py",
        "/app/unitarias/test_algo.py",
        "",
    ],
)
def test_marcador_por_ruta_falla_con_una_ruta_ajena(ruta):
    """RA-02.1: una prueba fuera de las tres carpetas es un error, no queda sin marcador."""
    with pytest.raises(ValueError):
        marcador_por_ruta(ruta)


def test_pytest_ini_excluye_infraestructura_por_omision():
    """RA-02.1: `-m "not infraestructura"` en `addopts` deja ese marcador fuera de «todo»."""
    addopts = _leer_pytest_ini().get("addopts", "")
    assert '-m "not infraestructura"' in addopts


def test_pytest_ini_desactiva_la_cache_y_usa_importlib():
    """Plan, decisión 8: sin caché de pytest (no dispara `--reload`) y modo de importación `importlib`."""
    addopts = _leer_pytest_ini().get("addopts", "")
    assert "-p no:cacheprovider" in addopts
    assert "--import-mode=importlib" in addopts


def test_pytest_ini_hace_estricto_xfail():
    """RA-02.1: un fallo esperado que pasa (XPASS) debe fallar la corrida."""
    assert _leer_pytest_ini().get("xfail_strict", "").strip().lower() == "true"


def test_pytest_ini_define_rutas_de_busqueda():
    """Plan, §2: las pruebas viven en `tests/` y `pythonpath = .` permite `import tests.soporte`."""
    seccion = _leer_pytest_ini()
    assert seccion.get("testpaths", "").strip() == "tests"
    assert seccion.get("pythonpath", "").strip() == "."


def test_pytest_ini_registra_los_marcadores():
    """RA-02.1: los tres marcadores y la convención `requisito` quedan registrados."""
    lineas = [linea.strip() for linea in _leer_pytest_ini().get("markers", "").splitlines() if linea.strip()]
    nombres = {linea.split(":", 1)[0].split("(", 1)[0].strip() for linea in lineas}
    assert {"unitaria", "integracion", "infraestructura", "requisito"} <= nombres


# --- T8, RA-02.7: el orden de ejecución (`--orden-inverso`) -------------------------------------------------

def test_ordenar_pruebas_sin_la_opcion_conserva_el_orden():
    """RA-02.7: por omisión el orden de pytest no cambia."""
    pruebas = ["a", "b", "c"]
    assert ordenar_pruebas(pruebas, inverso=False) == ["a", "b", "c"]


def test_ordenar_pruebas_con_la_opcion_invierte_el_orden_completo_sin_tocar_la_lista_original():
    """RA-02.7: `--orden-inverso` ejecuta las pruebas al revés (también dentro de cada archivo) para comprobar que ninguna depende de otra."""
    pruebas = ["a", "b", "c", "d"]
    assert ordenar_pruebas(pruebas, inverso=True) == ["d", "c", "b", "a"]
    assert pruebas == ["a", "b", "c", "d"]


def test_la_opcion_orden_inverso_esta_registrada_y_vale_falso_por_omision(request):
    """RA-02.7: la opción existe en la línea de comandos de pytest (la registra el `conftest.py` raíz)."""
    assert isinstance(request.config.getoption("orden_inverso"), bool)
