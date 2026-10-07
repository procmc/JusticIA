"""Pruebas de T8 (spec 002, RA-02.7) del marcador `infraestructura`: la limpieza por prueba y el conteo de residuos al cerrar la sesión.

Lanzan otras corridas de `pytest` (plan, decisión 14b): como la base y la colección se llaman siempre `servia_pruebas`,
la fixture `entorno_para_hijos` (de `conftest.py`) cierra las de la sesión antes y las restaura al final. La prueba de
ejemplo (`tests/integracion/ejemplo_residuos.py`) crea una fila, un punto y un archivo y termina sin limpiar nada:
- con la limpieza real, el cierre de la hija cuenta cero residuos y sale con 0;
- sin ella (un plugin la desactiva), el cierre cuenta lo que quedó, lo nombra y la hija sale distinta de cero.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.soporte import entorno
from tests.soporte.nombres import NOMBRE_PRUEBAS

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
EJEMPLO = "tests/integracion/ejemplo_residuos.py"


def _correr_pytest_hijo(*argumentos: str, timeout: int = 300):
    """Lanza `python -m pytest ...` en otro proceso, desde la raíz del backend, con el entorno actual."""
    return subprocess.run(
        [sys.executable, "-m", "pytest", *argumentos],
        cwd=RAIZ_BACKEND, env=dict(os.environ), capture_output=True, text=True, timeout=timeout,
    )


def _carpetas_temporales():
    """Las carpetas temporales de la suite que hay ahora (la de esta sesión existe antes y después de cada hija)."""
    return sorted(p.name for p in Path(tempfile.gettempdir()).glob("servia_pruebas_*"))


def test_una_prueba_que_crea_una_fila_un_punto_y_un_archivo_no_deja_residuos_al_cerrar_la_sesion(entorno_para_hijos):
    """RA-02.7: la prueba crea los tres y termina; la limpieza de la prueba los quita y el conteo del cierre da cero."""
    carpetas_antes = _carpetas_temporales()

    hija = _correr_pytest_hijo(EJEMPLO)
    salida = hija.stdout + hija.stderr

    assert hija.returncode == 0, salida[-3000:]
    assert "Pasan: 1" in salida
    assert "Resultado: corrida correcta." in salida
    assert "Residuos de datos de prueba al cerrar la sesión: ninguno" in salida
    assert "quedaron datos de prueba sin limpiar" not in salida
    assert not entorno.base_existe(NOMBRE_PRUEBAS)  # la hija eliminó su base
    assert _carpetas_temporales() == carpetas_antes  # y su carpeta temporal: el cierre la elimina después de contar


def test_sin_la_limpieza_por_prueba_el_cierre_de_la_sesion_encuentra_los_residuos_y_falla_nombrandolos(entorno_para_hijos):
    """RA-02.7: si algo queda (aquí, porque un plugin desactiva la limpieza), la sesión falla y dice qué quedó."""
    carpetas_antes = _carpetas_temporales()

    hija = _correr_pytest_hijo("-p", "tests.infraestructura.plugin_sin_limpieza", EJEMPLO)
    salida = hija.stdout + hija.stderr

    assert hija.returncode != 0, salida[-3000:]
    assert "Pasan: 1" in salida  # la prueba en sí pasó: lo que falla es el cierre de la sesión
    assert "quedaron datos de prueba sin limpiar" in salida
    assert "corrida correcta" not in salida  # el resultado del resumen tampoco puede anunciar éxito
    assert "Resultado: corrida con problemas" in salida
    assert "T_Usuario: 1" in salida  # la fila
    assert "puntos de la colección de Qdrant: 1" in salida  # el punto
    assert "PRUEBA_archivo_del_ejemplo.txt" in salida  # el archivo
    assert not entorno.base_existe(NOMBRE_PRUEBAS)  # aun así la hija eliminó su base
    assert _carpetas_temporales() == carpetas_antes  # y la carpeta temporal con el archivo que dejó la prueba
