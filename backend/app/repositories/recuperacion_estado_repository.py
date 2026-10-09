"""Almacén de estado y de límites de la recuperación de contraseña por código, en Redis (RF-03.4, 03.7, 03.9 a 03.12, 03.20, 03.25).

Es el único módulo que habla con Redis en la recuperación (monolito modular: servicio -> este repositorio). Todo se
guarda en la base 3 y se identifica por la huella del correo normalizado (`app/utils/recuperacion_codigos.py`): ni el
correo ni el código aparecen jamás en una clave o un valor (el código se guarda como HMAC).

| Clave                              | Contenido                                          | Caducidad                   |
|------------------------------------|----------------------------------------------------|-----------------------------|
| `recuperacion:estado:<huella>`     | hash: codigo, intentos, emision, cedula, vinculo   | 900 s                       |
| `recuperacion:verificacion:<huella>` | texto `hash_del_secreto|cedula|vinculo`          | 600 s                       |
| `recuperacion:bloqueo:<huella>`    | `1`                                                | 60 s                        |
| `recuperacion:hora:<huella>`       | contador de solicitudes aceptadas                  | 3 600 s desde la primera    |

Sin scripts Lua ni `WATCH`: la atomicidad sale de órdenes atómicas sueltas (`SET NX`, `INCR`, `HINCRBY`, `DEL`) y de
transacciones (`MULTI`/`EXEC`), con «devoluciones» cuando una operación resulta no aceptada (plan, decisión 3).

Falla cerrada (RF-03.20): cualquier error de `redis` o del sistema al hablar con el servidor sale como
`AlmacenNoDisponible`, sin datos del correo, y el servicio responde con el error de servicio uniforme. El cliente se
crea con un tiempo de espera fijo (`TIEMPO_ESPERA_REDIS`), menor que los 30 s que espera el navegador.

Ver también: `app/utils/recuperacion_codigos.py` y `specs/003b-recuperacion-publica-segura/plan.md` §3.1 y §3.4.
"""
import functools
import threading
from typing import NamedTuple, Optional

import redis

from app.config.config import REDIS_URL

# La base 3 es de la recuperación: Celery usa la 0 y la 1; las conversaciones, la 2.
BASE_REDIS = 3
TIEMPO_ESPERA_REDIS = 2.0

CADUCIDAD_ESTADO = 900            # RF-03.4: el código vale 15 minutos
CADUCIDAD_VERIFICACION = 600      # RF-03.7: el cambio de contraseña se permite 10 minutos
ESPERA_ENTRE_SOLICITUDES = 60     # RF-03.10: una solicitud por minuto
VENTANA_DE_SOLICITUDES = 3600     # RF-03.11: cinco por hora, contada desde la primera aceptada
MAXIMO_SOLICITUDES_POR_HORA = 5
MAXIMO_INTENTOS = 5               # RF-03.9: intentos de verificación por código

_CAMPOS_DEL_ESTADO = ("codigo", "emision", "cedula", "vinculo")

_cliente: Optional[redis.Redis] = None
_cerrojo_del_cliente = threading.Lock()


class AlmacenNoDisponible(Exception):
    """Redis no respondió (conexión, tiempo o error del sistema). No lleva datos del correo; la causa va encadenada."""

    def __init__(self):
        super().__init__("El almacén de estado de la recuperación no está disponible")


class EstadoGuardado(NamedTuple):
    """Lo que guarda una solicitud aceptada, salvo el contador de intentos."""

    hash_codigo: str
    emision: str
    cedula: str
    vinculo: str


class IntentoRegistrado(NamedTuple):
    """El resultado de contar un intento: su número (puede pasar de 5) y el estado de la solicitud."""

    numero: int
    estado: EstadoGuardado


class VerificacionGuardada(NamedTuple):
    """Lo que guarda una verificación exitosa del código."""

    hash_secreto: str
    cedula: str
    vinculo: str


def obtener_cliente() -> redis.Redis:
    """El cliente de la base 3, creado una sola vez, con el tiempo de espera fijo en la conexión y en cada orden."""
    global _cliente
    with _cerrojo_del_cliente:
        if _cliente is None:
            _cliente = redis.Redis.from_url(
                f"{REDIS_URL.rstrip('/')}/{BASE_REDIS}",
                decode_responses=True,
                socket_timeout=TIEMPO_ESPERA_REDIS,
                socket_connect_timeout=TIEMPO_ESPERA_REDIS,
            )
        return _cliente


def _falla_cerrada(funcion):
    """Traduce los errores de `redis` y del sistema a `AlmacenNoDisponible`; un defecto del programa no se disfraza."""

    @functools.wraps(funcion)
    def envuelta(*args, **kwargs):
        try:
            return funcion(*args, **kwargs)
        except (redis.RedisError, OSError) as error:
            raise AlmacenNoDisponible() from error

    return envuelta


def _clave_estado(huella: str) -> str:
    return f"recuperacion:estado:{huella}"


def _clave_verificacion(huella: str) -> str:
    return f"recuperacion:verificacion:{huella}"


def _clave_bloqueo(huella: str) -> str:
    return f"recuperacion:bloqueo:{huella}"


def _clave_hora(huella: str) -> str:
    return f"recuperacion:hora:{huella}"


# --- Estado de la solicitud ------------------------------------------------------------------------------------------

@_falla_cerrada
def guardar_estado(huella: str, hash_codigo: str, emision: str, cedula: str, vinculo: str) -> None:
    """Guarda la solicitud: reemplaza el estado anterior entero y fija la caducidad, todo en una transacción (RF-03.4, 03.9).

    Un código nuevo invalida el anterior y reinicia el contador de intentos. `cedula` va vacía cuando no hay una
    cuenta Activa (estado señuelo, RF-03.8): el hash conserva siempre los mismos cinco campos.
    """
    clave = _clave_estado(huella)
    with obtener_cliente().pipeline(transaction=True) as tuberia:
        tuberia.delete(clave)
        tuberia.hset(clave, mapping={
            "codigo": hash_codigo,
            "intentos": "0",
            "emision": emision,
            "cedula": cedula or "",
            "vinculo": vinculo,
        })
        tuberia.expire(clave, CADUCIDAD_ESTADO)
        tuberia.execute()


@_falla_cerrada
def registrar_intento(huella: str) -> Optional[IntentoRegistrado]:
    """Cuenta un intento de verificación y devuelve su número con el estado; `None` si no hay estado (RF-03.9, 03.25).

    El contador solo crece con `HINCRBY` (atómico). Si el número pasa de 5, el intento se devuelve con otro
    `HINCRBY -1`: así 20 verificaciones simultáneas dejan el contador en 5 y solo cinco reciben un número permitido
    (quien recibe más de 5 no debe comprobar el código). Contar sobre una clave que no existe la crearía sin
    caducidad y sin código: se detecta y se borra, para no dejar nada (si Redis desalojó el estado, el proceso
    se rechaza como vencido).
    """
    cliente = obtener_cliente()
    clave = _clave_estado(huella)
    with cliente.pipeline(transaction=True) as tuberia:
        tuberia.hincrby(clave, "intentos", 1)
        tuberia.hmget(clave, _CAMPOS_DEL_ESTADO)
        numero, campos = tuberia.execute()
    hash_codigo, emision, cedula, vinculo = campos
    if hash_codigo is None:
        cliente.delete(clave)
        return None
    if numero > MAXIMO_INTENTOS:
        with cliente.pipeline(transaction=True) as tuberia:
            tuberia.hincrby(clave, "intentos", -1)
            tuberia.hexists(clave, "codigo")
            _, sigue_el_estado = tuberia.execute()
        if not sigue_el_estado:  # el estado caducó o se perdió justo ahora: que no quede un contador huérfano
            cliente.delete(clave)
    return IntentoRegistrado(int(numero), EstadoGuardado(hash_codigo, emision, cedula, vinculo))


# --- Límites de solicitudes -------------------------------------------------------------------------------------------

@_falla_cerrada
def aceptar_solicitud(huella: str) -> bool:
    """Decide si se acepta una solicitud: una por minuto y cinco por hora por correo (RF-03.10, 03.11, 03.12).

    El minuto lo toma `SET NX EX 60` (si dos llegan a la vez, solo una gana). Después `INCR` cuenta la hora, con
    `EXPIRE NX` para que la ventana parta de la primera aceptada y no se alargue nunca. Si la hora ya se agotó, la
    solicitud se devuelve (`DECR` y se quita el bloqueo de 60 s que acababa de crear): lo bloqueado no cuenta, no
    reinicia nada ni deja un bloqueo. Una solicitud bloqueada por el minuto no toca el contador.
    """
    cliente = obtener_cliente()
    bloqueo, hora = _clave_bloqueo(huella), _clave_hora(huella)
    if not cliente.set(bloqueo, "1", nx=True, ex=ESPERA_ENTRE_SOLICITUDES):
        return False
    with cliente.pipeline(transaction=True) as tuberia:
        tuberia.incr(hora)
        tuberia.expire(hora, VENTANA_DE_SOLICITUDES, nx=True)
        total, _ = tuberia.execute()
    if total > MAXIMO_SOLICITUDES_POR_HORA:
        with cliente.pipeline(transaction=True) as tuberia:
            tuberia.decr(hora)
            tuberia.expire(hora, VENTANA_DE_SOLICITUDES, nx=True)  # si la ventana venció justo ahora, que no quede sin caducidad
            tuberia.delete(bloqueo)
            tuberia.execute()
        return False
    return True


# --- Verificación del código ------------------------------------------------------------------------------------------

@_falla_cerrada
def guardar_verificacion(huella: str, hash_secreto: str, cedula: str, vinculo: str) -> None:
    """Guarda la verificación exitosa por 10 minutos; una nueva del mismo correo reemplaza a la anterior (RF-03.7)."""
    obtener_cliente().set(_clave_verificacion(huella), f"{hash_secreto}|{cedula}|{vinculo}", ex=CADUCIDAD_VERIFICACION)


@_falla_cerrada
def leer_verificacion(huella: str) -> Optional[VerificacionGuardada]:
    """Lee la verificación sin gastarla (así «igual a la actual» deja reintentar); `None` si no hay o caducó (RF-03.7, 03.25)."""
    valor = obtener_cliente().get(_clave_verificacion(huella))
    if valor is None or valor.count("|") < 2:
        return None
    # El hash y el vínculo son hexadecimales: la cédula es lo que queda entre el primer y el último separador.
    hash_secreto, _, resto = valor.partition("|")
    cedula, _, vinculo = resto.rpartition("|")
    return VerificacionGuardada(hash_secreto, cedula, vinculo)


@_falla_cerrada
def consumir_verificacion(huella: str) -> int:
    """Gasta la verificación con un `DEL`: devuelve 1 a quien la gasta y 0 a los demás, así solo una petición cambia la contraseña."""
    return int(obtener_cliente().delete(_clave_verificacion(huella)))
