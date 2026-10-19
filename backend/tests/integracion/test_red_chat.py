"""Red de seguridad del chat acotado, del motor caído y de la descarga del citado (spec 004, T10; RF-11.1, RF-11.2, RF-12.1,
RF-21.7, RNF-09.1).

Sube y procesa documentos por la API como lo haría la interfaz (Tika, SQL Server y Qdrant reales del entorno aislado, Redis
simulado) y consulta `POST /rag/consulta-con-historial-stream` con un Usuario Gubernamental `PRUEBA`. El motor de lenguaje es el
simulado de la suite (RNF-09.1: nada llega a un servicio de IA real): lo que se comprueba es lo que RECIBE el modelo y los eventos
que la API devuelve, no el texto de una respuesta real.
- RF-11.1: el contexto trae la frase distintiva del documento y su nombre de archivo; el chat acotado a un tema no trae
  fragmentos de otro tema aunque la pregunta los nombre (control: en el chat general sí); los eventos terminan con el evento
  final; la consulta queda en la bitácora con el tema (RF-21.7).
- RF-11.2: sin conexión con el motor, el error llega dentro de la conversación, en español y sin el texto de la excepción; si el
  modelo no devuelve texto, el flujo cierra con el evento final y sin error.
- RF-12.1: la descarga del documento citado entrega el archivo tal cual; si no existe en ese tema, 404 en español y sin contenido.

Los temas llevan un número en el formato que el chat acotado reconoce hoy: el tema de nombre libre ya está cubierto, como fallo
esperado «RF-06.2 · ingesta», en `test_red_ingesta.py`.
"""
import json
import uuid

import pytest
from sqlalchemy import text

from tests.soporte.flujos import (
    cargar, contexto_enviado, documento_de_prueba, id_del_documento, leer_eventos, tema_heredado,
)
from tests.soporte.nombres import PREFIJO_DATOS

# La tarea de ingesta consulta su estado en Celery; en modo inmediato Celery avisa que ese resultado no se guarda en el
# backend. Es un aviso del propio sistema en un modo que nunca usa en producción (como en `test_red_ingesta.py`).
pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")

CONSULTA_RAG = 12  # TiposAccion.CONSULTA_RAG
RESPUESTA_SIMULADA = "Respuesta simulada de PRUEBA para el chat."
TEXTO_DE_LA_EXCEPCION = "PRUEBA-fallo-inventado-7q3x"  # cadena que solo existe en la excepción simulada


@pytest.fixture
def sesion(iniciar_sesion, usuario_gubernamental):
    return iniciar_sesion(usuario_gubernamental)


# --- Apoyos --------------------------------------------------------------------------------------------------------------------

def _subir_y_procesar(cliente_api, sesion, procesamiento, tema, documento) -> None:
    """Sube el documento al tema y ejecuta su procesamiento; deja el documento Procesado y sus fragmentos en Qdrant."""
    respuesta = cargar(cliente_api, sesion, tema, [(documento.nombre, documento.contenido)])
    assert respuesta.status_code == 200, f"la carga respondió {respuesta.status_code}"
    [id_tarea] = respuesta.json()["task_ids"]
    resultado = procesamiento.procesar()[id_tarea]
    assert resultado.state == "SUCCESS", f"la tarea {id_tarea} terminó en {resultado.state}"


def _dos_temas(cliente_api, sesion, procesamiento, registro_de_datos):
    """Dos temas, cada uno con un documento Procesado y su frase distintiva: devuelve `(tema_a, doc_a, tema_b, doc_b)`."""
    tema_a, tema_b = tema_heredado(registro_de_datos), tema_heredado(registro_de_datos)
    doc_a, doc_b = documento_de_prueba(), documento_de_prueba()
    _subir_y_procesar(cliente_api, sesion, procesamiento, tema_a, doc_a)
    _subir_y_procesar(cliente_api, sesion, procesamiento, tema_b, doc_b)
    return tema_a, doc_a, tema_b, doc_b


def _pregunta_sobre(documento) -> str:
    """Una pregunta que nombra al documento por su número pero sin repetir su frase distintiva ni su nombre de archivo, para
    poder comprobar que la frase y el nombre llegaron al modelo desde el contexto y no desde la pregunta."""
    sufijo = documento.nombre[len(PREFIJO_DATOS) + 1:-len(".txt")]
    return f"¿Qué dice el documento inventado número {sufijo} sobre la quebrada ficticia {sufijo}?"


def _consultar_chat(cliente_api, sesion, usuario, pregunta: str, tema: str = None):
    """Consulta el chat (acotado a `tema`, o general si no hay) y devuelve la respuesta HTTP en flujo ya leída."""
    cuerpo = {"query": pregunta, "session_id": f"session_{usuario.cedula}_{uuid.uuid4().hex[:8]}"}
    if tema is not None:
        cuerpo["expediente_number"] = tema
    return cliente_api.post("/rag/consulta-con-historial-stream", json=cuerpo, headers=sesion)


def _consultar_bd(consulta: str, parametros: dict = None) -> list:
    from app.db.database import engine

    with engine.connect() as conexion:
        return [tuple(fila) for fila in conexion.execute(text(consulta), parametros or {}).fetchall()]


def _tipos(eventos: list) -> list:
    return [e.get("type") for e in eventos]


# --- RF-11.1: lo que recibe el modelo ---------------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-11.1")
def test_contexto_con_frase_y_nombre(cliente_api, sesion, usuario_gubernamental, registro_de_datos, procesamiento_en_prueba,
                                     ollama_simulado):
    """RF-11.1 (a): en el chat acotado a un tema, por un documento recién Procesado, el modelo recibe el fragmento con la
    frase distintiva Y el nombre de su archivo. La pregunta no trae ni la frase ni el nombre."""
    tema = tema_heredado(registro_de_datos)
    documento = documento_de_prueba()
    _subir_y_procesar(cliente_api, sesion, procesamiento_en_prueba, tema, documento)
    pregunta = _pregunta_sobre(documento)
    assert documento.frase not in pregunta and documento.nombre not in pregunta
    ollama_simulado.responder(RESPUESTA_SIMULADA)

    respuesta = _consultar_chat(cliente_api, sesion, usuario_gubernamental, pregunta, tema)

    assert respuesta.status_code == 200
    contexto = contexto_enviado(ollama_simulado)
    contexto_sin_pregunta = contexto.replace(pregunta, "")
    assert documento.frase in contexto_sin_pregunta, "el modelo no recibió el fragmento con la frase distintiva"
    assert documento.nombre in contexto_sin_pregunta, "el modelo no recibió el nombre del archivo del fragmento"


@pytest.mark.requisito("RF-11.1")
def test_no_mezcla_otro_tema(cliente_api, sesion, usuario_gubernamental, registro_de_datos, procesamiento_en_prueba,
                             ollama_simulado):
    """RF-11.1 (b): acotado al tema A, aunque la pregunta nombre el documento del tema B, el modelo recibe el de A y nada
    del de B (ni su frase ni su nombre). Control: en la consulta general sí se recupera el de B, así que la prueba distingue
    un chat acotado de uno general."""
    tema_a, doc_a, tema_b, doc_b = _dos_temas(cliente_api, sesion, procesamiento_en_prueba, registro_de_datos)
    ollama_simulado.responder(RESPUESTA_SIMULADA)

    # Control: sin tema, el documento de B se recupera.
    pregunta_b = _pregunta_sobre(doc_b)
    assert _consultar_chat(cliente_api, sesion, usuario_gubernamental, pregunta_b).status_code == 200
    contexto_general = contexto_enviado(ollama_simulado).replace(pregunta_b, "")
    assert doc_b.frase in contexto_general, "control: la consulta general no recuperó el documento de B"

    # Acotado a A, preguntando por B: solo llega A.
    assert _consultar_chat(cliente_api, sesion, usuario_gubernamental, pregunta_b, tema_a).status_code == 200
    contexto = contexto_enviado(ollama_simulado).replace(pregunta_b, "")
    assert doc_a.frase in contexto, "el chat acotado no recuperó el documento de su tema"
    assert doc_b.frase not in contexto, "el chat acotado trajo la frase de un fragmento de otro tema"
    assert doc_b.nombre not in contexto, "el chat acotado trajo el nombre de un archivo de otro tema"


# --- RF-11.1 (c) y (d), RF-21.7: eventos y bitácora -----------------------------------------------------------------------------

@pytest.mark.requisito("RF-11.1")
def test_eventos_hasta_el_final(cliente_api, sesion, usuario_gubernamental, registro_de_datos, procesamiento_en_prueba,
                                ollama_simulado):
    """RF-11.1 (c): la respuesta es un flujo de eventos `data: {...}` con el formato que define el código (`type`, `content`,
    `done`): fragmentos de texto que, unidos, dan la respuesta del modelo, y un único evento final al cierre, sin errores."""
    tema = tema_heredado(registro_de_datos)
    documento = documento_de_prueba()
    _subir_y_procesar(cliente_api, sesion, procesamiento_en_prueba, tema, documento)
    ollama_simulado.responder(RESPUESTA_SIMULADA)

    respuesta = _consultar_chat(cliente_api, sesion, usuario_gubernamental, _pregunta_sobre(documento), tema)

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/event-stream")
    eventos = leer_eventos(respuesta)
    assert eventos, "el chat no devolvió eventos"
    assert all({"type", "content", "done"} <= set(e) for e in eventos), f"eventos con otro formato: {eventos}"
    tipos = _tipos(eventos)
    assert tipos.count("chunk") >= 2, "se esperaban varios fragmentos (streaming), no una sola entrega"
    assert tipos[-1] == "done" and tipos.count("done") == 1 and eventos[-1]["done"] is True
    assert set(tipos) == {"chunk", "done"}, f"no se esperaban otros eventos: {tipos}"
    assert all(e["done"] is False for e in eventos[:-1])
    assert "".join(e["content"] for e in eventos if e["type"] == "chunk").strip() == RESPUESTA_SIMULADA


@pytest.mark.requisito("RF-11.1")
@pytest.mark.requisito("RF-21.7")
def test_consulta_registrada_con_el_tema(cliente_api, sesion, usuario_gubernamental, registro_de_datos,
                                         procesamiento_en_prueba, ollama_simulado):
    """RF-11.1 (d), RF-21.7: la consulta acotada deja una fila de consulta al asistente con el usuario, el tipo y el tema; la
    fila no lleva ni contraseña ni token."""
    tema = tema_heredado(registro_de_datos)
    documento = documento_de_prueba()
    _subir_y_procesar(cliente_api, sesion, procesamiento_en_prueba, tema, documento)
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    ultimo_id = int(_consultar_bd("SELECT COALESCE(MAX(CN_Id_bitacora), 0) FROM T_Bitacora")[0][0])

    assert _consultar_chat(cliente_api, sesion, usuario_gubernamental, _pregunta_sobre(documento), tema).status_code == 200

    filas = _consultar_bd(
        "SELECT b.CN_Id_usuario, b.CT_Texto, b.CT_Informacion_adicional, e.CT_Num_expediente "
        "FROM T_Bitacora b LEFT JOIN T_Expediente e ON e.CN_Id_expediente = b.CN_Id_expediente "
        "WHERE b.CN_Id_bitacora > :d AND b.CN_Id_tipo_accion = :t AND b.CN_Id_usuario = :u",
        {"d": ultimo_id, "t": CONSULTA_RAG, "u": usuario_gubernamental.cedula})
    assert len(filas) == 1, f"se esperaba una fila de consulta al asistente y hay {len(filas)}"
    _, texto, adicional, tema_de_la_fila = filas[0]
    assert tema_de_la_fila == tema, "la fila de consulta no quedó asociada al tema"
    assert tema in (texto or "") or tema in (adicional or ""), "la fila no menciona el tema"
    registrado = f"{texto} {adicional}".lower()
    assert sesion["Authorization"].split()[-1] not in registrado and "password" not in registrado
    assert "contraseña" not in registrado and "token" not in registrado
    if adicional:
        assert isinstance(json.loads(adicional), dict)


# --- RF-11.2: motor sin conexión y respuesta vacía -------------------------------------------------------------------------------

@pytest.fixture
def tema_con_documento(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba):
    """Un tema con un documento Procesado: `(tema, documento)`."""
    tema = tema_heredado(registro_de_datos)
    documento = documento_de_prueba()
    _subir_y_procesar(cliente_api, sesion, procesamiento_en_prueba, tema, documento)
    return tema, documento


@pytest.mark.requisito("RF-11.2")
def test_motor_sin_conexion_cierra_con_evento_final(cliente_api, sesion, usuario_gubernamental, tema_con_documento,
                                                    ollama_simulado):
    """RF-11.2 (estructura): si el motor de lenguaje no responde, la petición no da 5xx, el error viaja DENTRO de la
    conversación como un evento de error y el flujo cierra con el evento final."""
    tema, documento = tema_con_documento
    ollama_simulado.fallar(ConnectionError(TEXTO_DE_LA_EXCEPCION))

    respuesta = _consultar_chat(cliente_api, sesion, usuario_gubernamental, _pregunta_sobre(documento), tema)

    assert respuesta.status_code == 200
    eventos = leer_eventos(respuesta)
    tipos = _tipos(eventos)
    assert "error" in tipos, f"el error no viajó dentro de la conversación: {tipos}"
    assert tipos[-1] == "done" and eventos[-1]["done"] is True
    assert "chunk" not in tipos, "no debería haber texto de respuesta si el motor no respondió"
    assert ollama_simulado.preguntas, "el motor simulado no llegó a recibir la consulta (la prueba no ejercitó el fallo)"


@pytest.mark.requisito("RF-11.2")
@pytest.mark.xfail(strict=True, reason="RF-11.2 · RAG")
def test_motor_sin_conexion(cliente_api, sesion, usuario_gubernamental, tema_con_documento, ollama_simulado):
    """RF-11.2 (mensaje): el error que ve el usuario está en español, menciona la conexión y NO contiene el texto de la
    excepción (ese texto expone el funcionamiento interno; `api-conventions.md`). Hoy el evento de error incluye `str(e)`."""
    tema, documento = tema_con_documento
    ollama_simulado.fallar(ConnectionError(TEXTO_DE_LA_EXCEPCION))

    respuesta = _consultar_chat(cliente_api, sesion, usuario_gubernamental, _pregunta_sobre(documento), tema)

    assert respuesta.status_code == 200
    eventos = leer_eventos(respuesta)
    errores = [e for e in eventos if e.get("type") == "error"]
    assert errores, "no hay evento de error"
    mensaje = errores[0]["content"]
    assert TEXTO_DE_LA_EXCEPCION not in respuesta.text, "el texto de la excepción llegó al usuario"
    assert "conexión" in mensaje.lower(), f"el mensaje no habla de la conexión con el motor: {mensaje!r}"
    assert eventos[-1]["type"] == "done"


@pytest.mark.requisito("RF-11.2")
def test_respuesta_vacia_cierra(cliente_api, sesion, usuario_gubernamental, tema_con_documento, ollama_simulado):
    """RF-11.2: si el modelo no devuelve texto, el backend cierra con el evento final y sin error (la interfaz decide el
    reintento, spec 005). Responde 200 y el modelo sí recibió la consulta."""
    tema, documento = tema_con_documento
    ollama_simulado.responder("")

    respuesta = _consultar_chat(cliente_api, sesion, usuario_gubernamental, _pregunta_sobre(documento), tema)

    assert respuesta.status_code == 200
    eventos = leer_eventos(respuesta)
    tipos = _tipos(eventos)
    assert ollama_simulado.preguntas, "el modelo simulado no recibió la consulta"
    assert "error" not in tipos, f"una respuesta vacía no es un error: {tipos}"
    assert tipos[-1] == "done" and tipos.count("done") == 1 and eventos[-1]["done"] is True


@pytest.mark.requisito("RF-11.2")
@pytest.mark.xfail(strict=True, reason="RF-11.2 · RAG")
def test_respuesta_vacia_sin_fragmentos(cliente_api, sesion, usuario_gubernamental, tema_con_documento, ollama_simulado):
    """RF-11.2: si el modelo no devuelve texto, el backend cierra «sin fragmentos» (spec, RF-11.2): solo el evento final, para
    que la interfaz pueda reintentar. Hoy `stream_chain_response` inventa un fragmento de relleno («No encontré información…»)
    antes del evento final, y la interfaz no puede distinguir una respuesta vacía de una real."""
    tema, documento = tema_con_documento
    ollama_simulado.responder("")

    respuesta = _consultar_chat(cliente_api, sesion, usuario_gubernamental, _pregunta_sobre(documento), tema)

    assert respuesta.status_code == 200
    assert _tipos(leer_eventos(respuesta)) == ["done"]


# --- RF-12.1: descarga del documento citado ---------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-12.1")
def test_descarga_del_citado(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba):
    """RF-12.1: el original de un documento de un tema se entrega tal cual (mismos bytes). Si el nombre no existe en ese
    tema, o es el de un documento de otro tema, responde 404 en español y sin contenido del archivo."""
    tema_a, doc_a, tema_b, doc_b = _dos_temas(cliente_api, sesion, procesamiento_en_prueba, registro_de_datos)

    entregado = cliente_api.get(f"/archivos/expediente/{tema_a}/archivo/{doc_a.nombre}", headers=sesion)
    assert entregado.status_code == 200
    assert entregado.content == doc_a.contenido, "el archivo entregado no es el original"

    inexistente = cliente_api.get(f"/archivos/expediente/{tema_a}/archivo/{PREFIJO_DATOS}_no_existe.txt", headers=sesion)
    de_otro_tema = cliente_api.get(f"/archivos/expediente/{tema_a}/archivo/{doc_b.nombre}", headers=sesion)
    for negada in (inexistente, de_otro_tema):
        assert negada.status_code == 404
        cuerpo = negada.json()
        assert cuerpo == {"detail": "Archivo no encontrado"}, f"el 404 debe traer solo un mensaje en español: {cuerpo}"
        assert doc_a.frase not in negada.text and doc_b.frase not in negada.text, "el 404 trajo contenido de un archivo"
    # El documento de B sigue siendo descargable desde su propio tema.
    assert id_del_documento(doc_b.nombre) is not None
    assert cliente_api.get(f"/archivos/expediente/{tema_b}/archivo/{doc_b.nombre}", headers=sesion).content == doc_b.contenido
