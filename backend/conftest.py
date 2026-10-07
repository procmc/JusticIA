"""Raíz de la suite de pruebas del backend (spec 002).

Solo orquesta; la lógica vive en `tests/soporte/`. Regla del plan: este archivo (y todo
`conftest.py`) NO importa nada de `app` al cargarse, porque `database.py` se conecta al importarse.
Fija el entorno de la suite, simula Redis y crea y migra la base de pruebas antes de importar nada
de `app` que se conecte (`pytest_configure`); la elimina al terminar la sesión (`pytest_sessionfinish`,
con `pytest_unconfigure` como respaldo). Además asigna el marcador de cada prueba por su carpeta y
publica el resumen en español (RA-02.1). La colección de Qdrant de pruebas la crea la fixture
`entorno_integracion` (`tests/integracion/conftest.py`) y la elimina `entorno.cerrar`. Al cerrar la sesión cuenta los
residuos de datos de prueba ANTES de eliminar la colección, la carpeta temporal y la base, y falla la corrida si
quedó algo (RA-02.7); la opción `--orden-inverso` ejecuta las pruebas al revés para comprobar que son independientes.
"""
import sys

import pytest

from tests.soporte import configuracion, entorno
from tests.soporte.marcadores import marcador_por_ruta, ordenar_pruebas
from tests.soporte.proteccion import AbortoPruebas
from tests.soporte.resumen import calcular_resumen, codigo_salida, texto_resumen

# Fixtures de las piezas simuladas (Celery inmediato, carpeta temporal de archivos...) y de los datos de prueba
# (usuarios `PRUEBA`, limpieza automática de cada prueba).
pytest_plugins = ["tests.soporte.simulados", "tests.soporte.datos"]


def pytest_addoption(parser):
    """`--orden-inverso`: ejecuta las pruebas al revés. Una prueba que dependa de otra falla (RA-02.7)."""
    parser.addoption(
        "--orden-inverso", action="store_true", default=False,
        help="Ejecuta las pruebas en orden inverso (comprueba que ninguna depende de lo que dejó otra).",
    )


def pytest_configure(config):
    """Fija el entorno propio de la suite, simula Redis y prepara la base de pruebas (RA-02.2, RA-02.4, RA-02.5).

    `database.py` se conecta al importarse y `session_store.py` hace `ping()` a Redis al importarse:
    por eso esto va aquí, antes de recolectar, y la base de pruebas ya existe cuando `preparar()` lo
    importa. Si algo no es seguro, aborta con un mensaje en español y elimina lo que alcanzó a crear.
    """
    from tests.soporte import simulados  # ya cargado como plugin; aquí solo se usa

    try:
        configuracion.fijar_entorno_de_pruebas()
        simulados.instalar_redis_simulado()
        entorno.preparar()
    except AbortoPruebas as aborto:
        _cerrar_tras_abortar()
        pytest.exit(str(aborto), returncode=2)
    except Exception as error:  # un fallo de preparación inesperado: igual se limpia y se detiene la corrida
        _cerrar_tras_abortar()
        pytest.exit(
            "Se aborta la suite de pruebas: error inesperado al preparar el entorno "
            f"({type(error).__name__}). Revise `docker compose logs sqlserver` y la configuración.",
            returncode=2,
        )


def _cerrar_tras_abortar() -> None:
    """Elimina la base de pruebas que alcanzó a crearse antes del aborto; no oculta el motivo del aborto."""
    try:
        entorno.cerrar()
    except Exception as error:
        sys.stderr.write(f"No se pudo eliminar la base o la colección de pruebas tras abortar ({type(error).__name__}).\n")


def pytest_report_header(config):
    """Encabezado de la corrida: qué base de pruebas se creó y en qué versión de las migraciones quedó."""
    lineas = []
    linea = entorno.encabezado()
    if linea:
        lineas.append(linea)
    if config.getoption("orden_inverso"):
        lineas.append("Orden de las pruebas: inverso (--orden-inverso)")
    return lineas


def pytest_collection_modifyitems(config, items):
    """Marca cada prueba con `unitaria`, `integracion` o `infraestructura` según su carpeta y, con `--orden-inverso`, las invierte."""
    for item in items:
        item.add_marker(getattr(pytest.mark, marcador_por_ruta(item.path)))
    items[:] = ordenar_pruebas(items, config.getoption("orden_inverso"))


def _estadisticas(config):
    reportero = config.pluginmanager.get_plugin("terminalreporter")
    return reportero.stats if reportero is not None else {}


# Por qué se detuvo la corrida (`pytest.exit` desde una fixture, p. ej. Qdrant o Tika caídos, o una interrupción).
_motivo_del_aborto = {"texto": None}


def pytest_keyboard_interrupt(excinfo):
    """Guarda el motivo de la detención para que el resumen lo diga (RA-02.1)."""
    motivo = getattr(excinfo.value, "msg", None) or str(excinfo.value) or "interrumpida por el usuario"
    _motivo_del_aborto["texto"] = str(motivo).strip()


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Imprime el resumen en español con los seis contadores al terminar cada corrida.

    Recibe el código de salida con el que pytest cierra la corrida: si no es 0 ni 1 (nada recolectado,
    aborto, interrupción, error interno o de uso), el resumen no dice «corrida correcta» (RA-02.1).
    """
    if config.option.collectonly:
        return
    from tests.soporte import datos  # ya cargado como plugin

    terminalreporter.write_sep("=", "Resumen de la suite de pruebas")
    terminalreporter.write_line(
        texto_resumen(
            calcular_resumen(terminalreporter.stats), exitstatus, _motivo_del_aborto["texto"],
            residuos=datos.hay_problema_de_residuos(),
        )
    )
    for linea in datos.lineas_de_residuos():
        terminalreporter.write_line(linea)


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """Fija el código de salida y elimina la colección y la base de pruebas, haya o no pruebas que fallen (RA-02.4).

    El código de salida es éxito solo sin fallos, XPASS ni errores de preparación. Solo corrige las
    corridas que ejecutaron pruebas (0 o 1): «nada recolectado», interrupciones y errores de uso
    conservan su código de pytest. Las omitidas no hacen fallar la corrida. Si la base o la colección de
    pruebas no se puede eliminar, la corrida falla y lo dice: algo huérfano no debe pasar inadvertido.

    ANTES de eliminar nada cuenta los residuos de datos de prueba (filas `PRUEBA`, puntos, archivos y claves de Redis
    simulado) y compara los catálogos de las migraciones; si quedó algo, o el conteo mismo falla, la corrida falla y
    el resumen lo nombra (RA-02.7). Después elimina la colección, la base y la carpeta temporal.
    """
    from tests.soporte import datos, simulados  # ya cargados como plugins

    if exitstatus in (pytest.ExitCode.OK, pytest.ExitCode.TESTS_FAILED):
        session.exitstatus = codigo_salida(calcular_resumen(_estadisticas(session.config)))
    problema = False
    try:
        residuos = datos.contar_residuos_de_la_sesion()
        problema = residuos is not None and residuos.hay
    except Exception as error:
        sys.stderr.write("\nNo se pudo contar los residuos de datos de prueba (" + type(error).__name__ + ").\n")
        problema = True
    try:
        entorno.cerrar()
    except Exception as error:
        sys.stderr.write(
            f"\nNo se pudo eliminar la base o la colección de pruebas al terminar ({type(error).__name__}). "
            "La siguiente corrida las reemplazará.\n"
        )
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
    finally:
        simulados.eliminar_carpeta_temporal()
    if problema and session.exitstatus == pytest.ExitCode.OK:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_unconfigure(config):
    """Respaldo: si la corrida terminó sin pasar por `pytest_sessionfinish` (p. ej. `--markers`), elimina la base."""
    try:
        entorno.cerrar()
    except Exception as error:
        sys.stderr.write(f"No se pudo eliminar la base o la colección de pruebas ({type(error).__name__}).\n")
