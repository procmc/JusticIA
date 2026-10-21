"""Aislamiento de los notebooks entre usuarios, parte de integración (spec 004b, T2; RF-17.3, RF-11.31, RF-17.31, RF-17.32,
RF-11.30, RF-21.33; T3: RF-17.3, RF-17.31, RF-21.33 en temas similares y resumen IA; T4: RF-11.32, RF-21.31, RF-21.32,
RF-17.4 en el chat del notebook y en la carga).

Usa la API real con dos Usuarios Gubernamentales `PRUEBA` (el dueño de un notebook y otro), SQL Server, Tika, Qdrant y los
embeddings reales del entorno aislado, y el Ollama simulado: lo que se comprueba es lo que RECIBE el modelo, lo que responde
la API y lo que queda en la bitácora, no el texto de una respuesta real.
- RF-17.3: la búsqueda del chat excluye lo ajeno dentro de la consulta (los fragmentos ajenos mejor puntuados no reducen los
  resultados propios; una clave en otra grafía o de un notebook sin registro no llega a nadie), y lo propio y el tema
  general siguen apareciendo.
- RF-11.31, RF-17.31 y RF-21.33: el chat por tema con forma de clave de notebook es el chat general del usuario, y su
  bitácora no lleva la clave (con la ajena o la inexistente, además, el intento fallido con su motivo).
- RF-17.32: la clave mencionada en la pregunta no se detecta como tema.
Los datos son inventados (prefijo `PRUEBA`) y se limpian solos.
"""
import asyncio
import json
import logging
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from tests.integracion.conftest import (
    RESPUESTA_SIMULADA, _consultar, _consultar_chat, _documento_procesado_en_el_notebook, _pregunta_sobre,
    _todo_lo_que_recibio_el_modelo,
)
from tests.soporte.flujos import (
    DocumentoPrueba, cargar, crear_notebook, documento_de_prueba, foto_de_efectos, leer_eventos, tema_heredado,
)
from tests.soporte.nombres import PREFIJO_DATOS

pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")

CONSULTA_RAG = 12
MOTIVO_NOTEBOOK = "notebook no disponible"


# --- Apoyos ---------------------------------------------------------------------------------------------------------------------

def _documento_de_otro_asunto() -> DocumentoPrueba:
    """Un documento inventado sobre un asunto sin relación con los de `documento_de_prueba` (la quebrada ficticia), para que
    una consulta sobre aquellos lo deje muy abajo en el orden de similitud."""
    base = documento_de_prueba()
    sufijo = base.nombre[len(PREFIJO_DATOS) + 1:-len(".txt")]
    frase = f"la receta ficticia {sufijo} mezcla harina de maíz imaginaria con miel de abejas inventadas"
    texto = (f"{PREFIJO_DATOS} receta inventada número {sufijo}. {frase}. Es un texto ficticio de cocina sin relación con ningún "
             "trámite: ingredientes, pasos y tiempos de horneado que no existen, repetidos para formar un fragmento completo.")
    return DocumentoPrueba(nombre=f"{PREFIJO_DATOS}_{sufijo}.txt", contenido=texto.encode("utf-8"), frase=frase)


def _ids_visibles(cedula: str) -> set:
    from app.db.database import SessionLocal
    from app.services.notebook_service import NotebookService

    with SessionLocal() as db:
        return asyncio.run(NotebookService().ids_documentos_visibles(db, cedula))


def _buscar(consulta: str, visibles: set, k: int) -> list:
    from app.vectorstore import get_vectorstore_backend

    return asyncio.run(get_vectorstore_backend().search_by_text(consulta, top_k=k, score_threshold=0.0, documentos_visibles=visibles))


def _puntos_del_documento(id_documento: int) -> list:
    """Los puntos de Qdrant de un documento, con su carga útil."""
    import os

    from qdrant_client.models import FieldCondition, Filter, MatchValue

    from tests.soporte import entorno

    cliente = entorno.cliente_qdrant()
    try:
        filtro = Filter(must=[FieldCondition(key="metadata.id_documento", match=MatchValue(value=id_documento))])
        puntos, _ = cliente.scroll(collection_name=os.environ["QDRANT_COLLECTION_NAME"], scroll_filter=filtro, limit=100,
                                   with_payload=True)
        return list(puntos)
    finally:
        cliente.close()


def _cambiar_el_tema_en_la_base(id_documento: int, tema: str) -> None:
    """Deja al documento unido SOLO al tema `tema` en la base (que se crea si hace falta): simula datos guardados con otra
    grafía de la clave o con la clave de un notebook que no existe, que la API de hoy ya no deja crear."""
    from app.db.database import engine

    with engine.begin() as conexion:
        existe = conexion.execute(text("SELECT COUNT(*) FROM T_Expediente WHERE CT_Num_expediente = :t"), {"t": tema}).scalar()
        if not existe:
            conexion.execute(text("INSERT INTO T_Expediente (CT_Num_expediente, CF_Fecha_creacion) VALUES (:t, GETDATE())"), {"t": tema})
        conexion.execute(
            text("UPDATE T_Expediente_Documento SET CN_Id_expediente = (SELECT CN_Id_expediente FROM T_Expediente "
                 "WHERE CT_Num_expediente = :t) WHERE CN_Id_documento = :d"),
            {"t": tema, "d": id_documento})


def _marca_de_bitacora() -> int:
    return int(_consultar("SELECT COALESCE(MAX(CN_Id_bitacora), 0) FROM T_Bitacora")[0][0])


def _filas_nuevas(usuario, desde: int) -> list:
    """Las filas de consulta del usuario posteriores a la marca: `{texto, expediente, info}` con `info` ya decodificado."""
    filas = _consultar(
        "SELECT CT_Texto, CN_Id_expediente, CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_usuario = :u "
        "AND CN_Id_tipo_accion = :t AND CN_Id_bitacora > :m ORDER BY CN_Id_bitacora",
        {"u": usuario.cedula, "t": CONSULTA_RAG, "m": desde})
    return [{"texto": t, "expediente": e, "info": json.loads(i) if i else {}} for t, e, i in filas]


_VOLATIL = ("timestamp", "session_id", "tiempo_procesamiento_segundos")


def _sin_lo_volatil(filas: list) -> list:
    """Las filas sin lo que cambia en cada petición (hora, sesión, tiempo), en un orden estable, para compararlas."""
    limpias = [{"texto": f["texto"], "expediente": f["expediente"], "info": {k: v for k, v in f["info"].items() if k not in _VOLATIL}}
               for f in filas]
    return sorted(limpias, key=lambda f: json.dumps(f, sort_keys=True, ensure_ascii=False))


def _preguntar(cliente_api, ollama_simulado, cabeceras, pregunta: str, **alcance):
    """Hace la consulta con el modelo recién vaciado y devuelve `(respuesta, lo que recibió el modelo sin la pregunta)`."""
    ollama_simulado.preguntas.clear()
    respuesta = _consultar_chat(cliente_api, cabeceras, pregunta, **alcance)
    return respuesta, _todo_lo_que_recibio_el_modelo(ollama_simulado, pregunta)


def _tipos_de_evento(respuesta) -> list:
    return [evento.get("type") for evento in leer_eventos(respuesta)]


# --- RF-17.3: lo ajeno no reduce los resultados propios --------------------------------------------------------------------

@pytest.mark.requisito("RF-17.3")
def test_ajenos_mejor_puntuados_no_reducen_resultados(cliente_api, ajeno, registro_de_datos, procesamiento_en_prueba):
    """RF-17.3: el dueño tiene tres documentos que responden a la consulta mucho mejor que el único documento del otro usuario.
    Con `k` menor que los fragmentos ajenos, la búsqueda del otro usuario le devuelve igual su documento (la misma cantidad
    que si lo ajeno no existiera) y ninguno del dueño: la exclusión ocurre dentro de la consulta, no después de recuperar."""
    dueno_extra = [_documento_procesado_en_el_notebook(cliente_api, ajeno.cabeceras_dueno, procesamiento_en_prueba,
                                                       ajeno.notebook)[0] for _ in range(2)]
    del dueno_extra
    notebook_otro = crear_notebook(cliente_api, ajeno.cabeceras_otro, f"{PREFIJO_DATOS} notebook del otro", registro_de_datos)
    propio, id_propio = _documento_procesado_en_el_notebook(
        cliente_api, ajeno.cabeceras_otro, procesamiento_en_prueba, notebook_otro, _documento_de_otro_asunto())
    fragmentos_propios = len(_puntos_del_documento(id_propio))
    assert fragmentos_propios >= 1

    resultados = _buscar(ajeno.documento.frase, _ids_visibles(ajeno.otro.cedula), k=2)

    nombres = [r["document_name"] for r in resultados]
    assert set(nombres) == {propio.nombre}, f"se esperaba solo el documento propio y llegó {nombres}"
    assert len(resultados) == min(2, fragmentos_propios)


@pytest.mark.requisito("RF-17.3")
def test_el_dueno_y_el_otro_reciben_lo_suyo_y_el_tema_general(cliente_api, ajeno, registro_de_datos, procesamiento_en_prueba,
                                                              ollama_simulado):
    """RF-17.3: los notebooks propios y los temas generales siguen apareciendo en el chat general: el dueño recibe su
    documento; el otro usuario recibe el suyo y el de un tema general (y ninguno de ellos recibe el del otro)."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    notebook_otro = crear_notebook(cliente_api, ajeno.cabeceras_otro, f"{PREFIJO_DATOS} notebook del otro", registro_de_datos)
    propio, _ = _documento_procesado_en_el_notebook(cliente_api, ajeno.cabeceras_otro, procesamiento_en_prueba, notebook_otro)
    general, _ = _documento_procesado_en_el_notebook(
        cliente_api, ajeno.cabeceras_otro, procesamiento_en_prueba, {"clave_interna": tema_heredado(registro_de_datos)})

    def recibido_por(cabeceras, documento) -> str:
        respuesta, recibido = _preguntar(cliente_api, ollama_simulado, cabeceras, _pregunta_sobre(documento))
        assert respuesta.status_code == 200
        return recibido

    del_dueno = recibido_por(ajeno.cabeceras_dueno, ajeno.documento)
    assert ajeno.documento.frase in del_dueno and ajeno.documento.nombre in del_dueno, "el dueño no recibió su documento"

    del_otro = recibido_por(ajeno.cabeceras_otro, propio)
    assert propio.frase in del_otro and propio.nombre in del_otro, "el otro usuario no recibió su documento"
    assert ajeno.documento.frase not in del_otro and ajeno.documento.nombre not in del_otro

    del_otro = recibido_por(ajeno.cabeceras_otro, general)
    assert general.frase in del_otro and general.nombre in del_otro, "el otro usuario no recibió el documento del tema general"
    assert ajeno.documento.frase not in del_otro


@pytest.mark.requisito("RF-17.3")
def test_grafia_distinta_y_sin_notebook_no_llegan(cliente_api, ajeno, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    """RF-17.3: los fragmentos de un notebook con otra grafía de la clave (en la base o solo en Qdrant) o de un notebook que
    no existe no llegan al otro usuario por el chat general. Solo el dueño recibe lo que está en su notebook (aunque el
    fragmento diga `nb-<id>`); `NB-0<id>` y la clave sin notebook no son de nadie."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    heredado = {"clave_interna": tema_heredado(registro_de_datos)}
    id_dueno = ajeno.notebook["id"]
    casos = {}
    for nombre in ("ceros", "sin_notebook", "minusculas"):
        casos[nombre] = _documento_procesado_en_el_notebook(cliente_api, ajeno.cabeceras_dueno, procesamiento_en_prueba, heredado)
    _cambiar_el_tema_en_la_base(casos["ceros"][1], f"NB-0{id_dueno}")
    _cambiar_el_tema_en_la_base(casos["sin_notebook"][1], f"NB-{ajeno.id_inexistente}")
    _cambiar_el_tema_en_la_base(casos["minusculas"][1], ajeno.notebook["clave_interna"])
    registro_de_datos.registrar_tema(f"NB-0{id_dueno}")
    registro_de_datos.registrar_tema(f"NB-{ajeno.id_inexistente}")
    # En Qdrant el fragmento del tercero dice `nb-<id>` (la grafía guardada de otro modo): se anotan sus puntos para limpiarlos.
    import os

    from qdrant_client.models import FieldCondition, Filter, MatchValue

    from tests.soporte import entorno

    cliente = entorno.cliente_qdrant()
    try:
        for punto in _puntos_del_documento(casos["minusculas"][1]):
            registro_de_datos.registrar_punto(punto.id)
        cliente.set_payload(
            collection_name=os.environ["QDRANT_COLLECTION_NAME"], payload={"numero_expediente": f"nb-{id_dueno}"}, key="metadata",
            points=Filter(must=[FieldCondition(key="metadata.id_documento", match=MatchValue(value=casos["minusculas"][1]))]))
    finally:
        cliente.close()

    for nombre, (documento, _) in casos.items():
        pregunta = _pregunta_sobre(documento)
        respuesta, recibido = _preguntar(cliente_api, ollama_simulado, ajeno.cabeceras_otro, pregunta)
        assert respuesta.status_code == 200
        assert documento.frase not in recibido and documento.nombre not in recibido, f"el otro usuario recibió el caso «{nombre}»"
        respuesta, del_dueno = _preguntar(cliente_api, ollama_simulado, ajeno.cabeceras_dueno, pregunta)
        assert respuesta.status_code == 200
        assert (documento.frase in del_dueno) == (nombre == "minusculas"), f"el dueño y el caso «{nombre}»"


# --- RF-11.31, RF-17.31, RF-21.33: el chat por tema con la clave de un notebook ---------------------------------------------

@pytest.mark.requisito("RF-11.31")
@pytest.mark.requisito("RF-17.31")
@pytest.mark.requisito("RF-21.33")
def test_chat_por_tema_con_clave_es_general(cliente_api, ajeno, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    """RF-11.31 y RF-17.31: el otro usuario pregunta lo mismo en el chat general y en el chat por tema con la clave del
    notebook del dueño (`NB-<id>`, `nb-<id>`), con una inexistente y con la suya propia: el contexto que recibe el modelo es
    igual al del chat general y no trae nada del dueño; mismo código y misma estructura de respuesta.
    RF-21.33: con la clave ajena o inexistente la bitácora deja el intento fallido «notebook no disponible» y la consulta
    general, idénticos entre sí; con la propia, solo la consulta general; la clave no aparece en ninguna fila."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    notebook_otro = crear_notebook(cliente_api, ajeno.cabeceras_otro, f"{PREFIJO_DATOS} notebook del otro", registro_de_datos)
    _documento_procesado_en_el_notebook(cliente_api, ajeno.cabeceras_otro, procesamiento_en_prueba, notebook_otro)
    pregunta = _pregunta_sobre(ajeno.documento)
    clave = ajeno.notebook["clave_interna"]
    claves = {
        "ajena": clave, "ajena_en_minusculas": clave.lower(), "inexistente": f"NB-{ajeno.id_inexistente}",
        "propia": notebook_otro["clave_interna"],
    }

    marca = _marca_de_bitacora()
    general, contexto_general = _preguntar(cliente_api, ollama_simulado, ajeno.cabeceras_otro, pregunta)
    filas_generales = _sin_lo_volatil(_filas_nuevas(ajeno.otro, marca))
    assert general.status_code == 200
    assert ajeno.documento.frase not in contexto_general, "el chat general entregó el contenido del dueño"

    filas = {}
    for caso, tema in claves.items():
        marca = _marca_de_bitacora()
        respuesta, contexto = _preguntar(cliente_api, ollama_simulado, ajeno.cabeceras_otro, pregunta, expediente_number=tema)
        assert respuesta.status_code == general.status_code, caso
        assert _tipos_de_evento(respuesta) == _tipos_de_evento(general), f"estructura distinta en «{caso}»"
        assert contexto == contexto_general, f"el contexto de «{caso}» no es el del chat general"
        for dato in (ajeno.documento.frase, ajeno.documento.nombre, ajeno.notebook["nombre"]):
            assert dato not in contexto, f"el contexto de «{caso}» trae {dato!r}"
        filas[caso] = _filas_nuevas(ajeno.otro, marca)

    # Bitácora: sin la clave en ningún campo; ajena e inexistente dejan lo mismo.
    for caso, tema in claves.items():
        crudo = json.dumps(filas[caso], ensure_ascii=False).casefold()
        assert tema.casefold() not in crudo, f"la bitácora de «{caso}» lleva la clave"
    assert _sin_lo_volatil(filas["ajena"]) == _sin_lo_volatil(filas["ajena_en_minusculas"]) == _sin_lo_volatil(filas["inexistente"])
    consultas = [f for f in filas["ajena"] if f["info"].get("tipo_consulta") == "general"]
    intentos = [f for f in filas["ajena"] if f["info"].get("motivo") == MOTIVO_NOTEBOOK]
    assert len(filas["ajena"]) == 2 and len(consultas) == 1 and len(intentos) == 1, filas["ajena"]
    assert "expediente_numero" not in consultas[0]["info"] and consultas[0]["expediente"] is None
    assert intentos[0]["info"]["tipo_error"] == "acceso" and intentos[0]["expediente"] is None
    assert intentos[0]["texto"] == f"Intento fallido: {MOTIVO_NOTEBOOK}"
    # La propia no es un intento sobre algo ajeno: solo la consulta general, igual a la del chat general.
    assert _sin_lo_volatil(filas["propia"]) == filas_generales


# --- RF-17.32 y RF-11.30: la clave en la pregunta no es un tema -------------------------------------------------------------

@pytest.mark.requisito("RF-17.32")
def test_clave_en_la_pregunta_no_se_detecta(cliente_api, ajeno, ollama_simulado):
    """RF-17.32: el otro usuario escribe en su pregunta la clave del notebook del dueño (y la pregunta nombra su documento):
    la clave no se toma como tema y el modelo no recibe nada del dueño (ni frase, ni nombre de archivo, ni nombre del
    notebook); la consulta se atiende como el chat general."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    pregunta = f"{_pregunta_sobre(ajeno.documento)} Revisa también {ajeno.notebook['clave_interna']} y {ajeno.notebook['clave_interna'].lower()}."

    respuesta, recibido = _preguntar(cliente_api, ollama_simulado, ajeno.cabeceras_otro, pregunta)

    assert respuesta.status_code == 200
    for dato in (ajeno.documento.frase, ajeno.documento.nombre, ajeno.notebook["nombre"]):
        assert dato not in recibido, f"el modelo recibió {dato!r}"


@pytest.mark.requisito("RF-11.30")
def test_chat_por_tema_heredado_no_cambia(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    """RF-11.30: el chat por un tema en formato heredado sigue acotado a ese tema: el modelo recibe su documento y no el de otro
    tema, aunque la pregunta nombre al otro (la exclusión de lo ajeno no cambia este chat)."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    tema = tema_heredado(registro_de_datos)
    en_el_tema, _ = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, {"clave_interna": tema})
    en_otro, _ = _documento_procesado_en_el_notebook(
        cliente_api, sesion, procesamiento_en_prueba, {"clave_interna": tema_heredado(registro_de_datos)})
    pregunta = _pregunta_sobre(en_otro)

    respuesta, recibido = _preguntar(cliente_api, ollama_simulado, sesion, pregunta, expediente_number=tema)

    assert respuesta.status_code == 200
    assert en_el_tema.frase in recibido and en_otro.frase not in recibido


# --- RF-17.3, RF-17.31, RF-21.33 (T3): temas similares y resumen IA -------------------------------------------------------------

BUSQUEDA_SIMILARES = 1
GENERAR_RESUMEN = 13


def _filas_de(usuario, tipo: int, desde: int) -> list:
    """Las filas del usuario de ese tipo posteriores a la marca: `{texto, expediente, info}` con `info` ya decodificado."""
    filas = _consultar(
        "SELECT CT_Texto, CN_Id_expediente, CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_usuario = :u "
        "AND CN_Id_tipo_accion = :t AND CN_Id_bitacora > :m ORDER BY CN_Id_bitacora",
        {"u": usuario.cedula, "t": tipo, "m": desde})
    return [{"texto": t, "expediente": e, "info": json.loads(i) if i else {}} for t, e, i in filas]


def _busqueda_por_tema(cliente_api, cabeceras, tema: str):
    return cliente_api.post("/similarity/search", headers=cabeceras,
                            json={"modo_busqueda": "expediente", "numero_expediente": tema, "limite": 30, "umbral_similitud": 0.1})


def _resumen_de(cliente_api, cabeceras, tema: str):
    return cliente_api.post("/similarity/generate-summary", headers=cabeceras, json={"numero_expediente": tema})


def _forma_de(respuesta, tema: str):
    """Código y cuerpo de la respuesta con lo que cambia en cada petición (tiempos) fuera y el tema pedido sustituido."""
    cuerpo = respuesta.text.replace(tema, "<tema>")
    try:
        datos = json.loads(cuerpo)
    except ValueError:
        return respuesta.status_code, cuerpo
    if isinstance(datos, dict):
        datos = {k: v for k, v in datos.items() if not k.startswith("tiempo_")}
    return respuesta.status_code, datos


@pytest.mark.requisito("RF-17.3")
@pytest.mark.requisito("RF-17.31")
@pytest.mark.requisito("RF-21.33")
def test_similares_y_resumen_con_clave_como_inexistente(cliente_api, ajeno, registro_de_datos, ollama_simulado):
    """RF-17.31: el otro usuario pide temas similares por tema de referencia y el resumen IA con la clave del notebook del dueño
    (en cualquier grafía), con una inexistente y con la de su propio notebook: la respuesta es la de un tema inexistente (mismo
    código y cuerpo, sin nada del dueño) y el modelo no recibe nada. RF-21.33: la bitácora deja la fila normal sin la clave (ni
    en el texto ni en el tema asociado), más el intento fallido «notebook no disponible» con la ajena y la inexistente
    (idénticas entre sí); con la propia, solo la fila normal: no hay nada no disponible que registrar."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    sin_documentos = f"{PREFIJO_DATOS} tema sin documentos"
    clave = ajeno.notebook["clave_interna"]
    propio = crear_notebook(cliente_api, ajeno.cabeceras_otro, f"{PREFIJO_DATOS} notebook del otro", registro_de_datos)
    claves = {"ajena": clave, "ajena_en_minusculas": clave.lower(), "inexistente": f"NB-{ajeno.id_inexistente}",
              "propia": propio["clave_interna"]}

    esperadas = {
        "busqueda": _forma_de(_busqueda_por_tema(cliente_api, ajeno.cabeceras_otro, sin_documentos), sin_documentos),
        "resumen": _forma_de(_resumen_de(cliente_api, ajeno.cabeceras_otro, sin_documentos), sin_documentos),
    }
    ollama_simulado.preguntas.clear()

    filas = {}
    for caso, tema in claves.items():
        marca = _marca_de_bitacora()
        busqueda = _busqueda_por_tema(cliente_api, ajeno.cabeceras_otro, tema)
        resumen = _resumen_de(cliente_api, ajeno.cabeceras_otro, tema)
        assert _forma_de(busqueda, tema) == esperadas["busqueda"], f"la búsqueda de «{caso}» no es la de un tema inexistente"
        assert _forma_de(resumen, tema) == esperadas["resumen"], f"el resumen de «{caso}» no es el de un tema inexistente"
        for respuesta in (busqueda, resumen):
            for dato in (ajeno.documento.frase, ajeno.documento.nombre, ajeno.notebook["nombre"]):
                assert dato not in respuesta.text, f"la respuesta de «{caso}» trae {dato!r}"
        filas[caso] = {"busqueda": _filas_de(ajeno.otro, BUSQUEDA_SIMILARES, marca), "resumen": _filas_de(ajeno.otro, GENERAR_RESUMEN, marca)}

    assert not _todo_lo_que_recibio_el_modelo(ollama_simulado), "el modelo recibió algo con la clave de un notebook"
    for caso, tema in claves.items():
        crudo = json.dumps(filas[caso], ensure_ascii=False).casefold()
        assert tema.casefold() not in crudo, f"la bitácora de «{caso}» lleva la clave"
        for accion, resultado in filas[caso].items():
            intentos = [f for f in resultado if f["info"].get("motivo") == MOTIVO_NOTEBOOK]
            assert all(f["expediente"] is None for f in resultado), "la fila quedó asociada al tema del notebook"
            if caso == "propia":
                assert len(resultado) == 1 and not intentos, f"«{caso}», {accion}: {resultado}"
                continue
            assert len(resultado) == 2 and len(intentos) == 1, f"«{caso}», {accion}: {resultado}"
            assert intentos[0]["info"]["tipo_error"] == "acceso" and intentos[0]["texto"] == f"Intento fallido: {MOTIVO_NOTEBOOK}"
    for accion in ("busqueda", "resumen"):
        assert (_sin_lo_volatil(filas["ajena"][accion]) == _sin_lo_volatil(filas["ajena_en_minusculas"][accion])
                == _sin_lo_volatil(filas["inexistente"][accion]))


@pytest.mark.requisito("RF-17.3")
def test_similares_por_tema_no_trae_lo_ajeno(cliente_api, ajeno, registro_de_datos, procesamiento_en_prueba):
    """RF-17.3: el otro usuario busca temas similares a un tema general cuyo documento es casi igual al del notebook del dueño:
    el resultado no trae ese documento (ni su nombre, ni su frase, ni la clave del notebook). Control: el dueño sí lo ve."""
    base = ajeno.documento
    variante = DocumentoPrueba(nombre=f"{PREFIJO_DATOS}_variante_{base.nombre[len(PREFIJO_DATOS) + 1:]}",
                               contenido=base.contenido + " Texto añadido para la variante inventada.".encode("utf-8"), frase=base.frase)
    tema = tema_heredado(registro_de_datos)
    _documento_procesado_en_el_notebook(cliente_api, ajeno.cabeceras_otro, procesamiento_en_prueba, {"clave_interna": tema}, variante)

    del_dueno = _busqueda_por_tema(cliente_api, ajeno.cabeceras_dueno, tema)
    assert del_dueno.status_code == 200 and ajeno.documento.nombre in del_dueno.text, "control: el dueño no ve su documento"

    del_otro = _busqueda_por_tema(cliente_api, ajeno.cabeceras_otro, tema)
    assert del_otro.status_code == 200
    for dato in (ajeno.documento.nombre, ajeno.documento.frase, ajeno.notebook["clave_interna"]):
        assert dato not in del_otro.text, f"la búsqueda del otro usuario trae {dato!r}"


# --- RF-11.32, RF-21.31, RF-21.32 (T4): el chat del notebook ---------------------------------------------------------------------

CARGA_DOCUMENTOS = 2
INTENTO = f"Intento fallido: {MOTIVO_NOTEBOOK}"
_DIGITOS_ARABES = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def _chat_con_sesion(cliente_api, cabeceras, sesion: str, pregunta: str = "PRUEBA ¿qué dice el notebook?", **alcance):
    """Consulta el chat con una conversación elegida (para comprobar qué pasa con ella)."""
    return cliente_api.post("/rag/consulta-con-historial-stream", headers=cabeceras,
                            json={"query": pregunta, "session_id": sesion, **alcance})


def _estado_de_la_conversacion(sesion: str) -> tuple:
    """Fecha de la última actividad, contador y mensajes de una conversación guardada en memoria."""
    from app.services.RAG.session_store import conversation_store

    metadatos = conversation_store._metadata[sesion]
    return metadatos.updated_at, metadatos.message_count, len(conversation_store._store[sesion].messages)


@pytest.fixture
def bitacora_que_falla():
    """Devuelve una función que hace fallar el registro en la bitácora de los servicios de auditoría que intervienen, sobre su
    instancia. Al terminar quita el atributo de la instancia: `monkeypatch` lo dejaría puesto con el método original y taparía
    a las pruebas posteriores que parchan la clase."""
    from app.services.bitacora.ingesta_audit_service import ingesta_audit_service
    from app.services.bitacora.notebooks_audit_service import notebooks_audit_service
    from app.services.bitacora.rag_audit_service import rag_audit_service
    from app.services.bitacora.similarity_audit_service import similarity_audit_service

    async def _falla(*args, **kwargs):
        raise Exception("falla simulada de la bitácora")

    instancias = [s.bitacora_service for s in
                  (ingesta_audit_service, notebooks_audit_service, rag_audit_service, similarity_audit_service)]

    def _activar() -> None:
        for instancia in instancias:
            instancia.registrar = _falla

    yield _activar
    for instancia in instancias:
        instancia.__dict__.pop("registrar", None)


@pytest.mark.requisito("RF-11.32")
@pytest.mark.requisito("RNF-07.6")
def test_notebook_no_numerico_da_404(cliente_api, ajeno_ligero, registro_de_datos, ollama_simulado):
    """RF-11.32: en el chat del notebook, un identificador ajeno, inexistente o no numérico (`+5`, ` 5 `, `05`, dígitos
    Unicode, vacío, solo espacios, cero, enorme, con letras; incluso con la forma de un notebook PROPIO) da el mismo 404 (código
    y cuerpo), el modelo no se llama y la conversación que se nombra (aquí la del dueño) queda como estaba: ni mensajes ni
    fecha. Control: el identificador canónico de un notebook propio sí responde."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    propio = crear_notebook(cliente_api, ajeno_ligero.cabeceras_otro, f"{PREFIJO_DATOS} notebook del otro", registro_de_datos)
    n = str(propio["id"])
    pedidos = {
        "inexistente": str(ajeno_ligero.id_inexistente), "ajeno": str(ajeno_ligero.notebook["id"]),
        "mas": f"+{n}", "espacios": f" {n} ", "ceros": f"0{n}", "unicode": n.translate(_DIGITOS_ARABES), "vacio": "",
        "solo_espacios": "   ", "cero": "0", "enorme": "9" * 30, "con_letras": f"{n}a", "con_clave": f"NB-{n}",
    }
    antes = _estado_de_la_conversacion(ajeno_ligero.sesion_chat)

    respuestas = {caso: _chat_con_sesion(cliente_api, ajeno_ligero.cabeceras_otro, ajeno_ligero.sesion_chat, notebook_id=valor)
                  for caso, valor in pedidos.items()}

    for caso, respuesta in respuestas.items():
        assert respuesta.status_code == 404, f"«{caso}» dio {respuesta.status_code}"
        assert respuesta.json() == respuestas["inexistente"].json(), f"«{caso}» no responde igual que un notebook inexistente"
    assert not ollama_simulado.preguntas, "el modelo recibió algo"
    assert _estado_de_la_conversacion(ajeno_ligero.sesion_chat) == antes, "la conversación nombrada cambió"

    control = _chat_con_sesion(cliente_api, ajeno_ligero.cabeceras_otro, f"session_{PREFIJO_DATOS}control_{uuid.uuid4().hex[:8]}", notebook_id=n)
    assert control.status_code == 200 and ollama_simulado.preguntas, "control: el notebook propio no respondió"


@pytest.mark.requisito("RF-21.31")
def test_chat_de_notebook_se_registra_con_su_clave(cliente_api, ajeno, ollama_simulado):
    """RF-21.31: la consulta en el chat de un notebook propio queda en la bitácora con alcance de notebook y su clave como tema
    (también asociada al tema de la base), no como «general»; una sola fila, sin intento fallido."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    clave = ajeno.notebook["clave_interna"]
    marca = _marca_de_bitacora()

    respuesta = _consultar_chat(cliente_api, ajeno.cabeceras_dueno, _pregunta_sobre(ajeno.documento), notebook_id=str(ajeno.notebook["id"]))

    assert respuesta.status_code == 200
    filas = _filas_nuevas(ajeno.dueno, marca)
    assert len(filas) == 1, filas
    assert filas[0]["info"]["tipo_consulta"] == "notebook" and filas[0]["info"]["expediente_numero"] == clave
    assert clave in filas[0]["texto"] and "general" not in filas[0]["texto"]
    id_tema = _consultar("SELECT CN_Id_expediente FROM T_Expediente WHERE CT_Num_expediente = :t", {"t": clave})[0][0]
    assert filas[0]["expediente"] == id_tema


@pytest.mark.requisito("RF-21.32")
def test_intento_fallido_solo_con_motivo(cliente_api, ajeno_ligero, ollama_simulado, caplog):
    """RF-21.32: el chat del notebook con un notebook ajeno, inexistente o no numérico deja UNA fila de intento fallido por
    petición, igual en todos los casos: solo el motivo, clasificada como error de acceso, sin clave, identificador, pregunta ni
    conversación; y el registro del servidor tampoco repite el identificador ni la conversación pedidos."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    caplog.set_level(logging.DEBUG, logger="app")
    sesion = f"session_PRUEBA_pedida_{uuid.uuid4().hex[:8]}"
    pregunta = f"PRUEBA pregunta secreta {uuid.uuid4().hex[:8]}"
    pedidos = {"ajeno": str(ajeno_ligero.notebook["id"]), "inexistente": str(ajeno_ligero.id_inexistente), "no_numerico": f"+{ajeno_ligero.id_inexistente}"}

    filas = {}
    for caso, valor in pedidos.items():
        marca = _marca_de_bitacora()
        respuesta = _chat_con_sesion(cliente_api, ajeno_ligero.cabeceras_otro, sesion, pregunta, notebook_id=valor)
        assert (respuesta.status_code, respuesta.json()) == (404, {"detail": "Notebook no encontrado"}), caso
        filas[caso] = _filas_nuevas(ajeno_ligero.otro, marca)
        assert len(filas[caso]) == 1, f"«{caso}»: {filas[caso]}"
        fila = filas[caso][0]
        assert fila["texto"] == INTENTO and fila["expediente"] is None
        assert fila["info"]["motivo"] == MOTIVO_NOTEBOOK and fila["info"]["tipo_error"] == "acceso"
        assert "tipo_consulta" not in fila["info"] and "session_id" not in fila["info"]
        crudo = json.dumps(fila, ensure_ascii=False).casefold()
        for dato in (ajeno_ligero.notebook["clave_interna"], f"nb-{ajeno_ligero.id_inexistente}", str(ajeno_ligero.id_inexistente), sesion, pregunta):
            assert dato.casefold() not in crudo, f"«{caso}»: la bitácora lleva {dato!r}"
    assert _sin_lo_volatil(filas["ajeno"]) == _sin_lo_volatil(filas["inexistente"]) == _sin_lo_volatil(filas["no_numerico"])
    registro = caplog.text.casefold()
    for dato in (ajeno_ligero.notebook["clave_interna"], str(ajeno_ligero.id_inexistente), sesion):
        assert dato.casefold() not in registro, f"el registro del servidor lleva {dato!r}"


# --- RF-17.4, RF-21.32 (T4): la carga a un notebook no disponible --------------------------------------------------------------

@pytest.mark.requisito("RF-17.4")
@pytest.mark.requisito("RF-21.32")
def test_carga_con_clave_no_canonica_da_404(cliente_api, ajeno_ligero, registro_de_datos, correo_simulado, encolado_interceptado,
                                            carpeta_archivos, caplog):
    """RF-17.4: subir con la clave de un notebook ajeno (en cualquier grafía), inexistente o con una forma no canónica
    (`NB-0<id>` del propio notebook, con letras, dígitos Unicode, sin número) da el mismo 404, sin guardar el archivo, encolar,
    crear documento, tema ni fragmentos. RF-21.32: una fila de intento fallido por petición, solo con su motivo, igual en todos
    los casos y sin la clave; el registro del servidor tampoco la repite."""
    from tests.soporte.flujos import id_del_documento

    caplog.set_level(logging.DEBUG, logger="app")
    propio = crear_notebook(cliente_api, ajeno_ligero.cabeceras_otro, f"{PREFIJO_DATOS} notebook del otro", registro_de_datos)
    n = propio["id"]
    clave = ajeno_ligero.notebook["clave_interna"]
    claves = {
        "ajena": clave, "ajena_en_minusculas": clave.lower(), "inexistente": f"NB-{ajeno_ligero.id_inexistente}",
        "ceros_del_propio": f"NB-0{n}", "con_letras": f"NB-{n}x", "unicode": f"NB-{str(n).translate(_DIGITOS_ARABES)}",
        "sin_numero": "NB-", "enorme": "NB-" + "9" * 30,
    }
    intruso = documento_de_prueba()
    antes = foto_de_efectos(correo_simulado)
    tareas = len(encolado_interceptado.pendientes)
    marca = _marca_de_bitacora()

    respuestas = {caso: cargar(cliente_api, ajeno_ligero.cabeceras_otro, valor, [(intruso.nombre, intruso.contenido)])
                  for caso, valor in claves.items()}

    for caso, respuesta in respuestas.items():
        assert respuesta.status_code == 404, f"«{caso}» dio {respuesta.status_code}"
        assert respuesta.json() == respuestas["ajena"].json(), f"«{caso}» no responde igual que el ajeno"
    assert len(encolado_interceptado.pendientes) == tareas, "se encoló una tarea"
    assert id_del_documento(intruso.nombre) is None, "se creó el documento"
    despues = foto_de_efectos(correo_simulado)
    assert despues["filas"]["T_Bitacora"] - antes["filas"]["T_Bitacora"] == len(claves)
    for foto in (antes, despues):
        foto["filas"].pop("T_Bitacora")
    assert despues == antes
    filas = _filas_de(ajeno_ligero.otro, CARGA_DOCUMENTOS, marca)
    assert len(filas) == len(claves)
    assert all(f["texto"] == INTENTO and f["expediente"] is None and f["info"]["tipo_error"] == "acceso" for f in filas)
    unicas = {json.dumps(f, sort_keys=True) for f in _sin_lo_volatil(filas)}
    assert len(unicas) == 1, "los intentos no son idénticos"
    crudo = json.dumps(filas, ensure_ascii=False).casefold()
    registro = caplog.text.casefold()
    for caso, valor in claves.items():
        if caso in ("sin_numero", "enorme"):
            continue
        assert valor.casefold() not in crudo and valor.casefold() not in registro, f"«{caso}»: se repitió la clave pedida"


@pytest.mark.requisito("RF-17.4")
def test_carga_propia_en_otra_grafia_usa_la_canonica(cliente_api, sesion, usuario_gubernamental, registro_de_datos,
                                                     encolado_interceptado, carpeta_archivos):
    """RF-17.4: subir al notebook propio con su clave en otra grafía (`nb-<id>`, `Nb-<id>`, con espacios) se acepta y se guarda
    con la clave canónica `NB-<id>`: la carpeta, la tarea encolada y la respuesta usan esa clave, sin crear grafías nuevas,
    y no queda ningún intento fallido."""
    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook propio", registro_de_datos)
    clave, n = notebook["clave_interna"], notebook["id"]
    marca = _marca_de_bitacora()
    escritas = {}

    for grafia in (clave, f"nb-{n}", f"Nb-{n}", f" NB-{n} "):
        documento = documento_de_prueba()
        respuesta = cargar(cliente_api, sesion, grafia, [(documento.nombre, documento.contenido)])
        assert respuesta.status_code == 200, f"«{grafia}» dio {respuesta.status_code}"
        assert respuesta.json()["expediente"] == clave
        pendiente = encolado_interceptado.pendientes[-1]
        assert pendiente.tema == clave
        escritas[grafia] = Path(pendiente.archivo_info["filepath"])

    for grafia, ruta in escritas.items():
        assert ruta.parent.name == clave, f"«{grafia}» se guardó en la carpeta {ruta.parent.name!r}"
    filas = _filas_de(usuario_gubernamental, CARGA_DOCUMENTOS, marca)
    assert [f for f in filas if f["info"].get("motivo") == MOTIVO_NOTEBOOK] == [], "la carga propia dejó un intento fallido"


# --- RF-21.32, RF-21.33: con la bitácora fallando la respuesta es la misma ---------------------------------------------------------

@pytest.mark.requisito("RF-21.33")
@pytest.mark.requisito("RF-21.32")
def test_con_la_bitacora_fallando_las_respuestas_son_las_mismas(cliente_api, ajeno_ligero, registro_de_datos, correo_simulado,
                                                                 ollama_simulado, encolado_interceptado, carpeta_archivos,
                                                                 bitacora_que_falla):
    """RF-21.33 y RF-21.32: el chat por tema, los temas similares, el resumen, el chat del notebook y la carga, con la clave
    ajena, inexistente o propia, dan la MISMA respuesta (código y estructura) con la bitácora funcionando y con la bitácora
    fallando (simulado sobre cada servicio de auditoría); con ella fallando no queda ninguna fila nueva del usuario."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    propio = crear_notebook(cliente_api, ajeno_ligero.cabeceras_otro, f"{PREFIJO_DATOS} notebook del otro", registro_de_datos)
    cabeceras = ajeno_ligero.cabeceras_otro
    ajena, inexistente, suya = ajeno_ligero.notebook["clave_interna"], f"NB-{ajeno_ligero.id_inexistente}", propio["clave_interna"]
    pregunta = f"{PREFIJO_DATOS} ¿qué dice el documento inventado sobre la quebrada ficticia?"
    contenido = documento_de_prueba().contenido

    def _chat(**alcance):
        respuesta = _consultar_chat(cliente_api, cabeceras, pregunta, **alcance)
        return respuesta.status_code, _tipos_de_evento(respuesta)

    def _cargar(valor):
        respuesta = cargar(cliente_api, cabeceras, valor, [(f"{PREFIJO_DATOS}_{uuid.uuid4().hex[:6]}.txt", contenido)])
        cuerpo = respuesta.json()
        return respuesta.status_code, cuerpo.get("detail") or cuerpo.get("message")

    operaciones = {
        "chat_por_tema_ajena": lambda: _chat(expediente_number=ajena),
        "chat_por_tema_inexistente": lambda: _chat(expediente_number=inexistente),
        "chat_por_tema_propia": lambda: _chat(expediente_number=suya),
        "chat_notebook_ajeno": lambda: _chat(notebook_id=str(ajeno_ligero.notebook["id"])),
        "chat_notebook_inexistente": lambda: _chat(notebook_id=str(ajeno_ligero.id_inexistente)),
        "chat_notebook_propio": lambda: _chat(notebook_id=str(propio["id"])),
        "carga_ajena": lambda: _cargar(ajena),
        "carga_inexistente": lambda: _cargar(inexistente),
        "carga_propia": lambda: _cargar(suya),
    }
    for tema in (ajena, inexistente, suya):
        operaciones[f"similares_{tema}"] = lambda t=tema: _forma_de(_busqueda_por_tema(cliente_api, cabeceras, t), t)
        operaciones[f"resumen_{tema}"] = lambda t=tema: _forma_de(_resumen_de(cliente_api, cabeceras, t), t)

    con_bitacora = {nombre: operacion() for nombre, operacion in operaciones.items()}
    bitacora_que_falla()
    marca = _marca_de_bitacora()
    sin_bitacora = {nombre: operacion() for nombre, operacion in operaciones.items()}

    assert sin_bitacora == con_bitacora
    nuevas = _consultar("SELECT COUNT(*) FROM T_Bitacora WHERE CN_Id_usuario = :u AND CN_Id_bitacora > :m",
                        {"u": ajeno_ligero.otro.cedula, "m": marca})[0][0]
    assert nuevas == 0, "con la bitácora fallando quedaron filas"


# --- T5: tres tipos de acción nuevos (RF-21.34) -----------------------------------------------------------------------------

_TIPOS_NUEVOS = {16: "Crear Notebook", 17: "Quitar Documento de Notebook", 18: "Gestionar Conversación"}


@pytest.mark.requisito("RF-21.34")
def test_catalogo_con_tres_tipos_nuevos():
    """RF-21.34: el catálogo conserva los 15 tipos de siempre (mismo id y nombre) y suma 16, 17 y 18; las constantes y sus
    descripciones del backend coinciden con la base."""
    from app.constants.tipos_accion import DESCRIPCIONES_TIPOS_ACCION, TiposAccion

    filas = dict(_consultar("SELECT CN_Id_tipo_accion, CT_Nombre_tipo_accion FROM T_Tipo_accion"))
    assert sorted(filas) == list(range(1, 19))
    assert {i: filas[i] for i in range(16, 19)} == _TIPOS_NUEVOS
    assert {i: filas[i] for i in range(1, 16)} == {i: DESCRIPCIONES_TIPOS_ACCION[i] for i in range(1, 16)}
    assert (TiposAccion.CREAR_NOTEBOOK, TiposAccion.QUITAR_DOCUMENTO_NOTEBOOK, TiposAccion.GESTIONAR_CONVERSACION) == (16, 17, 18)
    assert {i: DESCRIPCIONES_TIPOS_ACCION[i] for i in range(16, 19)} == _TIPOS_NUEVOS


@pytest.mark.requisito("RF-21.34")
def test_filtro_por_tipo_nuevo(cliente_api, iniciar_sesion, administrador, usuario_gubernamental):
    """RF-21.34: la bitácora del Administrador y el historial propio aceptan y filtran por los tipos 16 a 18 (con `le=15`
    respondían 422); el 19 sigue rechazándose."""
    from fastapi.testclient import TestClient

    from app.db.database import SessionLocal
    from app.services.bitacora.bitacora_service import bitacora_service
    from app.services.bitacora.bitacora_stats_service import bitacora_stats_service

    texto = f"{PREFIJO_DATOS} acción de notebook {uuid.uuid4().hex[:6]}"
    with SessionLocal() as db:
        for tipo in _TIPOS_NUEVOS:
            fila = asyncio.run(bitacora_service.registrar(
                db=db, usuario_id=usuario_gubernamental.cedula, tipo_accion_id=tipo, texto=f"{texto} {tipo}"))
            assert fila is not None, f"no se pudo registrar el tipo {tipo}"
        for tipo in _TIPOS_NUEVOS:  # historial propio: su servicio filtra por el tipo
            propio = bitacora_stats_service.obtener_con_filtros(
                db=db, usuario_id=usuario_gubernamental.cedula, tipo_accion_id=tipo, limite=50)
            assert [i["texto"] for i in propio["items"] if texto in i["texto"]] == [f"{texto} {tipo}"]

    cabeceras = iniciar_sesion(administrador)
    for tipo, nombre in _TIPOS_NUEVOS.items():
        respuesta = cliente_api.get("/bitacora/registros", headers=cabeceras,
                                    params={"tipoAccion": tipo, "usuario": usuario_gubernamental.correo, "limite": 100})
        assert respuesta.status_code == 200, (tipo, respuesta.text)
        propios = [i for i in respuesta.json()["items"] if texto in i["texto"]]
        assert len(propios) == 1 and propios[0]["texto"] == f"{texto} {tipo}"

    sesion = iniciar_sesion(usuario_gubernamental)
    sin_relanzar = TestClient(cliente_api.app, raise_server_exceptions=False)
    for tipo in _TIPOS_NUEVOS:  # la ruta del historial propio hoy da 500 por otra causa (004, xfail): lo que no puede dar es 422
        assert sin_relanzar.get("/bitacora/mi-historial", headers=sesion, params={"tipoAccion": tipo}).status_code != 422, tipo
    assert cliente_api.get("/bitacora/registros", headers=cabeceras, params={"tipoAccion": 19}).status_code == 422
    assert sin_relanzar.get("/bitacora/mi-historial", headers=sesion, params={"tipoAccion": 19}).status_code == 422


# --- T6: la clave de ancho completo (RF-17.34) -----------------------------------------------------------------------------------

ANCHO_NB = "ＮＢ"
ANCHO_GUION = "－"
_ANCHO_DIGITOS = str.maketrans("0123456789", "０１２３４５６７８９")


def _la_base_iguala(uno: str, otro: str) -> tuple:
    """Si SQL Server iguala dos textos con la intercalación de la columna del tema, y cuál es esa intercalación: es lo que
    decide si una grafía de ancho completo llegaría al notebook de otro por la búsqueda del tema guardado (RF-17.34)."""
    intercalacion = _consultar("SELECT COLLATION_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'T_Expediente' "
                               "AND COLUMN_NAME = 'CT_Num_expediente'")[0][0]
    iguala = _consultar(f"SELECT CASE WHEN CAST(:a AS NVARCHAR(100)) COLLATE {intercalacion} = CAST(:b AS NVARCHAR(100)) "
                        f"COLLATE {intercalacion} THEN 1 ELSE 0 END", {"a": uno, "b": otro})[0][0]
    return bool(iguala), intercalacion


def _claves_de_ancho_completo(id_notebook: int) -> dict:
    """La clave `NB-<id>` con letras (y guion) de ancho completo y el número en dígitos ASCII, también en minúsculas y con espacios."""
    return {
        "letras": f"{ANCHO_NB}-{id_notebook}", "letras_y_guion": f"{ANCHO_NB}{ANCHO_GUION}{id_notebook}",
        "minusculas": f"ｎｂ{ANCHO_GUION}{id_notebook}", "con_espacios": f"  {ANCHO_NB}{ANCHO_GUION}{id_notebook}  ",
    }


@pytest.mark.requisito("RF-17.34")
@pytest.mark.requisito("RF-17.4")
@pytest.mark.requisito("RF-21.32")
def test_carga_con_clave_de_ancho_completo(cliente_api, ajeno_ligero, registro_de_datos, correo_simulado, encolado_interceptado,
                                           carpeta_archivos, caplog):
    """RF-17.34 (primera prueba de la T6: confirma o descarta que la base iguale `ＮＢ-<id>` con la clave `NB-<id>`; en ambos
    casos queda como protección): subir con la clave de A en ancho completo da el MISMO 404 que con la clave ajena escrita
    normal, sin guardar archivo, encolar, crear documento ni tema, con una fila de intento fallido (carga) por petición; el
    notebook de A sigue sin documentos. Con la propia en ancho completo la carga se acepta y se guarda como `NB-<id>`; con el
    dígito de ancho completo, no está disponible."""
    from tests.soporte.flujos import id_del_documento

    propio = crear_notebook(cliente_api, ajeno_ligero.cabeceras_otro, f"{PREFIJO_DATOS} notebook del otro", registro_de_datos)
    clave_a, n_a = ajeno_ligero.notebook["clave_interna"], ajeno_ligero.notebook["id"]
    iguala, intercalacion = _la_base_iguala(f"{ANCHO_NB}-{n_a}", clave_a)
    diagnostico = (f"la base (intercalación {intercalacion}) {'IGUALA' if iguala else 'NO iguala'} la clave de ancho completo "
                   f"con la clave")
    caplog.set_level(logging.DEBUG, logger="app")
    intruso = documento_de_prueba()
    antes = foto_de_efectos(correo_simulado)
    tareas = len(encolado_interceptado.pendientes)
    marca = _marca_de_bitacora()
    pedidos = _claves_de_ancho_completo(n_a)

    ajena_normal = cargar(cliente_api, ajeno_ligero.cabeceras_otro, clave_a, [(intruso.nombre, intruso.contenido)])
    respuestas = {caso: cargar(cliente_api, ajeno_ligero.cabeceras_otro, valor, [(intruso.nombre, intruso.contenido)])
                  for caso, valor in pedidos.items()}

    assert ajena_normal.status_code == 404
    for caso, respuesta in respuestas.items():
        assert respuesta.status_code == 404, f"«{caso}» dio {respuesta.status_code}; {diagnostico}"
        assert respuesta.json() == ajena_normal.json(), f"«{caso}» no responde igual que la clave ajena"
    assert len(encolado_interceptado.pendientes) == tareas, f"se encoló una tarea; {diagnostico}"
    assert id_del_documento(intruso.nombre) is None, f"se creó el documento; {diagnostico}"
    despues = foto_de_efectos(correo_simulado)
    assert despues["filas"]["T_Bitacora"] - antes["filas"]["T_Bitacora"] == 1 + len(pedidos)
    for foto in (antes, despues):
        foto["filas"].pop("T_Bitacora")
    assert despues == antes, f"la carga dejó efectos; {diagnostico}"
    filas = _filas_de(ajeno_ligero.otro, CARGA_DOCUMENTOS, marca)
    assert len(filas) == 1 + len(pedidos) and all(f["texto"] == INTENTO and f["info"]["tipo_error"] == "acceso" for f in filas)
    assert len({json.dumps(f, sort_keys=True) for f in _sin_lo_volatil(filas)}) == 1, "los intentos no son idénticos"
    lista = cliente_api.get(f"/notebooks/{n_a}/documentos", headers=ajeno_ligero.cabeceras_dueno)
    assert lista.status_code == 200 and lista.json() == [], "el notebook de A recibió un documento"
    registro = caplog.text.casefold()
    for caso, valor in pedidos.items():
        assert valor.strip().casefold() not in registro, f"«{caso}»: el registro del servidor repite la clave pedida"

    # La propia en ancho completo se acepta y se guarda con su clave canónica `NB-<id>`.
    for caso, valor in _claves_de_ancho_completo(propio["id"]).items():
        documento = documento_de_prueba()
        respuesta = cargar(cliente_api, ajeno_ligero.cabeceras_otro, valor, [(documento.nombre, documento.contenido)])
        assert respuesta.status_code == 200, f"la propia «{caso}» dio {respuesta.status_code}"
        assert respuesta.json()["expediente"] == propio["clave_interna"]
        pendiente = encolado_interceptado.pendientes[-1]
        assert pendiente.tema == propio["clave_interna"]
        assert Path(pendiente.archivo_info["filepath"]).parent.name == propio["clave_interna"]
    # El dígito de ancho completo no es una clave disponible (decisión 11).
    digito = cargar(cliente_api, ajeno_ligero.cabeceras_otro, f"NB-{str(propio['id']).translate(_ANCHO_DIGITOS)}",
                    [(intruso.nombre, intruso.contenido)])
    assert digito.status_code == 404 and digito.json() == ajena_normal.json()


@pytest.mark.requisito("RF-17.34")
@pytest.mark.requisito("RF-11.31")
@pytest.mark.requisito("RF-21.33")
def test_chat_por_tema_con_clave_de_ancho_completo(cliente_api, ajeno_ligero, registro_de_datos, ollama_simulado):
    """RF-17.34: el chat por tema con la clave de ancho completo (ajena, inexistente o propia) es el chat general, igual que
    con la clave normal: mismo contexto que el general, misma estructura, y la bitácora sin la clave (la ajena y la
    inexistente además dejan el intento fallido «notebook no disponible»; la propia, solo la consulta general)."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    propio = crear_notebook(cliente_api, ajeno_ligero.cabeceras_otro, f"{PREFIJO_DATOS} notebook del otro", registro_de_datos)
    pregunta = f"{PREFIJO_DATOS} ¿qué dice el documento inventado sobre la quebrada ficticia?"
    claves = {
        "ajena": _claves_de_ancho_completo(ajeno_ligero.notebook["id"])["letras_y_guion"],
        "inexistente": _claves_de_ancho_completo(ajeno_ligero.id_inexistente)["letras"],
        "propia": _claves_de_ancho_completo(propio["id"])["letras_y_guion"],
    }

    marca = _marca_de_bitacora()
    general, contexto_general = _preguntar(cliente_api, ollama_simulado, ajeno_ligero.cabeceras_otro, pregunta)
    filas_generales = _sin_lo_volatil(_filas_nuevas(ajeno_ligero.otro, marca))

    filas = {}
    for caso, tema in claves.items():
        marca = _marca_de_bitacora()
        respuesta, contexto = _preguntar(cliente_api, ollama_simulado, ajeno_ligero.cabeceras_otro, pregunta, expediente_number=tema)
        assert respuesta.status_code == general.status_code and _tipos_de_evento(respuesta) == _tipos_de_evento(general), caso
        assert contexto == contexto_general, f"el contexto de «{caso}» no es el del chat general"
        filas[caso] = _filas_nuevas(ajeno_ligero.otro, marca)
        crudo = json.dumps(filas[caso], ensure_ascii=False).casefold()
        assert tema.casefold() not in crudo and ANCHO_NB.casefold() not in crudo, f"la bitácora de «{caso}» lleva la clave"
        assert all(f["info"].get("tipo_consulta") != "expediente" for f in filas[caso]), f"«{caso}» se registró como un tema"
    for caso in ("ajena", "inexistente"):
        consultas = [f for f in filas[caso] if f["info"].get("tipo_consulta") == "general"]
        intentos = [f for f in filas[caso] if f["info"].get("motivo") == MOTIVO_NOTEBOOK]
        assert len(filas[caso]) == 2 and len(consultas) == 1 and len(intentos) == 1, f"«{caso}»: {filas[caso]}"
    assert _sin_lo_volatil(filas["ajena"]) == _sin_lo_volatil(filas["inexistente"])
    assert _sin_lo_volatil(filas["propia"]) == filas_generales


def _grafias_que_la_base_guarda_como_clave(id_notebook: int) -> dict:
    """Grafías de `NB-<id>` que no son forma de clave (ni en NFKC) y que la conversión a la columna VARCHAR de SQL Server puede
    dejar como `NB-<id>`: la `Ń` (U+0143), el guion U+2010 y el signo menos U+2212 (vuelta 1 de la revisión T6-T8, B1)."""
    return {"n_con_acento": f"ŃB-{id_notebook}", "guion_2010": f"NB‐{id_notebook}", "menos_2212": f"NB−{id_notebook}"}


def _como_la_base_guardaria(valor: str) -> str:
    """El valor tal como lo guardaría el INSERT del ORM en la columna VARCHAR del tema (la conversión la hace el controlador al
    enviar el parámetro: B2, vuelta 2): lo que responde `como_lo_guarda_la_base`, que otra prueba compara con el INSERT real."""
    from app.db.database import engine
    from app.repositories.expediente_repository import ExpedienteRepository
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        return ExpedienteRepository().como_lo_guarda_la_base(db, valor)


@pytest.mark.requisito("RF-17.34")
@pytest.mark.requisito("RF-17.4")
@pytest.mark.requisito("RNF-07.6")
@pytest.mark.requisito("RF-21.32")
@pytest.mark.parametrize("escenario", ["ajeno_ligero", "ajeno"])
def test_carga_con_grafia_que_la_base_guarda_como_clave(request, escenario, cliente_api, registro_de_datos, correo_simulado,
                                                        encolado_interceptado, carpeta_archivos, caplog):
    """RF-17.34 (B1 de la revisión T6-T8): una grafía que no es forma de clave pero que SQL Server guarda en la columna VARCHAR
    como `NB-<id>` (`ŃB-`, guion U+2010, signo menos U+2212) recibe el trato de esa clave aunque el notebook de A NO tenga fila
    de tema (`ajeno_ligero`, el caso más común: antes de su primera carga) o la tenga (`ajeno`, control): la carga de B da el
    MISMO 404 que con la clave ajena escrita normal, sin archivo, tarea, documento ni tema, con una fila de intento por petición;
    el notebook de A no recibe nada. Con la propia, la carga se acepta y se guarda como `NB-<id>`."""
    from tests.soporte.flujos import id_del_documento

    escenario = request.getfixturevalue(escenario)
    propio = crear_notebook(cliente_api, escenario.cabeceras_otro, f"{PREFIJO_DATOS} notebook del otro", registro_de_datos)
    clave_a, n_a = escenario.notebook["clave_interna"], escenario.notebook["id"]
    pedidos = _grafias_que_la_base_guarda_como_clave(n_a)
    diagnostico = "; ".join(f"«{caso}» se guardaría como {_como_la_base_guardaria(valor)!r}" for caso, valor in pedidos.items())
    caplog.set_level(logging.DEBUG, logger="app")
    intruso = documento_de_prueba()
    antes = foto_de_efectos(correo_simulado)
    tareas = len(encolado_interceptado.pendientes)
    marca = _marca_de_bitacora()
    documentos_de_a = cliente_api.get(f"/notebooks/{n_a}/documentos", headers=escenario.cabeceras_dueno).json()

    ajena_normal = cargar(cliente_api, escenario.cabeceras_otro, clave_a, [(intruso.nombre, intruso.contenido)])
    respuestas = {caso: cargar(cliente_api, escenario.cabeceras_otro, valor, [(intruso.nombre, intruso.contenido)])
                  for caso, valor in pedidos.items()}

    assert ajena_normal.status_code == 404
    for caso, respuesta in respuestas.items():
        assert respuesta.status_code == 404, f"«{caso}» dio {respuesta.status_code}; {diagnostico}"
        assert respuesta.json() == ajena_normal.json(), f"«{caso}» no responde igual que la clave ajena; {diagnostico}"
    assert len(encolado_interceptado.pendientes) == tareas, f"se encoló una tarea; {diagnostico}"
    assert id_del_documento(intruso.nombre) is None, f"se creó el documento; {diagnostico}"
    despues = foto_de_efectos(correo_simulado)
    assert despues["filas"]["T_Bitacora"] - antes["filas"]["T_Bitacora"] == 1 + len(pedidos)
    for foto in (antes, despues):
        foto["filas"].pop("T_Bitacora")
    assert despues == antes, f"la carga dejó efectos; {diagnostico}"
    filas = _filas_de(escenario.otro, CARGA_DOCUMENTOS, marca)
    assert len(filas) == 1 + len(pedidos) and all(f["texto"] == INTENTO and f["info"]["tipo_error"] == "acceso" for f in filas)
    assert len({json.dumps(f, sort_keys=True) for f in _sin_lo_volatil(filas)}) == 1, "los intentos no son idénticos"
    lista = cliente_api.get(f"/notebooks/{n_a}/documentos", headers=escenario.cabeceras_dueno)
    assert lista.status_code == 200 and lista.json() == documentos_de_a, f"el notebook de A cambió; {diagnostico}"
    registro = caplog.text.casefold()
    for caso, valor in pedidos.items():
        assert valor.casefold() not in registro, f"«{caso}»: el registro del servidor repite la grafía pedida"

    for caso, valor in _grafias_que_la_base_guarda_como_clave(propio["id"]).items():
        documento = documento_de_prueba()
        respuesta = cargar(cliente_api, escenario.cabeceras_otro, valor, [(documento.nombre, documento.contenido)])
        assert respuesta.status_code == 200, f"la propia «{caso}» dio {respuesta.status_code}"
        assert respuesta.json()["expediente"] == propio["clave_interna"]
        assert encolado_interceptado.pendientes[-1].tema == propio["clave_interna"]


def _grafias_con_caracteres_invisibles(id_notebook: int) -> dict:
    """Grafías de `NB-<id>` con caracteres de ancho cero o ignorables que `validar_tema` deja pasar (B2, vuelta 2). Con la
    intercalación de la columna y la conversión del controlador, varias quedan guardadas EXACTAMENTE como `NB-<id>`."""
    n = id_notebook
    return {
        "guion_blando_00AD": f"N­B-{n}", "guion_blando_00AD_final": f"NB-{n}­",
        "ancho_cero_200B": f"NB-​{n}", "ancho_cero_200B_final": f"NB-{n}​",
        "no_une_200C": f"NB-‌{n}", "une_200D": f"NB‍-{n}", "une_palabras_2060": f"NB-⁠{n}",
        "bom_FEFF_inicio": f"﻿NB-{n}", "bom_FEFF_dentro": f"N﻿B-{n}", "separador_2063": f"NB-⁣{n}",
        "relleno_034F": f"NB-͏{n}", "selector_FE0F": f"NB-️{n}", "combinante_0301_final": f"NB-{n}́",
        "marca_200E": f"NB-‎{n}", "formato_202A": f"NB-‪{n}", "mongol_180E": f"NB-᠎{n}",
    }


def _nombres_bajo_el_tema(tema: str) -> list:
    """Los nombres de archivo de los documentos unidos al tema guardado con ese texto exacto."""
    return [n for (n,) in _consultar(
        "SELECT d.CT_Nombre_archivo FROM T_Documento d JOIN T_Expediente_Documento ed ON ed.CN_Id_documento = d.CN_Id_documento "
        "JOIN T_Expediente e ON e.CN_Id_expediente = ed.CN_Id_expediente WHERE e.CT_Num_expediente = :t", {"t": tema})]


def _digitos_no_ascii(id_notebook: int) -> dict:
    """Decisión 17 del plan: `NB‐５` y similares (el resto, en dígitos no ASCII) no están disponibles para nadie."""
    anchos = str(id_notebook).translate(_ANCHO_DIGITOS)
    return {"guion_2010_y_digitos_anchos": f"NB‐{anchos}", "acento_y_digitos_anchos": f"ŃB-{anchos}",
            "menos_2212_y_digitos_anchos": f"NB−{anchos}"}


@pytest.mark.requisito("RF-17.34")
@pytest.mark.requisito("RF-17.4")
@pytest.mark.requisito("RNF-07.6")
@pytest.mark.requisito("RF-21.32")
@pytest.mark.parametrize("escenario", ["ajeno_ligero", "ajeno"])
def test_carga_con_caracteres_invisibles_en_la_clave(request, escenario, cliente_api, registro_de_datos, correo_simulado,
                                                     encolado_interceptado, carpeta_archivos, caplog):
    """RF-17.34 (B2 de la vuelta 2): `N<U+00AD>B-<id>`, `NB-<U+200B><id>` y las demás grafías con caracteres de ancho cero o
    ignorables no pueden colar un documento de B en el notebook de A, aunque A aún no tenga fila de tema (`ajeno_ligero`) o ya
    la tenga (`ajeno`). Se comprueba: (1) la carga de B da el MISMO 404 que con la clave ajena escrita normal, con una fila de
    intento por petición; (2) no se crea ninguna fila de tema, documento, tarea ni archivo; (3) la primera carga legítima de A
    guarda sus documentos bajo `NB-<id>` y ninguno de B. Además (decisión 17) `NB‐５` y similares no están disponibles ni
    para el dueño del notebook propio."""
    from tests.soporte.flujos import id_del_documento

    escenario = request.getfixturevalue(escenario)
    propio = crear_notebook(cliente_api, escenario.cabeceras_otro, f"{PREFIJO_DATOS} notebook del otro", registro_de_datos)
    clave_a, n_a = escenario.notebook["clave_interna"], escenario.notebook["id"]
    pedidos = {**_grafias_con_caracteres_invisibles(n_a), **{f"ajeno_{c}": v for c, v in _digitos_no_ascii(n_a).items()}}
    propios_no_disponibles = {f"propio_{c}": v for c, v in _digitos_no_ascii(propio["id"]).items()}
    todos = {**pedidos, **propios_no_disponibles}
    diagnostico = "; ".join(f"«{caso}» se guardaría como {_como_la_base_guardaria(valor)!r}" for caso, valor in pedidos.items())
    caplog.set_level(logging.DEBUG, logger="app")
    intruso = documento_de_prueba()
    antes = foto_de_efectos(correo_simulado)
    tareas = len(encolado_interceptado.pendientes)
    marca = _marca_de_bitacora()
    nombres_de_a = set(_nombres_bajo_el_tema(clave_a))

    ajena_normal = cargar(cliente_api, escenario.cabeceras_otro, clave_a, [(intruso.nombre, intruso.contenido)])
    respuestas = {caso: cargar(cliente_api, escenario.cabeceras_otro, valor, [(intruso.nombre, intruso.contenido)])
                  for caso, valor in todos.items()}

    assert ajena_normal.status_code == 404
    for caso, respuesta in respuestas.items():
        assert respuesta.status_code == 404, f"«{caso}» dio {respuesta.status_code}; {diagnostico}"
        assert respuesta.json() == ajena_normal.json(), f"«{caso}» no responde igual que la clave ajena"
    assert len(encolado_interceptado.pendientes) == tareas, f"se encoló una tarea; {diagnostico}"
    assert id_del_documento(intruso.nombre) is None, f"se creó el documento; {diagnostico}"
    despues = foto_de_efectos(correo_simulado)
    assert despues["filas"]["T_Bitacora"] - antes["filas"]["T_Bitacora"] == 1 + len(todos)
    for foto in (antes, despues):
        foto["filas"].pop("T_Bitacora")
    assert despues == antes, f"la carga dejó efectos (¿una fila de tema nueva?); {diagnostico}"
    filas = _filas_de(escenario.otro, CARGA_DOCUMENTOS, marca)
    assert len(filas) == 1 + len(todos) and all(f["texto"] == INTENTO and f["info"]["tipo_error"] == "acceso" for f in filas)
    assert len({json.dumps(f, sort_keys=True) for f in _sin_lo_volatil(filas)}) == 1, "los intentos no son idénticos"

    # (3) La primera carga legítima de A: sus documentos quedan bajo `NB-<id>` y ninguno de B.
    propio_a = documento_de_prueba()
    primera = cargar(cliente_api, escenario.cabeceras_dueno, clave_a, [(propio_a.nombre, propio_a.contenido)])
    assert primera.status_code == 200 and primera.json()["expediente"] == clave_a
    assert encolado_interceptado.pendientes[-1].tema == clave_a
    temas = [t for (t,) in _consultar("SELECT CT_Num_expediente FROM T_Expediente WHERE CT_Num_expediente LIKE :p",
                                      {"p": f"%{n_a}%"})]
    assert all(t == clave_a for t in temas), f"hay un tema que no es la clave de A (¿el de B?): {temas!r}"
    nombres = _nombres_bajo_el_tema(clave_a)
    assert intruso.nombre not in nombres, "un documento de B quedó en el notebook de A"
    assert set(nombres) <= nombres_de_a | {propio_a.nombre}, f"documentos ajenos en el notebook de A: {nombres}"


@pytest.mark.requisito("RF-17.34")
@pytest.mark.parametrize("grafia", ["ŃB-{n}", "NB‐{n}", "NB−{n}", "N­B-{n}", "NB-​{n}", "NB-{n}́"])
def test_como_lo_guarda_la_base_coincide_con_el_insert_del_orm(grafia):
    """RF-17.34 (B2 de la vuelta 2): `como_lo_guarda_la_base` devuelve lo que de verdad guarda el INSERT del ORM
    (`ExpedienteRepository.crear`) y no lo que da un `CAST` del servidor: con `NB−<id>` el INSERT guarda un guion largo
    (U+2013) y el `CAST` un guion simple, y con `NB-<U+200B><id>` el INSERT quita el carácter y el `CAST` lo deja como `?`."""
    from app.db.database import engine
    from app.repositories.expediente_repository import ExpedienteRepository
    from sqlalchemy.orm import Session
    from app.db.models.expediente import T_Expediente

    repositorio = ExpedienteRepository()
    valor = grafia.format(n=987650123)
    with Session(engine) as db:
        previsto = repositorio.como_lo_guarda_la_base(db, valor)
        creado = repositorio.crear(db, valor)
        try:
            guardado = _consultar("SELECT CT_Num_expediente FROM T_Expediente WHERE CN_Id_expediente = :i",
                                  {"i": creado.CN_Id_expediente})[0][0]
        finally:
            db.execute(T_Expediente.__table__.delete().where(T_Expediente.CN_Id_expediente == creado.CN_Id_expediente))
            db.commit()
    assert previsto == guardado, f"se prevé {previsto!r} y el INSERT guarda {guardado!r}"


@pytest.mark.requisito("RF-17.34")
@pytest.mark.requisito("RF-11.31")
@pytest.mark.requisito("RF-21.33")
def test_chat_por_tema_con_grafia_que_la_base_guarda_como_clave(cliente_api, ajeno_ligero, registro_de_datos, ollama_simulado):
    """RF-17.34 (B1): el chat por tema con una grafía que la base guarda como la clave de un notebook sin fila de tema (ajeno o
    propio) es el chat general, igual que con la clave normal: mismo contexto, y la bitácora sin la grafía (la ajena, además,
    con el intento fallido «notebook no disponible»)."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    propio = crear_notebook(cliente_api, ajeno_ligero.cabeceras_otro, f"{PREFIJO_DATOS} notebook del otro", registro_de_datos)
    pregunta = f"{PREFIJO_DATOS} ¿qué dice el documento inventado sobre la quebrada ficticia?"
    _, contexto_general = _preguntar(cliente_api, ollama_simulado, ajeno_ligero.cabeceras_otro, pregunta)

    for etiqueta, id_notebook, intento in (("ajena", ajeno_ligero.notebook["id"], True), ("propia", propio["id"], False)):
        for caso, tema in _grafias_que_la_base_guarda_como_clave(id_notebook).items():
            marca = _marca_de_bitacora()
            respuesta, contexto = _preguntar(cliente_api, ollama_simulado, ajeno_ligero.cabeceras_otro, pregunta, expediente_number=tema)
            assert respuesta.status_code == 200 and contexto == contexto_general, f"«{etiqueta} {caso}» no es el chat general"
            filas = _filas_nuevas(ajeno_ligero.otro, marca)
            crudo = json.dumps(filas, ensure_ascii=False).casefold()
            assert tema.casefold() not in crudo, f"la bitácora de «{etiqueta} {caso}» lleva la grafía"
            assert all(f["info"].get("tipo_consulta") != "expediente" for f in filas), f"«{etiqueta} {caso}» se registró como un tema"
            assert len([f for f in filas if f["info"].get("motivo") == MOTIVO_NOTEBOOK]) == (1 if intento else 0)


# --- T7: NotebookServIA por su servicio, con bitácora y mensajes (RF-17.30, RF-21.30, RNF-07.32, RNF-07.6) -----------------------

CONSULTAR_ARCHIVO = 10          # descarga o visualización
LISTAR_ARCHIVOS = 11
CREAR_NOTEBOOK = 16
QUITAR_DOCUMENTO = 17
MOTIVO_DOCUMENTO = "documento no disponible"
_TIPO_DE_OPERACION = {"listar": LISTAR_ARCHIVOS, "previsualizar": CONSULTAR_ARCHIVO, "quitar": QUITAR_DOCUMENTO}


def _filas_del_usuario(usuario, desde: int) -> list:
    """TODAS las filas del usuario posteriores a la marca: `{tipo, texto, expediente, info}` con `info` ya decodificado."""
    filas = _consultar(
        "SELECT CN_Id_tipo_accion, CT_Texto, CN_Id_expediente, CT_Informacion_adicional FROM T_Bitacora "
        "WHERE CN_Id_usuario = :u AND CN_Id_bitacora > :m ORDER BY CN_Id_bitacora", {"u": usuario.cedula, "m": desde})
    return [{"tipo": t, "texto": x, "expediente": e, "info": json.loads(i) if i else {}} for t, x, e, i in filas]


def _sin_bitacora(foto: dict) -> dict:
    """La foto de efectos sin el conteo de filas de la bitácora (que admite la fila del intento fallido)."""
    return {**foto, "filas": {tabla: n for tabla, n in foto["filas"].items() if tabla != "T_Bitacora"}}


def _contenido_de_la_fila(fila: dict) -> str:
    """El texto y la información adicional de una fila, en minúsculas y sin la hora (sus dígitos coincidirían con cualquier
    identificador numérico), para comprobar que no lleva lo pedido."""
    info = {clave: valor for clave, valor in fila["info"].items() if clave != "timestamp"}
    return (fila["texto"] + json.dumps(info, ensure_ascii=False)).casefold()


def _operacion_de_notebook(cliente_api, cabeceras, operacion: str, id_notebook, id_documento=1):
    ruta = f"/notebooks/{id_notebook}/documentos"
    if operacion == "listar":
        return cliente_api.get(ruta, headers=cabeceras)
    if operacion == "previsualizar":
        return cliente_api.get(f"{ruta}/{id_documento}/archivo", headers=cabeceras)
    return cliente_api.delete(f"{ruta}/{id_documento}", headers=cabeceras)


@pytest.mark.requisito("RF-17.30")
def test_crear_con_error_inesperado_es_generico(cliente_api, sesion, correo_simulado, monkeypatch, caplog):
    """RF-17.30: si crear el notebook falla por un error inesperado (aquí el repositorio lanza con una ruta inventada) la
    respuesta es 500 «Error interno del servidor», sin el texto de la excepción ni la ruta, ni en el cuerpo ni en el registro
    del servidor, y no queda ningún efecto (ni notebook ni fila de bitácora). Un nombre vacío conserva su 400 con mensaje."""
    from app.repositories.notebook_repository import NotebookRepository

    caplog.set_level(logging.DEBUG, logger="app")
    ruta = f"/srv/{PREFIJO_DATOS}_interno/almacen_{uuid.uuid4().hex[:6]}.py"

    def _falla(self, *args, **kwargs):
        raise Exception(f"Error creando notebook: falla simulada en {ruta}")

    monkeypatch.setattr(NotebookRepository, "crear", _falla)
    antes = foto_de_efectos(correo_simulado)

    respuesta = cliente_api.post("/notebooks", json={"nombre": f"{PREFIJO_DATOS} notebook que falla"}, headers=sesion)

    assert respuesta.status_code == 500 and respuesta.json() == {"detail": "Error interno del servidor"}
    assert ruta not in respuesta.text and ruta not in caplog.text, "la ruta de la excepción salió a la respuesta o al registro"
    assert foto_de_efectos(correo_simulado) == antes, "el error dejó algún efecto"
    vacio = cliente_api.post("/notebooks", json={"nombre": "  "}, headers=sesion)
    assert vacio.status_code == 400 and "nombre" in vacio.json()["detail"].lower()


@pytest.mark.requisito("RF-21.30")
def test_acciones_de_notebook_en_bitacora(cliente_api, sesion, usuario_gubernamental, registro_de_datos, procesamiento_en_prueba):
    """RF-21.30: crear un notebook, previsualizar un documento y quitarlo dejan UNA fila cada uno, con el usuario, el tipo
    (16, 10 y 17), la clave `NB-<id>` como tema (también asociada al tema de la base cuando ya existe), el número del
    documento y el resultado; listar no deja fila. Ni el nombre del notebook ni el del archivo (aquí con un nombre de persona
    inventado) llegan a la bitácora."""
    import dataclasses

    persona = "Maria Fernanda Rojas Quesada"
    base = documento_de_prueba()
    documento = dataclasses.replace(base, nombre=base.nombre.replace(PREFIJO_DATOS, f"{PREFIJO_DATOS}_Maria_Rojas", 1))
    marca = _marca_de_bitacora()

    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} {persona}", registro_de_datos)
    clave = notebook["clave_interna"]
    creadas = _filas_de(usuario_gubernamental, CREAR_NOTEBOOK, marca)
    assert len(creadas) == 1, creadas
    assert clave in creadas[0]["texto"] and creadas[0]["info"]["tema"] == clave and creadas[0]["info"]["resultado"] == "exitoso"

    _, id_documento = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook, documento)
    id_tema = _consultar("SELECT CN_Id_expediente FROM T_Expediente WHERE CT_Num_expediente = :t", {"t": clave})[0][0]
    marca = _marca_de_bitacora()
    ruta = f"/notebooks/{notebook['id']}/documentos"

    assert cliente_api.get(ruta, headers=sesion).status_code == 200
    assert _filas_del_usuario(usuario_gubernamental, marca) == [], "listar dejó una fila"
    vista = cliente_api.get(f"{ruta}/{id_documento}/archivo", headers=sesion)
    assert vista.status_code == 200 and vista.content == documento.contenido
    quitado = cliente_api.delete(f"{ruta}/{id_documento}", headers=sesion)
    assert quitado.status_code == 200 and quitado.json() == {"message": "Documento eliminado", "documento_id": id_documento}

    filas = _filas_del_usuario(usuario_gubernamental, marca)
    assert [f["tipo"] for f in filas] == [CONSULTAR_ARCHIVO, QUITAR_DOCUMENTO], filas
    for fila in filas:
        assert clave in fila["texto"] and str(id_documento) in fila["texto"], fila
        assert fila["expediente"] == id_tema, "la fila no quedó asociada al tema del notebook"
        assert fila["info"]["tema"] == clave and fila["info"]["documento_id"] == id_documento
        assert fila["info"]["resultado"] == "exitoso" and "tipo_error" not in fila["info"]
    todo = json.dumps(creadas + filas, ensure_ascii=False).casefold()
    for dato in (persona, "Rojas", "Quesada", documento.nombre, notebook["nombre"]):
        assert dato.casefold() not in todo, f"la bitácora lleva {dato!r}"


@pytest.mark.requisito("RF-21.30")
def test_quitar_fallido_se_registra_como_interno(cliente_api, ajeno, monkeypatch, caplog):
    """RF-21.30: si quitar un documento falla, la fila lleva el tipo 17, la clave, el número del documento, el resultado de
    error clasificado «interno» y ningún texto de la excepción; el documento sigue en el notebook (el registro del fallo no
    cambia lo que la ruta responde: un 500 con el mensaje de RF-19.2, sin texto de la excepción)."""
    from fastapi.testclient import TestClient

    from app.vectorstore import get_vectorstore_backend

    caplog.set_level(logging.DEBUG, logger="app")
    interno = f"/srv/{PREFIJO_DATOS}_interno/almacen_{uuid.uuid4().hex[:6]}.py"
    clase = type(get_vectorstore_backend())

    async def _falla(self, document_id):
        raise RuntimeError(f"falla simulada en {interno}")

    monkeypatch.setattr(clase, "delete_document_chunks", _falla)
    marca = _marca_de_bitacora()

    respuesta = TestClient(cliente_api.app, raise_server_exceptions=False).delete(
        f"/notebooks/{ajeno.notebook['id']}/documentos/{ajeno.id_documento}", headers=ajeno.cabeceras_dueno)

    assert respuesta.status_code == 500 and interno not in respuesta.text
    assert respuesta.json() == {"detail": "No se pudo quitar el documento. Intente de nuevo."}
    filas = _filas_de(ajeno.dueno, QUITAR_DOCUMENTO, marca)
    assert len(filas) == 1, filas
    info = filas[0]["info"]
    assert ajeno.notebook["clave_interna"] in filas[0]["texto"] and info["documento_id"] == ajeno.id_documento
    assert info["tema"] == ajeno.notebook["clave_interna"] and info["resultado"] == "error" and info["tipo_error"] == "interno"
    assert interno not in json.dumps(filas, ensure_ascii=False) and ajeno.documento.nombre not in json.dumps(filas, ensure_ascii=False)
    lista = cliente_api.get(f"/notebooks/{ajeno.notebook['id']}/documentos", headers=ajeno.cabeceras_dueno).json()
    assert [d["id"] for d in lista] == [ajeno.id_documento], "el documento dejó de estar en el notebook"


@pytest.mark.requisito("RF-17.34")
@pytest.mark.requisito("RF-17.31")
@pytest.mark.requisito("RF-21.33")
def test_similares_y_resumen_con_grafia_que_la_base_guarda_como_clave(cliente_api, ajeno_ligero, registro_de_datos, ollama_simulado):
    """RF-17.34 (B1): temas similares y resumen IA con una grafía que la base guardaría como la clave de un notebook ajeno sin
    fila de tema responden como un tema inexistente (igual que con la clave normal), el modelo no recibe nada y la bitácora
    no lleva la grafía, con el intento fallido «notebook no disponible» (como con la clave normal)."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    normal = ajeno_ligero.notebook["clave_interna"]
    grafias = {"normal": normal, **_grafias_que_la_base_guarda_como_clave(ajeno_ligero.notebook["id"])}
    esperada, filas = {}, {}
    for caso, tema in grafias.items():
        marca = _marca_de_bitacora()
        busqueda = _busqueda_por_tema(cliente_api, ajeno_ligero.cabeceras_otro, tema)
        resumen = _resumen_de(cliente_api, ajeno_ligero.cabeceras_otro, tema)
        formas = (_forma_de(busqueda, tema), _forma_de(resumen, tema))
        esperada.setdefault("formas", formas)
        assert formas == esperada["formas"], f"«{caso}» no responde como la clave normal"
        filas[caso] = {"busqueda": _filas_de(ajeno_ligero.otro, BUSQUEDA_SIMILARES, marca),
                       "resumen": _filas_de(ajeno_ligero.otro, GENERAR_RESUMEN, marca)}
    assert not _todo_lo_que_recibio_el_modelo(ollama_simulado), "el modelo recibió algo con la clave de un notebook"
    for caso, tema in grafias.items():
        assert tema.casefold() not in json.dumps(filas[caso], ensure_ascii=False).casefold(), f"la bitácora de «{caso}» lleva la grafía"
        for accion in ("busqueda", "resumen"):
            assert _sin_lo_volatil(filas[caso][accion]) == _sin_lo_volatil(filas["normal"][accion]), f"«{caso}», {accion}"
            assert len([f for f in filas[caso][accion] if f["info"].get("motivo") == MOTIVO_NOTEBOOK]) == 1


@pytest.mark.requisito("RF-21.30")
@pytest.mark.parametrize("caso, estado, detalle, motivo, tipo_error", [
    ("sin_procesar", 400, "El archivo aún no está disponible para previsualizar", "documento sin procesar", "validacion"),
    ("archivo_faltante", 404, "Archivo no encontrado", "archivo no encontrado", "interno"),
], ids=["sin_procesar", "archivo_faltante"])
def test_previsualizar_fallido_se_registra(caso, estado, detalle, motivo, tipo_error, cliente_api, ajeno, bitacora_que_falla):
    """RF-21.30 (H1 de la revisión T6-T8, plan §7 y §14.13): si previsualizar un documento PROPIO falla, la fila lleva el tipo 10,
    la clave `NB-<id>`, el número del documento, el resultado de error, el motivo fijo («documento sin procesar» como
    «validacion»; «archivo no encontrado» como «interno») y ni el nombre del archivo ni su ruta. La respuesta no cambia
    (400/404 con su mensaje) y es la misma con la bitácora fallando."""
    from app.db.database import engine
    from app.services.documentos.file_management_service import file_management_service

    clave, nombre = ajeno.notebook["clave_interna"], ajeno.documento.nombre
    ruta = f"/notebooks/{ajeno.notebook['id']}/documentos/{ajeno.id_documento}/archivo"
    ruta_del_archivo = str(file_management_service.obtener_ruta_archivo(clave, nombre))
    if caso == "sin_procesar":
        with engine.begin() as conexion:
            conexion.execute(
                text("UPDATE T_Documento SET CN_Id_estado = (SELECT CN_Id_estado FROM T_Estado_procesamiento "
                     "WHERE CT_Nombre_estado = 'Pendiente') WHERE CN_Id_documento = :d"), {"d": ajeno.id_documento})
    else:
        Path(ruta_del_archivo).unlink()
    marca = _marca_de_bitacora()

    respuesta = cliente_api.get(ruta, headers=ajeno.cabeceras_dueno)

    assert respuesta.status_code == estado and respuesta.json() == {"detail": detalle}
    filas = _filas_de(ajeno.dueno, CONSULTAR_ARCHIVO, marca)
    assert len(filas) == 1, filas
    info = filas[0]["info"]
    assert clave in filas[0]["texto"] and str(ajeno.id_documento) in filas[0]["texto"]
    assert info["tema"] == clave and info["documento_id"] == ajeno.id_documento
    assert info["resultado"] == "error" and info["tipo_error"] == tipo_error and info["motivo"] == motivo
    crudo = json.dumps(filas, ensure_ascii=False)
    assert nombre not in crudo and ruta_del_archivo not in crudo and str(Path(ruta_del_archivo).parent) not in crudo
    bitacora_que_falla()
    marca = _marca_de_bitacora()
    con_bitacora_caida = cliente_api.get(ruta, headers=ajeno.cabeceras_dueno)
    assert (con_bitacora_caida.status_code, con_bitacora_caida.json()) == (respuesta.status_code, respuesta.json())
    assert _filas_de(ajeno.dueno, CONSULTAR_ARCHIVO, marca) == []


@pytest.mark.requisito("RF-21.30")
def test_con_la_bitacora_fallando_las_acciones_de_notebook_se_completan(cliente_api, ajeno, registro_de_datos, bitacora_que_falla):
    """RF-21.30: con el registro de la bitácora fallando, crear, previsualizar y quitar responden lo mismo que con ella
    funcionando (la acción se completa) y no queda ninguna fila nueva del usuario."""
    bitacora_que_falla()
    marca = _marca_de_bitacora()
    ruta = f"/notebooks/{ajeno.notebook['id']}/documentos"

    nuevo = crear_notebook(cliente_api, ajeno.cabeceras_dueno, f"{PREFIJO_DATOS} notebook con bitácora caída", registro_de_datos)
    vista = cliente_api.get(f"{ruta}/{ajeno.id_documento}/archivo", headers=ajeno.cabeceras_dueno)
    quitado = cliente_api.delete(f"{ruta}/{ajeno.id_documento}", headers=ajeno.cabeceras_dueno)

    assert nuevo["clave_interna"] == f"NB-{nuevo['id']}"
    assert vista.status_code == 200 and vista.content == ajeno.documento.contenido
    assert quitado.status_code == 200 and quitado.json() == {"message": "Documento eliminado", "documento_id": ajeno.id_documento}
    assert _filas_del_usuario(ajeno.dueno, marca) == [], "con la bitácora fallando quedaron filas"


@pytest.mark.requisito("RF-21.32")
@pytest.mark.requisito("RNF-07.6")
def test_intento_fallido_de_notebook_por_operacion(cliente_api, ajeno_ligero, caplog, bitacora_que_falla):
    """RF-21.32 y RNF-07.6: listar, previsualizar o quitar en un notebook ajeno o inexistente da el mismo 404 y deja UNA fila
    de intento fallido del tipo de la acción (11, 10 y 17), idéntica para lo ajeno y lo inexistente: solo el motivo, como error
    de acceso, sin clave ni identificadores; el registro del servidor tampoco los repite. Con la bitácora fallando, la
    respuesta es la misma y no queda ninguna fila."""
    caplog.set_level(logging.DEBUG, logger="app")
    otro = ajeno_ligero.cabeceras_otro
    pedidos = {"ajeno": ajeno_ligero.notebook["id"], "inexistente": ajeno_ligero.id_inexistente, "enorme": 10**30}

    for operacion, tipo in _TIPO_DE_OPERACION.items():
        filas = {}
        for caso, id_notebook in pedidos.items():
            marca = _marca_de_bitacora()
            respuesta = _operacion_de_notebook(cliente_api, otro, operacion, id_notebook)
            assert (respuesta.status_code, respuesta.json()) == (404, {"detail": "Notebook no encontrado"}), (operacion, caso)
            filas[caso] = _filas_del_usuario(ajeno_ligero.otro, marca)
            assert len(filas[caso]) == 1 and filas[caso][0]["tipo"] == tipo, (operacion, caso, filas[caso])
            fila = filas[caso][0]
            assert fila["texto"] == INTENTO and fila["expediente"] is None
            assert fila["info"]["motivo"] == MOTIVO_NOTEBOOK and fila["info"]["tipo_error"] == "acceso"
            crudo = _contenido_de_la_fila(fila)
            for dato in (ajeno_ligero.notebook["clave_interna"], f"nb-{ajeno_ligero.id_inexistente}", str(id_notebook)):
                assert dato.casefold() not in crudo, f"«{operacion}/{caso}»: la bitácora lleva {dato!r}"
        assert _sin_lo_volatil(filas["ajeno"]) == _sin_lo_volatil(filas["inexistente"]) == _sin_lo_volatil(filas["enorme"])
    registro = caplog.text.casefold()
    for dato in (ajeno_ligero.notebook["clave_interna"], f"nb-{ajeno_ligero.id_inexistente}"):
        assert dato.casefold() not in registro, f"el registro del servidor lleva {dato!r}"

    bitacora_que_falla()
    marca = _marca_de_bitacora()
    for operacion in _TIPO_DE_OPERACION:
        respuesta = _operacion_de_notebook(cliente_api, otro, operacion, ajeno_ligero.notebook["id"])
        assert (respuesta.status_code, respuesta.json()) == (404, {"detail": "Notebook no encontrado"}), operacion
    assert _filas_del_usuario(ajeno_ligero.otro, marca) == [], "con la bitácora fallando quedaron filas"


@pytest.mark.requisito("RNF-07.32")
def test_documento_ajeno_en_notebook_propio(cliente_api, ajeno, registro_de_datos, correo_simulado, caplog):
    """RNF-07.32: en un notebook PROPIO, previsualizar o quitar un documento de otro usuario o inexistente da el mismo 404
    «Documento no encontrado en este notebook» y deja UNA fila de intento fallido (tipo 10 o 17, «documento no disponible»,
    error de acceso, sin clave, nombre ni identificadores); nada cambia en la base, Qdrant ni los archivos y el dueño sigue
    viendo y descargando su documento."""
    caplog.set_level(logging.DEBUG, logger="app")
    propio = crear_notebook(cliente_api, ajeno.cabeceras_otro, f"{PREFIJO_DATOS} notebook del otro", registro_de_datos)
    inexistente = ajeno.id_documento + 1_000_000
    pedidos = {"ajeno": ajeno.id_documento, "inexistente": inexistente, "enorme": 10**30}
    antes = foto_de_efectos(correo_simulado)

    for operacion, tipo in (("previsualizar", CONSULTAR_ARCHIVO), ("quitar", QUITAR_DOCUMENTO)):
        filas = {}
        for caso, id_documento in pedidos.items():
            marca = _marca_de_bitacora()
            respuesta = _operacion_de_notebook(cliente_api, ajeno.cabeceras_otro, operacion, propio["id"], id_documento)
            assert (respuesta.status_code, respuesta.json()) == (404, {"detail": "Documento no encontrado en este notebook"}), (operacion, caso)
            assert ajeno.documento.frase not in respuesta.text
            filas[caso] = _filas_del_usuario(ajeno.otro, marca)
            assert len(filas[caso]) == 1 and filas[caso][0]["tipo"] == tipo, (operacion, caso, filas[caso])
            fila = filas[caso][0]
            assert fila["texto"] == f"Intento fallido: {MOTIVO_DOCUMENTO}" and fila["expediente"] is None
            assert fila["info"]["motivo"] == MOTIVO_DOCUMENTO and fila["info"]["tipo_error"] == "acceso"
            crudo = _contenido_de_la_fila(fila)
            for dato in (propio["clave_interna"], ajeno.notebook["clave_interna"], ajeno.documento.nombre, str(id_documento)):
                assert dato.casefold() not in crudo, f"«{operacion}/{caso}»: la bitácora lleva {dato!r}"
        assert _sin_lo_volatil(filas["ajeno"]) == _sin_lo_volatil(filas["inexistente"]) == _sin_lo_volatil(filas["enorme"])
    registro = caplog.text.casefold()
    for dato in (ajeno.documento.nombre, ajeno.notebook["clave_interna"]):
        assert dato.casefold() not in registro, f"el registro del servidor lleva {dato!r}"

    despues = foto_de_efectos(correo_simulado)
    assert despues["filas"]["T_Bitacora"] - antes["filas"]["T_Bitacora"] == 6
    assert _sin_bitacora(despues) == _sin_bitacora(antes), "se leyó o cambió algo"
    original = cliente_api.get(f"/notebooks/{ajeno.notebook['id']}/documentos/{ajeno.id_documento}/archivo", headers=ajeno.cabeceras_dueno)
    assert original.status_code == 200 and original.content == ajeno.documento.contenido
