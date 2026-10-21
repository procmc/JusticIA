"""Conversaciones propias, de integración (spec 004b, T6; RNF-07.6, RNF-07.31, RNF-07.33, RNF-07.34, RF-21.32).

Usa la API real con dos Usuarios Gubernamentales `PRUEBA` (A, dueño de las conversaciones, y B, otro usuario), SQL Server y el
Redis simulado, y el Ollama simulado: lo que se comprueba es lo que RECIBE el modelo, lo que responde la API, lo que queda
guardado en la conversación (memoria y Redis) y lo que queda en la bitácora.
- RNF-07.31: B chatea con el identificador de una conversación de A y se le atiende como una conversación nueva.
- RNF-07.33: la conversación nueva guarda como dueño a quien la crea, aunque el identificador contenga a otro; las ya
  guardadas antes siguen siendo de su usuario, también con `_` en el correo; los chats de notebook no entran en la lista.
- RNF-07.6: ver, restaurar y eliminar la conversación de otro da el mismo 404 que una inexistente, sin cargarla.
- RNF-07.34: asociar el tema de la conversación de otro da la misma respuesta que con una inexistente, sin tocarla.
Los datos son inventados (prefijo `PRUEBA`) y cada prueba quita las conversaciones que crea.
"""
import dataclasses
import json
import logging
import uuid

import pytest
from sqlalchemy import text

from tests.integracion.conftest import RESPUESTA_SIMULADA, _consultar
from tests.soporte.flujos import crear_notebook, leer_eventos
from tests.soporte.nombres import PREFIJO_DATOS

CONSULTA_RAG = 12
GESTIONAR_CONVERSACION = 18
MOTIVO_CONVERSACION = "conversación no disponible"
INTENTO = f"Intento fallido: {MOTIVO_CONVERSACION}"
TEMA = "99-000123-0001-PE"        # un tema en el formato heredado: lo que la interfaz asocia al elegir el primer tema


# --- Apoyos ---------------------------------------------------------------------------------------------------------------------

def _almacen():
    from app.services.RAG.session_store import conversation_store

    return conversation_store


@pytest.fixture
def conversaciones():
    """La lista de identificadores de conversación que una prueba crea: al terminar se quitan de la memoria, de los índices y de
    Redis (su usuario es un correo y no un identificador `PRUEBA`, así que la limpieza de la suite no las alcanza)."""
    creadas = []
    yield creadas
    almacen = _almacen()
    redis = almacen._redis_history.redis_client
    for sesion in creadas:
        almacen._store.pop(sesion, None)
        almacen._metadata.pop(sesion, None)
        for lista in almacen._user_sessions.values():
            if sesion in lista:
                lista.remove(sesion)
        redis.delete(f"conversation:{sesion}", f"conversation_meta:{sesion}")
        for indice in list(redis.scan_iter("user_sessions:*")):
            redis.zrem(indice, sesion)


def _sesion(correo: str, notebook: int = None) -> str:
    base = f"session_notebook_{notebook}_{correo}" if notebook is not None else f"session_{correo}"
    return f"{base}_{uuid.uuid4().hex[:8]}"


def _chat(cliente, cabeceras, sesion: str, pregunta: str = f"{PREFIJO_DATOS} ¿qué dice el notebook?", **alcance):
    return cliente.post("/rag/consulta-con-historial-stream", headers=cabeceras,
                        json={"query": pregunta, "session_id": sesion, **alcance})


def _tipos_de_evento(respuesta) -> list:
    return [evento.get("type") for evento in leer_eventos(respuesta)]


def _lista(cliente, cabeceras) -> list:
    respuesta = cliente.get("/rag/conversations", headers=cabeceras)
    assert respuesta.status_code == 200
    return sorted(c["session_id"] for c in respuesta.json()["conversations"])


def _foto(sesion: str) -> tuple:
    """Lo que hay guardado de una conversación: su estado en memoria (si está) y su registro completo en Redis."""
    almacen = _almacen()
    en_memoria = None
    if sesion in almacen._metadata:
        meta = almacen._metadata[sesion]
        mensajes = [str(m.content) for m in almacen._store[sesion].messages] if sesion in almacen._store else None
        en_memoria = (meta.updated_at, meta.message_count, meta.title, mensajes)
    return en_memoria, almacen._redis_history.load_conversation(sesion)


def _marca_de_bitacora() -> int:
    return int(_consultar("SELECT COALESCE(MAX(CN_Id_bitacora), 0) FROM T_Bitacora")[0][0])


def _filas(usuario, tipo: int, desde: int) -> list:
    filas = _consultar(
        "SELECT CT_Texto, CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_usuario = :u AND CN_Id_tipo_accion = :t "
        "AND CN_Id_bitacora > :m ORDER BY CN_Id_bitacora", {"u": usuario.cedula, "t": tipo, "m": desde})
    return [{"texto": t, "info": json.loads(i) if i else {}} for t, i in filas]


def _crear_como(cliente, cabeceras, sesion: str, pregunta: str, conversaciones: list, **alcance) -> None:
    respuesta = _chat(cliente, cabeceras, sesion, pregunta, **alcance)
    assert respuesta.status_code == 200
    conversaciones.append(sesion)


def _recibido(ollama_simulado) -> str:
    return "\n".join(ollama_simulado.preguntas)


def _con_correo_con_guion_bajo(usuario):
    """El mismo usuario de prueba con un `_` en su correo (que el identificador `session_<correo>_<hora>` no distingue)."""
    from app.db.database import engine

    correo = f"prueba_guion_{usuario.cedula.lower()}@prueba.invalid"
    with engine.begin() as conexion:
        conexion.execute(text("UPDATE T_Usuario SET CT_Correo = :c WHERE CN_Id_usuario = :u"), {"c": correo, "u": usuario.cedula})
    return dataclasses.replace(usuario, correo=correo)


# --- RNF-07.31: la conversación de otro se atiende como nueva ----------------------------------------------------------------------

@pytest.mark.requisito("RNF-07.31")
@pytest.mark.requisito("RF-21.32")
@pytest.mark.parametrize("caso", ["general_guardada_antes", "general_creada_por_el_chat", "notebook"])
def test_conversacion_ajena_como_nueva(cliente_api, ajeno_ligero, registro_de_datos, ollama_simulado, conversaciones, caplog, caso):
    """RNF-07.31: B chatea con el identificador de una conversación de A (general guardada antes de esta spec, general
    creada por el chat, y de notebook): el modelo no recibe nada de A, la conversación de A queda igual en memoria y en Redis
    (mensajes, título, fecha), las listas de A y de B no cambian, B recibe su respuesta (200) y queda una fila de consulta
    y una de intento fallido «conversación no disponible» sin el identificador; el registro del servidor no lo repite.
    Control: A sí recibe su historial con ese identificador."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    caplog.set_level(logging.DEBUG, logger="app")
    a, b = ajeno_ligero.dueno, ajeno_ligero.otro
    secreto = f"PRUEBA secreto de A {uuid.uuid4().hex[:8]}"
    alcance_a, alcance_b = {}, {}
    if caso == "general_guardada_antes":
        sesion = ajeno_ligero.sesion_chat
        _almacen().get_session_history(sesion).add_user_message(secreto)
    elif caso == "general_creada_por_el_chat":
        sesion = _sesion(a.correo)
        _crear_como(cliente_api, ajeno_ligero.cabeceras_dueno, sesion, secreto, conversaciones)
    else:
        propio_b = crear_notebook(cliente_api, ajeno_ligero.cabeceras_otro, f"{PREFIJO_DATOS} notebook de B", registro_de_datos)
        sesion = _sesion(a.correo, ajeno_ligero.notebook["id"])
        alcance_a, alcance_b = {"notebook_id": str(ajeno_ligero.notebook["id"])}, {"notebook_id": str(propio_b["id"])}
        _crear_como(cliente_api, ajeno_ligero.cabeceras_dueno, sesion, secreto, conversaciones, **alcance_a)
    antes = _foto(sesion)
    lista_a, lista_b = _lista(cliente_api, ajeno_ligero.cabeceras_dueno), _lista(cliente_api, ajeno_ligero.cabeceras_otro)
    en_memoria = (set(_almacen()._store), set(_almacen()._metadata))
    ollama_simulado.preguntas.clear()
    marca = _marca_de_bitacora()
    caplog.clear()

    respuesta = _chat(cliente_api, ajeno_ligero.cabeceras_otro, sesion, f"{PREFIJO_DATOS} pregunta de B", **alcance_b)
    registro = caplog.text           # antes de que la propia prueba lea la conversación para compararla

    assert respuesta.status_code == 200 and _tipos_de_evento(respuesta), "B no recibió su respuesta"
    assert secreto not in _recibido(ollama_simulado), "el modelo recibió un mensaje de la conversación de A"
    assert _foto(sesion) == antes, "la conversación de A cambió"
    assert (set(_almacen()._store), set(_almacen()._metadata)) == en_memoria, "se creó una conversación en memoria"
    assert _almacen()._efimeras == {}, "la conversación efímera no se descartó al terminar la respuesta"
    assert _lista(cliente_api, ajeno_ligero.cabeceras_dueno) == lista_a and _lista(cliente_api, ajeno_ligero.cabeceras_otro) == lista_b
    filas = _filas(b, CONSULTA_RAG, marca)
    intentos = [f for f in filas if f["info"].get("motivo") == MOTIVO_CONVERSACION]
    assert len(filas) == 2 and len(intentos) == 1, filas
    assert intentos[0]["texto"] == INTENTO and intentos[0]["info"]["tipo_error"] == "acceso"
    assert sesion not in json.dumps(intentos, ensure_ascii=False), "el intento fallido lleva el identificador"
    assert sesion not in registro, "el registro del servidor repite la conversación pedida"
    # Control: con su propio token, A sí recibe su historial.
    ollama_simulado.preguntas.clear()
    assert _chat(cliente_api, ajeno_ligero.cabeceras_dueno, sesion, f"{PREFIJO_DATOS} otra de A", **alcance_a).status_code == 200
    assert secreto in _recibido(ollama_simulado), "control: A no recibió su propio historial"


# --- RNF-07.33: el dueño se fija al crear ------------------------------------------------------------------------------------------

@pytest.mark.requisito("RNF-07.33")
@pytest.mark.requisito("RNF-07.6")
def test_escritura_cruzada(cliente_api, ajeno_ligero, registro_de_datos, ollama_simulado, conversaciones):
    """RNF-07.33: B crea una conversación con un identificador que contiene el usuario de A: aparece en la lista de B y no en
    la de A, y A no puede verla, restaurarla, eliminarla ni usarla (su chat no recibe lo de B ni cambia la de B); B sí. Un chat
    de notebook con el usuario de A tampoco aparece en ninguna lista, y solo B lo ve."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    a, b = ajeno_ligero.cabeceras_dueno, ajeno_ligero.cabeceras_otro
    mensaje_de_b = f"{PREFIJO_DATOS} mensaje de B {uuid.uuid4().hex[:8]}"
    propio_b = crear_notebook(cliente_api, b, f"{PREFIJO_DATOS} notebook de B", registro_de_datos)
    general = _sesion(ajeno_ligero.dueno.correo)
    de_notebook = _sesion(ajeno_ligero.dueno.correo, propio_b["id"])
    lista_a = _lista(cliente_api, a)

    _crear_como(cliente_api, b, general, mensaje_de_b, conversaciones)
    _crear_como(cliente_api, b, de_notebook, mensaje_de_b, conversaciones, notebook_id=str(propio_b["id"]))

    assert general in _lista(cliente_api, b) and general not in _lista(cliente_api, a)
    assert de_notebook not in _lista(cliente_api, b) and de_notebook not in _lista(cliente_api, a)
    assert _lista(cliente_api, a) == lista_a
    for sesion in (general, de_notebook):
        assert cliente_api.get(f"/rag/conversations/{sesion}", headers=b).status_code == 200, "B no ve la suya"
        assert cliente_api.get(f"/rag/conversations/{sesion}", headers=a).status_code == 404
        assert cliente_api.post(f"/rag/conversations/{sesion}/restore", headers=a).status_code == 404
        assert cliente_api.delete(f"/rag/conversations/{sesion}", headers=a).status_code == 404
    antes = _foto(general)
    ollama_simulado.preguntas.clear()
    assert _chat(cliente_api, a, general, f"{PREFIJO_DATOS} pregunta de A").status_code == 200
    assert mensaje_de_b not in _recibido(ollama_simulado), "el chat de A cargó la conversación de B"
    assert _foto(general) == antes, "el chat de A cambió la conversación de B"
    assert cliente_api.get(f"/rag/conversations/{general}", headers=b).json()["conversation"]["messages"][0]["content"] == mensaje_de_b


@pytest.mark.requisito("RNF-07.33")
@pytest.mark.parametrize("correo_con_guion_bajo", [False, True], ids=["correo_normal", "correo_con_guion_bajo"])
def test_historial_igual_que_antes(cliente_api, usuario_gubernamental, iniciar_sesion, registro_de_datos, ollama_simulado,
                                   conversaciones, correo_con_guion_bajo):
    """RNF-07.33: las conversaciones propias ya guardadas antes de esta spec (sin dueño registrado), generales y de notebook,
    de un usuario con o sin `_` en el correo, siguen siendo suyas: el modelo recibe el historial de antes, la conversación
    crece, su lista no cambia y los datos guardados no se reescriben. Único efecto visible: las de un usuario con `_` pasan a
    poder verse, restaurarse y eliminarse (antes se le rechazaban)."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    usuario = _con_correo_con_guion_bajo(usuario_gubernamental) if correo_con_guion_bajo else usuario_gubernamental
    cabeceras = iniciar_sesion(usuario)
    notebook = crear_notebook(cliente_api, cabeceras, f"{PREFIJO_DATOS} notebook propio", registro_de_datos)
    almacen = _almacen()
    guardadas = {
        _sesion(usuario.correo): {},
        _sesion(usuario.correo, notebook["id"]): {"notebook_id": str(notebook["id"])},
    }
    marcas = {}
    for sesion in guardadas:
        marcas[sesion] = f"PRUEBA mensaje de antes {uuid.uuid4().hex[:8]}"
        conversaciones.append(sesion)
        almacen.get_session_history(sesion).add_user_message(marcas[sesion])      # como lo guardaba el sistema: sin dueño
    registros_antes = {s: almacen._redis_history.load_conversation(s)["metadata"] for s in guardadas}
    assert all("dueno" not in meta for meta in registros_antes.values()), "precondición: guardadas sin dueño"
    lista_antes = _lista(cliente_api, cabeceras)
    for sesion in guardadas:                    # solo en Redis, como una conversación que el servidor ya no tiene en memoria
        almacen._store.pop(sesion, None)
        almacen._metadata.pop(sesion, None)

    for sesion, alcance in guardadas.items():
        ollama_simulado.preguntas.clear()
        respuesta = _chat(cliente_api, cabeceras, sesion, f"{PREFIJO_DATOS} otra pregunta", **alcance)
        assert respuesta.status_code == 200
        assert marcas[sesion] in _recibido(ollama_simulado), "el modelo no recibió el historial de antes"
        detalle = cliente_api.get(f"/rag/conversations/{sesion}", headers=cabeceras)
        assert detalle.status_code == 200, "el dueño no ve su conversación"
        contenidos = [m["content"] for m in detalle.json()["conversation"]["messages"]]
        assert contenidos[0] == marcas[sesion] and len(contenidos) == 3, contenidos
        guardado = almacen._redis_history.load_conversation(sesion)["metadata"]
        assert "dueno" not in guardado and guardado["user_id"] == registros_antes[sesion]["user_id"] and guardado["created_at"] == registros_antes[sesion]["created_at"]
    assert _lista(cliente_api, cabeceras) == lista_antes, "la lista de conversaciones del usuario cambió"
    for sesion in guardadas:
        almacen._store.pop(sesion, None)
        almacen._metadata.pop(sesion, None)
        assert cliente_api.post(f"/rag/conversations/{sesion}/restore", headers=cabeceras).status_code == 200
        assert cliente_api.delete(f"/rag/conversations/{sesion}", headers=cabeceras).status_code == 200
        assert cliente_api.get(f"/rag/conversations/{sesion}", headers=cabeceras).status_code == 404


@pytest.mark.requisito("RNF-07.6")
@pytest.mark.requisito("RNF-07.31")
def test_restaurar_no_carga_la_ajena(cliente_api, ajeno_ligero, conversaciones):
    """RNF-07.6: B restaura una conversación de A que el servidor solo tiene en Redis: el mismo 404 que con una inexistente
    (salvo el identificador) y la de A no se carga a la memoria, ni siquiera un instante; Redis queda igual. A sí la restaura."""
    almacen = _almacen()
    sesion = ajeno_ligero.sesion_chat
    almacen._store.pop(sesion, None)
    almacen._metadata.pop(sesion, None)
    antes = almacen._redis_history.load_conversation(sesion)
    en_memoria = (set(almacen._store), set(almacen._metadata), {u: list(s) for u, s in almacen._user_sessions.items()})
    inexistente = _sesion(ajeno_ligero.otro.correo)

    de_otro = cliente_api.post(f"/rag/conversations/{sesion}/restore", headers=ajeno_ligero.cabeceras_otro)
    sin_conversacion = cliente_api.post(f"/rag/conversations/{inexistente}/restore", headers=ajeno_ligero.cabeceras_otro)

    assert de_otro.status_code == sin_conversacion.status_code == 404
    assert de_otro.text.replace(sesion, "<sesion>") == sin_conversacion.text.replace(inexistente, "<sesion>")
    assert (set(almacen._store), set(almacen._metadata), {u: list(s) for u, s in almacen._user_sessions.items()}) == en_memoria
    assert almacen._redis_history.load_conversation(sesion) == antes
    assert cliente_api.post(f"/rag/conversations/{sesion}/restore", headers=ajeno_ligero.cabeceras_dueno).status_code == 200


# --- RNF-07.34: asociar el tema de una conversación -------------------------------------------------------------------------------

def _asociar(cliente, cabeceras, sesion: str, accion: str, tema: str = TEMA):
    return cliente.post("/rag/update-expediente-context", headers=cabeceras,
                        json={"session_id": sesion, "expediente_number": tema, "action": accion})


@pytest.mark.requisito("RNF-07.34")
@pytest.mark.requisito("RF-21.32")
@pytest.mark.parametrize("accion", ["set", "change"])
def test_tema_de_conversacion_ajena_no_la_toca(cliente_api, ajeno_ligero, registro_de_datos, ollama_simulado, conversaciones,
                                               caplog, accion):
    """RNF-07.34: B asocia (`set`) o cambia (`change`) el tema en una conversación de A (general guardada antes y de notebook):
    el MISMO código y cuerpo que con una inexistente (salvo el identificador y el tema que repite), la de A queda igual en
    memoria y en Redis, las listas de A y de B no cambian, una fila de intento (tipo 18) por petición, y el registro del
    servidor no lleva ni el identificador ni el tema."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    caplog.set_level(logging.DEBUG, logger="app")
    a, b = ajeno_ligero.cabeceras_dueno, ajeno_ligero.cabeceras_otro
    de_notebook = _sesion(ajeno_ligero.dueno.correo, ajeno_ligero.notebook["id"])
    _crear_como(cliente_api, a, de_notebook, f"{PREFIJO_DATOS} chat del notebook", conversaciones,
                notebook_id=str(ajeno_ligero.notebook["id"]))
    ajenas = [ajeno_ligero.sesion_chat, de_notebook]
    antes = {s: _foto(s) for s in ajenas}
    listas = (_lista(cliente_api, a), _lista(cliente_api, b))
    en_memoria = (set(_almacen()._store), set(_almacen()._metadata))
    marca = _marca_de_bitacora()
    tema = f"{TEMA}-PRUEBA{uuid.uuid4().hex[:6]}"
    caplog.clear()

    respuestas = [_asociar(cliente_api, b, sesion, accion, tema) for sesion in ajenas]
    registro = caplog.text           # antes de que la propia prueba lea las conversaciones para compararlas

    assert (set(_almacen()._store), set(_almacen()._metadata)) == en_memoria, "se creó o cargó una conversación"
    assert {s: _foto(s) for s in ajenas} == antes, "la conversación de A cambió"
    assert (_lista(cliente_api, a), _lista(cliente_api, b)) == listas
    filas = _filas(ajeno_ligero.otro, GESTIONAR_CONVERSACION, marca)
    assert len(filas) == len(ajenas) and all(f["texto"] == INTENTO and f["info"]["tipo_error"] == "acceso" for f in filas), filas
    assert all(sesion not in json.dumps(filas, ensure_ascii=False) for sesion in ajenas)
    assert sesion_en_el_registro(registro, ajenas + [tema]) == [], "el registro del servidor repite lo pedido"
    # Lo mismo que con una conversación inexistente (que se crea, con su dueño B).
    inexistente = _sesion(ajeno_ligero.otro.correo)
    conversaciones.append(inexistente)
    nueva = _asociar(cliente_api, b, inexistente, accion, tema)
    for sesion, respuesta in zip(ajenas, respuestas):
        assert respuesta.status_code == nueva.status_code == 200
        assert respuesta.text.replace(sesion, "<sesion>") == nueva.text.replace(inexistente, "<sesion>")


def sesion_en_el_registro(registro: str, datos: list) -> list:
    return [dato for dato in datos if dato in registro]


@pytest.mark.requisito("RNF-07.34")
@pytest.mark.requisito("RNF-07.33")
def test_tema_de_conversacion_nueva_fija_el_dueno(cliente_api, ajeno_ligero, conversaciones):
    """RNF-07.33 y RNF-07.34: asociar el tema a una conversación que no existe la crea con los dos avisos y como dueño a quien
    la pide, aunque el identificador contenga a otro: aparece en su lista y no en la del otro, que no puede verla, restaurarla
    ni eliminarla."""
    a, b = ajeno_ligero.cabeceras_dueno, ajeno_ligero.cabeceras_otro
    sesion = _sesion(ajeno_ligero.dueno.correo)           # B la nombra con el usuario de A
    conversaciones.append(sesion)

    respuesta = _asociar(cliente_api, b, sesion, "set")

    assert respuesta.status_code == 200 and respuesta.json()["success"] is True
    assert sesion in _lista(cliente_api, b) and sesion not in _lista(cliente_api, a)
    detalle = cliente_api.get(f"/rag/conversations/{sesion}", headers=b)
    assert detalle.status_code == 200 and len(detalle.json()["conversation"]["messages"]) == 2
    assert cliente_api.get(f"/rag/conversations/{sesion}", headers=a).status_code == 404
    assert cliente_api.post(f"/rag/conversations/{sesion}/restore", headers=a).status_code == 404
    assert cliente_api.delete(f"/rag/conversations/{sesion}", headers=a).status_code == 404
    assert cliente_api.get(f"/rag/conversations/{sesion}", headers=b).status_code == 200


@pytest.mark.requisito("RNF-07.34")
def test_tema_de_conversacion_500_sin_detalle(cliente_api, ajeno_ligero, caplog):
    """RNF-07.34: si asociar el tema falla por un error inesperado (aquí el servicio simulado lanza con una ruta inventada) la
    respuesta es 500 «Error interno del servidor», sin el texto de la excepción ni la ruta, ni en el cuerpo ni en el
    registro del servidor."""
    from app.services.RAG import rag_chain_service

    caplog.set_level(logging.DEBUG, logger="app")
    ruta = f"/srv/{PREFIJO_DATOS}_interno/almacen_{uuid.uuid4().hex[:6]}.py"
    servicio = rag_chain_service._rag_service or rag_chain_service.RAGChainService()
    rag_chain_service._rag_service = servicio

    async def _falla(*args, **kwargs):
        raise RuntimeError(f"falla simulada en {ruta}")

    servicio.update_expediente_context = _falla
    try:
        respuesta = _asociar(cliente_api, ajeno_ligero.cabeceras_otro, _sesion(ajeno_ligero.otro.correo), "set")
    finally:
        servicio.__dict__.pop("update_expediente_context", None)

    assert respuesta.status_code == 500 and respuesta.json() == {"detail": "Error interno del servidor"}
    assert ruta not in respuesta.text and ruta not in caplog.text, "la ruta de la excepción salió a la respuesta o al registro"

