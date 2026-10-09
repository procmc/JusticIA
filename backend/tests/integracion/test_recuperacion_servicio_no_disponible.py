"""Pruebas de T8 (spec 003b): la recuperación falla cerrada cuando Redis no responde o la clave de firma no es válida.

Cubren RF-03.20 (falla cerrada y tiempo máximo), RNF-07.3 (integración: clave ausente, de respaldo o débil), RF-03.25 y RF-03.8
(con Redis en fallo) y el 503 de RF-03.22, en los TRES pasos de la recuperación y por la API, como lo vería el navegador:

- Con Redis sin respuesta (error de conexión y de tiempo), los pasos 1, 2 y 3 responden igual en forma, código (503) y mensaje
  para una cuenta Activa, una no registrada y una Inactiva; no sale ningún correo, no cambia ninguna contraseña y no se consulta
  la base de datos (Redis se comprueba ANTES de mirar la cuenta). Con Redis restablecido el reintento se comporta con normalidad.
- Con Redis colgado, la petición no responde antes de 2 s y responde 503 a los 2 s: el tiempo es VIRTUAL (`reloj_controlable`) y
  la aplicación se llama por ASGI dentro del bucle de la prueba (`llamar_asgi`), así que no se espera tiempo real.
- Con la clave de firma ausente, de respaldo (cada valor de la lista del sistema) o débil, los tres pasos responden el MISMO error
  de servicio uniforme, el inicio de sesión sigue funcionando y el registro del servidor nombra `JWT_SECRET_KEY` y el motivo, nunca
  el valor.

Usan la base `servia_pruebas`, el correo y el Redis simulados: nada sale de la prueba. Las cuentas son `PRUEBA`. Los códigos, las
contraseñas y las claves débiles o ausentes las construye la suite en cada corrida (las de respaldo son los valores públicos de
la lista del sistema) y NINGUNA se escribe en un archivo ni sale en un mensaje de fallo: los parámetros se identifican por un
nombre, nunca por el valor.
"""
import asyncio
import logging
import os
import secrets
from dataclasses import dataclass, field
from typing import Optional

import pytest
from sqlalchemy import event, text

from app.utils import clave_firma as cf
from tests.soporte import datos, rastros
from tests.soporte import flujo_recuperacion as flujo

# El error de servicio uniforme (spec y ERS): el mismo texto para las dos causas, en los tres pasos y para cualquier cuenta.
MENSAJE_SERVICIO_NO_DISPONIBLE = (
    "El servicio de recuperación de contraseña no está disponible por el momento. Inténtalo de nuevo más tarde."
)
CUERPO_503 = {"detail": MENSAJE_SERVICIO_NO_DISPONIBLE}
MENSAJE_INCORRECTO = "Código de verificación incorrecto"
MENSAJE_CAMBIADO = "Contraseña recuperada exitosamente"
COTA = 3.0  # segundos REALES: solo una red de seguridad; si se agota, la prueba falla

CAUSAS_DE_CLAVE = [
    "ausente-vacia", "ausente-sin-definir", "debil-corta", "debil-poco-variada",
] + [f"respaldo-{indice}" for indice in range(len(cf.VALORES_DE_RESPALDO_CONOCIDOS))]


# --- Apoyo --------------------------------------------------------------------------------------------------------------

@dataclass
class Caso:
    """Un proceso de recuperación ya iniciado (con todo funcionando) para uno de los tres casos de RF-03.8."""

    nombre: str
    correo: str
    token: str = field(repr=False)
    codigo: str = field(repr=False)
    token_de_verificacion: str = field(repr=False)
    cuenta: Optional[object] = None


def _hash_guardado(cedula):
    from app.db.database import engine

    with engine.connect() as conexion:
        return conexion.execute(
            text("SELECT CT_Contrasenna FROM T_Usuario WHERE CN_Id_usuario = :c"), {"c": cedula}
        ).scalar()


def _iniciar_sesion_con(cliente_api, correo, contrasena):
    return cliente_api.post("/auth/login", json={"email": correo, "password": str(contrasena)})


def _preparar_procesos(cliente_api, correo_simulado, nueva_cuenta, cuenta_inactiva):
    """Con todo funcionando, inicia un proceso por caso: cuenta Activa, correo no registrado y cuenta Inactiva.

    La cuenta Activa llega hasta el token de verificación (con su código real, leído del correo simulado). Los otros dos casos
    solo tienen el token de la solicitud (un estado señuelo) y un código inventado; como no hay un token de verificación real,
    se arma uno con la forma correcta (no se emitió: el paso 3 lo trataría como un proceso vencido). Devuelve los casos por nombre.
    """
    activa = nueva_cuenta()
    sin_cuenta = flujo.correo_sin_cuenta()
    casos = {}
    for nombre, correo, cuenta in (
        ("activa", activa.correo, activa),
        ("no registrada", sin_cuenta, None),
        ("inactiva", cuenta_inactiva.correo, cuenta_inactiva),
    ):
        respuesta = flujo.solicitar(cliente_api, correo)
        assert respuesta.status_code == 200, f"la solicitud de preparación del caso {nombre} dio {respuesta.status_code}"
        token = respuesta.json()["token"]
        if nombre == "activa":
            codigo = flujo.codigo_enviado(correo_simulado)
            verificada = flujo.verificar(cliente_api, token, codigo)
            assert verificada.status_code == 200, f"la verificación de preparación dio {verificada.status_code}"
            token_de_verificacion = verificada.json()["verificationToken"]
        else:
            codigo = flujo.codigo_inventado()
            token_de_verificacion = token.split(".")[0] + "." + secrets.token_urlsafe(32)
        casos[nombre] = Caso(nombre, correo, token, codigo, token_de_verificacion, cuenta)
    return casos


def _tres_pasos(cliente_api, caso, contrasena_nueva):
    """Los tres pasos de un caso, en orden: lo que enviaría el navegador."""
    return [
        flujo.solicitar(cliente_api, caso.correo),
        flujo.verificar(cliente_api, caso.token, caso.codigo),
        flujo.cambiar(cliente_api, caso.token_de_verificacion, contrasena_nueva),
    ]


def _comprobar_503_uniforme(respuestas):
    """Todas las respuestas son 503 con el mismo cuerpo exacto (mismos bytes) y la misma forma, sea cual sea el paso y la cuenta."""
    assert [r.status_code for r in respuestas] == [503] * len(respuestas)
    assert {r.content for r in respuestas} == {respuestas[0].content}, "las respuestas 503 no son idénticas entre sí"
    assert respuestas[0].json() == CUERPO_503
    assert len({str(flujo.normalizar_para_comparar(r)) for r in respuestas}) == 1


@pytest.fixture
def nueva_cuenta(registro_de_datos):
    """Una función que crea una cuenta `PRUEBA` más (Usuario Gubernamental, Activa) y la deja registrada para su limpieza."""

    def _crear():
        return datos.crear_usuario(datos.ROL_USUARIO_GUBERNAMENTAL, registro_de_datos)

    return _crear


@pytest.fixture
def cuenta_inactiva(cliente_api, iniciar_sesion, administrador, nueva_cuenta):
    """Una cuenta `PRUEBA` ya desactivada por el Administrador con `PUT /usuarios/{id}`, como lo hace la interfaz."""
    cuenta = nueva_cuenta()
    flujo.desactivar_cuenta(cliente_api, iniciar_sesion(administrador), cuenta)
    return cuenta


@pytest.fixture
def registros_del_servidor(caplog):
    """Captura el registro del servidor del paquete `app` (nivel INFO), sin los de SQLAlchemy ni los de otras librerías."""
    caplog.set_level(logging.INFO, logger="app")
    return caplog


@pytest.fixture
def consultas_a_cuentas():
    """Anota cada `SELECT` sobre `T_Usuario` que llega a la base de pruebas (la lista crece sola mientras la prueba corre).

    Sirve para comprobar que, con el servicio caído, la recuperación NO consulta la cuenta: la respuesta no puede depender de
    ella (RF-03.20, RF-03.8). Se mide por lo que llega a la base, no por cómo se llame el método que la consulta.
    """
    from app.db.database import engine

    vistas = []

    def _anotar(conexion, cursor, sentencia, parametros, contexto, varias):
        if sentencia.lstrip().upper().startswith("SELECT") and "T_USUARIO" in sentencia.upper():
            vistas.append(sentencia)

    event.listen(engine, "before_cursor_execute", _anotar)
    try:
        yield vistas
    finally:
        event.remove(engine, "before_cursor_execute", _anotar)


def _clave_invalida(causa):
    """`(valor, motivo)` de la clave de cada causa: `None` es «no definida». Las construye la prueba; nunca se imprimen."""
    if causa == "ausente-vacia":
        return "", "ausente"
    if causa == "ausente-sin-definir":
        return None, "ausente"
    if causa == "debil-corta":
        return secrets.token_hex(15), "menos de 32 caracteres"  # 30 caracteres
    if causa == "debil-poco-variada":
        return secrets.token_hex(2) * 11, "menos de 12 caracteres distintos"  # 44 caracteres, a lo más 4 distintos
    indice = int(causa.rsplit("-", 1)[1])
    return sorted(cf.VALORES_DE_RESPALDO_CONOCIDOS)[indice], "valor de respaldo conocido"


def _poner_clave(monkeypatch, valor):
    if valor is None:
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    else:
        monkeypatch.setenv("JWT_SECRET_KEY", valor)


async def _esperar(esperable, que):
    """Espera hasta `COTA` s reales; si se agota, la prueba falla diciendo qué esperaba (sin tokens ni códigos)."""
    try:
        return await asyncio.wait_for(esperable, COTA)
    except asyncio.TimeoutError:
        raise AssertionError(f"Se agotó la cota de {COTA:g} s reales esperando {que}.") from None


# --- RF-03.20, RF-03.8, RF-03.22, RF-03.25: Redis sin respuesta, en los tres pasos --------------------------------------------------

@pytest.mark.parametrize("tipo", ["conexion", "tiempo"])
def test_con_redis_sin_respuesta_los_tres_pasos_responden_503_igual_para_cualquier_cuenta(
    tipo, cliente_api, correo_simulado, redis_controlable, consultas_a_cuentas, registros_del_servidor, capsys,
    nueva_cuenta, cuenta_inactiva,
):
    """RF-03.20, RF-03.8 y RF-03.22: con Redis sin respuesta (error de conexión o de tiempo), los pasos 1, 2 y 3 responden 503
    con el mismo mensaje y la misma forma para una cuenta Activa (incluso con su código real y su verificación vigentes), una no
    registrada y una Inactiva. No sale ningún correo, no cambia ninguna contraseña, no se consulta la cuenta y no se escribe nada
    en Redis. Cuando Redis responde de nuevo, esos mismos pedidos se comportan con normalidad."""
    casos = _preparar_procesos(cliente_api, correo_simulado, nueva_cuenta, cuenta_inactiva)
    assert len(consultas_a_cuentas) > 0, "control positivo: con Redis funcionando sí se consulta la cuenta"
    activa = casos["activa"]
    nueva = datos.generar_contrasena()
    correos_antes = len(correo_simulado.intentos)
    hash_antes = _hash_guardado(activa.cuenta.cedula)
    claves_antes = redis_controlable.claves()
    consultas_antes = len(consultas_a_cuentas)
    registros_del_servidor.clear()

    redis_controlable.no_responde(tipo)
    respuestas = [r for caso in casos.values() for r in _tres_pasos(cliente_api, caso, nueva)]

    assert len(respuestas) == 9
    _comprobar_503_uniforme(respuestas)
    assert len(correo_simulado.intentos) == correos_antes, "con el servicio caído no puede salir ningún correo"
    assert len(consultas_a_cuentas) == consultas_antes, "con Redis en fallo no se consulta la base de datos"
    assert redis_controlable.claves() == claves_antes, "con el servicio caído no se crea ni se pierde ninguna clave"
    assert _hash_guardado(activa.cuenta.cedula) == hash_antes, "la contraseña no puede cambiar"
    registros, salida = registros_del_servidor.text, capsys.readouterr()
    assert "no respondió" in registros, "el servidor debe registrar que el almacén no respondió"
    for caso in casos.values():
        rastros.buscar_en_rastros(caso.correo, registros=registros, salida=salida.out + salida.err)
    rastros.buscar_en_rastros(activa.codigo, registros=registros, salida=salida.out + salida.err)

    # Redis vuelve: lo que fue 503 ahora se comporta con normalidad, y la contraseña solo cambia con el cambio legítimo.
    redis_controlable.responder_bien()
    assert _iniciar_sesion_con(cliente_api, activa.cuenta.correo, activa.cuenta.contrasena).status_code == 200
    por_cuenta = flujo.verificar(cliente_api, casos["no registrada"].token, casos["no registrada"].codigo)
    assert (por_cuenta.status_code, por_cuenta.json()["detail"]) == (400, MENSAJE_INCORRECTO)
    cambio = flujo.cambiar(cliente_api, activa.token_de_verificacion, nueva)
    assert (cambio.status_code, cambio.json()["message"]) == (200, MENSAJE_CAMBIADO)
    assert _iniciar_sesion_con(cliente_api, activa.cuenta.correo, nueva).status_code == 200


@pytest.mark.parametrize("tipo", ["conexion", "tiempo"])
def test_con_redis_restablecido_cada_paso_se_reintenta_con_normalidad(
    tipo, cliente_api, correo_simulado, redis_controlable, nueva_cuenta
):
    """RF-03.20: un 503 en un paso no deja nada a medias. Con `responder_bien` el mismo paso funciona: la solicitud (sin el
    bloqueo de un minuto) envía su correo, el código correcto se acepta (el pedido fallido no gastó un intento) y el cambio se
    hace con la misma verificación."""
    cuenta = nueva_cuenta()
    nueva = datos.generar_contrasena()

    redis_controlable.no_responde(tipo)
    caida = flujo.solicitar(cliente_api, cuenta.correo)
    assert (caida.status_code, caida.json()) == (503, CUERPO_503) and correo_simulado.intentos == []
    redis_controlable.responder_bien()
    solicitud = flujo.solicitar(cliente_api, cuenta.correo)
    assert solicitud.status_code == 200 and len(correo_simulado.intentos) == 1
    token, codigo = solicitud.json()["token"], flujo.codigo_enviado(correo_simulado)

    redis_controlable.no_responde(tipo)
    caida = flujo.verificar(cliente_api, token, codigo)
    assert (caida.status_code, caida.json()) == (503, CUERPO_503)
    redis_controlable.responder_bien()
    verificada = flujo.verificar(cliente_api, token, codigo)
    assert verificada.status_code == 200
    token_de_verificacion = verificada.json()["verificationToken"]

    redis_controlable.no_responde(tipo)
    caida = flujo.cambiar(cliente_api, token_de_verificacion, nueva)
    assert (caida.status_code, caida.json()) == (503, CUERPO_503)
    assert _iniciar_sesion_con(cliente_api, cuenta.correo, cuenta.contrasena).status_code == 200
    redis_controlable.responder_bien()
    cambio = flujo.cambiar(cliente_api, token_de_verificacion, nueva)
    assert (cambio.status_code, cambio.json()["message"]) == (200, MENSAJE_CAMBIADO)
    assert _iniciar_sesion_con(cliente_api, cuenta.correo, nueva).status_code == 200


# --- RF-03.20: el tiempo máximo, con Redis colgado y tiempo virtual ----------------------------------------------------------------

@pytest.mark.parametrize("paso", ["solicitar", "verificar", "cambiar"])
def test_con_redis_colgado_no_responde_antes_de_2_s_y_responde_503_a_los_2_s(
    paso, cliente_api, llamar_asgi, correo_simulado, redis_controlable, reloj_controlable, nueva_cuenta
):
    """RF-03.20: con Redis colgado (la llamada queda retenida), la petición sigue pendiente a los 1,9 s virtuales y responde 503
    a los 2,0 s, sin esperar tiempo real. Nada sale por correo y la contraseña no cambia. Al final se libera el Redis para que
    el hilo retenido termine."""
    cuenta = nueva_cuenta()
    nueva = datos.generar_contrasena()
    token = codigo = token_de_verificacion = None
    if paso != "solicitar":  # con todo funcionando, el proceso llega hasta donde el paso colgado lo necesita
        solicitud = flujo.solicitar(cliente_api, cuenta.correo)
        token, codigo = solicitud.json()["token"], flujo.codigo_enviado(correo_simulado)
        if paso == "cambiar":
            token_de_verificacion = flujo.verificar(cliente_api, token, codigo).json()["verificationToken"]
    ruta, cuerpo = {
        "solicitar": (flujo.RUTA_SOLICITAR, {"email": cuenta.correo}),
        "verificar": (flujo.RUTA_VERIFICAR, {"token": token, "codigo": str(codigo)}),
        "cambiar": (flujo.RUTA_CAMBIAR, {"verificationToken": token_de_verificacion, "nuevaContrasenna": str(nueva)}),
    }[paso]
    correos_antes, hash_antes = len(correo_simulado.intentos), _hash_guardado(cuenta.cedula)

    async def escenario():
        redis_controlable.colgar()
        try:
            llamada = llamar_asgi("POST", ruta, json=cuerpo)
            if not await asyncio.to_thread(redis_controlable.esperar_retenida, COTA):
                raise AssertionError(f"Se agotó la cota de {COTA:g} s reales esperando que la petición llegara a Redis.")
            plazos = reloj_controlable.esperas_pendientes
            await reloj_controlable.avanzar(1.9)
            pendiente_a_los_1_9 = not llamada.respuesta.done()
            await reloj_controlable.avanzar(0.1)
            respuesta = await _esperar(llamada.respuesta, "el 503 a los 2 s virtuales")
        finally:
            redis_controlable.liberar()  # sin esto, el cierre del bucle esperaría al hilo retenido
        await _esperar(llamada.tarea, "que la aplicación termine")
        return plazos, pendiente_a_los_1_9, respuesta

    plazos, pendiente_a_los_1_9, respuesta = asyncio.run(escenario())

    assert plazos >= 1, "la petición debe haber registrado su plazo de 2 s antes de que el tiempo avance"
    assert pendiente_a_los_1_9 is True, "a los 1,9 s virtuales la petición debe seguir pendiente"
    assert (respuesta.status_code, respuesta.json()) == (503, CUERPO_503)
    assert len(correo_simulado.intentos) == correos_antes
    assert _hash_guardado(cuenta.cedula) == hash_antes


# --- RNF-07.3 (integración): clave de firma ausente, de respaldo o débil -----------------------------------------------------------

@pytest.mark.parametrize("causa", CAUSAS_DE_CLAVE)
def test_con_la_clave_de_firma_invalida_los_tres_pasos_responden_el_mismo_error_y_el_login_sigue(
    causa, cliente_api, correo_simulado, redis_controlable, consultas_a_cuentas, registros_del_servidor, capsys, monkeypatch,
    nueva_cuenta, cuenta_inactiva,
):
    """RNF-07.3: con la clave de firma ausente, de respaldo (cada valor de la lista) o débil, los pasos 1, 2 y 3 responden el
    MISMO 503 para una cuenta Activa, una no registrada y una Inactiva. No sale ningún correo, no cambia ninguna contraseña,
    no se toca Redis ni la cuenta, `POST /auth/login` sigue funcionando y el registro del servidor nombra `JWT_SECRET_KEY` y el
    motivo, nunca el valor. Con la clave válida de nuevo, la recuperación vuelve."""
    casos = _preparar_procesos(cliente_api, correo_simulado, nueva_cuenta, cuenta_inactiva)
    activa = casos["activa"]
    nueva = datos.generar_contrasena()
    clave_valida = os.environ["JWT_SECRET_KEY"]  # la de la suite: no se imprime
    valor, motivo = _clave_invalida(causa)
    correos_antes = len(correo_simulado.intentos)
    hash_antes = _hash_guardado(activa.cuenta.cedula)
    claves_antes = redis_controlable.claves()
    consultas_antes = len(consultas_a_cuentas)
    registros_del_servidor.clear()

    _poner_clave(monkeypatch, valor)
    respuestas = [r for caso in casos.values() for r in _tres_pasos(cliente_api, caso, nueva)]

    assert len(respuestas) == 9
    _comprobar_503_uniforme(respuestas)
    assert len(correo_simulado.intentos) == correos_antes, "con la clave inválida no puede salir ningún correo"
    assert len(consultas_a_cuentas) == consultas_antes, "con la clave inválida no se consulta la cuenta"
    assert redis_controlable.claves() == claves_antes, "con la clave inválida no se usa Redis para guardar nada"
    assert _hash_guardado(activa.cuenta.cedula) == hash_antes, "la contraseña no puede cambiar"
    inicio = _iniciar_sesion_con(cliente_api, activa.cuenta.correo, activa.cuenta.contrasena)
    assert inicio.status_code == 200 and "access_token" in inicio.json(), "el inicio de sesión sigue funcionando"

    lineas = [r.getMessage() for r in registros_del_servidor.records if r.levelno >= logging.ERROR]
    assert any("JWT_SECRET_KEY" in linea and motivo in linea for linea in lineas), (
        "el registro del servidor debe nombrar la variable JWT_SECRET_KEY y el motivo"
    )
    salida = capsys.readouterr()
    fuentes = {"registros": registros_del_servidor.text, "salida": salida.out + salida.err,
               "respuestas": [r.text for r in respuestas] + [inicio.text]}
    if valor:  # una clave ausente no tiene valor que buscar
        rastros.buscar_en_rastros(valor, **fuentes)
    rastros.buscar_en_rastros(clave_valida, **fuentes)
    for caso in casos.values():
        rastros.buscar_en_rastros(caso.correo, registros=fuentes["registros"], salida=fuentes["salida"])

    monkeypatch.setenv("JWT_SECRET_KEY", clave_valida)
    cambio = flujo.cambiar(cliente_api, activa.token_de_verificacion, nueva)
    assert (cambio.status_code, cambio.json()["message"]) == (200, MENSAJE_CAMBIADO)
    assert _iniciar_sesion_con(cliente_api, activa.cuenta.correo, nueva).status_code == 200


def test_redis_caido_y_clave_invalida_dan_exactamente_el_mismo_error(
    cliente_api, redis_controlable, monkeypatch, nueva_cuenta
):
    """RNF-07.3 y RF-03.20: el 503 no revela cuál de las dos causas ocurrió: mismo código, mismo cuerpo y mismos encabezados de
    contenido, en cada uno de los tres pasos."""
    cuenta = nueva_cuenta()
    clave_valida = os.environ["JWT_SECRET_KEY"]
    token = f"{secrets.token_urlsafe(16)}.{secrets.token_urlsafe(16)}"  # con la forma del token de la solicitud (22 + 22)
    pedidos = (
        lambda: flujo.solicitar(cliente_api, cuenta.correo),
        lambda: flujo.verificar(cliente_api, token, flujo.codigo_inventado()),
        lambda: flujo.cambiar(cliente_api, token, datos.generar_contrasena()),
    )

    redis_controlable.no_responde("conexion")
    por_redis = [pedido() for pedido in pedidos]
    redis_controlable.responder_bien()
    monkeypatch.setenv("JWT_SECRET_KEY", "")
    por_clave = [pedido() for pedido in pedidos]
    monkeypatch.setenv("JWT_SECRET_KEY", clave_valida)

    for uno, otro in zip(por_redis, por_clave):
        assert uno.status_code == otro.status_code == 503
        assert uno.content == otro.content
        assert uno.headers.get("content-type") == otro.headers.get("content-type")
        assert uno.headers.get("content-length") == otro.headers.get("content-length")
        assert uno.json() == CUERPO_503
