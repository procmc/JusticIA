"""Pruebas de T2 (spec 003a, RA-02.10): el correo simulado ampliado.

El simulado de correo de la spec 002 (`correo_simulado`) gana cuatro capacidades para probar el envío sin
un servidor real: registra el plazo con que se lo llama, conserva los bytes ya serializados de cada
mensaje, entrega el contenido real sin mostrarlo en ningún `repr`, y puede simular un servidor que no
responde o que responde con lentitud (con el reloj controlable de T1). Ninguna prueba espera tiempo real:
los plazos de 15 y 20 s son tiempo virtual. Todos los datos son inventados (prefijo `PRUEBA`).
"""
import asyncio
import contextlib
import email
import email.policy
from email.message import EmailMessage

import aiosmtplib
import pytest

CLAVE = "PRUEBA-clave-ampliado-7742"
DESTINO = "destino.prueba@prueba.invalid"
ASUNTO = "Contraseña PRUEBA"
CUERPO = "Hola PRUEBA Peña Núñez"


def _servicio_de_correo():
    from app.email.core.email_service import EmailService, get_email_config_from_env

    return EmailService(get_email_config_from_env())


def _mensaje(asunto: str = "Asunto PRUEBA", cuerpo: str = "cuerpo PRUEBA") -> EmailMessage:
    """Un mensaje mínimo, armado por la prueba, para llamar directamente a `aiosmtplib.send`."""
    mensaje = EmailMessage()
    mensaje["To"] = DESTINO
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo)
    return mensaje


async def _cancelar(tarea: "asyncio.Future") -> None:
    """Termina una tarea que la prueba dejó pendiente a propósito (un servidor que nunca responde)."""
    tarea.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await tarea


# --- (a) El plazo con que se llama el envío ----------------------------------------------------------

def test_tiempos_maximos_registra_el_timeout_de_cada_llamada(correo_simulado):
    """RA-02.10 (a): `tiempos_maximos` guarda el `timeout` de cada envío, en orden, y `None` si no se pasa."""
    assert correo_simulado.tiempos_maximos == []

    async def escenario():
        await aiosmtplib.send(_mensaje(), timeout=15)
        await aiosmtplib.send(_mensaje(), timeout=2.5)
        await aiosmtplib.send(_mensaje())

    asyncio.run(escenario())

    assert correo_simulado.tiempos_maximos == [15, 2.5, None]
    assert len(correo_simulado.intentos) == 3


def test_tiempos_maximos_registra_tambien_el_envio_que_falla(correo_simulado):
    """RA-02.10 (a): el plazo queda registrado aunque el envío termine en error."""
    correo_simulado.fallar()

    with pytest.raises(aiosmtplib.SMTPConnectError):
        asyncio.run(aiosmtplib.send(_mensaje(), timeout=7))

    assert correo_simulado.tiempos_maximos == [7]


# --- (b) Los bytes serializados ---------------------------------------------------------------------

def test_cada_intento_trae_los_bytes_que_un_lector_independiente_decodifica(correo_simulado):
    """RA-02.10 (b): `email.message_from_bytes` (política por omisión) recupera asunto y cuerpos con tilde y «ñ»."""
    asyncio.run(_servicio_de_correo().send_email(DESTINO, ASUNTO, f"<p>{CUERPO}</p>", CUERPO))

    intento = correo_simulado.intentos[0]
    assert isinstance(intento.bytes_serializados, bytes)
    leido = email.message_from_bytes(intento.bytes_serializados, policy=email.policy.default)
    assert leido["Subject"] == ASUNTO
    assert leido["To"] == DESTINO
    assert CUERPO in leido.get_body(preferencelist=("plain",)).get_content()
    assert CUERPO in leido.get_body(preferencelist=("html",)).get_content()


def test_cada_intento_conserva_sus_propios_bytes(correo_simulado):
    """RA-02.10 (b): dos envíos distintos no comparten bytes, y el que falla también los conserva."""
    servicio = _servicio_de_correo()
    asyncio.run(servicio.send_email(DESTINO, "Primero PRUEBA", "<p>uno</p>", "uno"))
    correo_simulado.fallar()
    asyncio.run(servicio.send_email(DESTINO, "Segundo PRUEBA", "<p>dos</p>", "dos"))

    primero, segundo = correo_simulado.intentos
    assert email.message_from_bytes(primero.bytes_serializados, policy=email.policy.default)["Subject"] == "Primero PRUEBA"
    assert email.message_from_bytes(segundo.bytes_serializados, policy=email.policy.default)["Subject"] == "Segundo PRUEBA"


# --- (c) El contenido real, sin mostrarlo -----------------------------------------------------------

def test_contenido_real_entrega_la_contrasena_y_ningun_repr_la_muestra(correo_simulado):
    """RA-02.10 (c): la prueba obtiene la contraseña del contenido real; los `repr` no la muestran."""
    asyncio.run(_servicio_de_correo().send_password_reset_email(DESTINO, "Nombre PRUEBA", CLAVE))

    contenido = correo_simulado.contenido_real()

    assert CLAVE in contenido.texto
    assert CLAVE in contenido.html
    assert contenido.a == DESTINO
    assert CLAVE not in repr(contenido)
    assert CLAVE not in repr(correo_simulado.intentos[0])
    assert CLAVE not in repr(correo_simulado.intentos)
    assert CLAVE not in repr(correo_simulado)


def test_ocultar_sigue_reemplazando_en_el_intento_y_el_contenido_real_conserva_el_valor(correo_simulado):
    """RA-02.10 (c): `ocultar()` no cambia: el `Intento` queda con `<oculto>` y sus cuatro claves."""
    correo_simulado.ocultar(CLAVE)

    asyncio.run(_servicio_de_correo().send_password_reset_email(DESTINO, "Nombre PRUEBA", CLAVE))

    intento = correo_simulado.intentos[0]
    assert set(intento) == {"a", "asunto", "html", "texto"}
    assert CLAVE not in intento["html"] and CLAVE not in intento["texto"]
    assert "<oculto>" in intento["html"] and "<oculto>" in intento["texto"]
    assert CLAVE in correo_simulado.contenido_real().texto
    assert CLAVE not in repr(correo_simulado.contenido_real())


def test_contenido_real_elige_el_intento_y_avisa_si_no_hay(correo_simulado):
    """RA-02.10 (c): sin argumento es el último intento; con un índice, ese intento; sin intentos, un error claro."""
    with pytest.raises(LookupError):
        correo_simulado.contenido_real()

    servicio = _servicio_de_correo()
    asyncio.run(servicio.send_email(DESTINO, "Primero PRUEBA", "<p>uno</p>", "uno"))
    asyncio.run(servicio.send_email(DESTINO, "Segundo PRUEBA", "<p>dos</p>", "dos"))

    assert correo_simulado.contenido_real().asunto == "Segundo PRUEBA"
    assert correo_simulado.contenido_real(0).asunto == "Primero PRUEBA"


# --- (d) Un servidor que no responde o que es lento --------------------------------------------------

def test_no_responde_no_termina_por_si_solo_y_un_limite_de_15_s_lo_corta(correo_simulado, reloj_controlable):
    """RA-02.10 (d): sin límite el envío queda pendiente; `con_limite` de 15 s lo corta a los 15 s."""
    correo_simulado.no_responde()

    async def sin_limite():
        envio = asyncio.ensure_future(aiosmtplib.send(_mensaje(), timeout=15))
        await reloj_controlable.avanzar(3600)  # una hora virtual y nada lo termina
        pendiente = not envio.done()
        await _cancelar(envio)
        return pendiente

    async def con_limite():
        tarea = asyncio.ensure_future(reloj_controlable.con_limite(aiosmtplib.send(_mensaje(), timeout=15), 15))
        await reloj_controlable.avanzar(14.9)
        pendiente_a_los_14_9 = not tarea.done()
        await reloj_controlable.avanzar(0.1)
        cortado_a_los_15 = tarea.done()
        if not cortado_a_los_15:  # si el límite fallara, no se espera la tarea (colgaría la prueba)
            await _cancelar(tarea)
            return pendiente_a_los_14_9, False
        with pytest.raises(TimeoutError):
            await tarea
        return pendiente_a_los_14_9, True

    assert asyncio.run(sin_limite()) is True
    assert asyncio.run(con_limite()) == (True, True)
    assert correo_simulado.tiempos_maximos == [15, 15]
    assert len(correo_simulado.intentos) == 2


def test_lento_termina_exactamente_a_los_20_s_con_cuatro_operaciones_de_5_s(correo_simulado, reloj_controlable):
    """RA-02.10 (d): `lento(reloj, 4, 5)` sigue pendiente a los 19,9 s, termina a los 20 y devuelve la respuesta."""
    correo_simulado.lento(reloj_controlable, 4, 5)

    async def escenario():
        inicio = reloj_controlable.monotonico()
        envio = asyncio.ensure_future(aiosmtplib.send(_mensaje()))
        await reloj_controlable.avanzar(19.9)
        antes = envio.done()
        await reloj_controlable.avanzar(0.1)
        return antes, envio.done(), reloj_controlable.monotonico() - inicio, envio

    antes, despues, transcurrido, envio = asyncio.run(escenario())

    assert antes is False
    assert despues is True
    assert transcurrido == pytest.approx(20)
    assert envio.result() == ({}, "OK (simulado)")


def test_lento_supera_un_limite_de_15_s(correo_simulado, reloj_controlable):
    """RA-02.10 (d): un servidor lento de 20 s total no cabe en un límite de 15 s: `TimeoutError` a los 15 s."""
    correo_simulado.lento(reloj_controlable, 4, 5)

    async def escenario():
        tarea = asyncio.ensure_future(reloj_controlable.con_limite(aiosmtplib.send(_mensaje()), 15))
        await reloj_controlable.avanzar(14.9)
        pendiente_a_los_14_9 = not tarea.done()
        await reloj_controlable.avanzar(0.1)
        cortado_a_los_15 = tarea.done()
        if not cortado_a_los_15:
            await _cancelar(tarea)
            return pendiente_a_los_14_9, False
        with pytest.raises(TimeoutError):
            await tarea
        return pendiente_a_los_14_9, True

    assert asyncio.run(escenario()) == (True, True)


@pytest.mark.parametrize("modo", ["no_responde", "lento"])
def test_responder_bien_vuelve_a_la_normalidad(correo_simulado, reloj_controlable, modo):
    """RA-02.10 (d): tras `no_responde()` o `lento()`, `responder_bien()` hace que el envío termine sin avanzar el reloj."""
    if modo == "no_responde":
        correo_simulado.no_responde()
    else:
        correo_simulado.lento(reloj_controlable, 4, 5)
    correo_simulado.responder_bien()

    async def escenario():
        inicio = reloj_controlable.monotonico()
        envio = asyncio.ensure_future(aiosmtplib.send(_mensaje()))
        await reloj_controlable.avanzar(0)
        return envio.done(), reloj_controlable.monotonico() - inicio, envio

    terminado, transcurrido, envio = asyncio.run(escenario())

    assert terminado is True
    assert transcurrido == 0
    assert envio.result() == ({}, "OK (simulado)")


def test_el_repr_del_simulado_no_cambia_con_los_modos_nuevos(correo_simulado, reloj_controlable):
    """RA-02.10: el simulado sigue mostrando solo cuántos intentos tiene y si falla; ningún modo agrega contenido."""
    correo_simulado.no_responde()
    assert repr(correo_simulado) == "CorreoSimulado(intentos=0, falla=False)"
    correo_simulado.lento(reloj_controlable, 4, 5)
    assert repr(correo_simulado) == "CorreoSimulado(intentos=0, falla=False)"
