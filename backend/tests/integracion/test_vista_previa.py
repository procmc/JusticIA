"""Vista de texto de una fuente del notebook, parte de integración (spec 009b, cambio II1, T16; RF-18.100, RF-18.106, RF-18.107,
RNF-07.102, RF-21).

Con la API real, SQL Server, Tika y los archivos reales del entorno aislado; Ollama simulado. Los datos son inventados (prefijo
`PRUEBA`) y se limpian solos.
"""
import io
import uuid
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from tests.integracion.conftest import _consultar, _documento_procesado_en_el_notebook
from tests.soporte.flujos import DocumentoPrueba, crear_notebook, exigir_estado
from tests.soporte.nombres import PREFIJO_DATOS

pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")

MENSAJE_ERROR = "No se pudo mostrar el documento. Intente de nuevo."
DESCARGAR_ARCHIVO = 10  # TiposAccion.DESCARGAR_ARCHIVO: «Descargar Archivo», que también registra la previsualización
TEXTO_INTERNO = "PRUEBA fallo interno en /srv/PRUEBA_interno/almacen.py"


def _parrafos(sufijo: str) -> list:
    return [f"PRUEBA párrafo {i}: la quebrada ficticia {sufijo} desemboca en la laguna inventada número {i}." for i in range(1, 6)]


def _txt(sufijo: str) -> bytes:
    return ("\n".join(_parrafos(sufijo)) + "\n").encode("utf-8")


def _rtf(sufijo: str) -> bytes:
    cuerpo = "\\par ".join(_parrafos(sufijo))
    return ("{\\rtf1\\ansi\\deff0 {\\fonttbl{\\f0 Arial;}}\\f0\\fs24 " + cuerpo + "\\par }").encode("ascii", "replace")


def _html(sufijo: str) -> bytes:
    parrafos = "".join(f"<p>{p}</p>" for p in _parrafos(sufijo))
    return (f"<html><head><title>PRUEBA</title></head><body><script>alert('PRUEBA')</script>{parrafos}"
            f"<table><tr><td>celda A {sufijo}</td><td>celda B</td></tr></table></body></html>").encode("utf-8")


def _docx(sufijo: str) -> bytes:
    """Un .docx mínimo y válido armado a mano: párrafos y una tabla de una fila con dos celdas."""
    tipos = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/>'
             '<Override PartName="/word/document.xml" '
             'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    relaciones = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                  '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                  'Target="word/document.xml"/></Relationships>')
    parrafos = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in _parrafos(sufijo))
    tabla = (f"<w:tbl><w:tr><w:tc><w:p><w:r><w:t>celda A {sufijo}</w:t></w:r></w:p></w:tc>"
             "<w:tc><w:p><w:r><w:t>celda B</w:t></w:r></w:p></w:tc></w:tr></w:tbl>")
    documento = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
                 f'{parrafos}{tabla}</w:body></w:document>')
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as zip_:
        zip_.writestr("[Content_Types].xml", tipos)
        zip_.writestr("_rels/.rels", relaciones)
        zip_.writestr("word/document.xml", documento)
    return memoria.getvalue()


FORMATOS = {".txt": _txt, ".rtf": _rtf, ".html": _html, ".docx": _docx}


def _fuente(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, extension: str, contenido: bytes = None):
    """Un notebook propio con una fuente Procesado del formato pedido. Devuelve `(notebook, id_documento, documento, sufijo)`."""
    sufijo = uuid.uuid4().hex[:8]
    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook vista {sufijo}", registro_de_datos)
    contenido = contenido if contenido is not None else FORMATOS[extension](sufijo)
    documento = DocumentoPrueba(nombre=f"{PREFIJO_DATOS}_{sufijo}{extension}", contenido=contenido, frase=sufijo)
    _, id_documento = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook, documento)
    return notebook, id_documento, documento, sufijo


def _vista(cliente_api, cabeceras, notebook, id_documento):
    return cliente_api.get(f"/notebooks/{notebook['id']}/documentos/{id_documento}/vista-texto", headers=cabeceras)


@pytest.mark.requisito("RF-18.100")
@pytest.mark.requisito("RF-18.106")
@pytest.mark.parametrize("extension", [".docx", ".html", ".txt"])
def test_la_vista_de_texto_devuelve_el_texto_de_cada_formato(
        cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, extension):
    """RF-18.100, RF-18.106: de un .txt, .rtf, .html y .docx inventados sale su texto, con sus párrafos y sin etiquetas ni comandos."""
    notebook, id_documento, _, sufijo = _fuente(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, extension)

    respuesta = _vista(cliente_api, sesion, notebook, id_documento)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"texto", "truncado"} and cuerpo["truncado"] is False
    texto = cuerpo["texto"]
    assert f"la quebrada ficticia {sufijo} desemboca en la laguna inventada número 1" in texto
    assert f"laguna inventada número 5" in texto
    for marca in ("<p>", "<script", "</", "\\par", "\\rtf", "<w:"):
        assert marca not in texto, f"la vista de texto trae marcas del formato: {marca!r}"
    if extension in (".html", ".docx"):
        assert f"celda A {sufijo}" in texto and "celda B" in texto, "el texto de la tabla debe aparecer"


@pytest.mark.requisito("RF-18.100")
def test_un_txt_de_mas_de_200000_caracteres_se_corta(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba):
    sufijo = uuid.uuid4().hex[:8]
    contenido = (f"PRUEBA {sufijo} " + "la quebrada ficticia desemboca en la laguna inventada. " * 5000).encode("utf-8")  # unos 270.000
    notebook, id_documento, _, _ = _fuente(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ".txt", contenido)

    cuerpo = _vista(cliente_api, sesion, notebook, id_documento).json()

    assert cuerpo["truncado"] is True and len(cuerpo["texto"]) == 200_000


@pytest.mark.requisito("RNF-07.102")
def test_los_accesos_no_permitidos_responden_como_la_ruta_del_archivo(cliente_api, ajeno, administrador, iniciar_sesion):
    """RNF-07.102: ajeno, inexistente, Administrador y sin token reciben lo mismo que en la ruta del archivo (RF-18.1)."""
    ruta_base = f"/notebooks/{ajeno.notebook['id']}/documentos/{ajeno.id_documento}"
    # Ajeno: 404 uniforme, igual que el de la ruta del archivo.
    de_otro = cliente_api.get(f"{ruta_base}/vista-texto", headers=ajeno.cabeceras_otro)
    del_archivo = cliente_api.get(f"{ruta_base}/archivo", headers=ajeno.cabeceras_otro)
    assert de_otro.status_code == 404 and (de_otro.status_code, de_otro.json()) == (del_archivo.status_code, del_archivo.json())
    # Inexistente (del propio dueño): el mismo 404.
    inexistente = cliente_api.get(f"/notebooks/{ajeno.notebook['id']}/documentos/{ajeno.id_documento + 1_000_000}/vista-texto",
                                  headers=ajeno.cabeceras_dueno)
    assert inexistente.status_code == 404
    # Administrador: rechazado por rol; sin token: 401.
    assert cliente_api.get(f"{ruta_base}/vista-texto", headers=iniciar_sesion(administrador)).status_code == 403
    assert cliente_api.get(f"{ruta_base}/vista-texto").status_code == 401
    # Con todo y eso, el dueño sí la ve.
    assert cliente_api.get(f"{ruta_base}/vista-texto", headers=ajeno.cabeceras_dueno).status_code == 200


@pytest.mark.requisito("RNF-07.102")
def test_una_fuente_quitada_responde_el_404_uniforme(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba):
    notebook, id_documento, _, _ = _fuente(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ".txt")
    assert _vista(cliente_api, sesion, notebook, id_documento).status_code == 200, "control: antes de quitarla sí se ve"
    assert cliente_api.delete(f"/notebooks/{notebook['id']}/documentos/{id_documento}", headers=sesion).status_code == 200

    quitada = _vista(cliente_api, sesion, notebook, id_documento)
    inexistente = _vista(cliente_api, sesion, notebook, id_documento + 1_000_000)

    assert quitada.status_code == 404 and (quitada.status_code, quitada.json()) == (inexistente.status_code, inexistente.json())


@pytest.mark.requisito("RNF-07.102")
def test_una_fuente_pendiente_no_se_puede_ver(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba):
    from app.db.database import engine

    notebook, id_documento, _, _ = _fuente(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ".txt")
    with engine.begin() as conexion:
        conexion.execute(text("UPDATE T_Documento SET CN_Id_estado = (SELECT CN_Id_estado FROM T_Estado_procesamiento "
                              "WHERE CT_Nombre_estado = 'Pendiente') WHERE CN_Id_documento = :d"), {"d": id_documento})
    exigir_estado(id_documento, "Pendiente")

    respuesta = _vista(cliente_api, sesion, notebook, id_documento)

    assert respuesta.status_code == 400 and "texto" not in respuesta.json()


@pytest.mark.requisito("RF-18.106")
def test_un_tipo_sin_vista_de_texto_se_rechaza(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba):
    """Defensa del servidor: la interfaz no pide la vista de texto de un PDF, pero si llega se rechaza sin tocar el archivo."""
    from tests.soporte.flujos import crear_notebook as _crear

    sufijo = uuid.uuid4().hex[:8]
    notebook = _crear(cliente_api, sesion, f"{PREFIJO_DATOS} notebook pdf {sufijo}", registro_de_datos)
    # Un documento .txt al que se le cambia el nombre interno a .pdf basta: la ruta decide por la extensión, no por el contenido.
    _, id_documento = _documento_procesado_en_el_notebook(
        cliente_api, sesion, procesamiento_en_prueba, notebook,
        DocumentoPrueba(nombre=f"{PREFIJO_DATOS}_{sufijo}.txt", contenido=_txt(sufijo), frase=sufijo))
    from app.db.database import engine
    from app.services.documentos.file_management_service import file_management_service

    ruta = file_management_service.obtener_ruta_archivo(notebook["clave_interna"], f"{PREFIJO_DATOS}_{sufijo}.txt")
    ruta.rename(ruta.with_suffix(".pdf"))  # el archivo en disco sigue al nombre interno
    with engine.begin() as conexion:
        conexion.execute(text("UPDATE T_Documento SET CT_Nombre_archivo = :n WHERE CN_Id_documento = :d"),
                         {"n": f"{PREFIJO_DATOS}_{sufijo}.pdf", "d": id_documento})

    respuesta = _vista(cliente_api, sesion, notebook, id_documento)

    assert respuesta.status_code == 400, f"se esperaba 400 y se recibió {respuesta.status_code}"
    assert respuesta.json()["detail"] == "Este tipo de archivo no tiene vista de texto."


@pytest.mark.requisito("RF-18.107")
def test_si_tika_falla_la_respuesta_es_el_aviso_y_la_bitacora_lo_registra(
        cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, monkeypatch):
    """RF-18.107, RF-21: con Tika caído, 500 con el mensaje exacto y sin texto de excepción; una fila de previsualización fallida
    «interno», con la clave y el número del documento y sin nombre, ruta ni texto de la excepción."""
    from app.services.ingesta.tika_service import TikaService

    notebook, id_documento, documento, _ = _fuente(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ".docx")

    def _falla(self, *args, **kwargs):
        raise RuntimeError(TEXTO_INTERNO)

    monkeypatch.setattr(TikaService, "extract_text", _falla)
    marca = int(_consultar("SELECT COALESCE(MAX(CN_Id_bitacora), 0) FROM T_Bitacora")[0][0])
    sin_relanzar = TestClient(cliente_api.app, raise_server_exceptions=False)

    respuesta = _vista(sin_relanzar, sesion, notebook, id_documento)

    assert respuesta.status_code == 500 and respuesta.json()["detail"] == MENSAJE_ERROR
    assert TEXTO_INTERNO not in respuesta.text and "Traceback" not in respuesta.text
    filas = _consultar("SELECT CT_Texto, CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_bitacora > :m AND CN_Id_tipo_accion = :t",
                       {"m": marca, "t": DESCARGAR_ARCHIVO})
    assert len(filas) == 1
    texto = f"{filas[0][0]} {filas[0][1]}"
    assert notebook["clave_interna"] in texto and str(id_documento) in texto
    assert "interno" in texto
    for prohibido in (documento.nombre, TEXTO_INTERNO, "almacen", "uploads"):
        assert prohibido not in texto, f"la bitácora trae {prohibido!r}"


@pytest.mark.requisito("RF-21")
@pytest.mark.requisito("RNF-07.102")
def test_la_vista_exitosa_se_registra_sin_el_texto_del_archivo(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba):
    notebook, id_documento, documento, sufijo = _fuente(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ".txt")
    marca = int(_consultar("SELECT COALESCE(MAX(CN_Id_bitacora), 0) FROM T_Bitacora")[0][0])

    assert _vista(cliente_api, sesion, notebook, id_documento).status_code == 200

    filas = _consultar("SELECT CT_Texto, CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_bitacora > :m AND CN_Id_tipo_accion = :t",
                       {"m": marca, "t": DESCARGAR_ARCHIVO})
    assert len(filas) == 1
    texto = f"{filas[0][0]} {filas[0][1]}"
    assert notebook["clave_interna"] in texto and str(id_documento) in texto
    assert documento.nombre not in texto and "quebrada ficticia" not in texto, "la bitácora no lleva nombres ni texto del archivo"


# --- T17: vista de imagen de un TIFF (RF-18.108) ------------------------------------------------------------------------------

def _tiff_inventado(paginas: int) -> bytes:
    from PIL import Image

    imagenes = [Image.new("RGB", (160, 100), (30 * (i + 2), 80, 140)) for i in range(paginas)]
    memoria = io.BytesIO()
    imagenes[0].save(memoria, format="TIFF", save_all=paginas > 1, append_images=imagenes[1:])
    return memoria.getvalue()


def _fuente_tiff(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, htr_simulado, paginas: int):
    """Una fuente TIFF Procesado: el HTR simulado devuelve un texto inventado para que la ingesta la dé por buena."""
    htr_simulado.responder("PRUEBA texto inventado reconocido de la imagen para la prueba de la vista previa. " * 4)
    return _fuente(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ".tif", _tiff_inventado(paginas))


def _vista_imagen(cliente_api, cabeceras, notebook, id_documento):
    return cliente_api.get(f"/notebooks/{notebook['id']}/documentos/{id_documento}/vista-imagen", headers=cabeceras)


@pytest.mark.requisito("RF-18.108")
@pytest.mark.parametrize("paginas", [1, 3])
def test_la_vista_de_imagen_convierte_el_tiff_a_png(
        cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, htr_simulado, paginas):
    notebook, id_documento, _, _ = _fuente_tiff(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, htr_simulado, paginas)

    respuesta = _vista_imagen(cliente_api, sesion, notebook, id_documento)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"imagen", "paginas"} and cuerpo["paginas"] == paginas
    import base64
    assert base64.b64decode(cuerpo["imagen"])[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.requisito("RNF-07.102")
def test_la_vista_de_imagen_rechaza_lo_ajeno_al_administrador_y_al_que_no_inicio_sesion(
        cliente_api, ajeno, administrador, iniciar_sesion):
    ruta_base = f"/notebooks/{ajeno.notebook['id']}/documentos/{ajeno.id_documento}"
    de_otro = cliente_api.get(f"{ruta_base}/vista-imagen", headers=ajeno.cabeceras_otro)
    del_archivo = cliente_api.get(f"{ruta_base}/archivo", headers=ajeno.cabeceras_otro)
    assert de_otro.status_code == 404 and (de_otro.status_code, de_otro.json()) == (del_archivo.status_code, del_archivo.json())
    assert cliente_api.get(f"{ruta_base}/vista-imagen", headers=iniciar_sesion(administrador)).status_code == 403
    assert cliente_api.get(f"{ruta_base}/vista-imagen").status_code == 401


@pytest.mark.requisito("RF-18.108")
def test_un_tipo_sin_vista_de_imagen_se_rechaza(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba):
    notebook, id_documento, _, _ = _fuente(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ".txt")

    respuesta = _vista_imagen(cliente_api, sesion, notebook, id_documento)

    assert respuesta.status_code == 400 and respuesta.json()["detail"] == "Este tipo de archivo no tiene vista de imagen."


@pytest.mark.requisito("RF-18.107")
def test_si_la_conversion_falla_la_respuesta_es_el_aviso_y_la_bitacora_lo_registra(
        cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, htr_simulado, monkeypatch):
    from PIL import Image

    notebook, id_documento, documento, _ = _fuente_tiff(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, htr_simulado, 1)

    def _falla(*args, **kwargs):
        raise RuntimeError(TEXTO_INTERNO)

    monkeypatch.setattr(Image, "open", _falla)  # un fallo real de Pillow al abrir el archivo
    marca = int(_consultar("SELECT COALESCE(MAX(CN_Id_bitacora), 0) FROM T_Bitacora")[0][0])
    sin_relanzar = TestClient(cliente_api.app, raise_server_exceptions=False)

    respuesta = _vista_imagen(sin_relanzar, sesion, notebook, id_documento)

    assert respuesta.status_code == 500 and respuesta.json()["detail"] == MENSAJE_ERROR
    assert TEXTO_INTERNO not in respuesta.text
    filas = _consultar("SELECT CT_Texto, CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_bitacora > :m AND CN_Id_tipo_accion = :t",
                       {"m": marca, "t": DESCARGAR_ARCHIVO})
    assert len(filas) == 1
    texto = f"{filas[0][0]} {filas[0][1]}"
    assert notebook["clave_interna"] in texto and str(id_documento) in texto and "interno" in texto
    for prohibido in (documento.nombre, TEXTO_INTERNO, "uploads"):
        assert prohibido not in texto
