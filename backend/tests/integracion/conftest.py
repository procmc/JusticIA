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


@pytest.fixture
def iniciar_sesion(cliente_api):
    """Devuelve una función que inicia sesión con un usuario de prueba y entrega sus cabeceras con el token (spec 003a, T3).

    Se usa así: `cabeceras = iniciar_sesion(administrador)` y luego `cliente_api.get(ruta, headers=cabeceras)`. Entra por
    `POST /auth/login`, como lo haría el navegador, así que el token es el que firma el propio sistema. La contraseña de
    la prueba nunca se escribe en ningún mensaje: si el inicio de sesión falla, el error solo dice el código recibido.
    """

    def _iniciar(usuario) -> dict:
        respuesta = cliente_api.post("/auth/login", json={"email": usuario.correo, "password": usuario.contrasena})
        assert respuesta.status_code == 200, f"No se pudo iniciar sesión con el usuario de prueba (código {respuesta.status_code})."
        return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}

    return _iniciar


@pytest.fixture
def llamar_asgi(cliente_api):
    """Devuelve una función que llama a la aplicación real por ASGI dentro del bucle de la prueba (spec 003b, T7).

    Se usa dentro de un `asyncio.run`: `llamada = llamar_asgi("POST", ruta, json={...}, cabeceras={...})` devuelve enseguida
    una `Llamada` con `respuesta` (futuro que se resuelve al llegar el cuerpo) y `tarea` (la aplicación completa, con sus
    tareas posteriores). Así la prueba ve la respuesta MIENTRAS el envío del correo sigue pendiente, cosa que `cliente_api`
    no permite: espera a que la aplicación termine. Es la misma aplicación que usa `cliente_api`, sin su arranque.
    """
    from tests.soporte import asgi

    def _llamar(metodo, ruta, json=None, cabeceras=None):
        return asgi.llamar(cliente_api.app, metodo, ruta, json=json, cabeceras=cabeceras)

    return _llamar
