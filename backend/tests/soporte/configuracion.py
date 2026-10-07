"""Configuración propia de la suite (spec 002, RA-02.2 y RA-02.3).

El sistema lee su configuración con `load_dotenv()` en cinco módulos y esa función NO sobrescribe
una variable ya definida. Por eso la suite fija sus valores en `os.environ` antes de importar
nada de `app` (`pytest_configure`, en T4); solo toma de desarrollo las seis credenciales de
administración que necesita para crear y eliminar la base de pruebas.

Ningún `conftest.py` ni módulo de este paquete importa `app` al cargarse: `database.py` se
conecta a SQL Server en cuanto se importa. Ver también: `proteccion.py` y `nombres.py`.
"""
import os
import secrets
import sys
from pathlib import Path
from typing import Mapping, MutableMapping, Optional, Union

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

from tests.soporte.nombres import NOMBRE_PRUEBAS
from tests.soporte.proteccion import AbortoPruebas, exigir_nombre_pruebas

# Únicas variables que se toman de la configuración de desarrollo (entorno del contenedor o
# `/app/.env`): credenciales de administración de SQL Server y la dirección de Qdrant.
VARIABLES_DESARROLLO = (
    "SQL_SERVER_HOST",
    "SQL_SERVER_PORT",
    "SQL_SERVER_USER",
    "SQL_SERVER_PASSWORD",
    "SQL_SERVER_DRIVER",
    "QDRANT_URL",
)

RUTA_DOTENV_DESARROLLO = Path("/app/.env")

# Módulos del sistema que ya habrían leído el entorno real si estuvieran importados.
MODULOS_DEL_SISTEMA = ("app", "main", "celery_app")

# Dominio reservado (RFC 2606): nunca resuelve a un servidor real, así una llamada accidental falla.
SUFIJO_SIN_SERVIDOR = ".invalid"


def leer_configuracion_desarrollo(
    entorno: Optional[Mapping[str, str]] = None,
    ruta_dotenv: Union[str, Path] = RUTA_DOTENV_DESARROLLO,
) -> dict:
    """Devuelve solo las seis variables de desarrollo, del entorno y, si faltan, de `.env`.

    Usa `dotenv_values` (lee el archivo sin tocar `os.environ`). Una variable ausente o vacía
    cuenta como faltante: la suite aborta nombrándolas y nunca usa el valor por omisión del
    código (que apuntaría a otro servidor). El mensaje no incluye valores.
    """
    if entorno is None:
        entorno = os.environ
    en_dotenv = dotenv_values(ruta_dotenv) if Path(ruta_dotenv).is_file() else {}

    leidas = {}
    for nombre in VARIABLES_DESARROLLO:
        valor = entorno.get(nombre) or en_dotenv.get(nombre)
        if valor:
            leidas[nombre] = valor

    faltan = [nombre for nombre in VARIABLES_DESARROLLO if nombre not in leidas]
    if faltan:
        raise AbortoPruebas(
            "Se aborta la suite de pruebas: faltan en la configuración de desarrollo (el entorno "
            f"del contenedor o {ruta_dotenv}) las variables que necesita para crear la base de "
            f"pruebas: {', '.join(faltan)}."
        )
    return leidas


def construir_configuracion(desarrollo: Mapping[str, str]) -> dict:
    """Arma todas las variables de entorno de la suite (RA-02.2).

    De `desarrollo` copia únicamente las seis permitidas; el resto son valores de la suite:
    nombres de pruebas, direcciones `*.invalid`, datos de correo inventados y secretos
    aleatorios distintos en cada llamada (JWT, contraseña del administrador que siembra la
    migración, clave de correo y de Ollama). `TIKA_SERVER_URL` no se fija: queda el real, que
    solo usa la integración. El administrador sembrado no lleva el prefijo `PRUEBA` para que el
    conteo de residuos (RA-02.7) no lo cuente, y su contraseña no es la de la migración.
    """
    configuracion = {nombre: desarrollo[nombre] for nombre in VARIABLES_DESARROLLO}
    configuracion.update({
        # Nombres de datos y Redis (nunca se usa el real, RA-02.5).
        "SQL_SERVER_DATABASE": NOMBRE_PRUEBAS,
        "QDRANT_COLLECTION_NAME": NOMBRE_PRUEBAS,
        "REDIS_URL": "redis://redis-simulado.invalid:6379",
        # Seguridad.
        "JWT_SECRET_KEY": secrets.token_urlsafe(48),
        "ADMIN_CEDULA": "S" + secrets.token_hex(6),
        "ADMIN_USERNAME": "admin_sembrado_" + secrets.token_hex(3),
        "ADMIN_EMAIL": "admin.sembrado@sembrado.invalid",
        "ADMIN_PASSWORD": secrets.token_urlsafe(18),
        "ADMIN_NOMBRE": "Sembrado",
        "ADMIN_APELLIDO": "Migracion",
        # Correo con valores inventados (el envío real se simula, RA-02.6).
        "EMAIL_PROVIDER": "custom",
        "EMAIL_USERNAME": "usuario-suite@correo.invalid",
        "EMAIL_PASSWORD": secrets.token_urlsafe(18),
        "EMAIL_HOST": "smtp.correo.invalid",
        "EMAIL_PORT": "2525",
        "EMAIL_USE_TLS": "false",
        # Servicios simulados: una llamada accidental falla en vez de llegar al servicio real.
        "OLLAMA_BASE_URL": "http://ollama-simulado.invalid:11434",
        "OLLAMA_MODEL": "modelo-simulado",
        "OLLAMA_API_KEY": secrets.token_urlsafe(18),
        "HTR_SERVER_URL": "http://htr-simulado.invalid:9100",
        # Audio.
        "ENVIRONMENT": "development",
        "WHISPER_MODEL": "base",
        "WHISPER_DEVICE": "cpu",
        "WHISPER_COMPUTE_TYPE": "int8",
        "WHISPER_NUM_WORKERS": "1",
        "AUDIO_CHUNK_DURATION_MIN": "5",
        # Modelos de vectorización: los reales (la integración los carga de verdad).
        "EMBEDDING_MODEL": "intfloat/multilingual-e5-large",
        "DIM": "1024",
    })
    return configuracion


def aplicar(configuracion: Mapping[str, str], entorno: Optional[MutableMapping[str, str]] = None) -> None:
    """Fija la configuración en el entorno (por omisión, `os.environ`)."""
    if entorno is None:
        entorno = os.environ
    entorno.update(configuracion)


def fijar_entorno_de_pruebas(entorno: Optional[MutableMapping[str, str]] = None) -> dict:
    """Fija el entorno de la suite antes de importar nada de `app` y devuelve lo fijado.

    Orden: aborta si ya hay módulos del sistema importados; lee las 6 credenciales de desarrollo;
    arma la configuración; valida que los nombres sean los de pruebas (antes de escribir nada); y
    la aplica. No abre ninguna conexión. Lo llama `pytest_configure` (T4 le suma la creación de la
    base de pruebas).
    """
    exigir_sin_modulos_importados()
    cfg = construir_configuracion(leer_configuracion_desarrollo())
    exigir_nombre_pruebas(cfg["SQL_SERVER_DATABASE"], "la base de datos (SQL_SERVER_DATABASE)")
    exigir_nombre_pruebas(cfg["QDRANT_COLLECTION_NAME"], "la colección de Qdrant (QDRANT_COLLECTION_NAME)")
    aplicar(cfg, entorno)
    return cfg


def exigir_sin_modulos_importados(modulos: Optional[Mapping[str, object]] = None) -> None:
    """Aborta si algún módulo del sistema ya está importado.

    Esos módulos ya habrían leído el entorno real (y `database.py` ya se habría conectado), así
    que fijar la configuración después no serviría. Coincide por componente del nombre:
    `app` y `app.x.y` cuentan; `application` no.
    """
    if modulos is None:
        modulos = sys.modules
    importados = sorted(
        nombre for nombre in modulos
        if nombre.split(".", 1)[0] in MODULOS_DEL_SISTEMA
    )
    if importados:
        raise AbortoPruebas(
            "Se aborta la suite de pruebas: ya hay módulos del sistema importados "
            f"({', '.join(importados[:5])}) y habrían leído la configuración real de desarrollo. "
            "Ningún archivo de pruebas ni `conftest.py` debe importar `app` al cargarse."
        )


def _host_de(url: str) -> str:
    """Nombre de host de una URL, o cadena vacía si no se puede leer."""
    return (url or "").split("://", 1)[-1].split("/", 1)[0].rsplit("@", 1)[-1].split(":", 1)[0]


def validar_valores_efectivos(modulo_config, entorno: Optional[Mapping[str, str]] = None) -> None:
    """Comprueba lo que `app.config.config` ya tomó, no solo lo que la suite escribió (RA-02.3).

    - La base de la URL de conexión y el nombre de la colección deben ser el nombre de pruebas.
    - Redis, Ollama y HTR deben apuntar a un host `*.invalid`, igual que el servidor de correo
      (que no pasa por `config.py`, así que se lee de `entorno`).
    No abre ninguna conexión y los mensajes no incluyen la URL completa (lleva la contraseña).
    """
    if entorno is None:
        entorno = os.environ
    try:
        base = make_url(modulo_config.DATABASE_URL).database
    except Exception:  # una URL ilegible también es un valor que no se puede aceptar
        base = None
    exigir_nombre_pruebas(base, "la base de datos de la URL de conexión (DATABASE_URL)")
    exigir_nombre_pruebas(modulo_config.QDRANT_COLLECTION_NAME, "la colección de Qdrant (QDRANT_COLLECTION_NAME)")

    direcciones = {
        "REDIS_URL": _host_de(modulo_config.REDIS_URL),
        "OLLAMA_BASE_URL": _host_de(modulo_config.OLLAMA_BASE_URL),
        "HTR_SERVER_URL": _host_de(modulo_config.HTR_SERVER_URL),
        "EMAIL_HOST": entorno.get("EMAIL_HOST", ""),
    }
    for variable, host in direcciones.items():
        if not host.endswith(SUFIJO_SIN_SERVIDOR):
            raise AbortoPruebas(
                f"Se aborta la suite de pruebas: {variable} apunta a '{host}' y debe terminar en "
                f"'{SUFIJO_SIN_SERVIDOR}' para que ninguna prueba llegue a un servicio real."
            )
