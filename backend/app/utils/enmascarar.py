"""Enmascarado de correos electrónicos para los registros del servidor (RNF-08.2).

El correo de una persona es un dato personal: en los registros solo se deja la primera letra del usuario
y el dominio (`persona@dominio.cr` -> `p***@dominio.cr`). La bitácora (solo la ve el Administrador) sí
conserva el correo completo cuando hace falta para auditar; este módulo es solo para lo que se escribe en
la salida de los contenedores.

Ver también: `app/email/core/email_service.py` (registros del envío de correo).
"""
import re
from typing import Optional

# Un correo dentro de un texto. El usuario admite letras (con tilde), números y `. + -`; el dominio exige
# al menos un punto y no se lleva la puntuación que lo rodea (`a@x.cr.` termina en `x.cr`). Un correo ya
# enmascarado (`a***@x.cr`) no coincide, así que enmascarar dos veces no lo daña.
_PATRON_CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

_OMITIDO = "***"


def enmascarar_correo(correo: Optional[str]) -> str:
    """`persona@dominio.cr` -> `p***@dominio.cr`; lo que no tiene forma de correo se omite (`***`).

    Se respeta la capitalización original. Con varias arrobas manda la última (el dominio).
    """
    if not correo or "@" not in correo:
        return _OMITIDO
    usuario, _, dominio = correo.strip().rpartition("@")
    return f"{usuario[:1] or _OMITIDO}{'***' if usuario else ''}@{dominio}"


def enmascarar_correos_en_texto(texto: Optional[str]) -> str:
    """Enmascara cada correo que aparezca dentro de `texto` (por ejemplo, el texto de la bitácora)."""
    if texto is None:
        return ""
    return _PATRON_CORREO.sub(lambda coincidencia: enmascarar_correo(coincidencia.group(0)), str(texto))
