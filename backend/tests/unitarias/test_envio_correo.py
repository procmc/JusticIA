"""Pruebas de T4 (spec 003a): el servicio de correo con tiempo máximo, causas de fallo y UTF-8.

Cubre RF-03.16 (15 s en total, configurable con `EMAIL_TIMEOUT`), RF-03.17 (cada causa de fallo se trata
como envío fallido, se clasifica en el registro y nunca deja el texto del error, la clave ni el correo
completo; RNF-08.2 en los registros del servicio de correo) y RF-03.18 (UTF-8 en el mensaje tal como viaja).

Los plazos se miden con el reloj controlable (tiempo virtual): ninguna prueba espera tiempo real, y la
fixture automática de este archivo falla cualquier prueba que tarde 5 s o más. Datos inventados (prefijo
`PRUEBA`, dominios `.invalid`); el correo es siempre el simulado, nunca un servidor real.
"""
import asyncio
import contextlib
import email
import email.policy
import logging
import os
import time

import aiosmtplib
import pytest

CLAVE = "PRUEBA-clave-envio-5521"
DESTINO = "persona.prueba@prueba.invalid"
REMITENTE = "remitente.prueba@prueba.invalid"
NOMBRE = "PRUEBA Peña Núñez"
TEXTO_DEL_SERVIDOR = f"550 PRUEBA-detalle-del-servidor-7731 clave={CLAVE} para {DESTINO}"


@pytest.fixture(autouse=True)
def _sin_esperas_reales():
    """RF-03.16 (d): ninguna prueba de plazos tarda 5 s reales o más; los plazos son tiempo virtual."""
    inicio = time.perf_counter()
    yield
    assert time.perf_counter() - inicio < 5, "Una prueba de plazos esperó tiempo real."


def _config(**cambios):
    """Una cuenta de correo inventada y válida; cada prueba cambia solo lo que necesita."""
    from app.email.core.email_service import EmailConfig

    valores = dict(host="smtp.prueba.invalid", port=2525, username=REMITENTE, password=CLAVE, use_tls=False)
    valores.update(cambios)
    return EmailConfig(**valores)


def _servicio(**cambios):
    from app.email.core.email_service import EmailService

    return EmailService(_config(**cambios))


async def _terminar(tarea: "asyncio.Future") -> None:
    """Cancela una tarea que la prueba dejó pendiente (si la prueba falló antes de que terminara)."""
    if not tarea.done():
        tarea.cancel()
    with contextlib.suppress(asyncio.CancelledError, Exception):
        await tarea


# --- RF-03.16 (a): el tiempo máximo que recibe el envío -------------------------------------------------

def _enviar_con_la_configuracion_del_entorno(correo_simulado) -> list:
    from app.email.core.email_service import EmailService, get_email_config_from_env

    servicio = EmailService(get_email_config_from_env())
    assert asyncio.run(servicio.send_email(DESTINO, "Asunto PRUEBA", "<p>hola</p>", "hola")) is True
    return correo_simulado.tiempos_maximos


def test_el_tiempo_maximo_por_omision_es_de_15_segundos(correo_simulado, monkeypatch, caplog):
    """RF-03.16 (a): sin `EMAIL_TIMEOUT` el simulado recibe `timeout` 15, sin advertencias."""
    from app.email.core.email_service import get_email_config_from_env

    monkeypatch.delenv("EMAIL_TIMEOUT", raising=False)
    caplog.set_level(logging.DEBUG)

    assert get_email_config_from_env().timeout == 15
    assert _enviar_con_la_configuracion_del_entorno(correo_simulado) == [15]
    assert "EMAIL_TIMEOUT" not in caplog.text


def test_el_tiempo_maximo_se_cambia_con_email_timeout(correo_simulado, monkeypatch):
    """RF-03.16 (a): `EMAIL_TIMEOUT` fija el `timeout` con que se llama al envío."""
    monkeypatch.setenv("EMAIL_TIMEOUT", "7.5")

    assert _enviar_con_la_configuracion_del_entorno(correo_simulado) == [7.5]


@pytest.mark.parametrize("proveedor", ["gmail", "outlook", "custom"])
def test_email_timeout_se_lee_con_cualquier_proveedor(proveedor, monkeypatch):
    """RF-03.16: el tiempo máximo no depende de qué proveedor esté configurado."""
    from app.email.core.email_service import get_email_config_from_env

    monkeypatch.setenv("EMAIL_PROVIDER", proveedor)
    monkeypatch.setenv("EMAIL_TIMEOUT", "9")

    assert get_email_config_from_env().timeout == 9


@pytest.mark.parametrize("valor", ["", "abc", "0", "-5", "nan", "inf"])
def test_un_email_timeout_invalido_usa_15_y_deja_una_advertencia_que_nombra_la_variable(
        valor, correo_simulado, monkeypatch, caplog):
    """RF-03.16 (a): vacío, no numérico, ≤ 0, `nan` o infinito -> 15 s y advertencia con el nombre de la variable."""
    from app.email.core.email_service import get_email_config_from_env

    monkeypatch.setenv("EMAIL_TIMEOUT", valor)
    caplog.set_level(logging.DEBUG)

    assert get_email_config_from_env().timeout == 15
    advertencias = [r for r in caplog.records if r.levelno == logging.WARNING and "EMAIL_TIMEOUT" in r.getMessage()]
    assert len(advertencias) == 1
    assert _enviar_con_la_configuracion_del_entorno(correo_simulado) == [15]


def test_la_advertencia_de_un_email_timeout_invalido_no_repite_el_valor(monkeypatch, caplog):
    """RF-03.16: la advertencia nombra la variable pero no repite lo que escribieron en ella."""
    from app.email.core.email_service import get_email_config_from_env

    monkeypatch.setenv("EMAIL_TIMEOUT", "valor-PRUEBA-raro")
    caplog.set_level(logging.DEBUG)

    get_email_config_from_env()

    assert "valor-PRUEBA-raro" not in caplog.text


def test_la_configuracion_directa_trae_15_segundos_por_omision():
    """RF-03.16: una `EmailConfig` armada a mano también lleva el límite de 15 s."""
    assert _config().timeout == 15


# --- RF-03.16 (b), (c): el límite es de 15 s en total ---------------------------------------------------

def test_un_servidor_que_no_responde_sigue_pendiente_a_los_14_9_s_y_falla_a_los_15(correo_simulado, reloj_controlable):
    """RF-03.16 (b): pendiente a los 14,9 s, `False` a los 15,0 s y la espera interna cancelada."""
    correo_simulado.no_responde()

    async def escenario():
        tarea = asyncio.ensure_future(_servicio().send_email(DESTINO, "Asunto PRUEBA", "<p>hola</p>", "hola"))
        try:
            await reloj_controlable.avanzar(14.9)
            assert not tarea.done()
            await reloj_controlable.avanzar(0.1)
            assert tarea.done()
            return tarea.result()
        finally:
            await _terminar(tarea)

    assert asyncio.run(escenario()) is False
    assert correo_simulado.tiempos_maximos == [15]
    assert reloj_controlable.esperas_pendientes == 0


def test_un_servidor_que_no_responde_termina_como_fallido_a_mas_tardar_a_los_16_s(correo_simulado, reloj_controlable):
    """RF-03.16 (b): con el margen de 1 s del reloj controlable, a los 16 s el envío ya terminó como fallido."""
    correo_simulado.no_responde()

    async def escenario():
        tarea = asyncio.ensure_future(_servicio().send_email(DESTINO, "Asunto PRUEBA", "<p>hola</p>", "hola"))
        try:
            await reloj_controlable.avanzar(16)
            assert tarea.done()
            return tarea.result()
        finally:
            await _terminar(tarea)

    assert asyncio.run(escenario()) is False


def test_un_servidor_lento_en_cada_operacion_falla_a_los_15_s_aunque_ninguna_operacion_pase_de_5(
        correo_simulado, reloj_controlable):
    """RF-03.16 (c): cuatro operaciones de 5 s suman 20 s; el límite es TOTAL, así que falla a los 15 s."""
    correo_simulado.lento(reloj_controlable, 4, 5)

    async def escenario():
        tarea = asyncio.ensure_future(_servicio().send_email(DESTINO, "Asunto PRUEBA", "<p>hola</p>", "hola"))
        try:
            await reloj_controlable.avanzar(14.9)
            assert not tarea.done()
            await reloj_controlable.avanzar(0.1)
            assert tarea.done()
            return tarea.result()
        finally:
            await _terminar(tarea)

    assert asyncio.run(escenario()) is False
    # Control: el límite cortó el envío lento (no quedan esperas pendientes del servidor simulado).
    assert reloj_controlable.esperas_pendientes == 0


def test_un_servidor_lento_pero_dentro_del_limite_si_entrega(correo_simulado, reloj_controlable):
    """RF-03.16: control positivo: dos operaciones de 5 s (10 s en total) terminan bien a los 10 s."""
    correo_simulado.lento(reloj_controlable, 2, 5)

    async def escenario():
        tarea = asyncio.ensure_future(_servicio().send_email(DESTINO, "Asunto PRUEBA", "<p>hola</p>", "hola"))
        try:
            await reloj_controlable.avanzar(9.9)
            assert not tarea.done()
            await reloj_controlable.avanzar(0.1)
            assert tarea.done()
            return tarea.result()
        finally:
            await _terminar(tarea)

    assert asyncio.run(escenario()) is True


def test_el_limite_total_sigue_a_email_timeout(correo_simulado, reloj_controlable):
    """RF-03.16: con un tiempo máximo de 3 s el envío que no responde falla a los 3 s, no a los 15."""
    correo_simulado.no_responde()

    async def escenario():
        tarea = asyncio.ensure_future(_servicio(timeout=3).send_email(DESTINO, "Asunto PRUEBA", "<p>hola</p>"))
        try:
            await reloj_controlable.avanzar(2.9)
            assert not tarea.done()
            await reloj_controlable.avanzar(0.1)
            assert tarea.done()
            return tarea.result()
        finally:
            await _terminar(tarea)

    assert asyncio.run(escenario()) is False
    assert correo_simulado.tiempos_maximos == [3]


def test_el_servicio_usa_el_reloj_que_se_le_inyecta(correo_simulado, reloj_controlable):
    """RF-03.16 / RA-02.9: `EmailService(config, reloj=...)` mide el plazo con ese reloj y no con el del sistema."""
    from app.email.core.email_service import EmailService
    from tests.soporte.reloj import RelojControlable

    propio = RelojControlable()
    correo_simulado.no_responde()

    async def escenario():
        tarea = asyncio.ensure_future(
            EmailService(_config(), reloj=propio).send_email(DESTINO, "Asunto PRUEBA", "<p>hola</p>"))
        try:
            await propio.avanzar(0)          # cede el control: el envío registra su plazo
            registradas = (propio.esperas_pendientes, reloj_controlable.esperas_pendientes)
            await reloj_controlable.avanzar(30)   # el reloj del sistema no manda en este servicio
            sigue_pendiente = not tarea.done()
            await propio.avanzar(15)
            return registradas, sigue_pendiente, tarea.done(), tarea.result() if tarea.done() else None
        finally:
            await _terminar(tarea)

    registradas, sigue_pendiente, termino, resultado = asyncio.run(escenario())
    assert registradas == (1, 0)
    assert sigue_pendiente is True
    assert termino is True and resultado is False


# --- RF-03.17: cada causa de fallo -> False, causa clasificada, sin secretos en el registro --------------

def _causas():
    return [
        pytest.param(lambda t: aiosmtplib.SMTPDataError(554, t), "servidor", "SMTPDataError", id="error_del_servidor"),
        pytest.param(lambda t: aiosmtplib.SMTPException(t), "servidor", "SMTPException", id="smtp_generico"),
        pytest.param(lambda t: aiosmtplib.SMTPRecipientRefused(550, t, DESTINO), "rechazo", "SMTPRecipientRefused",
                     id="rechazo_del_destinatario"),
        pytest.param(lambda t: aiosmtplib.SMTPRecipientsRefused([aiosmtplib.SMTPRecipientRefused(550, t, DESTINO)]),
                     "rechazo", "SMTPRecipientsRefused", id="rechazo_de_todos_los_destinatarios"),
        pytest.param(lambda t: aiosmtplib.SMTPSenderRefused(553, t, REMITENTE), "rechazo", "SMTPSenderRefused",
                     id="rechazo_del_remitente"),
        pytest.param(lambda t: aiosmtplib.SMTPAuthenticationError(535, t), "autenticacion",
                     "SMTPAuthenticationError", id="autenticacion"),
        pytest.param(lambda t: aiosmtplib.SMTPConnectError(t), "conexion", "SMTPConnectError", id="conexion_rechazada"),
        pytest.param(lambda t: ConnectionRefusedError(t), "conexion", "ConnectionRefusedError",
                     id="conexion_rechazada_del_sistema"),
        pytest.param(lambda t: aiosmtplib.SMTPServerDisconnected(t), "conexion", "SMTPServerDisconnected",
                     id="servidor_desconectado"),
        pytest.param(lambda t: OSError(t), "conexion", "OSError", id="error_de_red"),
        pytest.param(lambda t: aiosmtplib.SMTPTimeoutError(t), "tiempo_agotado", "SMTPTimeoutError",
                     id="tiempo_agotado_de_la_libreria"),
        pytest.param(lambda t: aiosmtplib.SMTPConnectTimeoutError(t), "tiempo_agotado", "SMTPConnectTimeoutError",
                     id="tiempo_agotado_al_conectar"),
        pytest.param(lambda t: TimeoutError(t), "tiempo_agotado", "TimeoutError", id="tiempo_agotado_del_sistema"),
        pytest.param(lambda t: RuntimeError(t), "inesperado", "RuntimeError", id="error_inesperado"),
    ]


def _comprobar_que_el_registro_no_filtra(caplog, capsys) -> None:
    """RF-03.17, RNF-08.2: ni el texto del error, ni la clave, ni el correo completo, en ninguna salida."""
    from app.utils.enmascarar import enmascarar_correo

    salida = capsys.readouterr()
    todo = caplog.text + salida.out + salida.err
    for secreto in (TEXTO_DEL_SERVIDOR, "PRUEBA-detalle-del-servidor-7731", CLAVE, os.environ["EMAIL_PASSWORD"],
                    DESTINO, REMITENTE):
        assert secreto not in todo
    assert enmascarar_correo(DESTINO) in caplog.text
    assert "Traceback" not in todo  # una traza repetiría el texto del error


@pytest.mark.parametrize("fabricar, causa, tipo", _causas())
def test_cada_causa_de_fallo_devuelve_false_y_deja_la_causa_clasificada_sin_secretos(
        fabricar, causa, tipo, correo_simulado, caplog, capsys):
    """RF-03.17: no lanza, devuelve `False`; el registro dice la causa y el tipo, nunca `str(error)`."""
    correo_simulado.fallar(fabricar(TEXTO_DEL_SERVIDOR))
    caplog.set_level(logging.DEBUG)

    resultado = asyncio.run(_servicio().send_email(DESTINO, "Asunto PRUEBA", "<p>hola</p>", "hola"))

    assert resultado is False
    assert len(correo_simulado.intentos) == 1
    registros = [r for r in caplog.records if r.name.startswith("app.email")]
    assert len(registros) == 1
    assert f"causa={causa}" in registros[0].getMessage()
    assert f"tipo={tipo}" in registros[0].getMessage()
    _comprobar_que_el_registro_no_filtra(caplog, capsys)


def test_el_tiempo_agotado_por_el_limite_de_15_s_queda_clasificado_como_tiempo_agotado(
        correo_simulado, reloj_controlable, caplog, capsys):
    """RF-03.17: el corte del límite total también se clasifica (la causa «tiempo agotado» de la spec)."""
    correo_simulado.no_responde()
    caplog.set_level(logging.DEBUG)

    async def escenario():
        tarea = asyncio.ensure_future(_servicio().send_email(DESTINO, "Asunto PRUEBA", "<p>hola</p>"))
        try:
            await reloj_controlable.avanzar(15)
            return tarea.result() if tarea.done() else None
        finally:
            await _terminar(tarea)

    assert asyncio.run(escenario()) is False
    mensaje = [r.getMessage() for r in caplog.records if r.name.startswith("app.email")][0]
    assert "causa=tiempo_agotado" in mensaje and "tipo=TimeoutError" in mensaje
    _comprobar_que_el_registro_no_filtra(caplog, capsys)


@pytest.mark.parametrize("cambio", [
    pytest.param({"host": ""}, id="sin_servidor"),
    pytest.param({"username": ""}, id="sin_usuario"),
    pytest.param({"password": ""}, id="sin_clave"),
    pytest.param({"host": "", "username": "", "password": ""}, id="cuenta_sin_configurar"),
    pytest.param({"port": 0}, id="puerto_cero"),
    pytest.param({"port": -1}, id="puerto_negativo"),
    pytest.param({"port": 65536}, id="puerto_fuera_de_rango"),
])
def test_una_cuenta_sin_configurar_o_con_puerto_invalido_falla_sin_llamar_al_servidor(
        cambio, correo_simulado, caplog, capsys):
    """RF-03.17: cuenta sin configurar o puerto fuera de 1 a 65535 -> `False`, causa «configuracion», sin intentos."""
    caplog.set_level(logging.DEBUG)

    resultado = asyncio.run(_servicio(**cambio).send_email(DESTINO, "Asunto PRUEBA", "<p>hola</p>", "hola"))

    assert resultado is False
    assert correo_simulado.intentos == []
    assert correo_simulado.tiempos_maximos == []
    registros = [r.getMessage() for r in caplog.records if r.name.startswith("app.email")]
    assert len(registros) == 1 and "causa=configuracion" in registros[0]
    salida = capsys.readouterr()
    todo = caplog.text + salida.out + salida.err
    for secreto in (CLAVE, DESTINO, REMITENTE):
        assert secreto not in todo


@pytest.mark.parametrize("puerto", [1, 25, 65535])
def test_los_puertos_validos_de_los_extremos_si_llegan_al_servidor(puerto, correo_simulado):
    """RF-03.17: control: el rango válido es de 1 a 65535 (los extremos pasan)."""
    assert asyncio.run(_servicio(port=puerto).send_email(DESTINO, "Asunto PRUEBA", "<p>hola</p>")) is True
    assert len(correo_simulado.intentos) == 1


@pytest.mark.parametrize("metodo, argumentos", [
    ("send_password_email", (DESTINO, "PRUEBA-clave-temporal", NOMBRE)),
    ("send_password_reset_email", (DESTINO, NOMBRE, "PRUEBA-clave-temporal")),
    ("send_recovery_code_email", (DESTINO, NOMBRE, "PRUEBA-codigo")),
])
def test_los_envios_de_cada_tipo_devuelven_false_sin_lanzar_cuando_el_envio_falla(
        metodo, argumentos, correo_simulado, caplog, capsys):
    """RF-03.17: el contrato de los `send_*` no cambia: `bool` y sin lanzar (la 003b y la spec 002 dependen de eso)."""
    correo_simulado.fallar(aiosmtplib.SMTPAuthenticationError(535, TEXTO_DEL_SERVIDOR))
    caplog.set_level(logging.DEBUG)

    assert asyncio.run(getattr(_servicio(), metodo)(*argumentos)) is False
    _comprobar_que_el_registro_no_filtra(caplog, capsys)


def test_un_error_al_armar_el_correo_universal_devuelve_false_sin_dejar_el_texto_del_error(
        correo_simulado, monkeypatch, caplog, capsys):
    """RF-03.17: el `except` de `enviar_correo_universal` ya no usa `print` con `str(error)`."""
    from app.email.types.email_types import EmailData

    servicio = _servicio()

    def fallar_la_plantilla(**_):
        raise ValueError(TEXTO_DEL_SERVIDOR)

    monkeypatch.setattr(servicio.template, "generar_correo_universal", fallar_la_plantilla)
    caplog.set_level(logging.DEBUG)
    datos = EmailData(to=DESTINO, asunto="Asunto PRUEBA", titulo="Título", mensaje="Mensaje")

    assert asyncio.run(servicio.enviar_correo_universal(datos)) is False
    assert correo_simulado.intentos == []
    salida = capsys.readouterr()
    todo = caplog.text + salida.out + salida.err
    assert "PRUEBA-detalle-del-servidor-7731" not in todo
    assert CLAVE not in todo and DESTINO not in todo


def test_el_envio_exitoso_no_escribe_nada_en_el_registro_ni_en_la_salida(correo_simulado, caplog, capsys):
    """RNF-08.2: control: sin fallo no hay registro que pueda filtrar nada."""
    caplog.set_level(logging.DEBUG)

    assert asyncio.run(_servicio().send_email(DESTINO, "Asunto PRUEBA", "<p>hola</p>", "hola")) is True

    salida = capsys.readouterr()
    assert salida.out == "" and salida.err == ""
    assert DESTINO not in caplog.text and CLAVE not in caplog.text


# --- RF-03.18: UTF-8 en el mensaje tal como viaja -------------------------------------------------------

def _leer(intento) -> email.message.EmailMessage:
    """Decodifica los bytes que el simulado habría mandado al servidor con un lector independiente."""
    return email.message_from_bytes(intento.bytes_serializados, policy=email.policy.default)


def _cuerpos(mensaje) -> dict:
    return {parte.get_content_type(): parte.get_content()
            for parte in mensaje.walk() if not parte.is_multipart()}


def _sin_danos(texto: str) -> None:
    """Sin caracteres dañados ni secuencias de escape sin resolver."""
    for dano in ("�", "Ã", "Â", "=C3", "=?utf-8?", "\\xc3", "\\u00"):
        assert dano not in texto


def test_el_correo_de_creacion_viaja_en_utf8_con_el_nombre_y_el_asunto_con_tilde(correo_simulado):
    """RF-03.18: `send_password_email` -> un lector independiente encuentra el nombre y la «ñ» del asunto."""
    assert asyncio.run(_servicio().send_password_email(DESTINO, "PRUEBA-clave-temporal", NOMBRE)) is True

    mensaje = _leer(correo_simulado.intentos[0])
    cuerpos = _cuerpos(mensaje)
    assert set(cuerpos) == {"text/plain", "text/html"}
    for contenido in cuerpos.values():
        assert NOMBRE in contenido
        _sin_danos(contenido)
    asunto = str(mensaje["Subject"])
    assert "contraseña" in asunto.lower()
    _sin_danos(asunto)
    assert mensaje["To"] == DESTINO


def test_el_correo_de_restablecimiento_viaja_en_utf8_con_el_nombre_y_el_asunto_con_tilde(correo_simulado):
    """RF-03.18: `send_password_reset_email` -> «PRUEBA Peña Núñez» en texto y HTML, «Contraseña» en el asunto."""
    assert asyncio.run(_servicio().send_password_reset_email(DESTINO, NOMBRE, "PRUEBA-clave-temporal")) is True

    mensaje = _leer(correo_simulado.intentos[0])
    cuerpos = _cuerpos(mensaje)
    assert set(cuerpos) == {"text/plain", "text/html"}
    for contenido in cuerpos.values():
        assert NOMBRE in contenido
        _sin_danos(contenido)
    asunto = str(mensaje["Subject"])
    assert "Contraseña" in asunto
    _sin_danos(asunto)


def test_el_nombre_del_remitente_con_tilde_viaja_codificado_y_la_direccion_queda_intacta(correo_simulado):
    """RF-03.18: el nombre del remitente con «ñ» se codifica como encabezado UTF-8 sin dañar la dirección."""
    assert asyncio.run(_servicio(from_name="Sistema Peña ServIA").send_email(DESTINO, "Asunto PRUEBA", "<p>hola</p>")) is True

    remitente = _leer(correo_simulado.intentos[0])["From"]
    assert remitente.addresses[0].display_name == "Sistema Peña ServIA"
    assert remitente.addresses[0].addr_spec == REMITENTE


def test_los_bytes_del_mensaje_son_ascii_puro_en_los_encabezados(correo_simulado):
    """RF-03.18: ningún encabezado lleva bytes fuera de ASCII (viajan como palabras codificadas, RFC 2047)."""
    asyncio.run(_servicio().send_password_reset_email(DESTINO, NOMBRE, "PRUEBA-clave-temporal"))

    crudo = correo_simulado.intentos[0].bytes_serializados
    encabezados = crudo.split(b"\n\n", 1)[0].split(b"\r\n\r\n", 1)[0]
    encabezados.decode("ascii")  # lanza si algún encabezado trae bytes fuera de ASCII
