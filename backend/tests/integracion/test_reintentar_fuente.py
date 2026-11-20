"""Reintentar una fuente en Error de un notebook, parte de integración (spec 012; RF-07.60 a RF-07.68, RF-21.110).

Usa la API real con un Usuario Gubernamental `PRUEBA`, SQL Server, Tika, Qdrant y los embeddings reales del entorno aislado; la
tarea de procesamiento corre dentro de la prueba (`procesamiento_en_prueba`). Los datos son inventados (prefijo `PRUEBA`) y se
limpian solos.
"""
import json
from dataclasses import dataclass

import pytest

from app.constants.tipos_accion import TiposAccion
from tests.integracion.conftest import _consultar, _documento_procesado_en_el_notebook
from tests.integracion.test_aislamiento_notebooks import _puntos_del_documento
from tests.integracion.test_fuentes_notebook import _filas_desde, _marca_de_bitacora, _poner_estado
from tests.soporte.flujos import crear_notebook, estado_del_documento
from tests.soporte.nombres import PREFIJO_DATOS

pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")

MENSAJE_NO_ES_ERROR = "Solo se puede reintentar una fuente que terminó con error."
MENSAJE_SIN_ARCHIVO = "No se encontró el archivo original. Quite la fuente y vuelva a subirla."


@dataclass
class FuenteEnError:
    cabeceras: dict
    notebook: dict
    documento: object
    id: int
    fragmentos_antes: int


def _reintentar(cliente_api, cabeceras, notebook_id, documento_id):
    return cliente_api.post(f"/notebooks/{notebook_id}/documentos/{documento_id}/reintentar", headers=cabeceras)


@pytest.fixture
def fuente_en_error(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba):
    """Un notebook propio con una fuente que se procesó bien y se dejó en Error (con sus fragmentos de antes, como si el
    intento fallido hubiera dejado restos)."""
    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook de reintentos", registro_de_datos)
    documento, id_documento = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook)
    fragmentos = len(_puntos_del_documento(id_documento))
    assert fragmentos > 0
    _poner_estado(id_documento, "Error")
    return FuenteEnError(sesion, notebook, documento, id_documento, fragmentos)


@pytest.mark.requisito("RF-07.61")
@pytest.mark.requisito("RF-07.62")
@pytest.mark.requisito("RF-07.63")
@pytest.mark.requisito("RF-07.64")
def test_reintentar_procesa_de_nuevo_con_la_misma_fila_y_sin_fragmentos_duplicados(
        cliente_api, fuente_en_error, procesamiento_en_prueba):
    """RF-07.61, .62, .64: «Reintentar» devuelve la fuente a Pendiente con una tarea nueva, borra los fragmentos del intento
    anterior, reutiliza la fila del documento y, al terminar, la deja Procesado con tantos fragmentos como debe (sin duplicar).
    RF-07.63: se puede reintentar varias veces."""
    f = fuente_en_error
    nb = f.notebook["id"]
    filas_antes = _consultar("SELECT COUNT(*) FROM T_Documento WHERE CT_Nombre_archivo = :n", {"n": f.documento.nombre})[0][0]

    for vuelta in range(2):  # sin límite: dos reintentos seguidos (el primero termina bien y se vuelve a dejar en Error)
        r = _reintentar(cliente_api, f.cabeceras, nb, f.id)
        assert r.status_code == 200, (vuelta, r.text)
        cuerpo = r.json()
        assert cuerpo["id"] == f.id and cuerpo["estado"] == "Pendiente" and cuerpo["id_tarea"]
        assert estado_del_documento(f.id) == "Pendiente"
        assert _puntos_del_documento(f.id) == [], "los fragmentos del intento anterior no se borraron"

        resultados = procesamiento_en_prueba.procesar()
        assert resultados[cuerpo["id_tarea"]].state == "SUCCESS", resultados[cuerpo["id_tarea"]].result
        assert estado_del_documento(f.id) == "Procesado"
        assert len(_puntos_del_documento(f.id)) == f.fragmentos_antes
        assert _consultar("SELECT COUNT(*) FROM T_Documento WHERE CT_Nombre_archivo = :n",
                          {"n": f.documento.nombre})[0][0] == filas_antes == 1
        _poner_estado(f.id, "Error")


@pytest.mark.requisito("RF-07.62")
def test_si_el_reintento_falla_de_nuevo_vuelve_a_error_y_se_puede_reintentar(
        cliente_api, fuente_en_error, procesamiento_en_prueba, monkeypatch):
    """RF-07.62: un reintento que falla deja la fuente en Error otra vez, sin fragmentos, y «Reintentar» sigue disponible."""
    from app.services.ingesta.file_management import document_processor

    f = fuente_en_error

    async def _falla(*args, **kwargs):
        raise ValueError("falla simulada de la extracción")

    with monkeypatch.context() as local:
        local.setattr(document_processor, "extract_text_from_file", _falla)
        r = _reintentar(cliente_api, f.cabeceras, f.notebook["id"], f.id)
        assert r.status_code == 200
        resultados = procesamiento_en_prueba.procesar()
        assert resultados[r.json()["id_tarea"]].state == "FAILURE"
    assert estado_del_documento(f.id) == "Error"
    assert _puntos_del_documento(f.id) == []

    r = _reintentar(cliente_api, f.cabeceras, f.notebook["id"], f.id)
    assert r.status_code == 200, "tras un segundo fallo debe poder reintentarse"


@pytest.mark.requisito("RF-07.60")
@pytest.mark.requisito("RF-07.67")
def test_solo_se_reintenta_una_fuente_en_error_y_un_doble_clic_encola_una_sola_tarea(
        cliente_api, fuente_en_error, encolado_interceptado):
    """RF-07.60: una fuente Procesado o Pendiente no se reintenta (409 con su mensaje y sin encolar nada). RF-07.67: tras el
    primer «Reintentar» la fuente queda Pendiente, así que un segundo clic seguido no encola otra tarea."""
    f = fuente_en_error
    nb = f.notebook["id"]
    encoladas = len(encolado_interceptado.pendientes)

    _poner_estado(f.id, "Procesado")
    r = _reintentar(cliente_api, f.cabeceras, nb, f.id)
    assert r.status_code == 409 and r.json() == {"detail": MENSAJE_NO_ES_ERROR}
    assert len(encolado_interceptado.pendientes) == encoladas

    _poner_estado(f.id, "Error")
    assert _reintentar(cliente_api, f.cabeceras, nb, f.id).status_code == 200
    r = _reintentar(cliente_api, f.cabeceras, nb, f.id)
    assert r.status_code == 409 and r.json() == {"detail": MENSAJE_NO_ES_ERROR}
    assert len(encolado_interceptado.pendientes) == encoladas + 1
    assert estado_del_documento(f.id) == "Pendiente"


@pytest.mark.requisito("RF-07.65")
def test_sin_el_archivo_original_no_se_reintenta_y_sigue_en_error(cliente_api, fuente_en_error, encolado_interceptado):
    """RF-07.65: si el archivo original ya no está, 409 con su mensaje, la fuente sigue en Error y no se encola nada."""
    from app.services.documentos.file_management_service import file_management_service

    f = fuente_en_error
    ruta = file_management_service.obtener_ruta_archivo(f.notebook["clave_interna"], f.documento.nombre)
    assert ruta is not None
    ruta.unlink()
    encoladas = len(encolado_interceptado.pendientes)

    r = _reintentar(cliente_api, f.cabeceras, f.notebook["id"], f.id)

    assert r.status_code == 409 and r.json() == {"detail": MENSAJE_SIN_ARCHIVO}
    assert estado_del_documento(f.id) == "Error"
    assert len(encolado_interceptado.pendientes) == encoladas


@pytest.mark.requisito("RF-07.66")
def test_reintentar_en_un_notebook_o_fuente_no_disponible_da_404_uniforme(
        cliente_api, fuente_en_error, iniciar_sesion, administrador, registro_de_datos, encolado_interceptado):
    """RF-07.66: notebook ajeno o inexistente, y fuente de otro notebook o inexistente, dan el 404 uniforme sin reprocesar nada;
    el Administrador recibe 403 y sin sesión no se atiende."""
    from tests.soporte.datos import ROL_USUARIO_GUBERNAMENTAL, crear_usuario

    f = fuente_en_error
    ajeno = crear_usuario(ROL_USUARIO_GUBERNAMENTAL, registro_de_datos)
    cabeceras_ajeno = iniciar_sesion(ajeno)
    notebook_ajeno = crear_notebook(cliente_api, cabeceras_ajeno, f"{PREFIJO_DATOS} notebook de otro", registro_de_datos)
    otro_propio = crear_notebook(cliente_api, f.cabeceras, f"{PREFIJO_DATOS} notebook aparte", registro_de_datos)
    nb_inexistente = int(_consultar("SELECT COALESCE(MAX(CN_Id_notebook), 0) + 1000000 FROM T_Notebook")[0][0])
    doc_inexistente = int(_consultar("SELECT COALESCE(MAX(CN_Id_documento), 0) + 1000000 FROM T_Documento")[0][0])
    encoladas = len(encolado_interceptado.pendientes)

    casos = [
        (cabeceras_ajeno, notebook_ajeno["id"], f.id, "Documento no encontrado en este notebook"),  # el suyo, fuente ajena
        (cabeceras_ajeno, f.notebook["id"], f.id, "Notebook no encontrado"),  # notebook ajeno
        (f.cabeceras, nb_inexistente, f.id, "Notebook no encontrado"),
        (f.cabeceras, f.notebook["id"], doc_inexistente, "Documento no encontrado en este notebook"),
        (f.cabeceras, otro_propio["id"], f.id, "Documento no encontrado en este notebook"),  # fuente de otro notebook
        (f.cabeceras, "abc", f.id, "Notebook no encontrado"),
        (f.cabeceras, f.notebook["id"], "abc", "Documento no encontrado en este notebook"),
    ]
    for cabeceras, notebook_id, documento_id, detalle in casos:
        r = _reintentar(cliente_api, cabeceras, notebook_id, documento_id)
        assert r.status_code == 404 and r.json() == {"detail": detalle}, (notebook_id, documento_id, r.status_code, r.text)
    assert estado_del_documento(f.id) == "Error"
    assert len(encolado_interceptado.pendientes) == encoladas

    assert _reintentar(cliente_api, iniciar_sesion(administrador), f.notebook["id"], f.id).status_code == 403
    assert _reintentar(cliente_api, {}, f.notebook["id"], f.id).status_code in (401, 403)


@pytest.mark.requisito("RF-07.68")
def test_si_no_se_puede_encolar_la_fuente_sigue_en_error(cliente_api, fuente_en_error, monkeypatch):
    """RF-07.68: si el servidor no puede encolar el procesamiento, responde 500 con un mensaje en español sin datos internos y
    la fuente conserva el estado Error."""
    from app.services.ingesta.async_processing.celery_tasks import procesar_archivo_celery

    def _sin_cola(*args, **kwargs):
        raise ConnectionError("redis caído C:/ruta/secreta")

    monkeypatch.setattr(procesar_archivo_celery, "delay", _sin_cola)
    r = _reintentar(cliente_api, fuente_en_error.cabeceras, fuente_en_error.notebook["id"], fuente_en_error.id)

    assert r.status_code == 500 and r.json() == {"detail": "No se pudo reintentar la fuente. Intente de nuevo."}
    assert "secreta" not in r.text
    assert estado_del_documento(fuente_en_error.id) == "Error"


@pytest.mark.requisito("RF-21.110")
def test_el_reintento_queda_en_la_bitacora_sin_nombres(cliente_api, fuente_en_error, usuario_gubernamental):
    """RF-21.110: el reintento deja UNA fila de carga de documentos con el usuario, la clave NB-<id> y el número del documento,
    sin el nombre del archivo ni del notebook; el rechazo (409) no deja fila de reintento."""
    f = fuente_en_error
    marca = _marca_de_bitacora()

    r = _reintentar(cliente_api, f.cabeceras, f.notebook["id"], f.id)
    assert r.status_code == 200
    filas = _filas_desde(usuario_gubernamental, marca)
    assert len(filas) == 1 and filas[0]["tipo"] == TiposAccion.CARGA_DOCUMENTOS
    info = filas[0]["info"]
    assert info["accion"] == "reintentar_documento" and info["documento_id"] == f.id
    assert info["tema"] == f.notebook["clave_interna"] and info["resultado"] == "exitoso"
    assert f.documento.nombre not in json.dumps(filas, ensure_ascii=False)
    assert f.notebook["nombre"] not in json.dumps(filas, ensure_ascii=False)

    marca = _marca_de_bitacora()
    assert _reintentar(cliente_api, f.cabeceras, f.notebook["id"], f.id).status_code == 409  # ya está Pendiente
    assert _filas_desde(usuario_gubernamental, marca) == []
