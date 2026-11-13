"""Formatos de archivo permitidos para la carga (spec 006, cambio FFF1, T12; RF-05.52). Sin base de datos ni servidores.

El RTF dejó de ser un formato permitido: el Tika del despliegue lo detecta pero no extrae su texto y la ingesta lo dejaba siempre en
Error. Aquí se comprueba la lista del servidor y el validador del procesamiento, no la interfaz (eso lo cubre el extremo a extremo).
"""
import io

import pytest
from fastapi import UploadFile

from app.config.file_config import ALLOWED_EXTENSIONS, ALLOWED_FILE_TYPES
from app.services.ingesta.file_management.document_processor import validate_file

PERMITIDOS = [
    ".pdf", ".doc", ".docx", ".txt", ".html", ".htm", ".xhtml",
    ".mp3", ".wav", ".ogg", ".m4a",
    ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp",
]


def _archivo(nombre: str, tipo: str = None) -> UploadFile:
    return UploadFile(file=io.BytesIO(b"PRUEBA contenido inventado"), filename=nombre,
                      headers={"content-type": tipo} if tipo else None)


@pytest.mark.requisito("RF-05.52")
def test_el_rtf_no_esta_entre_los_formatos_permitidos():
    assert ".rtf" not in ALLOWED_EXTENSIONS
    assert "application/rtf" not in ALLOWED_FILE_TYPES
    assert not any(".rtf" in extensiones for extensiones in ALLOWED_FILE_TYPES.values())


@pytest.mark.requisito("RF-05.52")
def test_los_demas_formatos_siguen_permitidos():
    assert sorted(ALLOWED_EXTENSIONS) == sorted(PERMITIDOS)


@pytest.mark.requisito("RF-05.52")
@pytest.mark.parametrize("nombre", ["PRUEBA_a.rtf", "PRUEBA_a.RTF", "PRUEBA_a.Rtf"])
def test_el_validador_rechaza_un_rtf_sin_distinguir_mayusculas(nombre):
    error = validate_file(_archivo(nombre, "application/rtf"))
    assert error is not None and error.error == "Formato no permitido"
    assert ".rtf" not in error.formatos_permitidos


@pytest.mark.requisito("RF-05.52")
@pytest.mark.parametrize("nombre, tipo", [
    ("PRUEBA_a.pdf", "application/pdf"), ("PRUEBA_a.docx",
     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ("PRUEBA_a.txt", "text/plain"), ("PRUEBA_a.html", "text/html"),
])
def test_el_validador_sigue_aceptando_los_demas_formatos(nombre, tipo):
    assert validate_file(_archivo(nombre, tipo)) is None
