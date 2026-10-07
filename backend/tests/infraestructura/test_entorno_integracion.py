"""Pruebas de T5 (spec 002, RA-02.4 y RA-02.6) del marcador `infraestructura`: la colección y los servicios de la integración.

Lanzan otras corridas de `pytest`, así que solo corren con `docker compose exec backend pytest -m infraestructura`
(plan, decisión 14b): como la base y la colección se llaman siempre `servia_pruebas`, un hijo completo las
reemplaza y las elimina al terminar. Por eso cada prueba cierra la base de la sesión antes y la restaura al
final, y deja eliminada la colección de pruebas que haya creado. Solo se toca `servia_pruebas`, siempre por
el punto protegido (`proteccion.crear_coleccion` y `proteccion.eliminar_coleccion`); nunca la colección de desarrollo.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.soporte import entorno, proteccion
from tests.soporte.nombres import NOMBRE_PRUEBAS

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
DIMENSION_DE_LA_COLECCION_ANTERIOR = 8  # distinta de DIM: si la corrida no la reemplaza, sus pruebas fallan


def _correr_pytest_hijo(*argumentos: str, variables=None, timeout: int = 300):
    """Lanza `python -m pytest ...` en otro proceso, desde la raíz del backend, con el entorno actual y `variables`."""
    return subprocess.run(
        [sys.executable, "-m", "pytest", *argumentos],
        cwd=RAIZ_BACKEND, env={**os.environ, **(variables or {})}, capture_output=True, text=True, timeout=timeout,
    )


def _coleccion_existe() -> bool:
    """Consulta de solo lectura: ¿existe en Qdrant la colección de pruebas?"""
    cliente = entorno.cliente_qdrant()
    try:
        return cliente.collection_exists(NOMBRE_PRUEBAS)
    finally:
        cliente.close()


def _dimension_de_la_coleccion() -> int:
    cliente = entorno.cliente_qdrant()
    try:
        return cliente.get_collection(NOMBRE_PRUEBAS).config.params.vectors.size
    finally:
        cliente.close()


def test_con_qdrant_que_no_responde_aborta_nombrando_el_servicio_y_elimina_la_base(entorno_para_hijos):
    """RA-02.4: Qdrant caído (aquí, una dirección que no existe) detiene la integración diciendo cuál servicio no respondió.

    El hijo ya había creado la base de pruebas; el cierre de la sesión la elimina igual, y la colección no llega a crearse.
    """
    hijo = _correr_pytest_hijo(
        "-p", "tests.infraestructura.plugin_espera_corta", "-m", "integracion",
        "tests/integracion/test_coleccion_de_pruebas.py",
        variables={"QDRANT_URL": "http://qdrant-caido.invalid:6333"},
    )
    salida = hijo.stdout + hijo.stderr

    assert hijo.returncode != 0
    assert "Se aborta la suite de pruebas" in salida
    assert "Qdrant no respondió" in salida
    assert "Tika no respondió" not in salida
    assert not entorno.base_existe(NOMBRE_PRUEBAS)  # la base de pruebas se eliminó igual
    assert not _coleccion_existe()  # y la colección nunca se creó
    # M2: el resumen no anuncia éxito (con sus seis ceros) cuando la corrida se abortó, y trae el motivo.
    assert hijo.returncode == 2
    assert "corrida correcta" not in salida
    assert "la corrida se abortó" in salida
    assert re.search(r"Motivo:.*Qdrant no respondió", salida)


def test_si_no_se_recolecta_ninguna_prueba_el_resumen_no_dice_corrida_correcta(entorno_para_hijos):
    """RA-02.1 (M2): `-m marcador_inexistente` no ejecuta nada y sale con 5; el resumen lo dice en vez de «corrida correcta»."""
    hijo = _correr_pytest_hijo("-m", "marcador_que_no_existe")
    salida = hijo.stdout + hijo.stderr

    assert hijo.returncode == 5, salida[-2000:]
    assert "corrida correcta" not in salida
    assert "no se ejecutó ninguna prueba" in salida
    assert "Pasan: 0" in salida  # los seis contadores siguen apareciendo
    assert not entorno.base_existe(NOMBRE_PRUEBAS)


def test_una_corrida_de_integracion_reemplaza_la_coleccion_anterior_carga_el_modelo_una_vez_y_limpia_al_terminar(
        entorno_para_hijos, tmp_path):
    """RA-02.4, RA-02.6: la integración crea la colección (reemplazando una vieja), el modelo se carga solo al pedirlo y todo se elimina.

    - Una colección `servia_pruebas` de otro tamaño, dejada por una corrida cortada, la reemplaza la nueva (si no,
      la prueba de las 1024 dimensiones del hijo fallaría).
    - El modelo de embeddings real se carga UNA vez, durante `test_embeddings_reales`, y no en las pruebas de la
      colección ni de la API, que no lo piden.
    - Después de la corrida no quedan la base ni la colección.
    """
    proteccion.crear_coleccion(NOMBRE_PRUEBAS, entorno.cliente_qdrant, DIMENSION_DE_LA_COLECCION_ANTERIOR)
    assert _dimension_de_la_coleccion() == DIMENSION_DE_LA_COLECCION_ANTERIOR
    registro = tmp_path / "cargas_del_modelo.txt"

    hijo = _correr_pytest_hijo(
        "-p", "tests.infraestructura.plugin_contar_cargas", "-m", "integracion",
        "tests/integracion/test_coleccion_de_pruebas.py",
        "tests/integracion/test_cliente_api.py",
        "tests/integracion/test_embeddings_reales.py",
        variables={"RUTA_REGISTRO_CARGAS": str(registro)},
        timeout=600,
    )
    salida = hijo.stdout + hijo.stderr

    assert hijo.returncode == 0, salida[-3000:]
    assert re.search(r"Pasan: 7\b", salida), salida[-1500:]  # 4 de la colección, 1 de la API y 2 de los embeddings
    cargas = registro.read_text(encoding="utf-8").splitlines() if registro.exists() else []
    assert len(cargas) == 1, cargas
    assert "test_embeddings_reales.py" in cargas[0]
    assert not entorno.base_existe(NOMBRE_PRUEBAS)
    assert not _coleccion_existe()


@pytest.mark.parametrize("argumentos", [
    pytest.param(("-m", "unitaria", "tests/unitarias/test_marcadores.py"), id="solo-unitarias"),
    pytest.param(("--collect-only", "-q"), id="collect-only"),
    pytest.param(("--help",), id="help"),
])
def test_sin_pruebas_de_integracion_la_corrida_no_crea_ni_elimina_la_coleccion(entorno_para_hijos, argumentos):
    """RA-02.4: la colección es de la integración; las unitarias, `--collect-only` y `--help` no la crean ni la tocan.

    Se deja una colección de pruebas de otro tamaño: si la corrida la eliminara o la recreara, habría cambiado.
    """
    proteccion.crear_coleccion(NOMBRE_PRUEBAS, entorno.cliente_qdrant, DIMENSION_DE_LA_COLECCION_ANTERIOR)

    hijo = _correr_pytest_hijo(*argumentos)

    assert hijo.returncode == 0, (hijo.stdout + hijo.stderr)[-2000:]
    assert _coleccion_existe()
    assert _dimension_de_la_coleccion() == DIMENSION_DE_LA_COLECCION_ANTERIOR  # no se recreó
    assert not entorno.base_existe(NOMBRE_PRUEBAS)  # la base sí sigue su ciclo: se eliminó al terminar
