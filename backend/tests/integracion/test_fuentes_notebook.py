"""Selección de fuentes en el chat del notebook, parte de integración (spec 009b, T1; RF-11.101, RF-11.102, RF-11.105,
RF-11.106, RF-11.107, RNF-07.100, RF-21.102).

Usa la API real con un Usuario Gubernamental `PRUEBA`, SQL Server, Tika, Qdrant y los embeddings reales del entorno aislado, y
el Ollama simulado: lo que se comprueba es lo que RECIBE el modelo, lo que responde la API y lo que queda en la bitácora.
Los datos son inventados (prefijo `PRUEBA`) y se limpian solos.
"""
import json
import uuid
from dataclasses import dataclass

import pytest
from sqlalchemy import text

from app.db.database import engine
from tests.integracion.conftest import (
    RESPUESTA_SIMULADA, _consultar, _documento_procesado_en_el_notebook, _todo_lo_que_recibio_el_modelo,
)
from tests.integracion.test_aislamiento_notebooks import _documento_de_otro_asunto, _puntos_del_documento
from tests.soporte.flujos import cargar, crear_notebook, estado_del_documento, tema_heredado
from tests.soporte.nombres import PREFIJO_DATOS

pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")

MENSAJE_SIN_FUENTES = "Marque al menos una fuente para consultar."
CONSULTA_RAG = 12
PREGUNTA = "¿Qué dicen los documentos inventados sobre la quebrada ficticia y sobre la receta ficticia?"


@dataclass
class Fuentes:
    cabeceras: dict
    notebook: dict
    a: object
    id_a: int
    b: object
    id_b: int
    pendiente: object
    id_pendiente: int


def _chat(cliente_api, cabeceras, notebook_id, **extra):
    """Consulta el chat del notebook con la pregunta fija; devuelve `(respuesta, sesión usada)`."""
    sesion = f"session_{PREFIJO_DATOS}sel_{uuid.uuid4().hex[:8]}"
    cuerpo = {"query": PREGUNTA, "session_id": sesion, "notebook_id": str(notebook_id), **extra}
    return cliente_api.post("/rag/consulta-con-historial-stream", json=cuerpo, headers=cabeceras), sesion


def _recibido(ollama_simulado) -> str:
    return _todo_lo_que_recibio_el_modelo(ollama_simulado, PREGUNTA)


def _marca_de_bitacora() -> int:
    return int(_consultar("SELECT COALESCE(MAX(CN_Id_bitacora), 0) FROM T_Bitacora")[0][0])


def _historial_de(sesion: str) -> bool:
    from app.services.RAG.session_store import conversation_store

    return sesion in conversation_store._store


@pytest.fixture
def fuentes(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    """Un notebook propio con dos fuentes Procesado (de asuntos distintos) y una Pendiente."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook de fuentes", registro_de_datos)
    a, id_a = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook)
    b, id_b = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook, _documento_de_otro_asunto())
    # La fuente Pendiente conserva sus fragmentos en Qdrant: procesa y devuelve su fila a Pendiente
    pendiente, id_pendiente = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook)
    with engine.begin() as conexion:
        conexion.execute(
            text("UPDATE T_Documento SET CN_Id_estado = (SELECT CN_Id_estado FROM T_Estado_procesamiento "
                 "WHERE CT_Nombre_estado = 'Pendiente') WHERE CN_Id_documento = :d"), {"d": id_pendiente})
    assert estado_del_documento(id_pendiente) == "Pendiente"
    return Fuentes(sesion, notebook, a, id_a, b, id_b, pendiente, id_pendiente)


@pytest.mark.requisito("RF-11.101")
@pytest.mark.requisito("RF-11.102")
def test_chat_notebook_respeta_la_seleccion(cliente_api, fuentes, ollama_simulado):
    """RF-11.101, RF-11.102: el modelo no recibe fragmentos ni nombre de la fuente desmarcada; el cambio rige para la
    siguiente pregunta."""
    nb = fuentes.notebook["id"]

    ollama_simulado.preguntas.clear()
    r, _ = _chat(cliente_api, fuentes.cabeceras, nb)
    assert r.status_code == 200
    todo = _recibido(ollama_simulado)
    assert fuentes.a.frase in todo and fuentes.b.frase in todo, "sin selección el modelo debe recibir ambas fuentes"

    ollama_simulado.preguntas.clear()
    r, _ = _chat(cliente_api, fuentes.cabeceras, nb, documentos=[fuentes.id_a])
    assert r.status_code == 200 and '"type": "done"' in r.text
    todo = _recibido(ollama_simulado)
    assert fuentes.a.frase in todo and fuentes.a.nombre in todo
    assert fuentes.b.frase not in todo and fuentes.b.nombre not in todo, "la fuente desmarcada llegó al modelo"

    ollama_simulado.preguntas.clear()
    r, _ = _chat(cliente_api, fuentes.cabeceras, nb, documentos=[fuentes.id_b])
    assert r.status_code == 200
    todo = _recibido(ollama_simulado)
    assert fuentes.b.frase in todo and fuentes.a.frase not in todo and fuentes.a.nombre not in todo

    # RF-11.106: marcar una fuente Pendiente junto a una Procesado no lleva la Pendiente al chat
    ollama_simulado.preguntas.clear()
    r, _ = _chat(cliente_api, fuentes.cabeceras, nb, documentos=[fuentes.id_a, fuentes.id_pendiente])
    assert r.status_code == 200
    todo = _recibido(ollama_simulado)
    assert fuentes.a.frase in todo and fuentes.pendiente.nombre not in todo.replace(fuentes.a.nombre, "")


@pytest.mark.requisito("RF-11.105")
@pytest.mark.requisito("RF-11.106")
def test_seleccion_vacia_o_inefectiva_400(cliente_api, fuentes, ollama_simulado):
    """RF-11.105, RF-11.106: vacía, solo Pendiente o solo inexistente es un 400 con su mensaje, sin llamar al modelo, sin
    guardar historial y sin fila de consulta en la bitácora."""
    nb = fuentes.notebook["id"]
    casos = {"vacía": [], "solo pendiente": [fuentes.id_pendiente], "inexistente": [2 ** 62], "negativa": [-1]}
    marca = _marca_de_bitacora()
    ollama_simulado.preguntas.clear()
    for caso, ids in casos.items():
        r, sesion_chat = _chat(cliente_api, fuentes.cabeceras, nb, documentos=ids)
        assert r.status_code == 400, f"«{caso}» respondió {r.status_code}"
        assert r.json()["detail"] == MENSAJE_SIN_FUENTES, caso
        assert not _historial_de(sesion_chat), f"«{caso}» guardó la conversación"
    assert not ollama_simulado.preguntas, "el modelo fue llamado"
    filas = _consultar("SELECT COUNT(*) FROM T_Bitacora WHERE CN_Id_bitacora > :m AND CN_Id_tipo_accion = :t",
                       {"m": marca, "t": CONSULTA_RAG})[0][0]
    assert filas == 0, "el 400 dejó fila en la bitácora"


@pytest.mark.requisito("RF-11.105")
def test_seleccion_ausente_como_hoy(cliente_api, fuentes, ollama_simulado):
    """RF-11.105: con el campo ausente se consultan todas las fuentes, como antes de la 009b."""
    ollama_simulado.preguntas.clear()
    r, _ = _chat(cliente_api, fuentes.cabeceras, fuentes.notebook["id"])
    assert r.status_code == 200 and '"type": "done"' in r.text
    todo = _recibido(ollama_simulado)
    assert fuentes.a.frase in todo and fuentes.b.frase in todo


@pytest.mark.requisito("RF-11.107")
def test_seleccion_ignorada_en_general_y_tema(cliente_api, sesion, fuentes, ollama_simulado, procesamiento_en_prueba, registro_de_datos):
    """RF-11.107: en el chat general y en el de un tema el campo `documentos` se ignora (incluso vacío o con ids ajenos)."""
    tema = tema_heredado(registro_de_datos)
    doc_tema, _ = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, {"clave_interna": tema})
    pregunta = f"¿Qué dice el documento inventado sobre la quebrada ficticia {doc_tema.nombre[len(PREFIJO_DATOS) + 1:-4]}?"

    for alcance in ({"expediente_number": tema}, {}):
        for documentos in ([], [fuentes.id_a], [2 ** 62]):
            ollama_simulado.preguntas.clear()
            cuerpo = {"query": pregunta, "session_id": f"session_{PREFIJO_DATOS}ig_{uuid.uuid4().hex[:8]}",
                      "documentos": documentos, **alcance}
            r = cliente_api.post("/rag/consulta-con-historial-stream", json=cuerpo, headers=sesion)
            assert r.status_code == 200, f"{alcance} {documentos} respondió {r.status_code}"
            assert doc_tema.frase in _todo_lo_que_recibio_el_modelo(ollama_simulado, pregunta), f"{alcance} {documentos}"


@pytest.mark.requisito("RNF-07.100")
def test_seleccion_ajena_descartada(cliente_api, sesion, fuentes, ollama_simulado, procesamiento_en_prueba, registro_de_datos):
    """RNF-07.100: un documento de otro notebook mezclado en la selección se descarta y nunca llega al modelo; si era lo único
    marcado, 400. Un notebook inexistente sigue siendo el 404 uniforme."""
    otro = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook aparte", registro_de_datos)
    ajeno, id_ajeno = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, otro)
    nb = fuentes.notebook["id"]

    ollama_simulado.preguntas.clear()
    r, _ = _chat(cliente_api, fuentes.cabeceras, nb, documentos=[fuentes.id_a, id_ajeno, 2 ** 62])
    assert r.status_code == 200
    todo = _recibido(ollama_simulado)
    assert fuentes.a.frase in todo
    assert ajeno.frase not in todo and ajeno.nombre not in todo

    ollama_simulado.preguntas.clear()
    r, _ = _chat(cliente_api, fuentes.cabeceras, nb, documentos=[id_ajeno])
    assert r.status_code == 400 and r.json()["detail"] == MENSAJE_SIN_FUENTES
    assert not ollama_simulado.preguntas

    r, _ = _chat(cliente_api, fuentes.cabeceras, 2 ** 40, documentos=[fuentes.id_a])
    assert r.status_code == 404 and r.json()["detail"] == "Notebook no encontrado"


@pytest.mark.requisito("RF-11.105")
@pytest.mark.parametrize("documentos", [["5"], [5.5], [True], [None], "1"])
def test_seleccion_mal_formada_422(cliente_api, fuentes, documentos):
    """RF-11.105: ids mal formados son un 422 de la validación, no un 400 ni un 500."""
    r, _ = _chat(cliente_api, fuentes.cabeceras, fuentes.notebook["id"], documentos=documentos)
    assert r.status_code == 422


@pytest.mark.requisito("RF-21.102")
def test_la_seleccion_no_se_registra_en_la_bitacora(cliente_api, fuentes, ollama_simulado):
    """RF-21.102: la selección no se registra: la fila de la consulta no lleva los números de documento marcados."""
    marca = _marca_de_bitacora()
    r, _ = _chat(cliente_api, fuentes.cabeceras, fuentes.notebook["id"], documentos=[fuentes.id_a, fuentes.id_b])
    assert r.status_code == 200
    filas = _consultar("SELECT CT_Texto, CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_bitacora > :m", {"m": marca})
    assert filas, "la consulta debe dejar su fila"
    for texto, info in filas:
        assert "documentos" not in json.loads(info or "{}"), "la bitácora lleva la selección"


# --- T4: migración de la entrega 2 (RN-01.100, RF-21.100) ---------------------------------------------------------------------

@pytest.mark.requisito("RN-01.100")
@pytest.mark.requisito("RF-21.100")
def test_migracion_tipo_21_y_columna():
    """RN-01.100, RF-21.100: T_Documento tiene CT_Nombre_visible (500, admite vacío; el modelo la declara igual), el catálogo
    suma el tipo 21 sin tocar los demás y las constantes del backend coinciden con la base."""
    from app.constants.tipos_accion import DESCRIPCIONES_TIPOS_ACCION, TiposAccion
    from app.db.models.documento import T_Documento

    columna = _consultar(
        "SELECT IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = 'T_Documento' AND COLUMN_NAME = 'CT_Nombre_visible'")
    assert [tuple(fila) for fila in columna] == [("YES", 500)]
    assert T_Documento.__table__.c.CT_Nombre_visible.nullable is True

    filas = dict(_consultar("SELECT CN_Id_tipo_accion, CT_Nombre_tipo_accion FROM T_Tipo_accion"))
    assert filas[21] == "Renombrar Documento de Notebook"
    assert TiposAccion.RENOMBRAR_DOCUMENTO_NOTEBOOK == 21
    assert DESCRIPCIONES_TIPOS_ACCION[21] == "Renombrar Documento de Notebook"
    assert {i: filas[i] for i in range(1, 21)} == {i: DESCRIPCIONES_TIPOS_ACCION[i] for i in range(1, 21)}


# --- T5: renombrar una fuente, reglas y bitácora (RF-19.102, 19.106-19.109, RNF-07.101, RF-21.101, RF-21.104) ----------------------
# Las fuentes en Error no tienen fragmentos: son las que se renombran con éxito aquí; el renombrado de una Procesado (Qdrant y su
# compensación) es de T6. Los rechazos de una Procesado se deciden antes de tocar Qdrant.

RENOMBRAR_DOCUMENTO = 21
MENSAJE_VACIO_FUENTE = "El nombre de la fuente no puede estar vacío"
MENSAJE_EN_PROCESO = "Espere a que termine de procesarse."


def _renombrar(cliente_api, cabeceras, notebook_id, documento_id, nombre):
    return cliente_api.put(f"/notebooks/{notebook_id}/documentos/{documento_id}", json={"nombre": nombre}, headers=cabeceras)


def _poner_estado(id_documento: int, estado: str) -> None:
    with engine.begin() as conexion:
        conexion.execute(
            text("UPDATE T_Documento SET CN_Id_estado = (SELECT CN_Id_estado FROM T_Estado_procesamiento "
                 "WHERE CT_Nombre_estado = :e) WHERE CN_Id_documento = :d"), {"e": estado, "d": id_documento})


def _nombres_de(id_documento: int) -> tuple:
    """`(CT_Nombre_archivo, CT_Nombre_visible)` del documento."""
    return tuple(_consultar("SELECT CT_Nombre_archivo, CT_Nombre_visible FROM T_Documento WHERE CN_Id_documento = :d",
                            {"d": id_documento})[0])


def _filas_desde(usuario, marca: int) -> list:
    filas = _consultar(
        "SELECT CN_Id_tipo_accion, CT_Texto, CN_Id_expediente, CT_Informacion_adicional FROM T_Bitacora "
        "WHERE CN_Id_usuario = :u AND CN_Id_bitacora > :m ORDER BY CN_Id_bitacora", {"u": usuario.cedula, "m": marca})
    return [{"tipo": t, "texto": x, "expediente": e, "info": json.loads(i) if i else {}} for t, x, e, i in filas]


@pytest.mark.requisito("RF-19.106")
@pytest.mark.requisito("RF-19.107")
@pytest.mark.requisito("RF-21.101")
def test_renombrar_rechazos_400(cliente_api, fuentes, usuario_gubernamental):
    """RF-19.106, RF-19.107, RF-21.101: vacío, de más de 150, con caracteres no admitidos, duplicado (sin mayúsculas) y fuente
    en proceso dan 400 con su mensaje, no cambian el nombre y dejan UNA fila de error sin ningún nombre; el idéntico es 200 sin
    fila. Las reglas del nombre rigen también para una fuente Procesado (se rechaza antes de tocar Qdrant)."""
    nb, doc = fuentes.notebook["id"], fuentes.id_a
    antes = _nombres_de(doc)
    base_de_b = fuentes.b.nombre[:-len(".txt")]
    casos = [
        (doc, "   ", MENSAJE_VACIO_FUENTE, "nombre vacío"),
        (doc, "\u200b", MENSAJE_VACIO_FUENTE, "nombre vacío"),
        (doc, "a" * 151, "El nombre no puede superar 150 caracteres.", "nombre demasiado largo"),
        (doc, "Informe \U0001f600", "El nombre contiene caracteres no admitidos.", "nombre con caracteres no admitidos"),
        (doc, f"  {base_de_b.upper()} ", "Ya hay una fuente con ese nombre en este notebook.", "nombre duplicado"),
        (fuentes.id_pendiente, "Nuevo", MENSAJE_EN_PROCESO, "fuente en proceso"),
        (fuentes.id_pendiente, "   ", MENSAJE_EN_PROCESO, "fuente en proceso"),
    ]
    for destino, nombre, mensaje, motivo in casos:
        marca = _marca_de_bitacora()
        r = _renombrar(cliente_api, fuentes.cabeceras, nb, destino, nombre)
        assert r.status_code == 400 and r.json() == {"detail": mensaje}, (nombre, r.status_code, r.text)
        filas = _filas_desde(usuario_gubernamental, marca)
        assert len(filas) == 1 and filas[0]["tipo"] == RENOMBRAR_DOCUMENTO, (motivo, filas)
        info = filas[0]["info"]
        assert info["tema"] == fuentes.notebook["clave_interna"] and info["documento_id"] == destino
        assert info["resultado"] == "error" and info["motivo"] == motivo and info["tipo_error"] == "validacion"
        assert "Informe" not in json.dumps(filas[0], ensure_ascii=False) and base_de_b not in json.dumps(filas[0])
    assert _nombres_de(doc) == antes and _nombres_de(fuentes.id_pendiente)[1] is None

    # El idéntico (el nombre mostrado, extensión aparte) no cambia nada, responde 200 y no deja fila
    marca = _marca_de_bitacora()
    r = _renombrar(cliente_api, fuentes.cabeceras, nb, doc, fuentes.a.nombre[:-len(".txt")])
    assert r.status_code == 200 and r.json()["nombre_archivo"] == fuentes.a.nombre
    assert _filas_desde(usuario_gubernamental, marca) == [] and _nombres_de(doc) == antes


@pytest.mark.requisito("RNF-07.101")
@pytest.mark.requisito("RF-19.109")
@pytest.mark.requisito("RF-21.104")
def test_renombrar_no_disponible_404(cliente_api, sesion, fuentes, usuario_gubernamental, iniciar_sesion, administrador,
                                     registro_de_datos):
    """RNF-07.101, RF-19.109, RF-21.104: notebook ajeno, inexistente o con id no canónico, y fuente de otro notebook, inexistente
    o con id no canónico dan el 404 uniforme ANTES de validar el nombre (aquí vacío), con UNA fila de intento fallido solo con su
    motivo, sin cambiar nada. El Administrador recibe 403."""
    from tests.soporte.datos import ROL_USUARIO_GUBERNAMENTAL, crear_usuario

    ajeno_usuario = crear_usuario(ROL_USUARIO_GUBERNAMENTAL, registro_de_datos)
    cabeceras_ajeno = iniciar_sesion(ajeno_usuario)
    notebook_ajeno = crear_notebook(cliente_api, cabeceras_ajeno, f"{PREFIJO_DATOS} de otro", registro_de_datos)
    otro_propio = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} aparte", registro_de_datos)
    nb, doc = fuentes.notebook["id"], fuentes.id_a
    inexistente = int(_consultar("SELECT COALESCE(MAX(CN_Id_notebook), 0) + 1000000 FROM T_Notebook")[0][0])
    doc_inexistente = int(_consultar("SELECT COALESCE(MAX(CN_Id_documento), 0) + 1000000 FROM T_Documento")[0][0])
    no_canonicos = ["abc", "05", "+5", "9" * 30, "0", "-1", "5.0"]
    notebook_no_disponible = [(ajeno, doc) for ajeno in (notebook_ajeno["id"], inexistente, *no_canonicos)]
    documento_no_disponible = [(nb, d) for d in (doc_inexistente, *no_canonicos)] + [(otro_propio["id"], doc)]
    antes = _nombres_de(doc)
    for (notebook_id, documento_id), motivo, detalle in (
            [(c, "notebook no disponible", "Notebook no encontrado") for c in notebook_no_disponible]
            + [(c, "documento no disponible", "Documento no encontrado en este notebook") for c in documento_no_disponible]):
        marca = _marca_de_bitacora()
        r = _renombrar(cliente_api, fuentes.cabeceras, notebook_id, documento_id, "   ")
        assert r.status_code == 404 and r.json() == {"detail": detalle}, (notebook_id, documento_id, r.status_code, r.text)
        filas = _filas_desde(usuario_gubernamental, marca)
        assert len(filas) == 1 and filas[0]["tipo"] == RENOMBRAR_DOCUMENTO, (notebook_id, documento_id, filas)
        assert filas[0]["info"]["motivo"] == motivo and filas[0]["info"]["tipo_error"] == "acceso"
        assert filas[0]["info"]["error"] == "intento fallido" and filas[0]["expediente"] is None
        assert "tema" not in filas[0]["info"] and "documento_id" not in filas[0]["info"]
    assert _nombres_de(doc) == antes

    # El dueño del documento tampoco lo cambia desde el notebook de otro usuario
    r = _renombrar(cliente_api, cabeceras_ajeno, notebook_ajeno["id"], doc, "Robado")
    assert r.status_code == 404 and _nombres_de(doc) == antes
    cabeceras_admin = iniciar_sesion(administrador)
    assert _renombrar(cliente_api, cabeceras_admin, nb, doc, "x").status_code == 403


@pytest.mark.requisito("RF-19.102")
@pytest.mark.requisito("RF-19.103")
@pytest.mark.requisito("RF-19.108")
@pytest.mark.requisito("RF-21.101")
def test_bitacora_renombrar(cliente_api, fuentes, usuario_gubernamental, monkeypatch):
    """RF-19.102, RF-19.103, RF-19.108, RF-21.101: renombrar una fuente en Error guarda base + extensión como nombre visible
    sin tocar el interno, y deja UNA fila con usuario, tipo, clave, número de documento y resultado, sin ningún nombre (persona
    inventada); un fallo inesperado es 500 genérico, no cambia nada y deja su fila «error inesperado»; si la bitácora falla,
    la acción continúa."""
    from app.repositories.documento_repository import DocumentoRepository
    from app.services.bitacora.notebooks_audit_service import notebooks_audit_service

    nb, doc = fuentes.notebook["id"], fuentes.id_a
    _poner_estado(doc, "Error")
    interno = _nombres_de(doc)[0]

    marca = _marca_de_bitacora()
    r = _renombrar(cliente_api, fuentes.cabeceras, nb, doc, "  PRUEBA Carlos Mora Vargas  ")
    assert r.status_code == 200
    assert r.json() == {"id": doc, "nombre_archivo": "PRUEBA Carlos Mora Vargas.txt", "extension": ".txt", "estado": "Error"}
    assert _nombres_de(doc) == (interno, "PRUEBA Carlos Mora Vargas.txt")
    filas = _filas_desde(usuario_gubernamental, marca)
    assert len(filas) == 1 and filas[0]["tipo"] == RENOMBRAR_DOCUMENTO
    assert filas[0]["info"]["tema"] == fuentes.notebook["clave_interna"] and filas[0]["info"]["documento_id"] == doc
    assert filas[0]["info"]["resultado"] == "exitoso" and filas[0]["expediente"] is not None
    assert "Carlos" not in json.dumps(filas, ensure_ascii=False) and interno not in json.dumps(filas, ensure_ascii=False)

    # Un fallo inesperado: 500 genérico, nada cambia y la fila no lleva el texto de la excepción
    def _falla(*args, **kwargs):
        raise Exception("detalle interno secreto C:/ruta")

    marca = _marca_de_bitacora()
    with monkeypatch.context() as local:
        local.setattr(DocumentoRepository, "renombrar", _falla)
        r = _renombrar(cliente_api, fuentes.cabeceras, nb, doc, "Otro nombre")
    assert r.status_code == 500 and r.json() == {"detail": "Error interno del servidor"}
    assert _nombres_de(doc) == (interno, "PRUEBA Carlos Mora Vargas.txt")
    filas = _filas_desde(usuario_gubernamental, marca)
    assert len(filas) == 1 and filas[0]["tipo"] == RENOMBRAR_DOCUMENTO and filas[0]["info"]["documento_id"] == doc
    assert filas[0]["info"]["resultado"] == "error" and filas[0]["info"]["motivo"] == "error inesperado"
    assert filas[0]["info"]["tipo_error"] == "interno" and "secreto" not in json.dumps(filas[0])

    # RF-21: con la bitácora caída la acción se hace igual
    async def _bitacora_caida(*args, **kwargs):
        raise Exception("falla simulada de la bitácora")

    monkeypatch.setattr(notebooks_audit_service.bitacora_service, "registrar", _bitacora_caida)
    r = _renombrar(cliente_api, fuentes.cabeceras, nb, doc, "Con bitacora caida")
    assert r.status_code == 200 and _nombres_de(doc)[1] == "Con bitacora caida.txt"


# --- T6: fragmentos en Qdrant, compensación y nombre mostrado -----------------------------------------------------------------

def _metadatos_de(id_documento: int) -> list:
    """Los `metadata` de los puntos del documento en Qdrant, ordenados por id de punto."""
    return [dict(p.payload["metadata"]) for p in sorted(_puntos_del_documento(id_documento), key=lambda p: str(p.id))]


def _ruta_en_disco(fuentes, id_documento: int):
    from app.services.documentos.file_management_service import file_management_service

    return file_management_service.obtener_ruta_archivo(fuentes.notebook["clave_interna"], _nombres_de(id_documento)[0])


@pytest.mark.requisito("RF-19.103")
@pytest.mark.requisito("RF-19.104")
def test_renombrar_fuente_procesada(cliente_api, fuentes):
    """RF-19.103, RF-19.104: renombrar una fuente Procesado guarda base + extensión como nombre visible, cambia SOLO el
    `metadata.nombre_archivo` de todos sus fragmentos (no los de otra fuente ni el resto de sus metadatos), deja el archivo en
    disco y el nombre interno igual, y el listado y la vista previa usan el nombre nuevo (el tipo sigue saliendo del interno)."""
    nb, doc = fuentes.notebook["id"], fuentes.id_a
    interno = _nombres_de(doc)[0]
    antes, de_b = _metadatos_de(doc), _metadatos_de(fuentes.id_b)
    ruta = _ruta_en_disco(fuentes, doc)
    assert antes and all(m["nombre_archivo"] == interno for m in antes) and ruta is not None and ruta.exists()

    r = _renombrar(cliente_api, fuentes.cabeceras, nb, doc, "  PRUEBA Acta renombrada ")
    nuevo = "PRUEBA Acta renombrada.txt"
    assert r.status_code == 200
    assert r.json() == {"id": doc, "nombre_archivo": nuevo, "extension": ".txt", "estado": "Procesado"}
    assert _nombres_de(doc) == (interno, nuevo)
    despues = _metadatos_de(doc)
    assert len(despues) == len(antes) and all(m["nombre_archivo"] == nuevo for m in despues)
    assert [{k: v for k, v in m.items() if k != "nombre_archivo"} for m in despues] == \
           [{k: v for k, v in m.items() if k != "nombre_archivo"} for m in antes]
    assert _metadatos_de(fuentes.id_b) == de_b
    assert _ruta_en_disco(fuentes, doc) == ruta and ruta.exists()

    listado = cliente_api.get(f"/notebooks/{nb}/documentos", headers=fuentes.cabeceras).json()
    fila = next(d for d in listado if d["id"] == doc)
    assert fila["nombre_archivo"] == nuevo and fila["extension"] == ".txt" and fila["estado"] == "Procesado"
    sin_renombrar = next(d for d in listado if d["id"] == fuentes.id_b)
    assert sin_renombrar["nombre_archivo"] == fuentes.b.nombre and sin_renombrar["extension"] == ".txt"

    vista = cliente_api.get(f"/notebooks/{nb}/documentos/{doc}/archivo", headers=fuentes.cabeceras)
    assert vista.status_code == 200 and vista.headers["content-type"].startswith("text/plain")
    from urllib.parse import unquote

    cabecera = vista.headers["content-disposition"]  # el nombre va codificado (`filename*=utf-8''...`)
    assert cabecera.startswith("inline") and nuevo in unquote(cabecera)
    assert vista.content == fuentes.a.contenido


@pytest.mark.requisito("RF-19.104")
def test_respuesta_nueva_cita_el_nombre_renombrado(cliente_api, fuentes, ollama_simulado):
    """RF-19.104 · tras renombrar una fuente Procesado, lo que recibe el modelo (encabezado del fragmento y lista de archivos)
    nombra el nombre nuevo y no el interno; la ruta de descarga conserva el interno. La fuente sin renombrar sigue igual."""
    nb, doc = fuentes.notebook["id"], fuentes.id_a
    interno = _nombres_de(doc)[0]
    assert _renombrar(cliente_api, fuentes.cabeceras, nb, doc, "PRUEBA cita renombrada").status_code == 200
    nuevo = "PRUEBA cita renombrada.txt"

    ollama_simulado.preguntas.clear()
    r, _ = _chat(cliente_api, fuentes.cabeceras, nb, documentos=[doc, fuentes.id_b])
    assert r.status_code == 200
    todo = _recibido(ollama_simulado)
    assert f"Archivo: {nuevo} |" in todo and f'- "{nuevo}"' in todo
    assert f"Archivo: {interno} |" not in todo and f'- "{interno}"' not in todo, "el modelo recibió el nombre interno"
    assert f"/{interno}" in todo, "la ruta de descarga debe seguir siendo la del archivo en disco"
    assert f"Archivo: {fuentes.b.nombre} |" in todo


@pytest.mark.requisito("RF-19.105")
@pytest.mark.requisito("RF-19.108")
def test_renombrar_compensa_si_falla_qdrant(cliente_api, fuentes, usuario_gubernamental, monkeypatch):
    """RF-19.105, RF-19.108: si Qdrant falla a mitad del cambio, o si falla la base con Qdrant ya cambiado, el nombre anterior
    vuelve a los fragmentos y la fila queda igual: 500 genérico, una fila «error inesperado» sin el texto de la excepción."""
    from app.repositories.documento_repository import DocumentoRepository
    from app.vectorstore.qdrant_backend import QdrantBackend

    nb, doc = fuentes.notebook["id"], fuentes.id_a
    nombres, metadatos = _nombres_de(doc), _metadatos_de(doc)
    original = QdrantBackend.actualizar_nombre_de_documento
    llamadas = []

    async def _cambia_y_falla(self, document_id, nombre):
        llamadas.append(nombre)
        await original(self, document_id, nombre)
        if len(llamadas) == 1:
            raise RuntimeError("detalle interno secreto C:/ruta")

    def _falla_la_base(*args, **kwargs):
        raise Exception("detalle interno secreto C:/ruta")

    def _verificar(respuesta, marca, escenario):
        assert respuesta.status_code == 500 and respuesta.json() == {"detail": "Error interno del servidor"}, escenario
        assert _nombres_de(doc) == nombres and _metadatos_de(doc) == metadatos, escenario
        filas = _filas_desde(usuario_gubernamental, marca)
        assert len(filas) == 1 and filas[0]["tipo"] == RENOMBRAR_DOCUMENTO and filas[0]["info"]["documento_id"] == doc
        assert filas[0]["info"]["motivo"] == "error inesperado" and filas[0]["info"]["tipo_error"] == "interno"
        assert "secreto" not in json.dumps(filas[0]) and "Pierde" not in json.dumps(filas[0])

    marca = _marca_de_bitacora()
    with monkeypatch.context() as local:
        local.setattr(QdrantBackend, "actualizar_nombre_de_documento", _cambia_y_falla)
        r = _renombrar(cliente_api, fuentes.cabeceras, nb, doc, "Pierde el contexto")
    assert llamadas == ["Pierde el contexto.txt", nombres[0]]
    _verificar(r, marca, "falla Qdrant")

    marca = _marca_de_bitacora()
    with monkeypatch.context() as local:
        local.setattr(DocumentoRepository, "renombrar", _falla_la_base)
        r = _renombrar(cliente_api, fuentes.cabeceras, nb, doc, "Pierde el contexto")
    _verificar(r, marca, "falla la base")

    # Sin fallos el mismo cambio sí se aplica: la compensación no dejó nada a medias
    assert _renombrar(cliente_api, fuentes.cabeceras, nb, doc, "Pierde el contexto").status_code == 200
    assert all(m["nombre_archivo"] == "Pierde el contexto.txt" for m in _metadatos_de(doc))


@pytest.mark.requisito("RF-19.103")
def test_carga_tras_renombrar(cliente_api, fuentes, procesamiento_en_prueba):
    """Casos límite de carga (QA-1): cargar un archivo con el nombre INTERNO de una fuente renombrada lo guarda aparte con
    sufijo y se muestra con ese nombre (la renombrada no cambia); cargar uno con el nombre VISIBLE de otra fuente no choca: las
    dos se muestran con el mismo nombre."""
    nb, doc = fuentes.notebook["id"], fuentes.id_a
    interno = _nombres_de(doc)[0]
    assert _renombrar(cliente_api, fuentes.cabeceras, nb, doc, "PRUEBA Acta vigente").status_code == 200
    visible = "PRUEBA Acta vigente.txt"

    def _nombres_listados():
        listado = cliente_api.get(f"/notebooks/{nb}/documentos", headers=fuentes.cabeceras).json()
        return {d["id"]: d["nombre_archivo"] for d in listado}

    antes = set(_nombres_listados())
    for nombre in (interno, visible):
        respuesta = cargar(cliente_api, fuentes.cabeceras, fuentes.notebook["clave_interna"],
                           [(nombre, b"PRUEBA texto inventado de carga")])
        assert respuesta.status_code == 200, (nombre, respuesta.text)
        procesamiento_en_prueba.procesar()
    listado = _nombres_listados()
    nuevos = [nombre for i, nombre in listado.items() if i not in antes]
    assert listado[doc] == visible and _nombres_de(doc)[0] == interno
    assert sorted(nuevos) == sorted([interno[:-len(".txt")] + "_1.txt", visible]), nuevos
