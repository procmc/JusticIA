"""Prueba de T5 (spec 003a): el archivo de ejemplo de configuración documenta el correo (RF-03.19).

Lee `backend/.env.example` desde donde está dentro del contenedor (`/app/.env.example`, la carpeta del backend
montada) y comprueba que define las variables del correo y el tiempo máximo del envío solo con marcadores:
hosts `.invalid`, ninguna credencial real. Si el archivo no está en la imagen o el montaje, la prueba se omite
diciendo por qué. No lee ningún `.env` real ni muestra valores.
"""
from pathlib import Path

import pytest
from dotenv import dotenv_values

RUTA_DEL_EJEMPLO = Path(__file__).resolve().parents[2] / ".env.example"

VARIABLES_DEL_CORREO = (
    "EMAIL_PROVIDER", "EMAIL_HOST", "EMAIL_PORT", "EMAIL_USE_TLS", "EMAIL_USERNAME", "EMAIL_PASSWORD", "EMAIL_TIMEOUT",
)
# Palabras con las que el ejemplo marca un valor como «ponga aquí el suyo», nunca una clave real.
PALABRAS_DE_MARCADOR = ("generado", "cambiar", "ejemplo", "marcador", "password", "clave")


@pytest.fixture(scope="module")
def ejemplo() -> dict:
    """Las variables que define el archivo de ejemplo (las líneas comentadas no cuentan)."""
    if not RUTA_DEL_EJEMPLO.is_file():
        pytest.skip(f"El archivo de ejemplo no está en el contenedor ({RUTA_DEL_EJEMPLO}); no se puede comprobar RF-03.19.")
    return {nombre: valor for nombre, valor in dotenv_values(RUTA_DEL_EJEMPLO).items() if valor is not None}


def test_define_las_variables_del_correo_y_el_tiempo_maximo(ejemplo):
    """RF-03.19: el archivo de ejemplo define las seis variables del correo y `EMAIL_TIMEOUT`."""
    faltan = [nombre for nombre in VARIABLES_DEL_CORREO if nombre not in ejemplo]

    assert faltan == [], f"Faltan en el archivo de ejemplo: {', '.join(faltan)}"


def test_el_servidor_propio_usa_solo_marcadores_sin_servidor_real(ejemplo):
    """RF-03.19: el bloque de «servidor propio» apunta a un host `.invalid`, con puerto y TLS de ejemplo y 15 s de límite."""
    assert ejemplo.get("EMAIL_HOST", "").endswith(".invalid"), "EMAIL_HOST debe ser un host .invalid (un marcador)"
    assert ejemplo.get("EMAIL_PORT", "").isdigit()
    assert ejemplo.get("EMAIL_USE_TLS", "").lower() in ("true", "false")
    assert ejemplo.get("EMAIL_TIMEOUT") == "15"


def test_explica_como_apuntar_el_correo_a_un_servidor_propio():
    """RF-03.19: el archivo dice que `EMAIL_PROVIDER=custom` es la opción de un servidor propio."""
    if not RUTA_DEL_EJEMPLO.is_file():
        pytest.skip(f"El archivo de ejemplo no está en el contenedor ({RUTA_DEL_EJEMPLO}); no se puede comprobar RF-03.19.")

    assert "EMAIL_PROVIDER=custom" in RUTA_DEL_EJEMPLO.read_text(encoding="utf-8")


def test_no_trae_credenciales_reales(ejemplo):
    """RF-03.19: el usuario y la clave de correo son marcadores («email@gmail.com», «app-password-generado»), no una cuenta."""
    usuario = ejemplo.get("EMAIL_USERNAME", "")
    clave = ejemplo.get("EMAIL_PASSWORD", "")

    assert usuario == "email@gmail.com" or usuario.endswith(".invalid"), "EMAIL_USERNAME debe ser un marcador"
    assert any(palabra in clave.lower() for palabra in PALABRAS_DE_MARCADOR), "EMAIL_PASSWORD debe ser un marcador"
