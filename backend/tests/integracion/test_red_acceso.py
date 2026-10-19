"""Red de seguridad del acceso (spec 004): ninguna ruta protegida responde sin una sesión válida (RNF-07.5, T3).

Recorre TODO el inventario de rutas de `tests/soporte/inventario_rutas.py` (RA-02.12), salvo las públicas y la pública
deliberada (los avatares, RF-04.20 y RNF-07.22, que cubren las pruebas de la 004a), con el método registrado y los datos
válidos de su ejemplo, y exige 401 sin ejecutar la acción y sin entregar contenido, con cuatro tokens: ausente, inválido,
vencido y firmado con otra clave. «Sin efecto» se comprueba comparando la foto de efectos (filas, puntos, archivos y correos)
de antes y después.

Lo que hoy responde sin sesión lleva en la tabla su `estado_actual` y aquí se marca como `xfail` estricto con esa etiqueta
(«RNF-07.5 · autenticación»): la lista de rutas con fallo la produce la prueba y nunca se copia en documentos. Los casos
del recorrido (a)-(e) están en `test_casos_del_recorrido`.

Todo ocurre en la base y la colección `servia_pruebas`, con el encolado, el LLM y el correo simulados y los archivos en la
carpeta temporal: aunque una ruta ejecutara la acción por error, no toca `uploads/` ni nada real.
"""
from datetime import datetime, timedelta, timezone

import pytest

from tests.soporte.flujos import foto_de_efectos
from tests.soporte.inventario_rutas import (
    ADMINISTRADOR, CLASIFICACION, PUBLICA, PUBLICA_DELIBERADA, USUARIO_GUBERNAMENTAL, ruta_de_ejemplo, rutas_registradas,
)

# La tarea de ingesta consulta su estado en Celery (ver `test_soporte_flujos.py`); solo aparece si una carga se ejecutara.
pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")

PROTEGIDAS = [(clave, entrada) for clave, entrada in CLASIFICACION.items()
              if entrada.clase not in (PUBLICA, PUBLICA_DELIBERADA)]
TOKENS = ("sin-token", "invalido", "vencido", "otra-clave")
ORIGEN_DE_PRUEBA = "http://localhost:3000"


def _marcas(entrada) -> list:
    """El `xfail` estricto de lo que hoy responde sin sesión: solo la etiqueta del estado actual, nunca la ruta."""
    if entrada.estado_actual is None:
        return []
    return [pytest.mark.xfail(strict=True, raises=AssertionError, reason=entrada.estado_actual)]


@pytest.fixture(autouse=True)
def entorno_aislado(carpeta_archivos, encolado_interceptado, ollama_simulado, correo_simulado):
    """Aísla lo que una ruta mal protegida podría ejecutar: archivos, encolado, LLM y correo quedan simulados."""
    return correo_simulado


def cabeceras_con(tipo: str) -> dict:
    """Las cabeceras de cada token del recorrido. Los tres con token llevan una carga que el sistema aceptaría si no fallara
    la firma o la vigencia, para que el 401 se deba a ese defecto y no a una carga incompleta."""
    if tipo == "sin-token":
        return {}
    if tipo == "invalido":
        return {"Authorization": "Bearer PRUEBA.token.invalido"}
    import jwt

    from app.config.config import JWT_ALGORITHM, JWT_SECRET_KEY
    from app.constants.roles import ADMINISTRADOR

    ahora = datetime.now(timezone.utc)
    carga = {"user_id": 1, "role": ADMINISTRADOR, "username": "PRUEBA", "iat": ahora}
    if tipo == "vencido":
        carga["exp"] = ahora - timedelta(hours=1)
        clave = JWT_SECRET_KEY
    else:
        carga["exp"] = ahora + timedelta(hours=1)
        clave = "PRUEBA-otra-clave-de-firma-distinta-de-la-del-sistema-0123456789"
    return {"Authorization": f"Bearer {jwt.encode(carga, clave, algorithm=JWT_ALGORITHM)}"}


def pedir(cliente, metodo: str, ruta: str, entrada, cabeceras: dict, con_datos: bool = True):
    """Llama a la ruta con el ejemplo válido de la tabla (o, sin `con_datos`, sin cuerpo ni consulta). Sigue los 307."""
    ejemplo = entrada.ejemplo if con_datos else {}
    return cliente.request(
        metodo, ruta, headers=cabeceras, params=ejemplo.get("consulta"), json=ejemplo.get("json"),
        data=ejemplo.get("formulario"), files=ejemplo.get("archivos"),
    )


def exigir_sin_contenido(respuesta) -> None:
    """Una respuesta de rechazo no entrega datos: a lo sumo el `detail` del error."""
    try:
        cuerpo = respuesta.json()
    except ValueError:
        cuerpo = None
    if isinstance(cuerpo, dict):
        assert set(cuerpo) <= {"detail"}, "la respuesta de rechazo trae contenido además del detalle del error"
    else:
        assert cuerpo is None, "la respuesta de rechazo trae contenido"


def exigir_sin_error_del_servidor(respuesta) -> None:
    """Ninguna 5xx. Es un `Failed` y no un `AssertionError`: el `xfail` del estado actual no puede esconderla."""
    if respuesta.status_code >= 500:
        pytest.fail(f"el servidor respondió con un error {respuesta.status_code}")


def exigir_rechazo_sin_efecto(respuesta, antes: dict, correo_simulado) -> None:
    exigir_sin_error_del_servidor(respuesta)
    assert respuesta.status_code == 401, f"se esperaba 401 y se obtuvo {respuesta.status_code}"
    exigir_sin_contenido(respuesta)
    assert foto_de_efectos(correo_simulado) == antes, "la petición rechazada dejó efectos"


# --- RNF-07.5: todo el inventario × cuatro tokens ----------------------------------------------------------------------

CASOS_DEL_INVENTARIO = [
    pytest.param(clave, tipo, id=f"{entrada.id}-{tipo}", marks=_marcas(entrada))
    for clave, entrada in PROTEGIDAS for tipo in TOKENS
]


@pytest.mark.requisito("RNF-07.5")
@pytest.mark.parametrize(("clave", "tipo"), CASOS_DEL_INVENTARIO)
def test_ruta_protegida_sin_token_o_invalido_da_401(cliente_api, entorno_aislado, clave, tipo):
    """RNF-07.5: una ruta protegida sin token, o con uno inválido, vencido o de otra clave, responde 401, sin ejecutar y sin contenido."""
    entrada = CLASIFICACION[clave]
    antes = foto_de_efectos(entorno_aislado)

    respuesta = pedir(cliente_api, clave[0], ruta_de_ejemplo(clave), entrada, cabeceras_con(tipo))

    exigir_rechazo_sin_efecto(respuesta, antes, entorno_aislado)


# --- RNF-07.5 (a)-(e): casos del recorrido -----------------------------------------------------------------------------

def _caso_a(cliente, correo, clave, entrada):
    """(a) OPTIONS (CORS) no es acceso: no devuelve contenido ni ejecuta nada."""
    antes = foto_de_efectos(correo)
    respuesta = cliente.options(
        ruta_de_ejemplo(clave), headers={"Origin": ORIGEN_DE_PRUEBA, "Access-Control-Request-Method": clave[0]},
    )
    exigir_sin_error_del_servidor(respuesta)
    assert respuesta.content in (b"", b"OK"), "OPTIONS entregó contenido"
    assert foto_de_efectos(correo) == antes, "OPTIONS dejó efectos"


def _caso_b(cliente, correo, clave, entrada):
    """(b) 307 por barra final: se sigue y el destino da 401."""
    antes = foto_de_efectos(correo)
    ruta = ruta_de_ejemplo(clave)
    alterna = ruta[:-1] if ruta.endswith("/") else ruta + "/"
    respuesta = pedir(cliente, clave[0], alterna, entrada, {})
    exigir_sin_error_del_servidor(respuesta)
    assert [r.status_code for r in respuesta.history] == [307], "la ruta con la barra cambiada no redirige con 307"
    assert respuesta.status_code == 401, f"tras el 307 se esperaba 401 y se obtuvo {respuesta.status_code}"
    exigir_sin_contenido(respuesta)
    assert foto_de_efectos(correo) == antes, "la petición rechazada dejó efectos"


def _caso_c(cliente, correo, clave, entrada):
    """(c) 405 no cuenta: un método no registrado no ejecuta nada ni entrega contenido (el recorrido usa solo los registrados)."""
    registrados = {metodo for metodo, plantilla in rutas_registradas(cliente.app) if plantilla == clave[1]}
    libres = [metodo for metodo in ("PUT", "PATCH", "DELETE", "POST") if metodo not in registrados]
    assert libres, "la ruta registra todos los métodos de la prueba"
    antes = foto_de_efectos(correo)
    respuesta = cliente.request(libres[0], ruta_de_ejemplo(clave))
    exigir_sin_error_del_servidor(respuesta)
    assert respuesta.status_code in (401, 405), f"se esperaba 401 o 405 y se obtuvo {respuesta.status_code}"
    exigir_sin_contenido(respuesta)
    assert foto_de_efectos(correo) == antes, "el método no registrado dejó efectos"


def _caso_d(cliente, correo, clave, entrada):
    """(d) 422 sin token solo con datos inválidos, sin efecto ni contenido (con datos válidos, 401: lo cubre el inventario)."""
    antes = foto_de_efectos(correo)
    respuesta = pedir(cliente, clave[0], ruta_de_ejemplo(clave), entrada, {}, con_datos=False)
    exigir_sin_error_del_servidor(respuesta)
    assert respuesta.status_code in (401, 422), f"se esperaba 401 o 422 y se obtuvo {respuesta.status_code}"
    if respuesta.status_code == 422:
        assert {"json", "formulario", "archivos"} & set(entrada.ejemplo), "422 en una ruta que no recibe datos"
    if respuesta.status_code == 401:
        exigir_sin_contenido(respuesta)
    assert foto_de_efectos(correo) == antes, "la petición con datos inválidos dejó efectos"


def _caso_e(cliente, correo, clave, entrada):
    """(e) La documentación automática es protegida: sin sesión, 401."""
    exigir_rechazo_sin_efecto(pedir(cliente, clave[0], ruta_de_ejemplo(clave), entrada, {}), foto_de_efectos(correo), correo)


CASOS = {"a": _caso_a, "b": _caso_b, "c": _caso_c, "d": _caso_d, "e": _caso_e}


def _casos_del_recorrido() -> list:
    por_plantilla = {}
    for clave, entrada in PROTEGIDAS:
        por_plantilla.setdefault(clave[1], (clave, entrada))  # (a) y (c) se prueban una vez por ruta, no por método
    casos = [pytest.param("a", clave, id=f"a-{entrada.id}") for clave, entrada in por_plantilla.values()]
    casos += [pytest.param("b", clave, id=f"b-{entrada.id}", marks=_marcas(entrada)) for clave, entrada in PROTEGIDAS]
    casos += [pytest.param("c", clave, id=f"c-{entrada.id}") for clave, entrada in por_plantilla.values()]
    casos += [pytest.param("d", clave, id=f"d-{entrada.id}") for clave, entrada in PROTEGIDAS
              if {"json", "formulario", "archivos"} & set(entrada.ejemplo)]
    casos += [pytest.param("e", clave, id=f"e-{entrada.id}", marks=_marcas(entrada)) for clave, entrada in PROTEGIDAS
              if entrada.grupo == "documentacion"]
    return casos


@pytest.mark.requisito("RNF-07.5")
@pytest.mark.parametrize(("caso", "clave"), _casos_del_recorrido())
def test_casos_del_recorrido(cliente_api, entorno_aislado, caso, clave):
    """RNF-07.5 (a)-(e): OPTIONS no es acceso, el 307 se sigue hasta el 401, el 405 no cuenta, el 422 solo con datos inválidos y la documentación pide sesión."""
    CASOS[caso](cliente_api, entorno_aislado, clave, CLASIFICACION[clave])


# --- RF-02.3: el otro rol en los flujos críticos -----------------------------------------------------------------------

# Solo las rutas exclusivas de un rol: las de sesión son de cualquier rol y no entran en la matriz. Hoy todas cumplen
# RF-02.3 (caracterización), así que ninguna lleva `xfail`; si una dejara de cumplirlo, se marcaría «RF-02.3 · <módulo>».
FLUJOS_CRITICOS = [(clave, entrada) for clave, entrada in CLASIFICACION.items()
                   if entrada.flujo_critico and entrada.clase in (ADMINISTRADOR, USUARIO_GUBERNAMENTAL)]


def _foto_con_usuarios(correo_simulado) -> dict:
    """La foto de efectos más las cuentas de usuario (alta, cambio y restablecimiento no entran en `foto_de_efectos`)."""
    from sqlalchemy import text

    from app.db.database import engine

    foto = foto_de_efectos(correo_simulado)
    with engine.connect() as conexion:
        foto["usuarios"] = tuple(conexion.execute(text("SELECT COUNT(*), CHECKSUM_AGG(CHECKSUM(*)) FROM T_Usuario")).one())
    return foto


@pytest.mark.requisito("RF-02.3")
@pytest.mark.parametrize(
    "clave", [pytest.param(clave, id=entrada.id) for clave, entrada in FLUJOS_CRITICOS],
)
def test_flujo_critico_con_el_otro_rol_da_403_sin_efectos(
    cliente_api, entorno_aislado, iniciar_sesion, administrador, usuario_gubernamental, clave,
):
    """RF-02.3: en un flujo crítico, el token del otro rol recibe 403 (no 5xx ni 404), sin contenido y sin ejecutar la acción."""
    entrada = CLASIFICACION[clave]
    otro_rol = usuario_gubernamental if entrada.clase == ADMINISTRADOR else administrador
    cabeceras = iniciar_sesion(otro_rol)
    antes = _foto_con_usuarios(entorno_aislado)

    respuesta = pedir(cliente_api, clave[0], ruta_de_ejemplo(clave), entrada, cabeceras)

    exigir_sin_error_del_servidor(respuesta)
    assert respuesta.status_code == 403, f"se esperaba 403 y se obtuvo {respuesta.status_code}"
    exigir_sin_contenido(respuesta)
    assert _foto_con_usuarios(entorno_aislado) == antes, "la petición rechazada dejó efectos"
