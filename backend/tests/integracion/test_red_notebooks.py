"""Red de seguridad de NotebookServIA (spec 004, T11; RF-17.1, RF-17.2, RF-18.1).

Usa la API real con Usuarios Gubernamentales `PRUEBA`, SQL Server, Tika y Qdrant reales del entorno aislado (base y colección
`servia_pruebas`), el Redis simulado y HTR, audio y Ollama simulados (RNF-09.1):
- RF-17.1: crear un notebook (clave interna propia, primero en la lista de su dueño y ausente de la de otro usuario) y el
  rechazo 4xx en español, sin efectos, de un nombre vacío o de solo espacios.
- RF-17.2: subir a la clave interna del notebook, procesar y verlo en la lista del notebook como Procesado, con sus
  fragmentos guardados bajo esa clave.
- RF-18.1: ver el original de un documento Procesado, byte a byte y en línea; uno no Procesado da un error de datos.

Spec 004, T12 (RF-11.3, RF-17.3, RF-17.4, RNF-07.6), con dos Usuarios Gubernamentales `PRUEBA` (dueño y otro) y el Ollama
simulado: lo que se comprueba es lo que RECIBE el modelo y lo que responde la API, no el texto de una respuesta real.
- RF-11.3: el chat del notebook propio envía al modelo solo fragmentos de ese notebook; de un notebook ajeno o inexistente,
  ninguno.
- RF-17.3: el documento del notebook de otro no se entrega en el chat (general y por tema), en temas similares ni en descargas.
- RF-17.4: subir con la clave de un notebook ajeno o inexistente da 404 y no deja ningún efecto.
- RNF-07.6: pedir un recurso ajeno (documentos, chat, conversaciones) da el mismo 404 que uno inexistente y no lo modifica.

Spec 004, T13 (RF-19.1, RF-19.2): quitar documentos de un notebook, el error de una eliminación y el reintento.
Los datos son inventados (prefijo `PRUEBA`) y se limpian solos.
"""
import os
import uuid
from dataclasses import dataclass

import pytest
from sqlalchemy import text

from tests.soporte import entorno
from tests.soporte.datos import ROL_USUARIO_GUBERNAMENTAL, UsuarioPrueba, crear_usuario
from tests.soporte.flujos import (
    cargar, contar_puntos, contexto_enviado, crear_notebook, documento_de_prueba, exigir_estado, foto_de_efectos,
    id_del_documento, tema_heredado,
)
from tests.soporte.nombres import PREFIJO_DATOS

# La tarea de ingesta consulta su estado en Celery; en modo inmediato Celery avisa que ese resultado no se guarda en el
# backend. Es un aviso del propio sistema en un modo que nunca usa en producción (como en `test_red_ingesta.py`).
pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")


@pytest.fixture
def sesion(iniciar_sesion, usuario_gubernamental):
    return iniciar_sesion(usuario_gubernamental)


def _consultar(consulta: str, parametros: dict = None) -> list:
    from app.db.database import engine

    with engine.connect() as conexion:
        return [tuple(fila) for fila in conexion.execute(text(consulta), parametros or {}).fetchall()]


def _puntos_del_tema(tema: str) -> list:
    """Los puntos de Qdrant cuyo `metadata.numero_expediente` es el tema, con su carga útil."""
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    cliente = entorno.cliente_qdrant()
    try:
        filtro = Filter(must=[FieldCondition(key="metadata.numero_expediente", match=MatchValue(value=tema))])
        puntos, _ = cliente.scroll(collection_name=os.environ["QDRANT_COLLECTION_NAME"], scroll_filter=filtro, limit=1000,
                                   with_payload=True)
        return list(puntos)
    finally:
        cliente.close()


def _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento, notebook: dict):
    """Sube un documento de prueba a la clave interna del notebook, lo procesa y devuelve `(documento, id)`."""
    documento = documento_de_prueba()
    respuesta = cargar(cliente_api, sesion, notebook["clave_interna"], [(documento.nombre, documento.contenido)])
    assert respuesta.status_code == 200, f"la carga respondió {respuesta.status_code}"
    id_tarea = respuesta.json()["task_ids"][0]
    resultados = procesamiento.procesar()
    assert resultados[id_tarea].state == "SUCCESS", f"la tarea {id_tarea} terminó en {resultados[id_tarea].state}"
    id_documento = id_del_documento(documento.nombre)
    assert id_documento is not None
    exigir_estado(id_documento, "Procesado")
    return documento, id_documento


# --- RF-17.1: crear y listar --------------------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-17.1")
def test_crear_y_orden_propio(cliente_api, sesion, usuario_gubernamental, iniciar_sesion, registro_de_datos):
    """RF-17.1: cada notebook se crea a nombre de su dueño, con una clave interna propia `NB-<id>`; la lista del dueño trae
    primero el más reciente, y los notebooks de un usuario no aparecen en la lista de otro."""
    primero = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook primero", registro_de_datos)
    segundo = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook segundo", registro_de_datos)

    assert primero["id"] != segundo["id"]
    assert primero["clave_interna"] == f"NB-{primero['id']}" and segundo["clave_interna"] == f"NB-{segundo['id']}"
    assert primero["nombre"] == f"{PREFIJO_DATOS} notebook primero"
    # A nombre de su dueño, en la base.
    duenos = _consultar("SELECT CN_Id_notebook, CN_Id_usuario FROM T_Notebook WHERE CN_Id_notebook IN (:a, :b)",
                        {"a": primero["id"], "b": segundo["id"]})
    assert sorted(duenos) == sorted([(primero["id"], usuario_gubernamental.cedula), (segundo["id"], usuario_gubernamental.cedula)])

    # Otro usuario con su propio notebook.
    otro = crear_usuario(ROL_USUARIO_GUBERNAMENTAL, registro_de_datos)
    sesion_de_otro = iniciar_sesion(otro)
    ajeno = crear_notebook(cliente_api, sesion_de_otro, f"{PREFIJO_DATOS} notebook de otro", registro_de_datos)

    mia = cliente_api.get("/notebooks", headers=sesion)
    assert mia.status_code == 200
    ids = [n["id"] for n in mia.json()]
    assert ids == [segundo["id"], primero["id"]], "la lista del dueño debe traer primero el más reciente y solo los suyos"
    de_otro = cliente_api.get("/notebooks", headers=sesion_de_otro)
    assert de_otro.status_code == 200
    assert [n["id"] for n in de_otro.json()] == [ajeno["id"]]


@pytest.mark.requisito("RF-17.1")
@pytest.mark.parametrize("nombre", ["", " ", "   ", "\t \n"])
def test_nombre_vacio_o_espacios(cliente_api, sesion, correo_simulado, nombre):
    """RF-17.1: un nombre vacío o de solo espacios no crea nada y responde 4xx (no 5xx) con un mensaje en español; no deja
    ningún efecto (ni notebook, ni fila de bitácora, ni archivo)."""
    antes = foto_de_efectos(correo_simulado)

    respuesta = cliente_api.post("/notebooks", json={"nombre": nombre}, headers=sesion)

    assert 400 <= respuesta.status_code < 500, f"se esperaba un 4xx y se recibió {respuesta.status_code}"
    detalle = respuesta.json().get("detail")
    assert isinstance(detalle, str) and "nombre" in detalle.lower(), f"se esperaba un mensaje en español: {detalle!r}"
    assert foto_de_efectos(correo_simulado) == antes


# --- RF-17.2: subir al notebook y llegar a Procesado --------------------------------------------------------------------------

@pytest.mark.requisito("RF-17.2")
def test_subir_al_notebook_procesado(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba):
    """RF-17.2: un documento subido con la clave interna del notebook se procesa como cualquier carga: queda en la lista del
    notebook con su nombre y el estado Procesado, y sus fragmentos en Qdrant llevan la clave en `numero_expediente`."""
    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook con carga", registro_de_datos)
    documento, id_documento = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook)

    lista = cliente_api.get(f"/notebooks/{notebook['id']}/documentos", headers=sesion)
    assert lista.status_code == 200
    assert lista.json() == [{"id": id_documento, "nombre_archivo": documento.nombre, "estado": "Procesado"}]

    puntos = _puntos_del_tema(notebook["clave_interna"])
    assert len(puntos) > 0 and len(puntos) == contar_puntos(notebook["clave_interna"])
    for punto in puntos:
        metadatos = punto.payload["metadata"]
        assert metadatos["numero_expediente"] == notebook["clave_interna"]
        assert metadatos["nombre_archivo"] == documento.nombre
        assert metadatos["id_documento"] == id_documento


# --- RF-18.1: previsualizar el original ---------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-18.1")
def test_previsualizar_en_linea(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba):
    """RF-18.1: el original de un documento Procesado se entrega tal cual (byte a byte), con tipo de contenido acorde y sin
    forzar la descarga (sin `Content-Disposition: attachment`)."""
    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook a previsualizar", registro_de_datos)
    documento, id_documento = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook)

    respuesta = cliente_api.get(f"/notebooks/{notebook['id']}/documentos/{id_documento}/archivo", headers=sesion)

    assert respuesta.status_code == 200
    assert respuesta.content == documento.contenido
    assert respuesta.headers["content-type"].split(";")[0] == "text/plain"
    assert "attachment" not in respuesta.headers.get("content-disposition", "").lower()


@pytest.mark.requisito("RF-18.1")
def test_previsualizar_no_procesado(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba):
    """RF-18.1: si el documento no está Procesado, la respuesta es un error de datos (4xx) con mensaje en español y sin el
    cuerpo del archivo. El documento Pendiente lo crea la prueba: sube uno, lo procesa y devuelve su fila a Pendiente."""
    from app.db.database import engine

    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook sin procesar", registro_de_datos)
    documento, id_documento = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook)
    with engine.begin() as conexion:
        conexion.execute(
            text("UPDATE T_Documento SET CN_Id_estado = (SELECT CN_Id_estado FROM T_Estado_procesamiento "
                 "WHERE CT_Nombre_estado = 'Pendiente') WHERE CN_Id_documento = :d"), {"d": id_documento})
    exigir_estado(id_documento, "Pendiente")

    respuesta = cliente_api.get(f"/notebooks/{notebook['id']}/documentos/{id_documento}/archivo", headers=sesion)

    assert 400 <= respuesta.status_code < 500, f"se esperaba un 4xx y se recibió {respuesta.status_code}"
    assert respuesta.headers["content-type"].split(";")[0] == "application/json"
    assert documento.contenido not in respuesta.content
    detalle = respuesta.json().get("detail")
    assert isinstance(detalle, str) and detalle, f"se esperaba un mensaje en español: {detalle!r}"


# --- T12: apoyos --------------------------------------------------------------------------------------------------------------

RESPUESTA_SIMULADA = "Respuesta simulada de PRUEBA para el chat del notebook."


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
def ajeno(cliente_api, sesion, usuario_gubernamental, iniciar_sesion, registro_de_datos, procesamiento_en_prueba):
    """Escenario de recursos ajenos. La conversación del dueño se crea con el formato de sesión de la interfaz
    (`session_<correo>_<hora>`) y se quita al terminar, porque su usuario es un correo y no un identificador `PRUEBA`."""
    from app.services.RAG.session_store import conversation_store

    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook propio", registro_de_datos)
    documento, id_documento = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook)
    otro = crear_usuario(ROL_USUARIO_GUBERNAMENTAL, registro_de_datos)
    id_inexistente = int(_consultar("SELECT COALESCE(MAX(CN_Id_notebook), 0) + 1000000 FROM T_Notebook")[0][0])
    sesion_chat = f"session_{usuario_gubernamental.correo}_{uuid.uuid4().hex[:8]}"
    conversation_store.get_session_history(sesion_chat).add_user_message(f"{PREFIJO_DATOS} pregunta del dueño")
    try:
        yield Ajeno(
            dueno=usuario_gubernamental, cabeceras_dueno=sesion, otro=otro, cabeceras_otro=iniciar_sesion(otro),
            notebook=notebook, documento=documento, id_documento=id_documento, id_inexistente=id_inexistente,
            sesion_chat=sesion_chat,
        )
    finally:
        conversation_store.delete_session(sesion_chat, usuario_gubernamental.correo)
        for resto in (sesion_chat, f"session_{otro.correo}_{PREFIJO_DATOS}inexistente"):
            conversation_store._store.pop(resto, None)
            conversation_store._metadata.pop(resto, None)


# --- RF-11.3: el chat del notebook ------------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-11.3")
def test_chat_solo_del_notebook(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    """RF-11.3: en el chat de su notebook, el modelo recibe solo fragmentos de ese notebook (frase y nombre de archivo), nunca
    de otro notebook del mismo usuario ni de un tema general, aunque la pregunta nombre el documento de ese otro. Control: en
    el chat general sí se recupera el del otro notebook, así que la prueba distingue un chat acotado de uno general."""
    nb_1 = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook uno", registro_de_datos)
    nb_2 = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook dos", registro_de_datos)
    doc_1, _ = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, nb_1)
    doc_2, _ = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, nb_2)
    # El tema general reutiliza el apoyo: un dict con la clave basta para subir y procesar.
    doc_general, _ = _documento_procesado_en_el_notebook(
        cliente_api, sesion, procesamiento_en_prueba, {"clave_interna": tema_heredado(registro_de_datos)})
    ollama_simulado.responder(RESPUESTA_SIMULADA)

    pregunta_2 = _pregunta_sobre(doc_2)
    assert _consultar_chat(cliente_api, sesion, pregunta_2).status_code == 200
    assert doc_2.frase in contexto_enviado(ollama_simulado).replace(pregunta_2, ""), "control: el chat general no lo recuperó"

    assert _consultar_chat(cliente_api, sesion, pregunta_2, notebook_id=str(nb_1["id"])).status_code == 200
    contexto = contexto_enviado(ollama_simulado).replace(pregunta_2, "")
    assert doc_1.frase in contexto and doc_1.nombre in contexto, "no llegó el documento del notebook consultado"
    for otro in (doc_2, doc_general):
        assert otro.frase not in contexto and otro.nombre not in contexto, "llegó un fragmento de fuera del notebook"

    pregunta_1 = _pregunta_sobre(doc_1)
    assert _consultar_chat(cliente_api, sesion, pregunta_1, notebook_id=str(nb_2["id"])).status_code == 200
    contexto = contexto_enviado(ollama_simulado).replace(pregunta_1, "")
    assert doc_2.frase in contexto and doc_2.nombre in contexto
    for otro in (doc_1, doc_general):
        assert otro.frase not in contexto and otro.nombre not in contexto, "llegó un fragmento de fuera del notebook"


@pytest.mark.requisito("RF-11.3")
@pytest.mark.xfail(strict=True, reason="RF-11.3 · notebooks")
@pytest.mark.parametrize("caso", ["ajeno", "inexistente"])
def test_notebook_ajeno_o_inexistente_sin_contenido(cliente_api, ajeno, ollama_simulado, caso):
    """RF-11.3: si el notebook consultado es ajeno o no existe, el modelo no recibe ninguna frase ni nombre de archivo de
    ninguna parte, aunque la pregunta nombre el documento del dueño. Hoy `_consulta_notebook_con_historial` cae al chat
    general (mismo criterio que el tema con formato inválido) y ese recupera el documento del dueño."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    id_notebook = ajeno.notebook["id"] if caso == "ajeno" else ajeno.id_inexistente
    pregunta = _pregunta_sobre(ajeno.documento)

    _consultar_chat(cliente_api, ajeno.cabeceras_otro, pregunta, notebook_id=str(id_notebook))

    recibido = _todo_lo_que_recibio_el_modelo(ollama_simulado, pregunta)
    assert ajeno.documento.frase not in recibido, "el modelo recibió una frase de un documento"
    assert ajeno.documento.nombre not in recibido, "el modelo recibió el nombre de un archivo"


# --- RF-17.3: los documentos del notebook de otro no se entregan --------------------------------------------------------------

def _alcance_chat_general(cliente_api, e, ollama_simulado):
    pregunta = _pregunta_sobre(e.documento)
    _consultar_chat(cliente_api, e.cabeceras_otro, pregunta)
    return _todo_lo_que_recibio_el_modelo(ollama_simulado, pregunta)


def _alcance_chat_por_tema(cliente_api, e, ollama_simulado):
    pregunta = _pregunta_sobre(e.documento)
    _consultar_chat(cliente_api, e.cabeceras_otro, pregunta, expediente_number=e.notebook["clave_interna"])
    return _todo_lo_que_recibio_el_modelo(ollama_simulado, pregunta)


def _buscar_similares(cliente_api, cabeceras, e):
    return cliente_api.post(
        "/similarity/search", headers=cabeceras,
        json={"modo_busqueda": "descripcion", "texto_consulta": e.documento.frase, "limite": 30, "umbral_similitud": 0.1})


def _alcance_temas_similares(cliente_api, e, ollama_simulado):
    # Control: el dueño sí encuentra su documento, así que la búsqueda es capaz de devolverlo.
    del ollama_simulado
    propia = _buscar_similares(cliente_api, e.cabeceras_dueno, e)
    assert propia.status_code == 200 and e.documento.nombre in propia.text, "control: el dueño no encontró su documento"
    return _buscar_similares(cliente_api, e.cabeceras_otro, e).text


def _alcance_descarga(cliente_api, e, ollama_simulado):
    del ollama_simulado
    ruta = f"uploads/{e.notebook['clave_interna']}/{e.documento.nombre}"
    propia = cliente_api.get("/archivos/download", params={"ruta_archivo": ruta}, headers=e.cabeceras_dueno)
    assert propia.status_code == 200 and propia.content == e.documento.contenido, "control: el dueño no lo descargó"
    ajena = cliente_api.get("/archivos/download", params={"ruta_archivo": ruta}, headers=e.cabeceras_otro)
    return ajena.text if ajena.status_code != 200 else ajena.content.decode("utf-8")


# Hoy ni el chat (general; el tema `NB-<id>` no pasa la regex del chat por tema y cae al general) ni los temas similares
# excluyen los notebooks de otros usuarios; la descarga sí (spec 004a).
_ABIERTO_17_3 = pytest.mark.xfail(strict=True, reason="RF-17.3 · notebooks")


@pytest.mark.requisito("RF-17.3")
@pytest.mark.parametrize("alcance", [
    pytest.param(_alcance_chat_general, id="chat_general", marks=_ABIERTO_17_3),
    pytest.param(_alcance_chat_por_tema, id="chat_por_tema", marks=_ABIERTO_17_3),
    pytest.param(_alcance_temas_similares, id="temas_similares", marks=_ABIERTO_17_3),
    pytest.param(_alcance_descarga, id="descarga"),
])
def test_documentos_de_notebook_ajeno_no_se_entregan(cliente_api, ajeno, ollama_simulado, alcance):
    """RF-17.3: el dueño sube a su notebook; otro usuario consulta la frase en el chat general, en el chat por tema (con la
    clave del notebook), en temas similares y en la descarga: ni el contexto, ni los resultados, ni la descarga traen el
    documento del dueño (ni su frase ni su nombre de archivo)."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)

    entregado = alcance(cliente_api, ajeno, ollama_simulado)

    assert ajeno.documento.frase not in entregado, "se entregó el contenido del documento de otro usuario"
    assert ajeno.documento.nombre not in entregado, "se entregó el nombre del archivo de otro usuario"
    assert ajeno.notebook["clave_interna"] not in entregado, "se entregó la clave del notebook de otro usuario"


# --- RNF-07.6: 404 idéntico para un recurso ajeno y uno inexistente ------------------------------------------------------------

def _id_notebook(e: Ajeno, ajena: bool) -> int:
    return e.notebook["id"] if ajena else e.id_inexistente


def _op_listar(cliente, e, ajena):
    return cliente.get(f"/notebooks/{_id_notebook(e, ajena)}/documentos", headers=e.cabeceras_otro)


def _op_previsualizar(cliente, e, ajena):
    return cliente.get(f"/notebooks/{_id_notebook(e, ajena)}/documentos/{e.id_documento}/archivo", headers=e.cabeceras_otro)


def _op_quitar(cliente, e, ajena):
    return cliente.delete(f"/notebooks/{_id_notebook(e, ajena)}/documentos/{e.id_documento}", headers=e.cabeceras_otro)


def _op_chat(cliente, e, ajena):
    return _consultar_chat(cliente, e.cabeceras_otro, _pregunta_sobre(e.documento), notebook_id=str(_id_notebook(e, ajena)))


def _sesion_de_chat(e: Ajeno, ajena: bool) -> str:
    return e.sesion_chat if ajena else f"session_{e.otro.correo}_{PREFIJO_DATOS}inexistente"


def _op_ver_conversacion(cliente, e, ajena):
    return cliente.get(f"/rag/conversations/{_sesion_de_chat(e, ajena)}", headers=e.cabeceras_otro)


def _op_eliminar_conversacion(cliente, e, ajena):
    return cliente.delete(f"/rag/conversations/{_sesion_de_chat(e, ajena)}", headers=e.cabeceras_otro)


def _op_restaurar_conversacion(cliente, e, ajena):
    return cliente.post(f"/rag/conversations/{_sesion_de_chat(e, ajena)}/restore", headers=e.cabeceras_otro)


def _como_se_ve(respuesta, e: Ajeno):
    """Código y cuerpo de la respuesta; los identificadores pedidos (que el mensaje repite) se sustituyen para compararlos."""
    cuerpo = respuesta.text
    for pedido in (e.sesion_chat, f"session_{e.otro.correo}_{PREFIJO_DATOS}inexistente"):
        cuerpo = cuerpo.replace(pedido, "<sesion>")
    return respuesta.status_code, cuerpo


@pytest.mark.requisito("RNF-07.6")
@pytest.mark.parametrize("operacion", [
    pytest.param(_op_listar, id="listar"),
    pytest.param(_op_previsualizar, id="previsualizar"),
    pytest.param(_op_quitar, id="quitar"),
    pytest.param(_op_chat, id="chat", marks=pytest.mark.xfail(strict=True, reason="RNF-07.6 · notebooks")),
    # Las conversaciones distinguen «existe» (403) de «no existe» (404) al ver y al restaurar (ERS, «Estado actual»).
    pytest.param(_op_ver_conversacion, id="ver_conversacion", marks=pytest.mark.xfail(strict=True, reason="RNF-07.6 · RAG")),
    pytest.param(_op_eliminar_conversacion, id="eliminar_conversacion"),
    pytest.param(_op_restaurar_conversacion, id="restaurar_conversacion",
                 marks=pytest.mark.xfail(strict=True, reason="RNF-07.6 · RAG")),
])
def test_recurso_ajeno_da_404_identico(cliente_api, ajeno, correo_simulado, ollama_simulado, operacion):
    """RNF-07.6: pedir un recurso de otro usuario (documentos, chat de un notebook, conversación) da 404 con el mismo código
    y cuerpo que pedir uno inexistente, y no lo lee, modifica ni entrega: el original del dueño, su lista de documentos y los
    datos quedan igual."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    antes = foto_de_efectos(correo_simulado)

    de_otro = operacion(cliente_api, ajeno, True)
    inexistente = operacion(cliente_api, ajeno, False)

    assert inexistente.status_code == 404, f"lo inexistente debe dar 404 y dio {inexistente.status_code}"
    assert de_otro.status_code == 404, f"lo ajeno debe dar 404 y dio {de_otro.status_code}"
    assert _como_se_ve(de_otro, ajeno) == _como_se_ve(inexistente, ajeno)
    assert ajeno.documento.frase not in de_otro.text, "la respuesta trajo contenido del documento del dueño"
    # Sin cambios: nada nuevo en la base, Qdrant ni archivos, y el dueño sigue viendo lo suyo.
    assert foto_de_efectos(correo_simulado) == antes
    lista = cliente_api.get(f"/notebooks/{ajeno.notebook['id']}/documentos", headers=ajeno.cabeceras_dueno)
    assert lista.json() == [{"id": ajeno.id_documento, "nombre_archivo": ajeno.documento.nombre, "estado": "Procesado"}]
    original = cliente_api.get(
        f"/notebooks/{ajeno.notebook['id']}/documentos/{ajeno.id_documento}/archivo", headers=ajeno.cabeceras_dueno)
    assert original.status_code == 200 and original.content == ajeno.documento.contenido
    conversacion = cliente_api.get(f"/rag/conversations/{ajeno.sesion_chat}", headers=ajeno.cabeceras_dueno)
    assert conversacion.status_code == 200, "el dueño perdió su conversación"


# --- RF-17.4: subir a un notebook ajeno ------------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-17.4")
@pytest.mark.xfail(strict=True, reason="RF-17.4 · notebooks")
def test_carga_a_notebook_ajeno_da_404(cliente_api, ajeno, correo_simulado, encolado_interceptado):
    """RF-17.4: subir archivos con la clave de un notebook ajeno o inexistente da 404 (el mismo para ambos), sin guardar el
    archivo, encolar la tarea, crear el documento, el tema ni los fragmentos."""
    antes = foto_de_efectos(correo_simulado)
    tareas = len(encolado_interceptado.pendientes)
    intruso = documento_de_prueba()

    respuestas = [
        cargar(cliente_api, ajeno.cabeceras_otro, clave, [(intruso.nombre, intruso.contenido)])
        for clave in (ajeno.notebook["clave_interna"], f"NB-{ajeno.id_inexistente}")
    ]

    for respuesta in respuestas:
        assert respuesta.status_code == 404, f"se esperaba 404 y se recibió {respuesta.status_code}"
    assert respuestas[0].json() == respuestas[1].json(), "ajeno e inexistente deben responder igual"
    assert len(encolado_interceptado.pendientes) == tareas, "se encoló una tarea"
    assert id_del_documento(intruso.nombre) is None, "se creó el documento"
    assert foto_de_efectos(correo_simulado) == antes


# --- T13: apoyos de RF-19 ---------------------------------------------------------------------------------------------------

TEXTO_INTERNO = "PRUEBA fallo interno en /srv/PRUEBA_interno/almacen.py"


def _tres_capas(clave: str, nombre: str, id_documento: int) -> dict:
    """Las representaciones de un documento: fragmentos en Qdrant, archivo en la carpeta del tema y fila con su relación."""
    from app.services.documentos.file_management_service import file_management_service

    fragmentos = [p for p in _puntos_del_tema(clave) if p.payload["metadata"]["id_documento"] == id_documento]
    parametros = {"d": id_documento}
    return {
        "fragmentos": len(fragmentos),
        "archivo": file_management_service.obtener_ruta_archivo(clave, nombre) is not None,
        "fila": _consultar("SELECT COUNT(*) FROM T_Documento WHERE CN_Id_documento = :d", parametros)[0][0],
        "relacion": _consultar("SELECT COUNT(*) FROM T_Expediente_Documento WHERE CN_Id_documento = :d", parametros)[0][0],
    }


CAPAS_VACIAS = {"fragmentos": 0, "archivo": False, "fila": 0, "relacion": 0}


def _lista_del_notebook(cliente_api, cabeceras, notebook: dict) -> list:
    respuesta = cliente_api.get(f"/notebooks/{notebook['id']}/documentos", headers=cabeceras)
    assert respuesta.status_code == 200
    return respuesta.json()


def _item(documento, id_documento: int) -> dict:
    return {"id": id_documento, "nombre_archivo": documento.nombre, "estado": "Procesado"}


# --- RF-19.1: quitar un documento de dos ------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-19.1")
def test_quitar_uno_de_dos(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    """RF-19.1: al quitar uno de dos documentos del notebook se eliminan sus tres representaciones (fragmentos, archivo y
    fila con su relación con el tema); el otro queda intacto (lista, fragmentos, archivo y vista previa), el chat del notebook
    ya no recibe el contenido del quitado, y no se elimina el notebook, el tema ni ninguna fila de la bitácora.
    Quitar un documento de un notebook es la excepción aprobada al borrado físico (RN-01), solo en el entorno aislado."""
    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook con dos documentos", registro_de_datos)
    quitado, id_quitado = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook)
    queda, id_queda = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook)
    clave = notebook["clave_interna"]
    capas_quitado = _tres_capas(clave, quitado.nombre, id_quitado)
    capas_queda = _tres_capas(clave, queda.nombre, id_queda)
    assert capas_quitado["fragmentos"] > 0 and capas_quitado["archivo"] and capas_quitado["fila"] == 1
    assert capas_queda["fragmentos"] > 0 and capas_queda["archivo"] and capas_queda["fila"] == 1
    assert capas_quitado["relacion"] == capas_queda["relacion"] == 1
    assert len(_lista_del_notebook(cliente_api, sesion, notebook)) == 2
    filas_bitacora = _consultar("SELECT COUNT(*) FROM T_Bitacora")[0][0]
    ollama_simulado.responder(RESPUESTA_SIMULADA)

    respuesta = cliente_api.delete(f"/notebooks/{notebook['id']}/documentos/{id_quitado}", headers=sesion)

    assert respuesta.status_code == 200, f"se esperaba 200 y se recibió {respuesta.status_code}"
    assert respuesta.json()["documento_id"] == id_quitado
    assert _tres_capas(clave, quitado.nombre, id_quitado) == CAPAS_VACIAS, "quedó alguna de las tres representaciones"
    # El otro, intacto en todo.
    assert _tres_capas(clave, queda.nombre, id_queda) == capas_queda
    assert _lista_del_notebook(cliente_api, sesion, notebook) == [_item(queda, id_queda)]
    vista = cliente_api.get(f"/notebooks/{notebook['id']}/documentos/{id_queda}/archivo", headers=sesion)
    assert vista.status_code == 200 and vista.content == queda.contenido
    # El quitado ya no se entrega ni se puede previsualizar.
    assert cliente_api.get(f"/notebooks/{notebook['id']}/documentos/{id_quitado}/archivo", headers=sesion).status_code == 404
    # Ni el notebook, ni el tema, ni la bitácora se eliminaron.
    assert [n["id"] for n in cliente_api.get("/notebooks", headers=sesion).json()] == [notebook["id"]]
    assert _consultar("SELECT COUNT(*) FROM T_Expediente WHERE CT_Num_expediente = :c", {"c": clave})[0][0] == 1
    assert _consultar("SELECT COUNT(*) FROM T_Bitacora")[0][0] >= filas_bitacora
    # El chat del notebook ya no recibe el contenido del quitado, pero sí el del que queda.
    pregunta = _pregunta_sobre(quitado)
    assert _consultar_chat(cliente_api, sesion, pregunta, notebook_id=str(notebook["id"])).status_code == 200
    contexto = contexto_enviado(ollama_simulado).replace(pregunta, "")
    assert quitado.frase not in contexto and quitado.nombre not in contexto, "el chat recibió el documento quitado"
    assert queda.frase in contexto and queda.nombre in contexto, "control: el chat no recibió el documento que queda"


# --- RF-19.2: falla una de las eliminaciones y el reintento --------------------------------------------------------------

def _provocar_fallo(monkeypatch, capa: str, nombre: str, id_documento: int) -> dict:
    """Hace fallar la eliminación de una capa SOLO para el documento marcado y mientras `activa` sea verdadero. Parcha la
    clase (no la instancia) y se restaura sola al terminar la prueba. Devuelve el interruptor `{"activa": bool}`."""
    from pathlib import Path

    from app.vectorstore import get_vectorstore_backend

    interruptor = {"activa": True}
    if capa == "fragmentos":
        clase = type(get_vectorstore_backend())
        original = clase.delete_document_chunks

        async def _falla_fragmentos(self, document_id):
            if interruptor["activa"] and document_id == id_documento:
                raise RuntimeError(TEXTO_INTERNO)
            return await original(self, document_id)

        monkeypatch.setattr(clase, "delete_document_chunks", _falla_fragmentos)
    else:
        original_unlink = Path.unlink

        def _falla_archivo(self, *args, **kwargs):
            if interruptor["activa"] and self.name == nombre:
                raise PermissionError(TEXTO_INTERNO)
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", _falla_archivo)
    return interruptor


@pytest.mark.requisito("RF-19.2")
@pytest.mark.xfail(strict=True, reason="RF-19.2 · notebooks")
@pytest.mark.parametrize("capa", ["fragmentos", "archivo"])
def test_fallo_al_quitar_y_reintento(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, monkeypatch, capa):
    """RF-19.2: si falla la eliminación de los fragmentos o la del archivo, la respuesta es un error (no un éxito) con un
    mensaje en español sin texto de la excepción, el documento sigue listado con sus capas y los demás intactos; un nuevo
    intento sin el fallo completa la eliminación y termina con éxito. Hoy (ERS, «Estado actual»): un fallo de fragmentos
    da un 500 sin mensaje (el reintento sí funciona) y un archivo que no se puede borrar se ignora, la fila se elimina y la
    respuesta es un éxito."""
    from fastapi.testclient import TestClient

    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook con fallo al quitar", registro_de_datos)
    objetivo, id_objetivo = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook)
    otro, id_otro = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook)
    clave = notebook["clave_interna"]
    capas_objetivo = _tres_capas(clave, objetivo.nombre, id_objetivo)
    capas_otro = _tres_capas(clave, otro.nombre, id_otro)
    assert capas_objetivo["fragmentos"] > 0 and capas_objetivo["archivo"] and capas_objetivo["fila"] == 1
    interruptor = _provocar_fallo(monkeypatch, capa, objetivo.nombre, id_objetivo)
    sin_relanzar = TestClient(cliente_api.app, raise_server_exceptions=False)
    ruta = f"/notebooks/{notebook['id']}/documentos/{id_objetivo}"

    primera = sin_relanzar.delete(ruta, headers=sesion)

    assert primera.status_code >= 400, f"se esperaba un error y se recibió {primera.status_code}"
    # Sigue listado hasta que se borren las tres capas; el otro documento no cambia.
    assert _item(objetivo, id_objetivo) in _lista_del_notebook(cliente_api, sesion, notebook)
    assert _tres_capas(clave, objetivo.nombre, id_objetivo)["fila"] == 1
    assert _tres_capas(clave, otro.nombre, id_otro) == capas_otro
    # Un nuevo intento, sin el fallo, completa lo que faltó.
    interruptor["activa"] = False
    segunda = sin_relanzar.delete(ruta, headers=sesion)
    assert segunda.status_code == 200, f"el reintento debía terminar con éxito y dio {segunda.status_code}"
    assert _tres_capas(clave, objetivo.nombre, id_objetivo) == CAPAS_VACIAS
    assert _lista_del_notebook(cliente_api, sesion, notebook) == [_item(otro, id_otro)]
    assert _tres_capas(clave, otro.nombre, id_otro) == capas_otro
    # El mensaje del primer intento: en español, sin el texto de la excepción ni su ruta.
    try:
        detalle = primera.json().get("detail")
    except ValueError:
        detalle = None
    assert isinstance(detalle, str) and detalle and detalle != "Internal Server Error", f"se esperaba un mensaje: {primera.text!r}"
    assert TEXTO_INTERNO not in primera.text and "Traceback" not in primera.text
