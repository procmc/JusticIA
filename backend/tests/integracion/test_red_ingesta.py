"""Red de seguridad de la ingesta (spec 004, T8; RF-05.1, RF-06.1, RF-06.2, RF-07.1, RF-08.1, RF-21.7).

Sube por `POST /ingesta/archivos`, como lo haría la interfaz, con un Usuario Gubernamental `PRUEBA`, Tika, SQL Server y
Qdrant reales del entorno aislado (base y colección `servia_pruebas`), el Redis simulado y HTR, audio y Ollama simulados:
- RF-05.1: con el encolado interceptado, un identificador por archivo, cada archivo guardado en la carpeta temporal de su
  tema, una tarea encolada por archivo y la fila de carga iniciada; todavía no hay documento ni fragmentos.
- RF-06.1, RF-07.1, RF-08.1, RF-21.7: con el procesamiento ejecutado dentro de la prueba (sin pausas), el tema y su relación,
  el documento Procesado, el progreso completado al 100 %, los fragmentos en Qdrant y las filas de la bitácora.
- RF-06.2: un tema de nombre libre se acepta y el chat acotado a él recupera el documento.
- RF-07.2 (T9): en una carga de dos documentos, el fallo de la extracción de uno no afecta al otro; el progreso del que falló,
  su fila de error en la bitácora y el estado Error de su documento se comprueban por separado.

Los datos son inventados (prefijo `PRUEBA` o temas registrados para la limpieza) y se limpian solos.
"""
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import text

from tests.soporte import entorno, rastros
from tests.soporte.flujos import (
    cargar, contexto_enviado, contar_puntos, documento_de_prueba, exigir_estado, exigir_progreso, id_del_documento,
    leer_eventos, tema_heredado,
)
from tests.soporte.nombres import PREFIJO_DATOS

# La tarea de ingesta consulta su estado en Celery; en modo inmediato Celery avisa que ese resultado no se guarda en el
# backend. Es un aviso del propio sistema en un modo que nunca usa en producción (como en `test_soporte_flujos.py`).
pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")

DIMENSION_DEL_VECTOR = 1024
CARGA_DOCUMENTOS = 2  # TiposAccion.CARGA_DOCUMENTOS


@pytest.fixture
def sesion(iniciar_sesion, usuario_gubernamental):
    return iniciar_sesion(usuario_gubernamental)


# --- Lectura de la base, de Qdrant y de la bitácora ----------------------------------------------------------------------

def _consultar(consulta: str, parametros: dict = None) -> list:
    from app.db.database import engine

    with engine.connect() as conexion:
        return [tuple(fila) for fila in conexion.execute(text(consulta), parametros or {}).fetchall()]


def _ultimo_id_de_bitacora() -> int:
    return int(_consultar("SELECT COALESCE(MAX(CN_Id_bitacora), 0) FROM T_Bitacora")[0][0])


def _filas_de_carga_desde(ultimo_id: int, cedula: str) -> list:
    """Las filas de carga de documentos creadas después de `ultimo_id` por ese usuario, con su información adicional ya leída."""
    filas = _consultar(
        "SELECT CN_Id_usuario, CT_Texto, CT_Informacion_adicional FROM T_Bitacora "
        "WHERE CN_Id_bitacora > :d AND CN_Id_tipo_accion = :t AND CN_Id_usuario = :u ORDER BY CN_Id_bitacora",
        {"d": ultimo_id, "t": CARGA_DOCUMENTOS, "u": cedula})
    return [{"usuario": f[0], "texto": f[1] or "", "info": json.loads(f[2]) if f[2] else {}} for f in filas]


def _fila_de_fase(filas: list, fase: str, archivo: str = None) -> dict:
    """La fila de esa fase (y de ese archivo, si se indica); falla diciendo qué fases hay si no existe."""
    coinciden = [f for f in filas if f["info"].get("fase") == fase and (archivo is None or f["info"].get("archivo") == archivo)]
    assert coinciden, f"falta la fila de la fase {fase!r} (archivo {archivo!r}); hay: {[f['info'].get('fase') for f in filas]}"
    return coinciden[0]


def _tema(numero: str):
    """La fila del tema (id, número) o `None` si no existe."""
    filas = _consultar("SELECT CN_Id_expediente, CT_Num_expediente FROM T_Expediente WHERE CT_Num_expediente = :n", {"n": numero})
    return filas[0] if filas else None


def _documentos_del_tema(numero: str) -> list:
    """(id, nombre, estado) de los documentos asociados al tema por la tabla intermedia."""
    return _consultar(
        "SELECT d.CN_Id_documento, d.CT_Nombre_archivo, es.CT_Nombre_estado "
        "FROM T_Expediente e JOIN T_Expediente_Documento ed ON ed.CN_Id_expediente = e.CN_Id_expediente "
        "JOIN T_Documento d ON d.CN_Id_documento = ed.CN_Id_documento "
        "JOIN T_Estado_procesamiento es ON es.CN_Id_estado = d.CN_Id_estado "
        "WHERE e.CT_Num_expediente = :n ORDER BY d.CN_Id_documento", {"n": numero})


def _puntos_del_tema(tema: str) -> list:
    """Los puntos de Qdrant cuyo `metadata.numero_expediente` es el tema, con su vector y su carga útil."""
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    cliente = entorno.cliente_qdrant()
    try:
        filtro = Filter(must=[FieldCondition(key="metadata.numero_expediente", match=MatchValue(value=tema))])
        puntos, _ = cliente.scroll(collection_name=os.environ["QDRANT_COLLECTION_NAME"], scroll_filter=filtro, limit=1000,
                                   with_payload=True, with_vectors=True)
        return list(puntos)
    finally:
        cliente.close()


def _subir_y_procesar(cliente_api, sesion, procesamiento, tema, documentos):
    """Sube los documentos al tema y ejecuta su procesamiento; devuelve los identificadores de tarea (uno por archivo)."""
    respuesta = cargar(cliente_api, sesion, tema, [(d.nombre, d.contenido) for d in documentos])
    assert respuesta.status_code == 200, f"la carga respondió {respuesta.status_code}"
    ids = respuesta.json()["task_ids"]
    resultados = procesamiento.procesar()
    for id_tarea in ids:
        assert resultados[id_tarea].state == "SUCCESS", f"la tarea {id_tarea} terminó en {resultados[id_tarea].state}"
    return ids


# --- RF-05.1 y RF-21.7: la carga con el encolado interceptado ----------------------------------------------------------------

@pytest.mark.requisito("RF-05.1")
@pytest.mark.requisito("RF-21.7")
def test_carga_encolada_un_id_por_archivo(cliente_api, sesion, usuario_gubernamental, registro_de_datos, carpeta_archivos,
                                          encolado_interceptado):
    """RF-05.1, RF-21.7: dos archivos a un tema dan un identificador por archivo sin esperar al procesamiento, cada uno queda
    guardado en la carpeta temporal de su tema, hay una tarea encolada por archivo y la bitácora registra la carga iniciada
    con el usuario y el tema; todavía no hay documento, tema ni fragmentos."""
    from app.services.ingesta.async_processing.progress_tracker import progress_manager

    tema = tema_heredado(registro_de_datos)
    uno, otro = documento_de_prueba(), documento_de_prueba()
    ultimo_id = _ultimo_id_de_bitacora()

    respuesta = cargar(cliente_api, sesion, tema, [(uno.nombre, uno.contenido), (otro.nombre, otro.contenido)])

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["task_ids"] == ["PRUEBA-tarea-1", "PRUEBA-tarea-2"]  # uno por archivo, todos de texto y distintos
    assert cuerpo["expediente"] == tema and cuerpo["total_files"] == 2
    # Una tarea encolada por archivo, con su tema, su usuario y su contenido.
    pendientes = encolado_interceptado.pendientes
    assert [(p.id, p.tema, p.usuario) for p in pendientes] == [
        ("PRUEBA-tarea-1", tema, usuario_gubernamental.cedula), ("PRUEBA-tarea-2", tema, usuario_gubernamental.cedula)]
    assert [p.archivo_info["filename"] for p in pendientes] == [uno.nombre, otro.nombre]
    # Cada archivo, en la carpeta de su tema dentro de la carpeta temporal (nunca el `uploads/` de desarrollo), sin pisar al otro.
    rutas = [Path(p.archivo_info["filepath"]) for p in pendientes]
    assert len(set(rutas)) == 2
    for ruta, documento in zip(rutas, (uno, otro)):
        assert ruta.is_file() and ruta.read_bytes() == documento.contenido
        assert ruta.parent.name == tema and carpeta_archivos in ruta.parents
    # Todavía no se procesó nada: ni documentos, ni tema, ni fragmentos, ni seguimiento de progreso.
    assert id_del_documento(uno.nombre) is None and id_del_documento(otro.nombre) is None
    assert _tema(tema) is None and contar_puntos(tema) == 0
    assert progress_manager.get_status("PRUEBA-tarea-1") is None
    # La fila de carga iniciada, a nombre del usuario y con el tema.
    filas = _filas_de_carga_desde(ultimo_id, usuario_gubernamental.cedula)
    iniciada = _fila_de_fase(filas, "iniciado")
    assert iniciada["usuario"] == usuario_gubernamental.cedula
    assert iniciada["info"]["expediente"] == tema
    assert iniciada["info"]["task_id"] == "PRUEBA-tarea-1,PRUEBA-tarea-2"


# --- RF-06.1, RF-07.1, RF-08.1, RF-21.7: procesado, fragmentos, tema y bitácora ---------------------------------------------

@pytest.mark.requisito("RF-06.1")
@pytest.mark.requisito("RF-07.1")
@pytest.mark.requisito("RF-08.1")
@pytest.mark.requisito("RF-21.7")
def test_procesado_con_fragmentos_y_tema_heredado(cliente_api, sesion, usuario_gubernamental, registro_de_datos,
                                                  procesamiento_en_prueba):
    """RF-07.1: cada documento queda Procesado y el progreso de su tarea informa completado al 100 %. RF-06.1: se creó el tema
    (uno) y se asoció cada documento. RF-08.1: todos sus fragmentos están en Qdrant (> 0), con vector de 1024 y metadatos de
    tema, archivo e id de documento, y su número es el que guarda la fila «Documento almacenado». RF-21.7: la bitácora tiene
    esa fila y la de procesamiento terminado, a nombre del usuario. Se suben dos documentos para que el id de cada uno sea
    distinto del id del tema y del otro documento."""
    from app.services.ingesta.async_processing.progress_tracker import progress_manager

    tema = tema_heredado(registro_de_datos)
    documentos = [documento_de_prueba(), documento_de_prueba()]
    ultimo_id = _ultimo_id_de_bitacora()
    assert _tema(tema) is None  # el tema no existía

    ids_de_tarea = _subir_y_procesar(cliente_api, sesion, procesamiento_en_prueba, tema, documentos)

    # RF-06.1: el tema se creó (uno) y cada documento quedó asociado por la tabla intermedia.
    fila_del_tema = _tema(tema)
    assert fila_del_tema is not None
    assert _consultar("SELECT COUNT(*) FROM T_Expediente WHERE CT_Num_expediente = :n", {"n": tema})[0][0] == 1
    ids_de_documento = {d.nombre: id_del_documento(d.nombre) for d in documentos}
    assert all(i is not None for i in ids_de_documento.values()) and len(set(ids_de_documento.values())) == 2
    assert [(d[1], d[2]) for d in _documentos_del_tema(tema)] == [(d.nombre, "Procesado") for d in documentos]
    puntos = _puntos_del_tema(tema)
    assert len(puntos) == contar_puntos(tema)
    filas = _filas_de_carga_desde(ultimo_id, usuario_gubernamental.cedula)
    for documento, id_tarea in zip(documentos, ids_de_tarea):
        id_documento = ids_de_documento[documento.nombre]
        # RF-07.1
        exigir_estado(id_documento, "Procesado")
        exigir_progreso(id_tarea, "completado")
        assert progress_manager.get_status(id_tarea)["progress"] == 100
        # RF-08.1: todos los fragmentos del documento, con vector de 1024 y los metadatos.
        propios = [p for p in puntos if p.payload["metadata"]["id_documento"] == id_documento]
        assert len(propios) > 0
        for punto in propios:
            metadatos = punto.payload["metadata"]
            assert len(punto.vector) == DIMENSION_DEL_VECTOR
            assert metadatos["numero_expediente"] == tema
            assert metadatos["nombre_archivo"] == documento.nombre
            assert metadatos["id_expediente"] == fila_del_tema[0]
        # RF-21.7 y RF-08.1: la fila «Documento almacenado» trae el id de documento y el número de fragmentos de Qdrant.
        almacenado = _fila_de_fase(filas, "vectorstore_exitoso", documento.nombre)
        assert almacenado["usuario"] == usuario_gubernamental.cedula
        assert almacenado["info"]["expediente"] == tema
        assert almacenado["info"]["documento_id"] == id_documento
        assert almacenado["info"]["num_chunks"] == len(propios)
        terminado = _fila_de_fase(filas, "completado", documento.nombre)
        assert terminado["usuario"] == usuario_gubernamental.cedula and terminado["info"]["expediente"] == tema
        assert "num_chunks" not in terminado["info"]  # la fila «Procesamiento terminado» no lleva el número de fragmentos
        assert terminado["info"]["task_id"] == id_tarea
    assert len(puntos) == sum(1 for p in puntos if p.payload["metadata"]["id_documento"] in ids_de_documento.values())


@pytest.mark.requisito("RF-06.1")
def test_segunda_carga_al_mismo_tema_sin_duplicar(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba):
    """RF-06.1: una segunda carga a un tema que ya existe lo reutiliza (sigue habiendo un solo tema), agrega el documento
    (dos relaciones y dos documentos Procesados) y los fragmentos de los dos llevan el mismo tema."""
    tema = tema_heredado(registro_de_datos)
    primero, segundo = documento_de_prueba(), documento_de_prueba()

    _subir_y_procesar(cliente_api, sesion, procesamiento_en_prueba, tema, [primero])
    id_del_tema = _tema(tema)[0]
    puntos_del_primero = contar_puntos(tema)
    _subir_y_procesar(cliente_api, sesion, procesamiento_en_prueba, tema, [segundo])

    assert _consultar("SELECT COUNT(*) FROM T_Expediente WHERE CT_Num_expediente = :n", {"n": tema})[0][0] == 1
    assert _tema(tema)[0] == id_del_tema  # el mismo tema, no uno nuevo
    documentos = _documentos_del_tema(tema)
    assert [(d[1], d[2]) for d in documentos] == [(primero.nombre, "Procesado"), (segundo.nombre, "Procesado")]
    relaciones = _consultar("SELECT COUNT(*) FROM T_Expediente_Documento WHERE CN_Id_expediente = :i", {"i": id_del_tema})
    assert relaciones[0][0] == 2
    puntos = _puntos_del_tema(tema)
    assert len(puntos) > puntos_del_primero > 0
    por_documento = {d[0]: sum(1 for p in puntos if p.payload["metadata"]["id_documento"] == d[0]) for d in documentos}
    assert all(cantidad > 0 for cantidad in por_documento.values()) and sum(por_documento.values()) == len(puntos)
    assert {p.payload["metadata"]["nombre_archivo"] for p in puntos} == {primero.nombre, segundo.nombre}


# --- RF-06.2: tema de nombre libre y chat acotado ------------------------------------------------------------------------------

def _tema_libre(registro_de_datos) -> str:
    """Un tema de nombre libre (con espacios, fuera del formato heredado), registrado para que se limpie."""
    tema = f"{PREFIJO_DATOS} tema libre {uuid.uuid4().hex[:8]}"
    registro_de_datos.registrar_tema(tema)
    return tema


def _pregunta_sobre(documento) -> str:
    """Una pregunta que nombra al documento por su número pero sin repetir su frase distintiva, para poder comprobar si la
    frase llegó al modelo desde el contexto y no desde la pregunta."""
    sufijo = documento.nombre[len(PREFIJO_DATOS) + 1:-len(".txt")]
    return f"¿Qué dice el documento inventado número {sufijo} sobre la quebrada ficticia {sufijo}?"


def _preguntar_acotado(cliente_api, sesion, usuario, ollama_simulado, tema: str, pregunta: str) -> str:
    """Consulta el chat acotado a `tema` y devuelve lo que recibió el modelo (pregunta y contexto)."""
    ollama_simulado.responder("Respuesta simulada de PRUEBA.")
    respuesta = cliente_api.post(
        "/rag/consulta-con-historial-stream",
        json={"query": pregunta, "session_id": f"session_{usuario.cedula}_{uuid.uuid4().hex[:8]}", "expediente_number": tema},
        headers=sesion)
    assert respuesta.status_code == 200
    assert leer_eventos(respuesta), "el chat acotado no devolvió eventos"
    return contexto_enviado(ollama_simulado)


@pytest.mark.requisito("RF-06.2")
def test_tema_libre_se_acepta_y_crea_el_tema(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba):
    """RF-06.2 (aceptar y crear): un tema de nombre libre se acepta, se crea con el documento Procesado y sus fragmentos."""
    tema = _tema_libre(registro_de_datos)
    documento = documento_de_prueba()

    [id_tarea] = _subir_y_procesar(cliente_api, sesion, procesamiento_en_prueba, tema, [documento])

    id_documento = id_del_documento(documento.nombre)
    exigir_estado(id_documento, "Procesado")
    exigir_progreso(id_tarea, "completado")
    assert _tema(tema) is not None
    assert [(d[0], d[1]) for d in _documentos_del_tema(tema)] == [(id_documento, documento.nombre)]
    puntos = _puntos_del_tema(tema)
    assert len(puntos) > 0 and all(p.payload["metadata"]["id_documento"] == id_documento for p in puntos)


@pytest.mark.requisito("RF-06.2")
@pytest.mark.xfail(strict=True, reason="RF-06.2 · ingesta")
def test_tema_libre_y_chat_acotado(cliente_api, sesion, usuario_gubernamental, registro_de_datos, procesamiento_en_prueba,
                                   ollama_simulado):
    """RF-06.2 (chat acotado): el chat acotado a un tema de nombre libre recupera SU documento y no mezcla el de otro tema
    (se comprueba lo que recibe el modelo, no el texto de la respuesta). Hay dos temas con una frase distintiva cada uno y
    la pregunta nombra al OTRO documento: si el chat no se limitara al tema, traería el documento ajeno. El control con el
    tema en formato heredado demuestra que la prueba distingue un chat acotado de uno general."""
    libre, heredado = _tema_libre(registro_de_datos), tema_heredado(registro_de_datos)
    en_libre, en_heredado = documento_de_prueba(), documento_de_prueba()
    _subir_y_procesar(cliente_api, sesion, procesamiento_en_prueba, libre, [en_libre])
    _subir_y_procesar(cliente_api, sesion, procesamiento_en_prueba, heredado, [en_heredado])

    # Control: acotado al tema heredado, aunque la pregunta nombre el documento del otro tema, el modelo solo recibe el propio.
    contexto = _preguntar_acotado(
        cliente_api, sesion, usuario_gubernamental, ollama_simulado, heredado, _pregunta_sobre(en_libre))
    assert en_heredado.frase in contexto and en_libre.frase not in contexto

    # RF-06.2: lo mismo con el tema de nombre libre.
    contexto = _preguntar_acotado(
        cliente_api, sesion, usuario_gubernamental, ollama_simulado, libre, _pregunta_sobre(en_heredado))
    assert en_libre.frase in contexto, "el chat acotado al tema libre no recuperó su documento"
    assert en_heredado.frase not in contexto, "el chat acotado al tema libre trajo el documento de otro tema"


# --- RF-07.2 y RF-21.7: el fallo de la extracción de un documento no afecta al otro ------------------------------------------

TEXTO_FIJO_DE_FALLO = "No se pudo procesar el archivo. Por favor, intente nuevamente."
CAUSA_DE_EXTRACCION = "no se pudo extraer el texto"  # «Causa clasificada» (spec 004, Definiciones)
# Lo que la excepción provocada lleva y que nunca debe llegar al progreso: un texto interno y una ruta del servidor inventados.
DETALLE_INTERNO = "detalle-interno-PRUEBA-7"
RUTA_INVENTADA = "/app/uploads/PRUEBA-ruta-inventada/interno.bin"


@dataclass
class CargaConFallo:
    """Una carga de dos documentos a un tema en la que falla la extracción del primero (`malo`) y no la del segundo (`bueno`)."""

    tema: str
    malo: object
    bueno: object
    id_malo: str
    id_bueno: str
    resultados: dict
    ultimo_id_de_bitacora: int


@pytest.fixture
def carga_con_fallo(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, monkeypatch) -> CargaConFallo:
    """Sube dos documentos y procesa ambos con la extracción forzada a fallar solo para el primero, sin detener servicios
    (plan §9.4): el simulado lanza el mismo error que envuelve la extracción real («Error extrayendo texto de …»). El
    fallo del primero va antes que el segundo para comprobar que no lo arrastra."""
    from app.services.ingesta.file_management import document_processor

    tema = tema_heredado(registro_de_datos)
    malo, bueno = documento_de_prueba(), documento_de_prueba()
    extraer_original = document_processor.extract_text_from_file

    async def extraer(content, filename, *args, **kwargs):
        if filename == malo.nombre:
            raise ValueError(f"Error extrayendo texto de {filename} (tipo: .txt): {DETALLE_INTERNO} en {RUTA_INVENTADA}")
        return await extraer_original(content, filename, *args, **kwargs)

    monkeypatch.setattr(document_processor, "extract_text_from_file", extraer)
    ultimo_id = _ultimo_id_de_bitacora()
    respuesta = cargar(cliente_api, sesion, tema, [(malo.nombre, malo.contenido), (bueno.nombre, bueno.contenido)])
    assert respuesta.status_code == 200, f"la carga respondió {respuesta.status_code}"
    id_malo, id_bueno = respuesta.json()["task_ids"]
    resultados = procesamiento_en_prueba.procesar()
    return CargaConFallo(tema, malo, bueno, id_malo, id_bueno, resultados, ultimo_id)


@pytest.mark.requisito("RF-07.2")
def test_extraccion_que_falla_no_afecta_al_otro(carga_con_fallo):
    """RF-07.2: si la extracción de un documento falla, el otro de la carga queda Procesado, con su progreso completado al
    100 %, sus fragmentos en Qdrant (> 0, y ninguno del que falló) y su relación con el tema. También fija lo que ya
    cumple el que falló: su tarea termina en fallo y su progreso informa fallo (no completado)."""
    carga = carga_con_fallo
    # La tarea del que falló termina en fallo y la del otro, bien: el fallo no se propaga.
    assert carga.resultados[carga.id_malo].state == "FAILURE"
    assert carga.resultados[carga.id_bueno].state == "SUCCESS"
    exigir_progreso(carga.id_malo, "fallido")
    # El otro: Procesado, completado al 100 %, asociado al tema y con fragmentos propios.
    id_bueno = id_del_documento(carga.bueno.nombre)
    assert id_bueno is not None, "el documento que no falló no se registró"
    exigir_estado(id_bueno, "Procesado")
    exigir_progreso(carga.id_bueno, "completado")
    from app.services.ingesta.async_processing.progress_tracker import progress_manager
    assert progress_manager.get_status(carga.id_bueno)["progress"] == 100
    assert (id_bueno, carga.bueno.nombre, "Procesado") in _documentos_del_tema(carga.tema)
    puntos = _puntos_del_tema(carga.tema)
    assert len(puntos) > 0
    assert {p.payload["metadata"]["id_documento"] for p in puntos} == {id_bueno}
    assert {p.payload["metadata"]["nombre_archivo"] for p in puntos} == {carga.bueno.nombre}  # ninguno del que falló


@pytest.mark.requisito("RF-07.2")
@pytest.mark.xfail(strict=True, reason="RF-07.2 · ingesta")
def test_progreso_con_texto_fijo_y_causa(carga_con_fallo):
    """RF-07.2 (a): el progreso de la tarea que falló informa fallo con el texto fijo «No se pudo procesar el archivo. Por
    favor, intente nuevamente.» y la causa clasificada, sin el texto de la excepción ni rutas del servidor."""
    from app.services.ingesta.async_processing.progress_tracker import progress_manager

    seguimiento = progress_manager.get_status(carga_con_fallo.id_malo)
    assert seguimiento is not None and seguimiento["status"] == "fallido"
    visible = json.dumps(seguimiento, ensure_ascii=False)
    assert TEXTO_FIJO_DE_FALLO in (seguimiento.get("message") or ""), f"el mensaje no es el texto fijo: {seguimiento.get('message')!r}"
    assert CAUSA_DE_EXTRACCION in visible.lower(), "el progreso no informa la causa clasificada"
    for prohibido in (DETALLE_INTERNO, RUTA_INVENTADA, "/app/", "Error extrayendo texto", "Traceback"):
        assert prohibido not in visible, f"el progreso muestra texto de la excepción o una ruta: {prohibido!r}"


@pytest.mark.requisito("RF-07.2")
@pytest.mark.requisito("RF-21.7")
def test_fila_de_error_con_la_causa(carga_con_fallo, sesion, usuario_gubernamental):
    """RF-07.2 (b), RF-21.7: la bitácora guarda una fila de error del archivo que falló, a nombre del usuario y con el tema,
    que conserva la causa tal como la dio la extracción (de ella sale la causa clasificada de RF-22.1); el otro archivo no
    tiene fila de error; y ninguna fila de la carga lleva la contraseña ni el token."""
    carga = carga_con_fallo
    filas = _filas_de_carga_desde(carga.ultimo_id_de_bitacora, usuario_gubernamental.cedula)

    con_error = _fila_de_fase(filas, "error", carga.malo.nombre)
    assert con_error["usuario"] == usuario_gubernamental.cedula
    assert con_error["info"]["expediente"] == carga.tema and con_error["info"]["task_id"] == carga.id_malo
    causa = con_error["info"].get("error_details") or ""
    assert causa.startswith("Error extrayendo texto"), f"la fila no conserva la causa de la extracción: {causa!r}"
    # El que no falló no tiene fila de error y sí la de su procesamiento terminado.
    assert [f for f in filas if f["info"].get("fase") == "error" and f["info"].get("archivo") != carga.malo.nombre] == []
    _fila_de_fase(filas, "completado", carga.bueno.nombre)
    # Ninguna fila lleva la contraseña ni el token.
    token = sesion["Authorization"].split(" ", 1)[1]
    for secreto in (usuario_gubernamental.contrasena, token):
        rastros.buscar_en_rastros(secreto, bitacora=[f["texto"] + json.dumps(f["info"], ensure_ascii=False) for f in filas])


@pytest.mark.requisito("RF-07.2")
@pytest.mark.xfail(strict=True, reason="RF-07.2 · ingesta")
def test_documento_queda_en_error(carga_con_fallo):
    """RF-07.2: el documento cuya extracción falló queda registrado en estado Error. Hoy el documento se registra después de
    extraer el texto, así que un fallo de extracción no deja documento."""
    id_malo = id_del_documento(carga_con_fallo.malo.nombre)
    assert id_malo is not None, "el fallo de extracción no dejó ningún documento"
    exigir_estado(id_malo, "Error")
