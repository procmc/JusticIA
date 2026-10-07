"""Fixtures de la integración (spec 002, RA-02.4 y RA-02.6; T5).

Las pruebas de este directorio usan el SQL Server, el Qdrant y el Tika reales del entorno, pero solo la
base y la colección `servia_pruebas`. La base la crea `pytest_configure` en toda corrida; la colección la
crea `entorno_integracion`, que es automática solo aquí: una corrida sin pruebas de integración (unitarias,
`--collect-only`, `--help`) no la crea ni la toca. Este archivo no importa `app` al cargarse (regla del
plan, decisión 3): lo hace dentro de las fixtures.
"""
import contextlib
from pathlib import Path

import pytest

from tests.soporte import entorno
from tests.soporte.proteccion import AbortoPruebas

RAIZ_BACKEND = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session", autouse=True)
def entorno_integracion():
    """Espera a Qdrant y a Tika (hasta 60 s cada uno) y crea la colección de pruebas.

    Si un servicio no responde, la corrida se detiene nombrándolo; el cierre de la sesión elimina igual
    la base de pruebas. La colección NO se elimina aquí: la elimina `entorno.cerrar` en `pytest_sessionfinish`,
    después de contar los residuos (T8), porque una fixture de sesión termina ANTES que el cierre y el conteo
    ya no vería los puntos que una prueba hubiera dejado en ella.
    """
    try:
        entorno.preparar_integracion()
    except AbortoPruebas as aborto:
        pytest.exit(str(aborto), returncode=2)
    yield


@pytest.fixture(scope="session")
def embeddings_reales():
    """El modelo de embeddings real (`multilingual-e5-large`), cargado una sola vez y solo si una prueba lo pide.

    Es el mismo que usa el sistema (`get_embeddings`), así que no hay dos copias en memoria. Devuelve el
    adaptador de LangChain del sistema, con `embed_query` y `embed_documents` síncronos. La primera
    consulta (de calentamiento) lo carga aquí, no en medio de la prueba que lo usa.
    """
    from app.embeddings.langchain_adapter import LangChainEmbeddingsAdapter

    adaptador = LangChainEmbeddingsAdapter()
    adaptador.embed_query("PRUEBA calentamiento del modelo")
    return adaptador


@pytest.fixture(scope="session")
def cliente_api():
    """Cliente de prueba de la API (`TestClient`) SIN ejecutar el arranque de `main.py`, que cargaría los embeddings.

    Solo `with TestClient(...)` ejecuta el arranque; aquí no se usa. `main.py` monta la carpeta relativa
    `uploads` al importarse, así que se importa parado en la raíz del backend: nunca crea otra `uploads`.
    """
    from fastapi.testclient import TestClient

    with contextlib.chdir(RAIZ_BACKEND):
        import main

    return TestClient(main.app)
