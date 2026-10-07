"""Entorno de datos de la suite: espera de servicios, base y colección de pruebas y cierre (spec 002, RA-02.4).

Flujo de `preparar()` (lo llama `pytest_configure`, antes de recolectar, ya con el entorno fijado
por `configuracion.fijar_entorno_de_pruebas`): valida el nombre, espera a SQL Server, reemplaza la
base de pruebas por una nueva, le aplica las migraciones de Alembic en un proceso hijo y recién
entonces importa `app.db.database`, que se conecta al importarse. Así no hay espera de 30 s ni motor
sin crear. `cerrar()` la elimina al terminar, aunque haya pruebas que fallen.

La colección de Qdrant de pruebas (T5) es solo de la integración: la crea la fixture
`entorno_integracion` (`tests/integracion/conftest.py`) después de esperar a Qdrant y a Tika, y la
eliminan esa fixture y, como respaldo, `cerrar()`. Una corrida sin pruebas de integración (unitarias,
`--collect-only`, `--help`) no la crea ni la toca. Toda creación o eliminación pasa por
`proteccion.crear_coleccion` y `proteccion.eliminar_coleccion`.

Nunca importa `app` ni `celery_app` al cargarse (regla del plan, decisión 3): lo hace dentro de las
funciones. Toda sentencia de creación o eliminación pasa por `proteccion.crear_base` y
`proteccion.eliminar_base`, que validan el nombre antes de abrir ninguna conexión.
"""
import contextlib
import io
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Dict, Optional
from urllib.parse import quote_plus

from sqlalchemy import text

from tests.soporte import configuracion
from tests.soporte.nombres import ESPERA_SERVICIOS_SEGUNDOS, NOMBRE_PRUEBAS
from tests.soporte.proteccion import (
    AbortoPruebas, crear_base, crear_coleccion, eliminar_base, eliminar_coleccion, exigir_nombre_pruebas,
)

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

# Segundos entre dos intentos de conexión mientras se espera a un servicio.
INTERVALO_ENTRE_INTENTOS = 2.0

# Segundos que se espera la respuesta de SQL Server en cada intento de conexión.
ESPERA_POR_INTENTO = 5

# Tiempo máximo de las migraciones de Alembic sobre una base nueva.
ESPERA_MIGRACIONES = 300

# Estado de la sesión: si hay una base creada que cerrar y qué revisión de Alembic tiene, y si la
# integración creó la colección de Qdrant de pruebas.
_estado: Dict[str, object] = {"base_creada": False, "nombre": None, "revision": None, "coleccion_creada": False}


# --- Espera de servicios -----------------------------------------------------------------------------

def esperar_servicio(
    servicio: str,
    intentar: Callable[[], object],
    *,
    segundos: float = ESPERA_SERVICIOS_SEGUNDOS,
    intervalo: float = INTERVALO_ENTRE_INTENTOS,
    reloj: Callable[[], float] = time.monotonic,
    pausa: Callable[[float], None] = time.sleep,
) -> None:
    """Llama a `intentar()` hasta que no lance ninguna excepción; aborta si pasan `segundos` sin respuesta.

    El reloj y la pausa se inyectan para probarlo con tiempo simulado. El mensaje de aborto nombra el
    servicio y el tipo de error, pero no su texto: los errores de conexión pueden traer direcciones
    o usuarios.
    """
    limite = reloj() + segundos
    while True:
        try:
            intentar()
            return
        except Exception as error:
            if reloj() >= limite:
                raise AbortoPruebas(
                    f"Se aborta la suite de pruebas: {servicio} no respondió en {segundos:g} segundos "
                    f"(último error: {type(error).__name__}). Compruebe que el servicio esté levantado "
                    "con `docker compose ps`."
                ) from None
            pausa(intervalo)


# --- Qdrant y Tika (integración, T5) ------------------------------------------------------------------

def cliente_qdrant():
    """Cliente de Qdrant para la dirección que leyó la suite (`QDRANT_URL`). Crearlo no abre ninguna conexión.

    Las unitarias no pueden usarlo: su guardián bloquea la creación de `QdrantClient`.

    Fuera de `proteccion.py` es SOLO PARA LECTURA (consultar si existe o qué contiene la colección de
    pruebas, o pasárselo a `crear_coleccion`/`eliminar_coleccion`): nunca se usa para crear, eliminar ni
    recrear colecciones directamente, porque eso se salta la validación del nombre (RA-02.3). Una prueba
    estática (`test_proteccion.py`) falla si esas llamadas aparecen fuera de `proteccion.py`.

    Única excepción (T8, RA-02.7): `datos.py` crea y borra PUNTOS (no colecciones) en la colección de pruebas,
    siempre después de validar su nombre; no es DDL y no la cubre la prueba estática.
    """
    from qdrant_client import QdrantClient

    return QdrantClient(url=os.environ["QDRANT_URL"], timeout=ESPERA_POR_INTENTO)


def esperar_qdrant(conectar: Optional[Callable] = None, **espera) -> None:
    """Espera hasta 60 s a que Qdrant responda; si no, aborta nombrándolo. `espera` se pasa a `esperar_servicio`."""
    conectar = conectar or cliente_qdrant

    def preguntar() -> None:
        cliente = conectar()
        try:
            cliente.get_collections()
        finally:
            cliente.close()

    esperar_servicio("Qdrant", preguntar, **espera)


def pedir_a_tika(url: Optional[str] = None) -> None:
    """Pregunta a Tika si está arriba (`GET /tika`, como `TikaService.is_available`); lanza si no responde 200."""
    import requests

    if url is None:
        from app.config.config import TIKA_SERVER_URL as url  # el Tika real: solo lo usa la integración
    requests.get(f"{url}/tika", timeout=ESPERA_POR_INTENTO).raise_for_status()


def esperar_tika(preguntar: Optional[Callable] = None, **espera) -> None:
    """Espera hasta 60 s a que Tika responda; si no, aborta nombrándolo."""
    esperar_servicio("Tika", preguntar or pedir_a_tika, **espera)


# --- Conexión a master -------------------------------------------------------------------------------

def _entre_llaves(valor: str) -> str:
    """Valor de una cadena de conexión de ODBC entre llaves, con `}` duplicada (admite `;`, `=` y `{`)."""
    return "{" + valor.replace("}", "}}") + "}"


def cadena_de_conexion(configuracion_sql: Dict[str, str], base: str = "master") -> str:
    """Cadena de conexión de ODBC a `base`. Usa las credenciales de administración que leyó la suite."""
    return (
        f"DRIVER={_entre_llaves(configuracion_sql['SQL_SERVER_DRIVER'])};"
        f"SERVER={configuracion_sql['SQL_SERVER_HOST']},{configuracion_sql['SQL_SERVER_PORT']};"
        f"DATABASE={base};"
        f"UID={_entre_llaves(configuracion_sql['SQL_SERVER_USER'])};"
        f"PWD={_entre_llaves(configuracion_sql['SQL_SERVER_PASSWORD'])};"
        "TrustServerCertificate=yes"
    )


def conectar_master(entorno: Optional[Dict[str, str]] = None):
    """Conexión en modo autocommit a `master` (`CREATE DATABASE` no puede ir dentro de una transacción)."""
    import pyodbc

    if entorno is None:
        entorno = os.environ
    return pyodbc.connect(cadena_de_conexion(entorno, "master"), autocommit=True, timeout=ESPERA_POR_INTENTO)


def base_existe(nombre: str, conectar: Optional[Callable] = None) -> bool:
    """Consulta de solo lectura: ¿existe en el servidor una base con ese nombre? (no valida el nombre)."""
    conexion = (conectar or conectar_master)()
    try:
        return conexion.execute("SELECT DB_ID(?)", nombre).fetchone()[0] is not None
    finally:
        conexion.close()


# --- Migraciones -------------------------------------------------------------------------------------

def _sin_secretos(salida: str) -> str:
    """Quita de un texto las contraseñas, claves y secretos del entorno (también codificados para una URL)."""
    for variable, valor in os.environ.items():
        if valor and any(marca in variable.upper() for marca in ("PASSWORD", "SECRET", "API_KEY")):
            salida = salida.replace(valor, "<oculto>").replace(quote_plus(valor), "<oculto>")
    return salida


def migrar() -> None:
    """Aplica las migraciones de Alembic a la base de pruebas desde cero, en un proceso hijo.

    Como proceso hijo porque `alembic/env.py` llama a `fileConfig` (que desactiva los registros ya
    configurados y rompe `caplog`) e importa `app.db.models` en el proceso de pruebas. El hijo hereda
    el entorno de la suite: `SQL_SERVER_DATABASE` de pruebas y `ADMIN_*` aleatorios.
    """
    exigir_nombre_pruebas(os.environ.get("SQL_SERVER_DATABASE"), "la base de datos de las migraciones (SQL_SERVER_DATABASE)")
    try:
        resultado = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=RAIZ_BACKEND, env=dict(os.environ), capture_output=True, text=True, timeout=ESPERA_MIGRACIONES,
        )
    except subprocess.TimeoutExpired:
        raise AbortoPruebas(
            f"Se aborta la suite de pruebas: las migraciones de Alembic no terminaron en {ESPERA_MIGRACIONES} segundos."
        ) from None
    if resultado.returncode != 0:
        cola = _sin_secretos((resultado.stderr or resultado.stdout)[-1500:])
        raise AbortoPruebas(
            f"Se aborta la suite de pruebas: fallaron las migraciones de Alembic sobre la base de pruebas:\n{cola}"
        )


# --- Preparar y cerrar -------------------------------------------------------------------------------

def _soltar_motor() -> None:
    """Cierra las conexiones del motor de SQLAlchemy, si `app.db.database` ya se importó."""
    motor = getattr(sys.modules.get("app.db.database"), "engine", None)
    if motor is not None:
        motor.dispose()


def preparar(conectar: Optional[Callable] = None) -> None:
    """Crea la base de pruebas, la migra a `head` y deja importado `app.db.database` contra ella.

    Si una corrida anterior dejó la base, la reemplaza (el nombre es siempre el mismo). Los aborts
    posteriores a la creación dejan registrada la base en `_estado` para que `cerrar()` la elimine.
    Se puede llamar más de una vez en el mismo proceso (la prueba de infraestructura lo hace).
    """
    conectar = conectar or conectar_master
    nombre = os.environ.get("SQL_SERVER_DATABASE")
    exigir_nombre_pruebas(nombre, "la base de datos (SQL_SERVER_DATABASE)")

    import app.config.config as config_del_sistema  # no se conecta a nada

    configuracion.validar_valores_efectivos(config_del_sistema)  # valor efectivo, no solo lo escrito

    esperar_servicio("SQL Server", lambda: conectar().close())
    _soltar_motor()
    eliminar_base(nombre, conectar)
    crear_base(nombre, conectar)
    _estado.update(base_creada=True, nombre=nombre, revision=None)
    migrar()

    with contextlib.redirect_stdout(io.StringIO()):  # `database.py` imprime el resultado de su conexión
        import app.db.database as base_de_datos

    motor = base_de_datos.engine
    if motor is None:
        raise AbortoPruebas("Se aborta la suite de pruebas: el sistema no pudo conectarse a la base de pruebas recién creada.")
    exigir_nombre_pruebas(motor.url.database, "la base de datos del motor de SQLAlchemy (engine)")
    with motor.connect() as conexion:
        _estado["revision"] = conexion.execute(text("SELECT version_num FROM alembic_version")).scalar()
    # Sin conexiones en el pool: una unitaria que llegue a `engine.connect()` abre una nueva y la
    # frena el guardián (plan, §12, O1); la integración las abre al usarlas.
    motor.dispose()


def preparar_coleccion(conectar: Optional[Callable] = None) -> None:
    """Crea la colección de Qdrant de pruebas con `DIM` dimensiones y distancia coseno, reemplazando una anterior.

    Valida el nombre que está en el entorno y el que ya tomó el sistema (`config.py` y, si ya se importó,
    `qdrant_backend`) ANTES de crear el cliente. Queda marcada para que `cerrar_coleccion` la elimine
    aunque la creación se corte a la mitad.
    """
    conectar = conectar or cliente_qdrant
    nombre = os.environ.get("QDRANT_COLLECTION_NAME")
    exigir_nombre_pruebas(nombre, "la colección de Qdrant (QDRANT_COLLECTION_NAME)")

    import app.config.config as config_del_sistema  # no se conecta a nada

    exigir_nombre_pruebas(config_del_sistema.QDRANT_COLLECTION_NAME, "la colección de Qdrant que tomó el sistema (config.py)")
    modulo_qdrant = sys.modules.get("app.vectorstore.qdrant_backend")
    if modulo_qdrant is not None:
        exigir_nombre_pruebas(
            getattr(modulo_qdrant, "QDRANT_COLLECTION_NAME", None), "la colección de Qdrant que usa el sistema (qdrant_backend)"
        )

    eliminar_coleccion(nombre, conectar)
    _estado["coleccion_creada"] = True
    crear_coleccion(nombre, conectar, int(config_del_sistema.DIM))


def preparar_integracion(conectar_qdrant: Optional[Callable] = None, preguntar_tika: Optional[Callable] = None,
                         **espera) -> None:
    """Prepara lo que necesitan las pruebas de integración: Qdrant y Tika arriba, y la colección de pruebas.

    La colección se crea solo después de comprobar los dos servicios: si Tika no responde, no queda nada
    que limpiar. `espera` (reloj, pausa...) se pasa a `esperar_servicio` para probarlo con tiempo simulado.
    """
    esperar_qdrant(conectar_qdrant, **espera)
    esperar_tika(preguntar_tika, **espera)
    preparar_coleccion(conectar_qdrant)


def cerrar_coleccion(conectar: Optional[Callable] = None) -> None:
    """Elimina la colección de Qdrant de pruebas si esta corrida la creó. Se puede llamar más de una vez.

    Si la eliminación falla (por ejemplo, Qdrant detenido), la colección queda marcada como pendiente
    para que otra llamada la reintente, y el error se propaga.
    """
    if not _estado["coleccion_creada"]:
        return
    eliminar_coleccion(NOMBRE_PRUEBAS, conectar or cliente_qdrant)
    _estado["coleccion_creada"] = False


def _cerrar_base(conectar: Optional[Callable] = None) -> None:
    """Elimina la base de pruebas si esta corrida la creó.

    Si soltar el motor falla, la base se elimina igual y el error se propaga después. Si la
    eliminación falla, la base queda marcada como pendiente para que otra llamada la reintente.
    """
    if not _estado["base_creada"]:
        return
    try:
        _soltar_motor()
    finally:
        eliminar_base(_estado["nombre"], conectar or conectar_master)
        _estado["base_creada"] = False


def cerrar(conectar: Optional[Callable] = None, conectar_qdrant: Optional[Callable] = None) -> None:
    """Elimina la colección de pruebas (si se creó) y la base de pruebas (si se creó). Se puede llamar más de una vez.

    La base se elimina aunque la colección no se pueda eliminar (Qdrant detenido): una base huérfana es
    peor que una colección huérfana, y ambas las reemplaza la siguiente corrida. El error de la colección
    se propaga después.
    """
    try:
        cerrar_coleccion(conectar_qdrant)
    finally:
        _cerrar_base(conectar)


def encabezado() -> Optional[str]:
    """Línea del encabezado de la corrida que dice qué base se creó y en qué versión de las migraciones."""
    if not _estado["base_creada"]:
        return None
    return f"Base de pruebas: {_estado['nombre']} (migraciones de Alembic en {_estado['revision']})"
