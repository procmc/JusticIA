"""Pruebas de T7 (spec 003b): el envío del código ocurre DESPUÉS de responder (RF-03.3), la respuesta uniforme no cambia
(RF-03.2) y la solicitud no responde 404 ni 429 (RF-03.22, paso 1).

RF-03.3 es determinista: no mide tiempo. La prueba llama a la aplicación por ASGI dentro de su propio bucle
(`llamar_asgi`, `tests/soporte/asgi.py`) con el envío del correo retenido (`correo_simulado.retener()`), y comprueba que la
respuesta llega ANTES de liberarlo, que en los casos con envío este ya fue invocado y sigue pendiente, y que solo al
liberarlo termina la tarea posterior. El `TestClient` y `httpx` no sirven para esto: devuelven la respuesta cuando la
aplicación terminó, tareas posteriores incluidas (una de las pruebas de abajo lo confirma). La única espera real es una cota
de seguridad de 3 s: si se agota, la prueba falla. La medición con `curl -w` entre casos es manual (T10).

Qué comprueban de lo REGISTRADO, con el registro de bitácora heredado que sigue vigente hasta T9:
- La fila de bitácora de la solicitud existe al terminar la aplicación, aunque la sesión de la petición ya se cerró, y NO
  existe mientras el envío está retenido (se registra al terminar el envío, no antes).
- El resultado (`código enviado`, `envío fallido`, `correo no registrado`, `cuenta inactiva`, `límite alcanzado`) queda en el
  registro del servidor, que es donde se escribe hoy. La bitácora heredada no lleva el resultado: que lo traiga la fila es de
  T9 (`test_recuperacion_bitacora.py`).
- El código no aparece en la respuesta, las filas de bitácora, el registro del servidor ni la salida; el correo completo no
  aparece en la respuesta, el registro del servidor ni la salida. En las filas de bitácora el correo de la solicitud SÍ
  aparece (el Historial lo muestra al Administrador, plan §6); de ese lado, que no lleve nada más, lo prueba T9.

Usan la base `servia_pruebas`, el correo y el Redis simulados: nada sale de la prueba. Las cuentas son `PRUEBA`; las contraseñas
y los códigos los genera la suite y el código real se lee del correo simulado y nunca se imprime. Todo correo de prueba sin
cuenta lleva «prueba» para que la limpieza por texto borre sus filas de bitácora.
"""
import asyncio
import logging

import aiosmtplib
import pytest
from sqlalchemy import text

from tests.soporte import asgi, datos, rastros
from tests.soporte import flujo_recuperacion as flujo

MENSAJE_DEL_ERS = "Si el correo existe en nuestro sistema, recibirás un email con las instrucciones"
MENSAJE_CORREO_INVALIDO = "Ingresa un correo electrónico válido"
CAMPOS_DE_LA_RESPUESTA = ["success", "message", "token"]
TIPO_RECUPERACION = 6  # TiposAccion.RECUPERACION_CONTRASENA
COTA = 3.0  # segundos REALES: solo una red de seguridad; si se agota, la prueba falla


# --- Apoyo --------------------------------------------------------------------------------------------------------------

def _filas_de_bitacora(correo):
    """Las filas de recuperación que nombran ese correo (la solicitud lo lleva), como tuplas `(texto, información)`."""
    from app.db.database import engine

    with engine.connect() as conexion:
        filas = conexion.execute(
            text(
                "SELECT CT_Texto, CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_tipo_accion = :t "
                "AND (CT_Texto LIKE :m OR CT_Informacion_adicional LIKE :m) ORDER BY CN_Id_bitacora"
            ),
            {"t": TIPO_RECUPERACION, "m": f"%{correo}%"},
        ).fetchall()
    return [tuple(fila) for fila in filas]


def _total_de_filas_de_recuperacion():
    from app.db.database import engine

    with engine.connect() as conexion:
        return conexion.execute(
            text("SELECT COUNT(*) FROM T_Bitacora WHERE CN_Id_tipo_accion = :t"), {"t": TIPO_RECUPERACION}
        ).scalar()


async def _esperar(esperable, que):
    """Espera hasta `COTA` s reales; si se agota, la prueba falla diciendo qué esperaba (sin tokens ni códigos)."""
    try:
        return await asyncio.wait_for(esperable, COTA)
    except asyncio.TimeoutError:
        raise AssertionError(f"Se agotó la cota de {COTA:g} s reales esperando {que}.") from None


class _Visto:
    """Lo que la prueba observó en una solicitud hecha con el envío retenido."""


async def _solicitar_con_el_envio_retenido(llamar_asgi, correo_simulado, correo, *, con_envio, error_del_envio=None):
    """Hace la solicitud con el envío retenido y anota lo que se ve ANTES y DESPUÉS de liberarlo.

    1. Retiene el envío y llama a la aplicación por ASGI.
    2. Espera la respuesta (sin liberar nada): si la ruta esperara el envío, aquí se agota la cota y la prueba falla.
    3. Con envío, espera a que la aplicación lo invoque y anota que sigue pendiente; sin envío, la aplicación debe terminar sola.
    4. Recién entonces libera el envío (con error si se pide) y espera a que termine la aplicación completa.
    """
    visto = _Visto()
    visto.intentos_antes = len(correo_simulado.intentos)
    visto.filas_antes = len(_filas_de_bitacora(correo))
    correo_simulado.retener()
    llamada = llamar_asgi("POST", flujo.RUTA_SOLICITAR, json={"email": correo})

    visto.respuesta = await _esperar(llamada.respuesta, "la respuesta de la solicitud con el envío retenido")
    if con_envio:
        if not await correo_simulado.esperar_retenido(COTA):
            raise AssertionError(f"Se agotó la cota de {COTA:g} s reales esperando que la aplicación invocara el envío.")
        visto.tarea_pendiente = not llamada.tarea.done()
    else:
        await _esperar(llamada.tarea, "que la aplicación termine sola (no hay envío que esperar)")
        visto.tarea_pendiente = False
    visto.invocados = len(correo_simulado.intentos) - visto.intentos_antes
    visto.retenidos = correo_simulado.envios_retenidos
    visto.filas_antes_de_liberar = len(_filas_de_bitacora(correo))

    correo_simulado.liberar(error_del_envio)
    await _esperar(llamada.tarea, "que la aplicación termine después de liberar el envío")
    visto.retenidos_al_terminar = correo_simulado.envios_retenidos
    visto.filas = _filas_de_bitacora(correo)
    return visto


def _comprobar_respuesta_uniforme(visto):
    """La respuesta del caso: 200, los tres campos en su orden, el mensaje del ERS y un token."""
    forma = flujo.normalizar_para_comparar(visto.respuesta)
    assert forma["estado"] == 200
    assert forma["campos"] == CAMPOS_DE_LA_RESPUESTA
    assert forma["mensaje"] == MENSAJE_DEL_ERS
    assert set(forma["tokens"]) == {"token"} and forma["tokens"]["token"] is not None


def _comprobar_lo_registrado(visto, correo, correo_simulado, caplog, capsys, resultado, con_codigo):
    """Lo registrado: la fila de bitácora, el resultado en el registro del servidor y ni el código ni el correo completo.

    Ver el docstring del módulo: el resultado va hoy en el registro del servidor y la bitácora lo traerá en T9.
    """
    assert len(visto.filas) == visto.filas_antes + 1, "la solicitud debe dejar una fila de bitácora al terminar"
    registros = caplog.text
    assert resultado in registros, "el resultado de la solicitud debe quedar en el registro del servidor"
    salida = capsys.readouterr()
    sin_el_correo = {"respuesta": visto.respuesta.text, "registros": registros, "salida": salida.out + salida.err}
    rastros.buscar_en_rastros(correo, **sin_el_correo)
    if con_codigo:
        codigo = flujo.codigo_enviado(correo_simulado)
        # Control positivo: el código sí está en el correo, así que la búsqueda de abajo no es en vacío.
        assert rastros.encontrar_en_rastros(codigo, correo=correo_simulado.contenido_real().texto) == ["correo"]
        rastros.buscar_en_rastros(codigo, bitacora=visto.filas, **sin_el_correo)


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


# --- RF-03.3: la respuesta llega antes de que termine el envío, una prueba por caso --------------------------------------------

def test_cuenta_activa_responde_antes_de_que_termine_el_envio(
    llamar_asgi, correo_simulado, nueva_cuenta, registros_del_servidor, capsys
):
    """RF-03.3 y RF-21.1: con el envío retenido, la respuesta llega 200 y el envío ya fue invocado y sigue pendiente; sin fila de
    bitácora todavía. Al liberarlo, la aplicación termina y la fila existe aunque la sesión de la petición ya se cerró."""
    cuenta = nueva_cuenta()

    visto = asyncio.run(_solicitar_con_el_envio_retenido(llamar_asgi, correo_simulado, cuenta.correo, con_envio=True))

    _comprobar_respuesta_uniforme(visto)
    assert (visto.invocados, visto.retenidos, visto.tarea_pendiente) == (1, 1, True)
    assert visto.filas_antes_de_liberar == visto.filas_antes, "la solicitud se registra al terminar el envío, no antes"
    assert visto.retenidos_al_terminar == 0
    _comprobar_lo_registrado(visto, cuenta.correo, correo_simulado, registros_del_servidor, capsys, "código enviado", True)


def test_correo_no_registrado_responde_igual_y_no_invoca_ningun_envio(
    llamar_asgi, correo_simulado, registros_del_servidor, capsys
):
    """RF-03.3 y RF-03.2: un correo sin cuenta recibe la misma respuesta; el envío no se invoca y la aplicación termina sola."""
    correo = flujo.correo_sin_cuenta()

    visto = asyncio.run(_solicitar_con_el_envio_retenido(llamar_asgi, correo_simulado, correo, con_envio=False))

    _comprobar_respuesta_uniforme(visto)
    assert (visto.invocados, visto.retenidos) == (0, 0)
    assert correo_simulado.intentos == []
    _comprobar_lo_registrado(visto, correo, correo_simulado, registros_del_servidor, capsys, "correo no registrado", False)


def test_cuenta_inactiva_responde_igual_y_no_invoca_ningun_envio(
    llamar_asgi, correo_simulado, cuenta_inactiva, registros_del_servidor, capsys
):
    """RF-03.3, RF-03.2 y RF-03.5: una cuenta Inactiva recibe la misma respuesta; el envío no se invoca."""
    visto = asyncio.run(
        _solicitar_con_el_envio_retenido(llamar_asgi, correo_simulado, cuenta_inactiva.correo, con_envio=False)
    )

    _comprobar_respuesta_uniforme(visto)
    assert (visto.invocados, visto.retenidos) == (0, 0)
    assert correo_simulado.intentos == []
    _comprobar_lo_registrado(
        visto, cuenta_inactiva.correo, correo_simulado, registros_del_servidor, capsys, "cuenta inactiva", False
    )


def test_envio_fallido_responde_antes_de_fallar_y_el_fallo_queda_registrado(
    llamar_asgi, correo_simulado, nueva_cuenta, registros_del_servidor, capsys
):
    """RF-03.3, RF-03.2 y RF-21.1: con el envío retenido, la respuesta llega 200 antes de que el envío falle; el envío ya fue
    invocado y sigue pendiente. Se libera CON error y el fallo (`envío fallido`) queda registrado al terminar."""
    cuenta = nueva_cuenta()
    error = aiosmtplib.SMTPConnectError("PRUEBA: el servidor de correo no responde (simulado)")

    visto = asyncio.run(
        _solicitar_con_el_envio_retenido(
            llamar_asgi, correo_simulado, cuenta.correo, con_envio=True, error_del_envio=error
        )
    )

    _comprobar_respuesta_uniforme(visto)
    assert (visto.invocados, visto.retenidos, visto.tarea_pendiente) == (1, 1, True)
    assert visto.filas_antes_de_liberar == visto.filas_antes
    _comprobar_lo_registrado(visto, cuenta.correo, correo_simulado, registros_del_servidor, capsys, "envío fallido", True)


def test_limite_alcanzado_responde_igual_y_no_invoca_un_segundo_envio(
    llamar_asgi, correo_simulado, nueva_cuenta, registros_del_servidor, capsys
):
    """RF-03.3, RF-03.2 y RF-03.10: la segunda solicitud de la misma cuenta dentro del minuto (límite alcanzado) recibe la misma
    respuesta; no se invoca un segundo envío y la aplicación termina sola."""
    cuenta = nueva_cuenta()

    async def escenario():
        primera = await _solicitar_con_el_envio_retenido(llamar_asgi, correo_simulado, cuenta.correo, con_envio=True)
        segunda = await _solicitar_con_el_envio_retenido(llamar_asgi, correo_simulado, cuenta.correo, con_envio=False)
        return primera, segunda

    primera, segunda = asyncio.run(escenario())

    _comprobar_respuesta_uniforme(segunda)
    assert flujo.normalizar_para_comparar(segunda.respuesta) == flujo.normalizar_para_comparar(primera.respuesta)
    assert (segunda.invocados, segunda.retenidos) == (0, 0)
    assert len(correo_simulado.intentos) == 1, "solo la primera solicitud envía un correo"
    assert len(segunda.filas) == 2, "cada solicitud deja su fila de bitácora"
    registros = registros_del_servidor.text
    assert "límite alcanzado" in registros
    rastros.buscar_en_rastros(cuenta.correo, respuesta=segunda.respuesta.text, registros=registros)


# --- RF-03.2 otra vez: los cinco casos, con el envío después de responder ---------------------------------------------------------

def test_los_cinco_casos_responden_igual_con_el_envio_pendiente(
    llamar_asgi, correo_simulado, nueva_cuenta, cuenta_inactiva, registros_del_servidor
):
    """RF-03.2 con RF-03.3: cuenta Activa, correo no registrado, cuenta Inactiva, envío fallido y límite alcanzado responden 200
    con los mismos campos en el mismo orden, el mismo mensaje y un token de la misma forma, todos con el envío retenido."""
    activa, con_envio_fallido, sin_cuenta = nueva_cuenta(), nueva_cuenta(), flujo.correo_sin_cuenta()
    error = aiosmtplib.SMTPConnectError("PRUEBA: el servidor de correo no responde (simulado)")

    async def escenario():
        formas = {}
        for nombre, correo, con_envio, fallo in (
            ("activa", activa.correo, True, None),
            ("limite", activa.correo, False, None),
            ("no_registrada", sin_cuenta, False, None),
            ("inactiva", cuenta_inactiva.correo, False, None),
            ("envio_fallido", con_envio_fallido.correo, True, error),
        ):
            visto = await _solicitar_con_el_envio_retenido(
                llamar_asgi, correo_simulado, correo, con_envio=con_envio, error_del_envio=fallo
            )
            formas[nombre] = flujo.normalizar_para_comparar(visto.respuesta)
        return formas

    formas = asyncio.run(escenario())

    assert formas["activa"]["estado"] == 200 and formas["activa"]["mensaje"] == MENSAJE_DEL_ERS
    distintos = [nombre for nombre in formas if formas[nombre] != formas["activa"]]
    assert distintos == [], f"casos que se distinguen de la cuenta Activa: {distintos}"
    assert len(correo_simulado.intentos) == 2, "solo la cuenta Activa y la del envío fallido intentaron enviar un correo"


# --- RF-03.22 (paso 1): nunca 404 ni 429; la entrada inválida da 400 ---------------------------------------------------------------

def test_la_solicitud_nunca_responde_404_ni_429_ni_con_el_limite_por_hora_alcanzado(
    cliente_api, correo_simulado, redis_controlable, nueva_cuenta, cuenta_inactiva
):
    """RF-03.22: el paso 1 responde siempre 200 para un correo bien formado: con cuenta Activa, Inactiva o sin cuenta, y también
    cuando se alcanza el límite de 5 solicitudes por hora. Control positivo: solo salieron cinco correos."""
    activa, sin_cuenta = nueva_cuenta(), flujo.correo_sin_cuenta()
    estados = []

    for _ in range(7):  # 5 aceptadas y 2 por encima del límite por hora
        estados.append(flujo.solicitar(cliente_api, activa.correo).status_code)
        redis_controlable.avanzar(61)  # supera el bloqueo de un minuto entre solicitudes
    estados.append(flujo.solicitar(cliente_api, sin_cuenta).status_code)
    estados.append(flujo.solicitar(cliente_api, cuenta_inactiva.correo).status_code)

    assert estados == [200] * 9
    assert len(correo_simulado.intentos) == 5, "el límite por hora debió dejar sin correo a la sexta y la séptima solicitudes"


@pytest.mark.parametrize("cuerpo", [{"email": ""}, {"email": "sin-arroba"}, {"email": "a" * 101 + "@prueba.invalid"}, {}])
def test_una_entrada_invalida_responde_400_sin_envio_ni_fila_de_bitacora(llamar_asgi, correo_simulado, cuerpo):
    """RF-03.22 y RF-03.12: correo vacío, mal formado, de más de 100 caracteres o ausente: 400 con el mensaje en español, sin
    invocar el envío y sin fila de bitácora (no cuenta para los límites ni se registra)."""
    filas_antes = _total_de_filas_de_recuperacion()

    async def escenario():
        correo_simulado.retener()
        llamada = llamar_asgi("POST", flujo.RUTA_SOLICITAR, json=cuerpo)
        respuesta = await _esperar(llamada.respuesta, "la respuesta a una entrada inválida")
        await _esperar(llamada.tarea, "que la aplicación termine sola")
        return respuesta

    respuesta = asyncio.run(escenario())

    assert respuesta.status_code == 400
    assert respuesta.json() == {"detail": MENSAJE_CORREO_INVALIDO}
    assert correo_simulado.intentos == []
    assert _total_de_filas_de_recuperacion() == filas_antes


# --- El soporte: `asgi.llamar` y la fixture `llamar_asgi` --------------------------------------------------------------------------

def _aplicacion_con_tarea_posterior(espera, marcas):
    """Una aplicación Starlette mínima cuya respuesta lleva una tarea posterior que espera `espera` (o termina enseguida)."""
    from starlette.applications import Starlette
    from starlette.background import BackgroundTask
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def tarea_posterior():
        if espera is not None:
            await espera.wait()
        marcas.append("tarea posterior terminada")

    async def eco(peticion):
        cuerpo = await peticion.json()
        return JSONResponse(
            {"eco": cuerpo, "cabecera": peticion.headers.get("x-prueba")}, background=BackgroundTask(tarea_posterior)
        )

    return Starlette(routes=[Route("/eco", eco, methods=["POST"])])


def test_llamar_devuelve_la_respuesta_mientras_la_tarea_posterior_sigue_pendiente():
    """RF-03.3 (soporte): `asgi.llamar` resuelve `respuesta` al llegar el cuerpo, con la tarea posterior todavía sin terminar, y
    `tarea` termina cuando esa tarea posterior termina. Lleva el cuerpo JSON y las cabeceras a la aplicación."""
    marcas = []

    async def escenario():
        senal = asyncio.Event()
        llamada = asgi.llamar(
            _aplicacion_con_tarea_posterior(senal, marcas), "POST", "/eco", json={"a": 1}, cabeceras={"X-Prueba": "valor"}
        )
        respuesta = await _esperar(llamada.respuesta, "la respuesta de la aplicación de ejemplo")
        antes = (llamada.tarea.done(), list(marcas))
        senal.set()
        await _esperar(llamada.tarea, "que termine la tarea posterior")
        return respuesta, antes

    respuesta, antes = asyncio.run(escenario())

    assert respuesta.status_code == 200
    assert respuesta.json() == {"eco": {"a": 1}, "cabecera": "valor"}
    assert "application/json" in respuesta.headers["content-type"]
    assert antes == (False, []), "la respuesta debe llegar con la tarea posterior sin terminar"
    assert marcas == ["tarea posterior terminada"]


def test_llamar_propaga_el_error_de_la_aplicacion_por_tarea_y_por_respuesta():
    """RF-03.3 (soporte): si la aplicación falla antes de responder, `respuesta` y `tarea` fallan con ese error; no se queda esperando."""

    async def aplicacion_rota(scope, receive, send):
        raise RuntimeError("PRUEBA: la aplicación falló (simulado)")

    async def escenario():
        llamada = asgi.llamar(aplicacion_rota, "GET", "/")
        with pytest.raises(RuntimeError):
            await _esperar(llamada.respuesta, "el fallo de la aplicación")
        with pytest.raises(RuntimeError):
            await _esperar(llamada.tarea, "el fallo de la aplicación")

    asyncio.run(escenario())


def test_llamar_fuera_de_un_bucle_de_eventos_da_un_error_claro():
    """RF-03.3 (soporte): `asgi.llamar` solo funciona dentro del bucle de la prueba; fuera de uno lo dice en español."""
    with pytest.raises(RuntimeError, match="bucle"):
        asgi.llamar(lambda *argumentos: None, "GET", "/")


def test_el_cliente_de_pruebas_normal_espera_la_tarea_posterior_antes_de_devolver_la_respuesta():
    """Premisa de la decisión 11 del plan: el `TestClient` y `httpx` devuelven la respuesta cuando la aplicación terminó, tareas
    posteriores incluidas. Por eso RF-03.3 se prueba con `asgi.llamar`: con ellos no se vería «respondió y sigue pendiente»."""
    from fastapi.testclient import TestClient
    import httpx

    marcas_cliente, marcas_httpx = [], []

    TestClient(_aplicacion_con_tarea_posterior(None, marcas_cliente)).post("/eco", json={"a": 1})

    async def con_httpx():
        transporte = httpx.ASGITransport(app=_aplicacion_con_tarea_posterior(None, marcas_httpx))
        async with httpx.AsyncClient(transport=transporte, base_url="http://prueba") as cliente:
            await cliente.post("/eco", json={"a": 1})

    asyncio.run(con_httpx())

    assert marcas_cliente == ["tarea posterior terminada"]
    assert marcas_httpx == ["tarea posterior terminada"]


def test_la_fixture_llamar_asgi_llama_a_la_aplicacion_real(llamar_asgi):
    """RF-03.3 (soporte): `llamar_asgi` entra por la aplicación real del sistema (`main.app`): su raíz responde 200 y una ruta
    que no existe, 404, igual que por HTTP."""

    async def escenario():
        raiz = llamar_asgi("GET", "/")
        inexistente = llamar_asgi("GET", "/ruta-que-no-existe")
        respuestas = [await _esperar(raiz.respuesta, "la raíz"), await _esperar(inexistente.respuesta, "la ruta inexistente")]
        await _esperar(raiz.tarea, "que termine la raíz")
        await _esperar(inexistente.tarea, "que termine la ruta inexistente")
        return respuestas

    raiz, inexistente = asyncio.run(escenario())

    assert raiz.status_code == 200 and isinstance(raiz.json(), dict)
    assert inexistente.status_code == 404


# --- El soporte: `CorreoSimulado.retener()` y `liberar()` --------------------------------------------------------------------------

def _mensaje():
    from email.message import EmailMessage

    mensaje = EmailMessage()
    mensaje["To"] = "destino.prueba@prueba.invalid"
    mensaje["Subject"] = "Asunto PRUEBA"
    mensaje.set_content("cuerpo PRUEBA")
    return mensaje


def test_retener_deja_el_envio_pendiente_y_liberar_sin_error_lo_termina_bien(correo_simulado):
    """RF-03.3 (soporte): con `retener()`, el envío queda registrado como intento pero pendiente; `liberar()` lo termina como un
    envío correcto. Lo que se envía después de liberar ya no se retiene."""

    async def escenario():
        correo_simulado.retener()
        envio = asyncio.ensure_future(aiosmtplib.send(_mensaje(), timeout=15))
        invocado = await correo_simulado.esperar_retenido(COTA)
        pendiente = (len(correo_simulado.intentos), correo_simulado.envios_retenidos, envio.done())
        correo_simulado.liberar()
        resultado = await _esperar(envio, "que termine el envío liberado")
        siguiente = await _esperar(aiosmtplib.send(_mensaje()), "un envío posterior sin retención")
        return invocado, pendiente, resultado, siguiente

    invocado, pendiente, resultado, siguiente = asyncio.run(escenario())

    assert invocado is True
    assert pendiente == (1, 1, False)
    assert resultado == ({}, "OK (simulado)")
    assert siguiente == ({}, "OK (simulado)")
    assert (len(correo_simulado.intentos), correo_simulado.envios_retenidos) == (2, 0)
    assert correo_simulado.tiempos_maximos == [15, None]


def test_liberar_con_error_hace_que_el_envio_retenido_falle(correo_simulado):
    """RF-03.3 (soporte): `liberar(error)` hace que el envío retenido lance ese error, como un servidor que cae mientras se envía."""
    error = aiosmtplib.SMTPConnectError("PRUEBA: el servidor de correo no responde (simulado)")

    async def escenario():
        correo_simulado.retener()
        envio = asyncio.ensure_future(aiosmtplib.send(_mensaje()))
        await correo_simulado.esperar_retenido(COTA)
        correo_simulado.liberar(error)
        with pytest.raises(aiosmtplib.SMTPConnectError):
            await _esperar(envio, "que falle el envío liberado con error")

    asyncio.run(escenario())

    assert (len(correo_simulado.intentos), correo_simulado.envios_retenidos) == (1, 0)


def test_liberar_suelta_todos_los_envios_retenidos_y_sin_retener_no_hace_nada(correo_simulado):
    """RF-03.3 (soporte): `liberar()` suelta todos los envíos retenidos a la vez; y llamarlo sin haber retenido no falla."""
    correo_simulado.liberar()  # sin retención: no hace nada

    async def escenario():
        correo_simulado.retener()
        envios = [asyncio.ensure_future(aiosmtplib.send(_mensaje())) for _ in range(3)]
        for _ in range(100):  # los tres llegan a su espera en pocas vueltas del bucle; la cota real evita colgarse
            if correo_simulado.envios_retenidos == 3:
                break
            await asyncio.sleep(0)
        antes = correo_simulado.envios_retenidos
        correo_simulado.liberar()
        resultados = [await _esperar(envio, "que termine un envío liberado") for envio in envios]
        return antes, resultados

    antes, resultados = asyncio.run(escenario())

    assert antes == 3
    assert resultados == [({}, "OK (simulado)")] * 3
    assert correo_simulado.envios_retenidos == 0


def test_esperar_retenido_dice_que_no_si_ningun_envio_llega(correo_simulado):
    """RF-03.3 (soporte): `esperar_retenido` espera tiempo REAL, como máximo el indicado, y devuelve `False` si no llegó ningún envío."""
    correo_simulado.retener()

    llego = asyncio.run(correo_simulado.esperar_retenido(0.05))

    assert llego is False


def test_responder_bien_tambien_suelta_y_deja_de_retener(correo_simulado):
    """RF-03.3 (soporte): `responder_bien()` vuelve a la normalidad, incluida la retención: lo retenido termina y lo siguiente pasa."""

    async def escenario():
        correo_simulado.retener()
        envio = asyncio.ensure_future(aiosmtplib.send(_mensaje()))
        await correo_simulado.esperar_retenido(COTA)
        correo_simulado.responder_bien()
        primero = await _esperar(envio, "que termine el envío retenido")
        segundo = await _esperar(aiosmtplib.send(_mensaje()), "un envío posterior sin retención")
        return primero, segundo

    primero, segundo = asyncio.run(escenario())

    assert primero == ({}, "OK (simulado)") and segundo == ({}, "OK (simulado)")
    assert correo_simulado.envios_retenidos == 0
