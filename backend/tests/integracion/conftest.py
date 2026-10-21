"""Fixtures de la integración (spec 002, RA-02.4 y RA-02.6; T5).

Las pruebas de este directorio usan el SQL Server, el Qdrant y el Tika reales del entorno, pero solo la
base y la colección `servia_pruebas`. La base la crea `pytest_configure` en toda corrida; la colección la
crea `entorno_integracion`, que es automática solo aquí: una corrida sin pruebas de integración (unitarias,
`--collect-only`, `--help`) no la crea ni la toca. Este archivo no importa `app` al cargarse (regla del
plan, decisión 3): lo hace dentro de las fixtures.
"""
import contextlib
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import text

from tests.soporte import entorno
from tests.soporte.datos import ROL_USUARIO_GUBERNAMENTAL, UsuarioPrueba, crear_usuario
from tests.soporte.flujos import cargar, crear_notebook, documento_de_prueba, exigir_estado, id_del_documento
from tests.soporte.nombres import PREFIJO_DATOS
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


# --- Apoyos compartidos por las pruebas de notebooks y de aislamiento (spec 004b, T2) -----------------------------------
# Salen de `test_red_notebooks.py` sin cambiar su comportamiento, para que las pruebas del aislamiento usen el mismo escenario.

RESPUESTA_SIMULADA = "Respuesta simulada de PRUEBA para el chat del notebook."


@pytest.fixture
def sesion(iniciar_sesion, usuario_gubernamental):
    return iniciar_sesion(usuario_gubernamental)


def _consultar(consulta: str, parametros: dict = None) -> list:
    from app.db.database import engine

    with engine.connect() as conexion:
        return [tuple(fila) for fila in conexion.execute(text(consulta), parametros or {}).fetchall()]


def _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento, notebook: dict, documento=None):
    """Sube un documento de prueba (el dado, o uno nuevo) a la clave interna del notebook, lo procesa y devuelve `(documento, id)`."""
    documento = documento or documento_de_prueba()
    respuesta = cargar(cliente_api, sesion, notebook["clave_interna"], [(documento.nombre, documento.contenido)])
    assert respuesta.status_code == 200, f"la carga respondió {respuesta.status_code}"
    id_tarea = respuesta.json()["task_ids"][0]
    resultados = procesamiento.procesar()
    assert resultados[id_tarea].state == "SUCCESS", f"la tarea {id_tarea} terminó en {resultados[id_tarea].state}"
    id_documento = id_del_documento(documento.nombre)
    assert id_documento is not None
    exigir_estado(id_documento, "Procesado")
    return documento, id_documento


def _pregunta_sobre(documento) -> str:
    """Una pregunta que nombra al documento por su número pero sin repetir su frase distintiva ni su nombre de archivo, para
    comprobar que la frase y el nombre llegaron al modelo desde el contexto y no desde la pregunta."""
    sufijo = documento.nombre[len(PREFIJO_DATOS) + 1:-len(".txt")]
    return f"¿Qué dice el documento inventado número {sufijo} sobre la quebrada ficticia {sufijo}?"


def _consultar_chat(cliente_api, cabeceras, pregunta: str, **alcance):
    """Consulta el chat (`notebook_id`, `expediente_number` o general si no hay alcance); la sesión es de un usuario `PRUEBA`."""
    cuerpo = {"query": pregunta, "session_id": f"session_{PREFIJO_DATOS}chat_{uuid.uuid4().hex[:8]}", **alcance}
    return cliente_api.post("/rag/consulta-con-historial-stream", json=cuerpo, headers=cabeceras)


def _todo_lo_que_recibio_el_modelo(ollama_simulado, *preguntas: str) -> str:
    """Todo lo que recibió el modelo simulado en la prueba, sin el texto de las preguntas hechas (puede no haber recibido nada)."""
    recibido = "\n".join(ollama_simulado.preguntas)
    for pregunta in preguntas:
        recibido = recibido.replace(pregunta, "")
    return recibido


@dataclass
class Ajeno:
    """Un dueño con un notebook que tiene un documento Procesado y una conversación, y otro usuario sin relación con él."""

    dueno: UsuarioPrueba
    cabeceras_dueno: dict
    otro: UsuarioPrueba
    cabeceras_otro: dict
    notebook: dict
    documento: object
    id_documento: int
    id_inexistente: int
    sesion_chat: str


@pytest.fixture
def ajeno_ligero(cliente_api, sesion, usuario_gubernamental, iniciar_sesion, registro_de_datos):
    """Escenario de recursos ajenos SIN documento: el dueño con su notebook vacío y una conversación, y otro usuario. Para las
    pruebas que solo necesitan un notebook ajeno (no su contenido), sin subir ni procesar nada (`documento` e `id_documento`
    quedan en `None`). La conversación del dueño se crea con el formato de sesión de la interfaz (`session_<correo>_<hora>`) y
    se quita al terminar, porque su usuario es un correo y no un identificador `PRUEBA`."""
    from app.services.RAG.session_store import conversation_store

    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook propio", registro_de_datos)
    otro = crear_usuario(ROL_USUARIO_GUBERNAMENTAL, registro_de_datos)
    id_inexistente = int(_consultar("SELECT COALESCE(MAX(CN_Id_notebook), 0) + 1000000 FROM T_Notebook")[0][0])
    sesion_chat = f"session_{usuario_gubernamental.correo}_{uuid.uuid4().hex[:8]}"
    conversation_store.get_session_history(sesion_chat).add_user_message(f"{PREFIJO_DATOS} pregunta del dueño")
    try:
        yield Ajeno(
            dueno=usuario_gubernamental, cabeceras_dueno=sesion, otro=otro, cabeceras_otro=iniciar_sesion(otro),
            notebook=notebook, documento=None, id_documento=None, id_inexistente=id_inexistente,
            sesion_chat=sesion_chat,
        )
    finally:
        conversation_store.delete_session(sesion_chat, usuario_gubernamental.correo)
        for resto in (sesion_chat, f"session_{otro.correo}_{PREFIJO_DATOS}inexistente"):
            conversation_store._store.pop(resto, None)
            conversation_store._metadata.pop(resto, None)


@pytest.fixture
def ajeno(ajeno_ligero, cliente_api, procesamiento_en_prueba):
    """Escenario de recursos ajenos: el de `ajeno_ligero` más un documento Procesado en el notebook del dueño."""
    ajeno_ligero.documento, ajeno_ligero.id_documento = _documento_procesado_en_el_notebook(
        cliente_api, ajeno_ligero.cabeceras_dueno, procesamiento_en_prueba, ajeno_ligero.notebook)
    return ajeno_ligero
