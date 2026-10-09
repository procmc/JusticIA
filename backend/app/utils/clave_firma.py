"""Clave de firma de la recuperación de contraseña: reglas de fuerza y derivación de claves (RNF-07.3).

La recuperación solo funciona si `JWT_SECRET_KEY` es una clave fuerte: 32 caracteres o más, 12 o más distintos
y que no sea un valor de respaldo conocido (el que trae el código por omisión o el marcador del archivo de
ejemplo). Si no lo es, la recuperación queda inhabilitada con el error de servicio uniforme y el resto del
sistema sigue funcionando como hoy (no se toca `config.JWT_SECRET_KEY` ni el inicio de sesión).

- `evaluar_clave_firma(valor)`: aplica las reglas y devuelve si es válida o el motivo. Nunca incluye el valor.
- `leer_clave_firma()`: lee la variable del entorno EN CADA USO (no al arrancar), así una prueba o una
  corrección del `.env` se notan en la siguiente petición; si no cumple, deja en el registro del servidor el
  nombre de la variable y el motivo (nunca el valor) y lanza `ClaveDeFirmaInvalida`.
- `derivar_clave(secreto, proposito)`: una clave distinta por propósito, derivada con HMAC; así lo que se
  guarda o se calcula para la recuperación no usa la clave que firma las sesiones.

Ver también: `app/utils/recuperacion_codigos.py` (funciones puras que usan estas claves) y
`backend/.env.example` (el marcador de `JWT_SECRET_KEY`).
"""
import hashlib
import hmac
import logging
import os
from typing import NamedTuple, Optional

logger = logging.getLogger(__name__)

VARIABLE_CLAVE_FIRMA = "JWT_SECRET_KEY"
LARGO_MINIMO = 32
DISTINTOS_MINIMOS = 12

MOTIVO_AUSENTE = "ausente"
MOTIVO_RESPALDO = "valor de respaldo conocido"
MOTIVO_CORTA = f"débil: menos de {LARGO_MINIMO} caracteres"
MOTIVO_POCO_VARIADA = f"débil: menos de {DISTINTOS_MINIMOS} caracteres distintos"

# Valores que alguna vez fueron el respaldo del código o el marcador del archivo de ejemplo. Aunque alguno
# parezca fuerte por su largo, es público (está en el repositorio): se rechaza siempre. Solo se agregan aquí
# valores de ejemplo, nunca una clave real.
VALORES_DE_RESPALDO_CONOCIDOS = frozenset({
    # Respaldo literal de `os.getenv("JWT_SECRET_KEY", ...)` en `auth_service.py` y `routes/auth.py`.
    "default-secret-key-change-in-production",
    # Marcador del archivo de ejemplo (antes de `SECRET_KEY`, hoy de `JWT_SECRET_KEY`).
    "cambiar-en-produccion-generar-con-openssl",
})

_CONOCIDOS_NORMALIZADOS = frozenset(valor.strip().casefold() for valor in VALORES_DE_RESPALDO_CONOCIDOS)


class ResultadoClave(NamedTuple):
    """Resultado de evaluar una clave: `valida` y, si no lo es, el `motivo`. No guarda el valor evaluado."""

    valida: bool
    motivo: Optional[str]


class ClaveDeFirmaInvalida(Exception):
    """La clave de firma no cumple las reglas. Lleva solo el motivo, nunca el valor."""

    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(f"{VARIABLE_CLAVE_FIRMA}: {motivo}")


def evaluar_clave_firma(valor: Optional[str]) -> ResultadoClave:
    """Aplica las reglas de RNF-07.3; la primera que falla da el motivo (ausente, respaldo, largo o variedad)."""
    if valor is None or not valor.strip():
        return ResultadoClave(False, MOTIVO_AUSENTE)
    if valor.strip().casefold() in _CONOCIDOS_NORMALIZADOS:
        return ResultadoClave(False, MOTIVO_RESPALDO)
    if len(valor) < LARGO_MINIMO:
        return ResultadoClave(False, MOTIVO_CORTA)
    if len(set(valor)) < DISTINTOS_MINIMOS:
        return ResultadoClave(False, MOTIVO_POCO_VARIADA)
    return ResultadoClave(True, None)


def leer_clave_firma() -> str:
    """Devuelve la clave de firma del entorno si cumple las reglas; si no, lo registra y lanza `ClaveDeFirmaInvalida`.

    El registro del servidor lleva el nombre de la variable y el motivo para quien opera el sistema; el
    valor no se escribe en ningún lado. Se lee en cada llamada, no al arrancar (plan, decisión 14).
    """
    valor = os.environ.get(VARIABLE_CLAVE_FIRMA)
    resultado = evaluar_clave_firma(valor)
    if not resultado.valida:
        logger.error("La clave de firma de la recuperación no es válida: %s (%s). La recuperación de contraseña queda "
                     "inhabilitada.", VARIABLE_CLAVE_FIRMA, resultado.motivo)
        raise ClaveDeFirmaInvalida(resultado.motivo)
    return valor


def derivar_clave(secreto: str, proposito: str) -> bytes:
    """Deriva una clave de 32 bytes: HMAC-SHA256 del secreto sobre la etiqueta `servia/<propósito>/v1`.

    Es determinista, distinta por propósito y distinta del secreto, así que quien lea una clave derivada
    (o lo que se firmó con ella) no obtiene la clave de las sesiones. Ninguna clave derivada se guarda.
    """
    if not secreto or not proposito:
        raise ValueError("Hacen falta el secreto y el propósito para derivar una clave")
    etiqueta = f"servia/{proposito}/v1".encode("utf-8")
    return hmac.new(secreto.encode("utf-8"), etiqueta, hashlib.sha256).digest()
