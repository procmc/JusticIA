"""Vista de texto de una fuente del notebook, parte unitaria (spec 009b, cambio II1, T16; RF-18.100, RF-18.106, RF-18.107).

El servicio con archivos en una carpeta temporal y Tika simulado: lo que se comprueba es qué texto devuelve, cuándo lo corta y cuándo
falla. Nada de red ni de base de datos. Nombres y textos inventados.
"""
import pytest

from app.services.vista_previa_service import (
    LIMITE_CARACTERES, VistaNoDisponible, VistaPreviaService, tiene_vista_de_texto,
)


class _TikaFalso:
    """Un extractor de Tika que devuelve lo que se le programa y anota con qué lo llamaron."""

    def __init__(self, texto="", falla=None):
        self.texto, self.falla, self.llamadas = texto, falla, []

    def extract_text(self, content, filename="", enable_ocr=True):
        self.llamadas.append({"bytes": len(content), "enable_ocr": enable_ocr})
        if self.falla:
            raise self.falla
        return self.texto


def _archivo(tmp_path, nombre, contenido: bytes):
    ruta = tmp_path / nombre
    ruta.write_bytes(contenido)
    return ruta


@pytest.mark.requisito("RF-18.100")
def test_un_txt_en_utf8_conserva_sus_saltos_de_linea(tmp_path):
    ruta = _archivo(tmp_path, "PRUEBA_a.txt", "primera línea\nsegunda línea con ñ\n".encode("utf-8"))
    assert VistaPreviaService().vista_de_texto_sync(ruta, ".txt") == ("primera línea\nsegunda línea con ñ\n", False)


@pytest.mark.requisito("RF-18.100")
def test_un_txt_que_no_es_utf8_se_muestra_con_simbolos_de_reemplazo(tmp_path):
    ruta = _archivo(tmp_path, "PRUEBA_a.txt", "caf\xe9 inventado".encode("latin-1"))
    texto, truncado = VistaPreviaService().vista_de_texto_sync(ruta, ".txt")
    assert "caf" in texto and "�" in texto and truncado is False
    assert ruta.read_bytes() == "caf\xe9 inventado".encode("latin-1"), "el archivo no se modifica"


@pytest.mark.requisito("RF-18.100")
def test_un_txt_largo_se_corta_a_200000_caracteres(tmp_path):
    ruta = _archivo(tmp_path, "PRUEBA_a.txt", ("a" * (LIMITE_CARACTERES + 50_000)).encode("utf-8"))
    texto, truncado = VistaPreviaService().vista_de_texto_sync(ruta, ".txt")
    assert len(texto) == LIMITE_CARACTERES and truncado is True


@pytest.mark.requisito("RF-18.100")
def test_un_txt_de_mas_de_un_megabyte_no_se_lee_entero(tmp_path):
    """El servidor lee a lo sumo 1 MiB de un archivo que puede pesar 1 GB; con más de 200.000 caracteres siempre está truncado."""
    ruta = _archivo(tmp_path, "PRUEBA_a.txt", b"b" * (3 * 1024 * 1024))
    texto, truncado = VistaPreviaService().vista_de_texto_sync(ruta, ".txt")
    assert len(texto) == LIMITE_CARACTERES and truncado is True


@pytest.mark.requisito("RF-18.100")
def test_un_txt_vacio_devuelve_texto_vacio(tmp_path):
    ruta = _archivo(tmp_path, "PRUEBA_a.txt", b"")
    assert VistaPreviaService().vista_de_texto_sync(ruta, ".txt") == ("", False)


@pytest.mark.requisito("RF-18.106")
@pytest.mark.parametrize("extension", [".doc", ".docx", ".html", ".htm", ".xhtml", ".DOCX"])
def test_word_y_html_usan_tika_sin_ocr(tmp_path, extension):
    tika = _TikaFalso(texto="Párrafo uno.\nPárrafo dos.")
    ruta = _archivo(tmp_path, "PRUEBA_a" + extension, b"contenido inventado")
    assert VistaPreviaService(tika=tika).vista_de_texto_sync(ruta, extension) == ("Párrafo uno.\nPárrafo dos.", False)
    assert tika.llamadas == [{"bytes": len(b"contenido inventado"), "enable_ocr": False}]


@pytest.mark.requisito("RF-18.106")
def test_el_texto_de_tika_largo_se_corta(tmp_path):
    tika = _TikaFalso(texto="x" * (LIMITE_CARACTERES + 10))
    ruta = _archivo(tmp_path, "PRUEBA_a.docx", b"zip")
    texto, truncado = VistaPreviaService(tika=tika).vista_de_texto_sync(ruta, ".docx")
    assert len(texto) == LIMITE_CARACTERES and truncado is True


@pytest.mark.requisito("RF-18.106")
def test_un_documento_sin_texto_devuelve_vacio(tmp_path):
    ruta = _archivo(tmp_path, "PRUEBA_a.docx", b"zip")
    assert VistaPreviaService(tika=_TikaFalso(texto="  \n\t ")).vista_de_texto_sync(ruta, ".docx") == ("", False)


@pytest.mark.requisito("RF-18.107")
def test_si_tika_falla_la_vista_no_esta_disponible_sin_texto_de_la_excepcion(tmp_path):
    ruta = _archivo(tmp_path, "PRUEBA_a.docx", b"zip")
    with pytest.raises(VistaNoDisponible) as error:
        VistaPreviaService(tika=_TikaFalso(falla=RuntimeError("PRUEBA fallo interno en /srv/almacen.py"))).vista_de_texto_sync(ruta, ".docx")
    assert "almacen" not in str(error.value)


@pytest.mark.requisito("RF-18.107")
def test_un_archivo_demasiado_grande_para_tika_no_se_envia(tmp_path):
    tika = _TikaFalso(texto="no debería llegar")
    ruta = tmp_path / "PRUEBA_grande.docx"
    with open(ruta, "wb") as f:
        f.truncate(60 * 1024 * 1024)  # archivo disperso: no ocupa 60 MiB en disco
    with pytest.raises(VistaNoDisponible):
        VistaPreviaService(tika=tika).vista_de_texto_sync(ruta, ".docx")
    assert tika.llamadas == []


@pytest.mark.requisito("RF-18.107")
def test_un_archivo_que_ya_no_esta_no_esta_disponible(tmp_path):
    with pytest.raises(VistaNoDisponible):
        VistaPreviaService().vista_de_texto_sync(tmp_path / "no_existe.txt", ".txt")


@pytest.mark.requisito("RF-18.106")
def test_tika_de_la_vista_previa_tiene_un_plazo_corto_y_un_solo_intento():
    """La ingesta usa 600 s y 3 intentos con esperas; para una persona que espera la vista previa, 30 s por intento y dos intentos
    (el segundo cubre el reinicio de Tika tras un archivo dañado, decisión D6)."""
    tika = VistaPreviaService()._crear_tika()
    assert tika.timeout == 30 and tika.max_retries == 2


@pytest.mark.requisito("RF-18.106")
@pytest.mark.parametrize("extension, esperado", [
    (".txt", True), (".doc", True), (".docx", True), (".rtf", False), (".html", True), (".htm", True), (".xhtml", True),
    (".TXT", True), (".pdf", False), (".png", False), (".mp3", False), (".tif", False), (".xlsx", False), ("", False),
])
def test_que_extensiones_tienen_vista_de_texto(extension, esperado):
    assert tiene_vista_de_texto(extension) is esperado


# --- T17: vista de imagen de un TIFF (RF-18.108) ------------------------------------------------------------------------------

import base64
import io

from app.services.vista_previa_service import tiene_vista_de_imagen


def _tiff(tmp_path, nombre, paginas=1, tamano=(120, 80)):
    from PIL import Image

    imagenes = [Image.new("RGB", tamano, (40 * (i + 1) % 255, 90, 160)) for i in range(paginas)]
    ruta = tmp_path / nombre
    imagenes[0].save(ruta, format="TIFF", save_all=paginas > 1, append_images=imagenes[1:])
    return ruta


def _png_de(base64_png):
    from PIL import Image

    datos = base64.b64decode(base64_png)
    assert datos[:8] == b"\x89PNG\r\n\x1a\n", "no es un PNG"
    return Image.open(io.BytesIO(datos))


@pytest.mark.requisito("RF-18.108")
def test_un_tiff_de_una_pagina_se_convierte_a_png(tmp_path):
    imagen, paginas = VistaPreviaService().vista_de_imagen_sync(_tiff(tmp_path, "PRUEBA_a.tif"))
    assert paginas == 1
    assert _png_de(imagen).size == (120, 80)


@pytest.mark.requisito("RF-18.108")
def test_un_tiff_de_varias_paginas_muestra_la_primera_e_informa_cuantas_hay(tmp_path):
    imagen, paginas = VistaPreviaService().vista_de_imagen_sync(_tiff(tmp_path, "PRUEBA_a.tiff", paginas=3))
    assert paginas == 3
    assert _png_de(imagen).size == (120, 80)


@pytest.mark.requisito("RF-18.108")
def test_un_tiff_muy_grande_se_reduce_a_4000_pixeles_por_lado(tmp_path):
    imagen, _ = VistaPreviaService().vista_de_imagen_sync(_tiff(tmp_path, "PRUEBA_grande.tif", tamano=(6000, 300)))
    ancho, alto = _png_de(imagen).size
    assert ancho == 4000 and alto == 200, "debe conservar la proporción"


@pytest.mark.requisito("RF-18.107")
def test_un_tiff_danado_no_esta_disponible(tmp_path):
    ruta = tmp_path / "PRUEBA_danado.tif"
    ruta.write_bytes(b"II*\x00esto no es un tiff valido" + b"\x00" * 40)
    with pytest.raises(VistaNoDisponible):
        VistaPreviaService().vista_de_imagen_sync(ruta)


@pytest.mark.requisito("RF-18.107")
def test_un_tiff_que_ya_no_esta_no_esta_disponible(tmp_path):
    with pytest.raises(VistaNoDisponible):
        VistaPreviaService().vista_de_imagen_sync(tmp_path / "no_existe.tif")


@pytest.mark.requisito("RF-18.108")
@pytest.mark.parametrize("extension, esperado", [(".tif", True), (".tiff", True), (".TIF", True), (".png", False), (".pdf", False), ("", False)])
def test_que_extensiones_tienen_vista_de_imagen(extension, esperado):
    assert tiene_vista_de_imagen(extension) is esperado
