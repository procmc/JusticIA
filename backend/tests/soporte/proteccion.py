"""Protección del nombre de pruebas (spec 002, RA-02.3).

Esta suite crea y elimina una base de datos y una colección de Qdrant; el nombre que va a
tocar se valida aquí, antes de abrir ninguna conexión. Este módulo es también el único punto
de DDL: `crear_base` y `eliminar_base` (T4) y `crear_coleccion` y `eliminar_coleccion` (T5).
Todas llaman siempre primero a `exigir_nombre_pruebas`, así que ninguna llega a crear ni a
eliminar nada que no se llame exactamente como la base o la colección de pruebas.

No hay ningún parámetro ni variable de entorno que desactive la validación.
"""
from typing import Callable

from tests.soporte.nombres import NOMBRE_PRUEBAS


class AbortoPruebas(Exception):
    """La suite no puede continuar sin riesgo para los datos de desarrollo.

    El `conftest.py` la convierte en `pytest.exit` con código distinto de cero; el mensaje
    va en español y nunca incluye contraseñas ni la URL de conexión completa.
    """


def exigir_nombre_pruebas(nombre: object, que: str) -> None:
    """Aborta si `nombre` no es exactamente el nombre de pruebas.

    `que` dice qué se está validando («la base de datos», «la colección de Qdrant») para el
    mensaje. Igualdad exacta: no sirven las mayúsculas, un nombre que lo contenga, uno vacío
    ni uno con caracteres de inyección, y tampoco un valor que no sea texto.
    """
    if not isinstance(nombre, str) or nombre != NOMBRE_PRUEBAS:
        raise AbortoPruebas(
            f"Se aborta la suite de pruebas: {que} es {nombre!r} y debe ser exactamente "
            f"'{NOMBRE_PRUEBAS}'. No se abrió ninguna conexión ni se ejecutó ninguna prueba."
        )


def _ejecutar_ddl(conectar: Callable, sentencia: str, accion: str) -> None:
    """Abre la conexión a `master` con `conectar`, ejecuta `sentencia` y la cierra siempre.

    El error del servidor (por ejemplo, el usuario sin permiso de `CREATE DATABASE`) se convierte en
    un aborto con su mensaje: en SQL Server no lleva contraseñas y ayuda a quien administra.
    """
    conexion = conectar()
    try:
        conexion.execute(sentencia)
    except Exception as error:
        raise AbortoPruebas(
            f"Se aborta la suite de pruebas: no se pudo {accion} la base de datos '{NOMBRE_PRUEBAS}': {error}"
        ) from error
    finally:
        conexion.close()


def crear_base(nombre: str, conectar: Callable) -> None:
    """Crea la base de pruebas. `conectar()` devuelve una conexión a `master` en modo autocommit.

    Valida el nombre ANTES de llamar a `conectar`: con otro nombre no se abre ninguna conexión.
    El nombre ya validado es una constante sin caracteres especiales, así que va directo al SQL.
    """
    exigir_nombre_pruebas(nombre, "la base de datos que se va a crear")
    _ejecutar_ddl(conectar, f"CREATE DATABASE [{nombre}]", "crear")


def eliminar_base(nombre: str, conectar: Callable) -> None:
    """Elimina la base de pruebas si existe, expulsando antes las conexiones que la tengan abierta.

    Mismas garantías que `crear_base`. Si la base no existe no hace nada. El modo de un solo
    usuario con `ROLLBACK IMMEDIATE` cierra las conexiones que dejó una corrida cortada o un pool.
    """
    exigir_nombre_pruebas(nombre, "la base de datos que se va a eliminar")
    _ejecutar_ddl(
        conectar,
        f"IF DB_ID(N'{nombre}') IS NOT NULL BEGIN "
        f"ALTER DATABASE [{nombre}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; "
        f"DROP DATABASE [{nombre}]; END",
        "eliminar",
    )


def _operar_en_qdrant(conectar: Callable, operacion: Callable, accion: str) -> None:
    """Crea el cliente con `conectar`, ejecuta `operacion(cliente)` y lo cierra siempre.

    Cualquier error (Qdrant detenido, operación rechazada) se convierte en un aborto en español que
    nombra a Qdrant y la colección. Solo lo llaman `crear_coleccion` y `eliminar_coleccion`, que ya
    validaron el nombre, así que aquí no se vuelve a decidir qué colección se toca.
    """
    try:
        cliente = conectar()
        try:
            operacion(cliente)
        finally:
            cliente.close()
    except Exception as error:
        raise AbortoPruebas(
            f"Se aborta la suite de pruebas: no se pudo {accion} la colección '{NOMBRE_PRUEBAS}' en Qdrant "
            f"({type(error).__name__}): {str(error)[:300]}"
        ) from error


def crear_coleccion(nombre: str, conectar: Callable, dimension: int) -> None:
    """Crea la colección de Qdrant de pruebas con `dimension` dimensiones y distancia coseno.

    Es la misma configuración que crea el sistema (`qdrant_backend._get_client`). `conectar()` devuelve
    el cliente de Qdrant. Valida el nombre ANTES de llamar a `conectar`: con otro nombre (incluida la
    colección de desarrollo) no se crea ningún cliente ni se abre ninguna conexión.
    """
    exigir_nombre_pruebas(nombre, "la colección de Qdrant que se va a crear")
    if not isinstance(dimension, int) or isinstance(dimension, bool) or dimension <= 0:
        raise AbortoPruebas(
            f"Se aborta la suite de pruebas: la dimensión de la colección es {dimension!r} y debe ser un entero positivo."
        )

    def _crear(cliente) -> None:
        from qdrant_client.models import Distance, VectorParams

        cliente.create_collection(
            collection_name=nombre, vectors_config=VectorParams(size=dimension, distance=Distance.COSINE)
        )

    _operar_en_qdrant(conectar, _crear, "crear")


def eliminar_coleccion(nombre: str, conectar: Callable) -> None:
    """Elimina la colección de Qdrant de pruebas si existe.

    Mismas garantías que `crear_coleccion`: valida el nombre antes de crear el cliente y solo puede
    eliminar la colección que se llama exactamente como la de pruebas. Si no existe, no hace nada.
    """
    exigir_nombre_pruebas(nombre, "la colección de Qdrant que se va a eliminar")

    def _eliminar(cliente) -> None:
        if cliente.collection_exists(nombre):
            cliente.delete_collection(nombre)

    _operar_en_qdrant(conectar, _eliminar, "eliminar")
