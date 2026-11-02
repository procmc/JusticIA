"""Contexto del chat por tema y del notebook contra Qdrant real (spec 007, T5b; RF-11.69).

Sube y procesa por la API un documento inventado LARGO (muchos más fragmentos que los 8 que se envían al motor, con la frase
que responde la pregunta en el último) y consulta `POST /rag/consulta-con-historial-stream`. El motor es el simulado de la suite:
lo que se comprueba es lo que RECIBE, no el texto de una respuesta.
- RF-11.69: el fragmento relevante llega aunque esté al final del tema o del notebook (antes llegaban los primeros por número);
  el chat no trae fragmentos de otro tema; una pregunta sin relación igual trae los 8 fragmentos (sin umbral de similitud).
- T6 (flujo del turno): etapas, pregunta demasiado larga, señal de vida, tope, desconexión, historial y bitácora (RF-11.62,
  RF-11.64, RF-11.68, RF-16.60, RF-16.62, RF-21.60) en los tres chats.
Los datos son inventados (prefijo `PRUEBA`) y se limpian solos.
"""
import asyncio
import dataclasses
import json
import time
import uuid

import pytest

from tests.integracion.conftest import (
    _consultar, _consultar_chat, _documento_procesado_en_el_notebook, _todo_lo_que_recibio_el_modelo,
)
from tests.soporte.flujos import (
    DocumentoPrueba, cargar, contar_puntos, crear_notebook, exigir_estado, id_del_documento, leer_eventos, tema_heredado,
)
from tests.soporte.nombres import PREFIJO_DATOS

pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")

CHATS = ["tema", "notebook"]
FRAGMENTOS_ENVIADOS = 8  # fragmentos_por_consulta por omisión (RF-11.65)


def _documento_largo() -> DocumentoPrueba:
    """Un `PRUEBA_<uuid8>.txt` de 14 párrafos de relleno (cada uno forma su fragmento) y, al final, el que trae la frase única."""
    sufijo = uuid.uuid4().hex[:8]
    frase = f"la quebrada ficticia {sufijo} desemboca en la laguna inventada de los patos azules"
    relleno = [
        f"{PREFIJO_DATOS} párrafo {n} del inventario inventado: las sillas, los escritorios y las lámparas de la oficina ficticia "
        "se cuentan cada mes y se anotan en una planilla que nadie revisa. " * 8
        for n in range(14)
    ]
    texto = "\n\n".join(relleno + [f"{PREFIJO_DATOS} nota final del documento número {sufijo}: {frase}."])
    return DocumentoPrueba(nombre=f"{PREFIJO_DATOS}_{sufijo}.txt", contenido=texto.encode("utf-8"), frase=frase)


def _pregunta_de(documento: DocumentoPrueba) -> str:
    """Pregunta por el contenido del último fragmento sin repetir la frase ni el nombre del archivo."""
    sufijo = documento.nombre[len(PREFIJO_DATOS) + 1:-len(".txt")]
    return f"¿Dónde desemboca la quebrada ficticia {sufijo}?"


def _alcance_con_documento(chat, cliente_api, sesion, registro_de_datos, procesamiento, documento):
    """Crea el tema o el notebook, le sube y procesa el documento y devuelve `(clave, alcance_de_la_consulta)`."""
    if chat == "tema":
        tema = tema_heredado(registro_de_datos)
        respuesta = cargar(cliente_api, sesion, tema, [(documento.nombre, documento.contenido)])
        assert respuesta.status_code == 200, f"la carga respondió {respuesta.status_code}"
        [id_tarea] = respuesta.json()["task_ids"]
        assert procesamiento.procesar()[id_tarea].state == "SUCCESS"
        exigir_estado(id_del_documento(documento.nombre), "Procesado")
        clave, alcance = tema, {"expediente_number": tema}
    else:
        notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook {uuid.uuid4().hex[:6]}", registro_de_datos)
        _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento, notebook, documento)
        clave, alcance = notebook["clave_interna"], {"notebook_id": str(notebook["id"])}
    assert contar_puntos(clave) > FRAGMENTOS_ENVIADOS, "el documento de prueba debe tener más fragmentos que los enviados"
    return clave, alcance


@pytest.mark.requisito("RF-11.69")
@pytest.mark.parametrize("chat", CHATS)
def test_recupera_por_relevancia(chat, cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    """RF-11.69 (regresión) · el fragmento con la frase, que es el último del documento, llega al motor aunque haya más de 8
    fragmentos: se recupera por relevancia y no los primeros por número."""
    documento = _documento_largo()
    _, alcance = _alcance_con_documento(chat, cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, documento)
    ollama_simulado.responder("Respuesta de PRUEBA.")
    pregunta = _pregunta_de(documento)
    assert documento.frase not in pregunta

    assert _consultar_chat(cliente_api, sesion, pregunta, **alcance).status_code == 200

    assert documento.frase in _todo_lo_que_recibio_el_modelo(ollama_simulado, pregunta), \
        "el fragmento relevante no llegó al motor"


@pytest.mark.requisito("RF-11.69")
@pytest.mark.parametrize("chat", CHATS)
def test_no_mezcla_otro_tema(chat, cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    """RF-11.69 · la búsqueda por relevancia está filtrada: acotado a A, aunque la pregunta sea sobre el contenido de B, el
    motor recibe fragmentos de A y ni la frase ni el nombre del archivo de B."""
    doc_a, doc_b = _documento_largo(), _documento_largo()
    _, alcance_a = _alcance_con_documento(chat, cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, doc_a)
    _, alcance_b = _alcance_con_documento(chat, cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, doc_b)
    ollama_simulado.responder("Respuesta de PRUEBA.")
    pregunta_b = _pregunta_de(doc_b)

    # Control: acotado a B, la frase de B llega (la prueba distingue un chat filtrado de uno que no encuentra nada).
    assert _consultar_chat(cliente_api, sesion, pregunta_b, **alcance_b).status_code == 200
    assert doc_b.frase in _todo_lo_que_recibio_el_modelo(ollama_simulado, pregunta_b)

    ollama_simulado.preguntas.clear()
    assert _consultar_chat(cliente_api, sesion, pregunta_b, **alcance_a).status_code == 200
    recibido = _todo_lo_que_recibio_el_modelo(ollama_simulado, pregunta_b)
    assert doc_a.nombre in recibido, "el chat acotado no trajo fragmentos de su propio tema"
    assert doc_b.frase not in recibido and doc_b.nombre not in recibido


@pytest.mark.requisito("RF-11.69")
@pytest.mark.parametrize("chat", CHATS)
def test_pregunta_sin_relacion_trae_8(chat, cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    """RF-11.69 · sin umbral de similitud: una pregunta sin relación con el contenido igual recibe los 8 fragmentos del tema o
    del notebook, en lugar de ninguno."""
    documento = _documento_largo()
    _, alcance = _alcance_con_documento(chat, cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, documento)
    ollama_simulado.responder("Respuesta de PRUEBA.")

    assert _consultar_chat(cliente_api, sesion, "¿Cuál es la capital de un país imaginario muy lejano?", **alcance).status_code == 200

    enviada = ollama_simulado.preguntas[-1]
    assert enviada.count("[Fragmento ") == FRAGMENTOS_ENVIADOS, f"llegaron {enviada.count('[Fragmento ')} fragmentos"


# --- T6: flujo del turno (RF-11.62, RF-11.64, RF-11.68, RF-16.60, RF-16.62, RF-21.60) ---------------------------------------------

TRES_CHATS = ["general", "tema", "notebook"]
CASOS = ["terminado", "rechazo", "tope", "error"]
MOTIVO_DEL_CASO = {"terminado": None, "rechazo": "pregunta demasiado larga", "tope": "tiempo máximo agotado", "error": "error del motor"}
ETAPAS = ["Procesando consulta", "Analizando documentos", "Generando respuesta"]
TEXTO_LARGA = "La pregunta es demasiado larga. Acórtela e intente de nuevo."
TEXTO_TOPE = "La consulta tardó demasiado. Intente de nuevo."
PREGUNTA_LARGA = "¿" + "palabra inventada " * 1800 + "?"  # ~32.400 caracteres: no cabe en los 7.168 tokens de entrada
VIDA_CORTA, TOPE_CORTO = 0.3, 1.0  # segundos reales: la señal de vida y el tope se acortan para que la prueba no espere 180 s


def _alcance_vacio(chat, cliente_api, sesion, registro_de_datos) -> dict:
    """El alcance de la consulta de cada chat, sin documentos: el flujo del turno no depende del contenido."""
    if chat == "general":
        return {}
    if chat == "tema":
        return {"expediente_number": tema_heredado(registro_de_datos)}
    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook {uuid.uuid4().hex[:6]}", registro_de_datos)
    return {"notebook_id": str(notebook["id"])}


def _tiempos_cortos(monkeypatch, vida=VIDA_CORTA, tope=TOPE_CORTO) -> None:
    from app.config.contexto_config import CONFIGURACION
    from app.services.RAG import general_chains

    monkeypatch.setattr(
        general_chains, "CONFIGURACION",
        dataclasses.replace(CONFIGURACION, senal_de_vida_segundos=vida, tiempo_maximo_segundos=tope), raising=False,
    )


def _cuerpo(pregunta: str, alcance: dict, session_id: str = None) -> dict:
    return {"query": pregunta, "session_id": session_id or f"session_{PREFIJO_DATOS}turno_{uuid.uuid4().hex[:8]}", **alcance}


def _mensajes_guardados(session_id: str) -> int:
    from app.services.RAG.session_store import conversation_store

    historial = conversation_store._store.get(session_id)
    return 0 if historial is None else len(historial.messages)


def _ultimo_id_de_bitacora() -> int:
    return int(_consultar("SELECT COALESCE(MAX(CN_Id_bitacora), 0) FROM T_Bitacora")[0][0])


def _consultas_registradas(cedula: str, desde: int) -> list:
    """Las filas de consulta al asistente del usuario desde `desde`, con su información adicional ya decodificada."""
    from app.constants.tipos_accion import TiposAccion

    filas = _consultar(
        "SELECT CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_bitacora > :d AND CN_Id_tipo_accion = :t AND CN_Id_usuario = :u",
        {"d": desde, "t": TiposAccion.CONSULTA_RAG, "u": cedula},
    )
    return [json.loads(fila[0]) for fila in filas]


def _hacer_turno(caso, chat, cliente_api, sesion, registro_de_datos, ollama_simulado, monkeypatch):
    """Hace un turno del caso en el chat y devuelve `(eventos, session_id)`."""
    alcance = _alcance_vacio(chat, cliente_api, sesion, registro_de_datos)
    pregunta = "¿Qué dice el documento inventado de PRUEBA?"
    if caso == "terminado":
        ollama_simulado.responder("Respuesta de PRUEBA con varias palabras.")
    elif caso == "rechazo":
        pregunta = PREGUNTA_LARGA
    elif caso == "tope":
        _tiempos_cortos(monkeypatch)
        ollama_simulado.retener()
    else:
        ollama_simulado.fallar(ConnectionError("motor caído de PRUEBA"))
    cuerpo = _cuerpo(pregunta, alcance)
    respuesta = cliente_api.post("/rag/consulta-con-historial-stream", json=cuerpo, headers=sesion)
    assert respuesta.status_code == 200
    return leer_eventos(respuesta), cuerpo["session_id"]


@pytest.mark.requisito("RF-11.64")
@pytest.mark.parametrize("chat", TRES_CHATS)
def test_etapas_por_chat(chat, cliente_api, sesion, registro_de_datos, ollama_simulado):
    """RF-11.64 (regresión) · en los tres chats llegan las tres etapas, en orden, antes del primer texto, y el turno termina en
    el evento de fin."""
    ollama_simulado.responder("Respuesta de PRUEBA con varias palabras.")
    alcance = _alcance_vacio(chat, cliente_api, sesion, registro_de_datos)

    respuesta = cliente_api.post("/rag/consulta-con-historial-stream", json=_cuerpo("¿Hola, PRUEBA?", alcance), headers=sesion)

    eventos = leer_eventos(respuesta)
    tipos = [e["type"] for e in eventos]
    assert [e["content"] for e in eventos if e["type"] == "etapa"] == ETAPAS
    assert tipos[:3] == ["etapa"] * 3 and tipos.index("chunk") == 3, f"las etapas deben ir antes del primer texto: {tipos}"
    assert tipos[-1] == "done" and "error" not in tipos


@pytest.mark.requisito("RF-11.62")
@pytest.mark.parametrize("chat", TRES_CHATS)
def test_pregunta_larga_solo_error(chat, cliente_api, sesion, registro_de_datos, ollama_simulado):
    """RF-11.62 · una pregunta que no cabe en el presupuesto recibe solo el error en español: sin etapas, sin llamar al motor
    (tampoco para reformular) y sin guardarse en el historial."""
    alcance = _alcance_vacio(chat, cliente_api, sesion, registro_de_datos)
    cuerpo = _cuerpo(PREGUNTA_LARGA, alcance)

    respuesta = cliente_api.post("/rag/consulta-con-historial-stream", json=cuerpo, headers=sesion)

    assert respuesta.status_code == 200
    assert [(e["type"], e["content"]) for e in leer_eventos(respuesta)] == [("error", TEXTO_LARGA)]
    assert ollama_simulado.preguntas == [], "el motor no debía recibir ninguna llamada"
    assert _mensajes_guardados(cuerpo["session_id"]) == 0


@pytest.mark.requisito("RF-16.60")
def test_senal_de_vida_con_motor_retenido(cliente_api, sesion, llamar_asgi, ollama_simulado, monkeypatch):
    """RF-16.60 (H3) · mientras el motor tarda en dar el primer texto (modelo frío o en cola) llegan señales de vida: el
    servidor no queda mudo, y la respuesta termina bien cuando el motor responde."""
    _tiempos_cortos(monkeypatch, vida=VIDA_CORTA, tope=60)
    ollama_simulado.responder("Respuesta de PRUEBA tras la espera.")
    ollama_simulado.retener()

    async def escenario():
        llamada = llamar_asgi("POST", "/rag/consulta-con-historial-stream", json=_cuerpo("¿Hola, PRUEBA?", {}), cabeceras=sesion)
        limite = time.monotonic() + 60
        while ollama_simulado.en_curso < 1 and time.monotonic() < limite:
            await asyncio.sleep(0.05)
        assert ollama_simulado.en_curso == 1, "el motor no llegó a recibir la consulta"
        await asyncio.sleep(VIDA_CORTA * 4)
        ollama_simulado.liberar()
        respuesta = await asyncio.wait_for(llamada.respuesta, 30)
        await asyncio.wait_for(llamada.tarea, 30)
        return respuesta

    eventos = leer_eventos(asyncio.run(escenario()))
    tipos = [e["type"] for e in eventos]
    assert tipos[:3] == ["etapa"] * 3
    assert tipos[3:].count("vida") >= 2, f"se esperaban señales de vida durante la espera: {tipos}"
    assert tipos.index("chunk") > max(i for i, t in enumerate(tipos) if t == "vida")
    assert tipos[-1] == "done" and "error" not in tipos
    assert "".join(e["content"] for e in eventos if e["type"] == "chunk").strip() == "Respuesta de PRUEBA tras la espera."


@pytest.mark.requisito("RF-16.62")
def test_tope_libera_el_motor(cliente_api, sesion, ollama_simulado, monkeypatch):
    """RF-16.62 · al cumplirse el tope llega el error, el motor recibe la cancelación y deja de generar, y la consulta
    siguiente se atiende."""
    _tiempos_cortos(monkeypatch)
    ollama_simulado.retener()

    respuesta = cliente_api.post("/rag/consulta-con-historial-stream", json=_cuerpo("¿Hola, PRUEBA?", {}), headers=sesion)

    eventos = leer_eventos(respuesta)
    assert (eventos[-1]["type"], eventos[-1]["content"]) == ("error", TEXTO_TOPE)
    assert ollama_simulado.cancelaciones == 1 and ollama_simulado.en_curso == 0, "el motor debió recibir la cancelación"
    ollama_simulado.responder("Respuesta de PRUEBA después del tope.")
    ollama_simulado.liberar()
    siguiente = leer_eventos(cliente_api.post("/rag/consulta-con-historial-stream", json=_cuerpo("¿Otra vez?", {}), headers=sesion))
    assert siguiente[-1]["type"] == "done" and any(e["type"] == "chunk" for e in siguiente)


@pytest.mark.requisito("RF-16.62")
@pytest.mark.requisito("RF-11.68")
@pytest.mark.requisito("RF-21.60")
@pytest.mark.parametrize("momento", ["antes", "despues"])
def test_desconexion_antes_y_despues_cancela(momento, cliente_api, sesion, usuario_gubernamental, llamar_asgi,
                                             ollama_simulado, monkeypatch):
    """RF-16.62 · si el usuario cierra la conexión antes o después del primer texto, el motor recibe la cancelación y queda
    libre; el turno no se guarda en el historial (RF-11.68) ni se registra en la bitácora (RF-21.60)."""
    _tiempos_cortos(monkeypatch, vida=VIDA_CORTA, tope=60)
    ollama_simulado.responder("Respuesta de PRUEBA con bastantes palabras para cortar a la mitad.")
    ollama_simulado.retener(tras=0 if momento == "antes" else 2)
    cuerpo = _cuerpo("¿Hola, PRUEBA?", {})
    desde = _ultimo_id_de_bitacora()

    async def esperar(condicion, mensaje):
        limite = time.monotonic() + 30
        while not condicion() and time.monotonic() < limite:
            await asyncio.sleep(0.05)
        assert condicion(), mensaje

    async def escenario():
        llamada = llamar_asgi("POST", "/rag/consulta-con-historial-stream", json=cuerpo, cabeceras=sesion)
        if momento == "antes":
            await esperar(lambda: ollama_simulado.en_curso == 1, "el motor no llegó a recibir la consulta")
        else:
            await esperar(lambda: ollama_simulado.entregados >= 2, "el motor no entregó texto")
        llamada.desconectar()
        await esperar(lambda: ollama_simulado.cancelaciones == 1 and ollama_simulado.en_curso == 0,
                      "el motor no recibió la cancelación")
        await asyncio.wait_for(asyncio.shield(llamada.tarea), 30)

    asyncio.run(escenario())
    assert _mensajes_guardados(cuerpo["session_id"]) == 0
    assert _consultas_registradas(usuario_gubernamental.cedula, desde) == [], "una desconexión no se registra"


@pytest.mark.requisito("RF-11.68")
@pytest.mark.parametrize("caso", CASOS)
@pytest.mark.parametrize("chat", TRES_CHATS)
def test_historial_solo_turnos_terminados(chat, caso, cliente_api, sesion, registro_de_datos, ollama_simulado, monkeypatch):
    """RF-11.68 · solo el turno terminado deja su pregunta y su respuesta en el historial; el rechazado, el detenido por el
    tope y el que termina en error del motor no dejan nada."""
    _, session_id = _hacer_turno(caso, chat, cliente_api, sesion, registro_de_datos, ollama_simulado, monkeypatch)

    assert _mensajes_guardados(session_id) == (2 if caso == "terminado" else 0)


@pytest.mark.requisito("RF-21.60")
@pytest.mark.parametrize("caso", CASOS)
@pytest.mark.parametrize("chat", TRES_CHATS)
def test_bitacora_por_turno(chat, caso, cliente_api, sesion, usuario_gubernamental, registro_de_datos, ollama_simulado,
                            monkeypatch):
    """RF-21.60 · cada turno deja un solo registro de consulta al asistente, al terminar: sin motivo si terminó bien, y con el
    motivo fijo si fue rechazado, detenido por el tope o terminó en error del motor."""
    desde = _ultimo_id_de_bitacora()

    _hacer_turno(caso, chat, cliente_api, sesion, registro_de_datos, ollama_simulado, monkeypatch)

    registros = _consultas_registradas(usuario_gubernamental.cedula, desde)
    assert len(registros) == 1, f"se esperaba un registro por turno y hay {len(registros)}"
    assert registros[0].get("motivo") == MOTIVO_DEL_CASO[caso]
    assert registros[0]["tipo_consulta"] == {"general": "general", "tema": "expediente", "notebook": "notebook"}[chat]
