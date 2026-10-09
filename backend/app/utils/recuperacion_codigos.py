"""Funciones puras de la recuperación de contraseña por código: normalización, huellas, códigos, tokens y vínculo.

Sin Redis ni base de datos: reciben claves derivadas (`ClavesDeRecuperacion`) y devuelven textos, así se prueban
con datos sintéticos. Lo que decide la recuperación (límites, estado, envío) está en el servicio y el repositorio.

- El código (6 dígitos) sale de `secrets` y solo viaja por correo; en el servidor queda un HMAC con una clave que
  nunca sale de él (RF-03.1).
- La huella identifica un correo normalizado sin guardarlo: 16 bytes de un HMAC en base64 «urlsafe» (RF-03.4, 03.12).
- Los dos tokens que recibe el navegador son `huella.emision` y `huella.secreto`; no llevan la cédula, el correo ni
  el código (RF-03.21).
- El vínculo une el proceso con el estado de la cuenta al emitirlo; si el Administrador la desactiva o cambia su
  correo o su contraseña, el vínculo deja de coincidir (RF-03.24).

Ver también: `app/utils/clave_firma.py` (claves derivadas) y `specs/003b-recuperacion-publica-segura/plan.md` §3.
"""
import base64
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass, field
from typing import Optional, Tuple

from app.utils.clave_firma import derivar_clave

LARGO_MAXIMO_CORREO = 100
DIGITOS_DEL_CODIGO = 6
LARGO_HUELLA = 22      # 16 bytes en base64 «urlsafe» sin relleno
LARGO_EMISION = 22     # 16 bytes aleatorios
LARGO_SECRETO = 43     # 32 bytes aleatorios

_ALFABETO_URL = r"[A-Za-z0-9_-]"
_PATRON_CORREO = re.compile(r"[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+")
_PATRON_CODIGO = re.compile(r"[0-9]{%d}" % DIGITOS_DEL_CODIGO)
_PATRON_TOKEN = re.compile(
    rf"({_ALFABETO_URL}{{{LARGO_HUELLA}}})\.({_ALFABETO_URL}{{{LARGO_EMISION}}}|{_ALFABETO_URL}{{{LARGO_SECRETO}}})"
)


@dataclass(frozen=True)
class ClavesDeRecuperacion:
    """Las cuatro claves derivadas de la clave de firma. Los bytes no salen en `repr` (trazas y registros)."""

    huella: bytes = field(repr=False)
    codigo: bytes = field(repr=False)
    verificacion: bytes = field(repr=False)
    vinculo: bytes = field(repr=False)


def derivar_claves_de_recuperacion(secreto: str) -> ClavesDeRecuperacion:
    """Deriva las cuatro claves de la recuperación (huella, código, verificación y vínculo) de la clave de firma."""
    return ClavesDeRecuperacion(
        huella=derivar_clave(secreto, "recuperacion/huella"),
        codigo=derivar_clave(secreto, "recuperacion/codigo"),
        verificacion=derivar_clave(secreto, "recuperacion/verificacion"),
        vinculo=derivar_clave(secreto, "recuperacion/vinculo"),
    )


def normalizar_correo(correo: Optional[str]) -> str:
    """Recorta los espacios y pasa a minúsculas: «Ana@Correo.cr » y «ana@correo.cr» son el mismo correo."""
    return (correo or "").strip().lower()


def es_correo_valido(correo: object) -> bool:
    """Un correo ya normalizado es válido si tiene hasta 100 caracteres, una sola arroba, sin espacios y con punto en el dominio."""
    return (
        isinstance(correo, str)
        and 0 < len(correo) <= LARGO_MAXIMO_CORREO
        and _PATRON_CORREO.fullmatch(correo) is not None
    )


def es_codigo_valido(codigo: object) -> bool:
    """Un código son exactamente 6 dígitos ASCII (no vale ningún otro tipo de dígito)."""
    return isinstance(codigo, str) and _PATRON_CODIGO.fullmatch(codigo) is not None


def huella_de_correo(clave_huella: bytes, correo: Optional[str]) -> str:
    """Identifica un correo (normalizado aquí) sin guardarlo: 22 caracteres «urlsafe» de un HMAC con la clave de huella."""
    resumen = hmac.new(clave_huella, normalizar_correo(correo).encode("utf-8"), hashlib.sha256).digest()[:16]
    return base64.urlsafe_b64encode(resumen).rstrip(b"=").decode("ascii")


def generar_codigo() -> str:
    """Un código de 6 dígitos con `secrets` (criptográficamente impredecible), con ceros a la izquierda."""
    return f"{secrets.randbelow(10 ** DIGITOS_DEL_CODIGO):0{DIGITOS_DEL_CODIGO}d}"


def generar_emision() -> str:
    """Identifica una solicitud aceptada: 22 caracteres aleatorios, distintos en cada una (un código reemplazado queda vencido)."""
    return secrets.token_urlsafe(16)


def generar_secreto() -> str:
    """El secreto del token de verificación: 43 caracteres aleatorios; el servidor solo guarda su HMAC."""
    return secrets.token_urlsafe(32)


def hash_de_codigo(clave_codigo: bytes, huella: str, codigo: str) -> str:
    """HMAC (hexadecimal) del código con su huella; con 10^6 códigos, un resumen sin clave se invertiría en segundos."""
    return hmac.new(clave_codigo, f"{huella}|{codigo}".encode("utf-8"), hashlib.sha256).hexdigest()


def hash_de_secreto(clave_verificacion: bytes, secreto: str) -> str:
    """HMAC (hexadecimal) del secreto del token de verificación."""
    return hmac.new(clave_verificacion, secreto.encode("utf-8"), hashlib.sha256).hexdigest()


def vinculo_de_cuenta(clave_vinculo: bytes, cedula: str, correo: str, estado: str, hash_contrasenna: str) -> str:
    """HMAC (hexadecimal) de la cédula, el correo, el estado y el hash de la contraseña de la cuenta.

    Cada dato lleva su largo por delante, así mover caracteres entre dos datos vecinos no da el mismo vínculo.
    """
    datos = (cedula, normalizar_correo(correo), estado, hash_contrasenna)
    mensaje = b"".join(len(dato.encode("utf-8")).to_bytes(4, "big") + dato.encode("utf-8") for dato in datos)
    return hmac.new(clave_vinculo, mensaje, hashlib.sha256).hexdigest()


def crear_token_solicitud(huella: str, emision: str) -> str:
    """El token de la solicitud: `huella.emision` (45 caracteres); no lleva cédula, correo, código ni indicador de la cuenta."""
    return f"{huella}.{emision}"


def crear_token_verificacion(huella: str, secreto: str) -> str:
    """El token de verificación: `huella.secreto` (66 caracteres)."""
    return f"{huella}.{secreto}"


def partir_token(token: object) -> Optional[Tuple[str, str]]:
    """Separa un token en (huella, segunda parte); `None` si no tiene el formato de alguno de los dos tokens."""
    if not isinstance(token, str):
        return None
    encontrado = _PATRON_TOKEN.fullmatch(token)
    return (encontrado.group(1), encontrado.group(2)) if encontrado else None
