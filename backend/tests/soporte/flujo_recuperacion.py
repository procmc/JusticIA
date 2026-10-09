"""Auxiliares del flujo de recuperación de contraseña para las pruebas de integración (spec 003b, T3).

Las pruebas de la recuperación hablan solo con la API, como lo haría el navegador, y no dependen de cómo el sistema guarda
el estado por dentro. Este módulo reúne lo que esas pruebas repiten:

- `solicitar`, `verificar` y `cambiar`: los tres pasos del flujo, contra las rutas públicas de `/auth`.
- `codigo_enviado(correo_simulado)`: el código de 6 dígitos que llevó el último correo (envuelto en `Contrasena`, cuyo
  `repr` no lo muestra). Es la única fuente legítima del código: nunca viaja en una respuesta (RF-03.1).
- `codigo_inventado(distinto_de=...)`: un código de 6 dígitos generado en cada corrida, para los intentos incorrectos o
  para los casos en que no salió ningún correo.
- `desactivar_cuenta(...)`: deja una cuenta de prueba Inactiva con `PUT /usuarios/{id}` como Administrador, igual que lo
  hace la interfaz (RF-03.5, RF-03.6).
- `normalizar_para_comparar(respuesta)` y `forma_del_token(valor)`: dejan una respuesta en una forma comparable (código,
  orden de los campos, mensaje y FORMA del token, nunca su valor) para decir «estas respuestas son iguales» sin que un
  informe de fallo muestre un token (RF-03.2, RF-03.8, RF-03.21).
- `decodificar_token(token)`: los textos que salen de decodificar en base64 cada segmento del token, para buscar en ellos
  un dato que no debía viajar (RF-03.1, RF-03.21).

Este módulo no importa `app` al cargarse (regla de la suite): lo hace dentro de la función que lo necesita. Los datos son
inventados; las contraseñas y los códigos los genera la suite en cada corrida y no se escriben en ningún archivo.
"""
import base64
import binascii
import re
import secrets
from typing import Any, Dict, List, Optional

from tests.soporte import rastros

RUTA_SOLICITAR = "/auth/solicitar-recuperacion"
RUTA_VERIFICAR = "/auth/verificar-codigo"
RUTA_CAMBIAR = "/auth/cambiar-contrasenna-recuperacion"

MARCADOR_DEL_CODIGO = "Tu código de verificación es:"
PATRON_DEL_CODIGO = r"[0-9]{6}"


# --- Los tres pasos ----------------------------------------------------------------------------------------------

def solicitar(cliente_api, correo: str):
    """Paso 1: pide un código de recuperación para `correo`. Devuelve la respuesta de la API."""
    return cliente_api.post(RUTA_SOLICITAR, json={"email": correo})


def verificar(cliente_api, token: Optional[str], codigo: str):
    """Paso 2: verifica el código con el token que devolvió la solicitud. Devuelve la respuesta de la API."""
    return cliente_api.post(RUTA_VERIFICAR, json={"token": token or "", "codigo": str(codigo)})


def cambiar(cliente_api, token_de_verificacion: Optional[str], contrasena_nueva: str):
    """Paso 3: define la contraseña nueva con el token que devolvió la verificación. Devuelve la respuesta de la API."""
    return cliente_api.post(
        RUTA_CAMBIAR, json={"verificationToken": token_de_verificacion or "", "nuevaContrasenna": str(contrasena_nueva)}
    )


# --- El código y el correo ----------------------------------------------------------------------------------------

def codigo_enviado(correo_simulado, indice: int = -1):
    """El código de 6 dígitos del correo `indice` del correo simulado (por omisión, el último), envuelto en `Contrasena`."""
    return rastros.valor_tras(
        correo_simulado.contenido_real(indice).texto, MARCADOR_DEL_CODIGO, patron=PATRON_DEL_CODIGO
    )


def codigo_inventado(distinto_de: Optional[str] = None) -> str:
    """Un código de 6 dígitos aleatorio, distinto de `distinto_de` si se da (para un intento que debe ser incorrecto)."""
    while True:
        codigo = f"{secrets.randbelow(10 ** 6):06d}"
        if codigo != (None if distinto_de is None else str(distinto_de)):
            return codigo


def correo_sin_cuenta() -> str:
    """Un correo bien formado que no pertenece a ninguna cuenta. Lleva «prueba» para que la limpieza por texto borre
    las filas de bitácora que deje (la solicitud sin cuenta se registra sin usuario)."""
    return f"prueba.sin.cuenta.{secrets.token_hex(4)}@prueba.invalid"


# --- La cuenta ----------------------------------------------------------------------------------------------------

def desactivar_cuenta(cliente_api, cabeceras_del_administrador: Dict[str, str], usuario) -> None:
    """Deja Inactiva la cuenta de prueba `usuario` con `PUT /usuarios/{cedula}` como Administrador.

    Conserva el resto de los datos de la cuenta (nombre, apellidos, correo y rol) y cambia solo su estado, como lo haría la
    pantalla de gestión de usuarios. Falla si la API no responde 200.
    """
    from app.db.database import SessionLocal
    from app.db.models import T_Estado, T_Usuario

    with SessionLocal() as db:
        fila = db.query(T_Usuario).filter(T_Usuario.CN_Id_usuario == usuario.cedula).one()
        id_inactivo = db.query(T_Estado.CN_Id_estado).filter(T_Estado.CT_Nombre_estado == "Inactivo").scalar()
        cuerpo = {
            "nombre_usuario": fila.CT_Nombre_usuario, "nombre": fila.CT_Nombre, "apellido_uno": fila.CT_Apellido_uno,
            "apellido_dos": fila.CT_Apellido_dos or "", "correo": fila.CT_Correo, "id_rol": fila.CN_Id_rol,
            "id_estado": id_inactivo,
        }
    respuesta = cliente_api.put(f"/usuarios/{usuario.cedula}", json=cuerpo, headers=cabeceras_del_administrador)
    assert respuesta.status_code == 200, f"No se pudo desactivar la cuenta de prueba (código {respuesta.status_code})."


# --- Formas comparables ----------------------------------------------------------------------------------------------

def forma_del_token(valor: Any) -> Optional[Dict[str, Any]]:
    """La FORMA de un token, sin su valor: largo total, largo de cada segmento separado por punto y si solo usa el alfabeto
    de una URL (letras, dígitos, guion, guion bajo y punto). `None` si no hay token."""
    if not isinstance(valor, str):
        return None
    return {
        "largo": len(valor),
        "segmentos": [len(segmento) for segmento in valor.split(".")],
        "alfabeto_url": re.fullmatch(r"[A-Za-z0-9_.\-]+", valor) is not None,
    }


def normalizar_para_comparar(respuesta) -> Dict[str, Any]:
    """Deja una respuesta de la API en una forma comparable: código HTTP, campos en su orden, mensaje y forma de los tokens.

    Dos respuestas con la misma forma son indistinguibles para quien solo ve lo que recibe el navegador. El valor de un
    token NUNCA entra (solo su forma), así que un fallo de comparación no lo muestra. El mensaje sale de `message` o, en un
    error, de `detail`.
    """
    try:
        cuerpo = respuesta.json()
    except ValueError:
        return {"estado": respuesta.status_code, "campos": None, "mensaje": None, "tokens": {}}
    if not isinstance(cuerpo, dict):
        return {"estado": respuesta.status_code, "campos": None, "mensaje": None, "tokens": {}}
    return {
        "estado": respuesta.status_code,
        "campos": list(cuerpo.keys()),
        "mensaje": cuerpo.get("message", cuerpo.get("detail")),
        "tokens": {campo: forma_del_token(cuerpo[campo]) for campo in ("token", "verificationToken") if campo in cuerpo},
    }


def decodificar_token(token: Optional[str]) -> List[str]:
    """Los textos que salen de decodificar en base64 (alfabeto de URL) el token entero y cada uno de sus segmentos.

    Lo que no se puede decodificar se omite. Sirve para buscar en lo que el navegador podría leer de un token un dato que
    no debía viajar (el código, la cédula, el correo), con `rastros.encontrar_en_rastros`.
    """
    if not isinstance(token, str) or not token:
        return []
    textos = []
    for pieza in [token] + token.split("."):
        if not pieza:
            continue
        try:
            textos.append(base64.urlsafe_b64decode(pieza + "=" * (-len(pieza) % 4)).decode("utf-8", errors="replace"))
        except (binascii.Error, ValueError):
            continue
    return textos
