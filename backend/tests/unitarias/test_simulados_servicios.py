"""Pruebas de T7 (spec 002, RA-02.6): Ollama, HTR, audio y correo simulados.

Cada simulado responde lo que la prueba le indica y registra lo recibido; ninguno abre una
conexión real. Los módulos del sistema se importan dentro de cada prueba.
"""
import asyncio
import json
import os

import pytest

from tests.soporte import simulados
from tests.soporte.proteccion import AbortoPruebas

CLAVE_DE_PRUEBA = "PRUEBA-clave-temporal-8431"
CODIGO_DE_PRUEBA = "PRUEBA-codigo-552977"
DESTINO = "destino.prueba@correo.invalid"


# --- Guardián de que el código usa el simulado (RA-02.6, 0) ---------------------------------------

@pytest.mark.parametrize("nombre, aparece", [
    ("ollama", "Ollama"), ("htr", "HTR"), ("audio", "audio"), ("correo", "correo"),
])
def test_si_un_servicio_no_esta_simulado_la_suite_aborta_y_lo_nombra(nombre, aparece):
    """RA-02.6 (0): sin la fixture, el cliente que usaría el código es el real y se aborta nombrándolo."""
    with pytest.raises(AbortoPruebas) as error:
        simulados.comprobar_simulados([nombre])
    assert aparece in str(error.value)


def test_con_las_cuatro_fixtures_el_codigo_usa_los_simulados(ollama_simulado, htr_simulado, audio_simulado,
                                                              correo_simulado):
    """RA-02.6 (0): el cliente que usa el código es el simulado, y la comprobación lo confirma."""
    simulados.comprobar_simulados(["ollama", "htr", "audio", "correo"])


def test_un_nombre_desconocido_es_un_error_de_la_suite():
    with pytest.raises(ValueError):
        simulados.comprobar_simulados(["inexistente"])


def test_los_servicios_vuelven_a_ser_los_reales_al_terminar_la_prueba():
    """Las fixtures restauran lo que parchearon: esta prueba (sin fixtures) ve los clientes reales."""
    with pytest.raises(AbortoPruebas):
        simulados.comprobar_simulados(["htr"])


# --- Ollama --------------------------------------------------------------------------------------

def test_ollama_simulado_devuelve_la_respuesta_definida_y_registra_la_pregunta(ollama_simulado):
    """RA-02.6 (a): una consulta con el flujo real de streaming usa la respuesta definida."""
    from app.llm.llm_service import consulta_general_streaming

    ollama_simulado.responder("Esta es la respuesta definida por la prueba PRUEBA.")

    async def consumir():
        respuesta = await consulta_general_streaming("¿Pregunta de PRUEBA sobre el tema?")
        return [trozo async for trozo in respuesta.body_iterator]

    eventos = asyncio.run(consumir())
    datos = [json.loads(evento.removeprefix("data: ")) for evento in eventos]
    texto = "".join(d["content"] for d in datos if d["type"] == "chunk")
    assert texto == "Esta es la respuesta definida por la prueba PRUEBA."
    assert datos[-1]["type"] == "done"
    assert any("¿Pregunta de PRUEBA sobre el tema?" in pregunta for pregunta in ollama_simulado.preguntas)


def test_ollama_simulado_funciona_dentro_de_una_cadena(ollama_simulado):
    """RA-02.6: `get_llm()` del sistema devuelve el simulado, también para quien lo importó por nombre."""
    from app.llm.llm_service import get_llm

    ollama_simulado.responder("respuesta de cadena")
    llm = asyncio.run(get_llm())
    assert llm is ollama_simulado
    assert asyncio.run(llm.ainvoke("hola PRUEBA")).content == "respuesta de cadena"
    assert ollama_simulado.preguntas == ["hola PRUEBA"]


# --- HTR -----------------------------------------------------------------------------------------

def test_htr_simulado_devuelve_el_texto_definido_y_registra_la_llamada(htr_simulado):
    """RA-02.6: el cliente HTR del sistema es el simulado; no se guarda el contenido de la imagen."""
    from app.services.ingesta.htr_service import htr_service

    htr_simulado.responder("texto reconocido PRUEBA")
    assert htr_service.extract_text(b"\x89PNG-inventado", "prueba_nota.png") == "texto reconocido PRUEBA"
    assert htr_service.is_available() is True
    assert htr_simulado.llamadas == [{"nombre": "prueba_nota.png", "bytes": len(b"\x89PNG-inventado")}]


def test_htr_simulado_puede_fallar_a_voluntad(htr_simulado):
    from app.services.ingesta.htr_service import htr_service

    htr_simulado.fallar(RuntimeError("HTR caído (simulado)"))
    with pytest.raises(RuntimeError, match="HTR caído"):
        htr_service.extract_text(b"x", "a.png")
    assert len(htr_simulado.llamadas) == 1


# --- Audio ---------------------------------------------------------------------------------------

def test_audio_simulado_devuelve_la_transcripcion_definida_sin_cargar_el_modelo(audio_simulado):
    """RA-02.6: ni el modelo faster-whisper ni sus estrategias se cargan."""
    from app.services.ingesta.audio_transcription.whisper_service import audio_processor

    audio_simulado.responder("transcripción de prueba PRUEBA")
    texto = asyncio.run(audio_processor.transcribe_audio_direct(b"audio-inventado", "prueba.mp3"))
    assert texto == "transcripción de prueba PRUEBA"
    assert audio_processor._load_faster_whisper_model() is audio_simulado.modelo
    assert audio_processor._whisper_model is None  # el modelo real nunca se cargó
    assert audio_simulado.llamadas == [{"nombre": "prueba.mp3", "bytes": len(b"audio-inventado")}]


def test_audio_simulado_puede_fallar_a_voluntad(audio_simulado):
    from app.services.ingesta.audio_transcription.whisper_service import audio_processor

    audio_simulado.fallar(ValueError("Whisper falló (simulado)"))
    with pytest.raises(ValueError, match="Whisper falló"):
        asyncio.run(audio_processor.transcribe_audio_direct(b"x", "a.mp3"))


# --- Correo --------------------------------------------------------------------------------------

def _servicio_de_correo():
    from app.email.core.email_service import EmailService, get_email_config_from_env

    return EmailService(get_email_config_from_env())


def test_la_configuracion_de_correo_de_la_suite_apunta_a_un_servidor_que_no_existe():
    """RA-02.2, RA-02.6: `EMAIL_*` son inventados y el servidor es `.invalid`."""
    from app.email.core.email_service import get_email_config_from_env

    configuracion = get_email_config_from_env()
    assert configuracion.host.endswith(".invalid")
    assert configuracion.username.endswith(".invalid")


def test_correo_que_falla_hace_que_el_envio_real_devuelva_false_sin_lanzar(correo_simulado):
    """RA-02.6 (b): `send_password_reset_email` real devuelve False sin lanzar y el intento queda registrado."""
    correo_simulado.fallar()

    resultado = asyncio.run(_servicio_de_correo().send_password_reset_email(DESTINO, "Nombre PRUEBA", CLAVE_DE_PRUEBA))

    assert resultado is False
    assert len(correo_simulado.intentos) == 1
    intento = correo_simulado.intentos[0]
    assert intento["a"] == DESTINO
    assert intento["asunto"]
    assert intento["html"] and intento["texto"]


def test_correo_que_responde_bien_devuelve_true(correo_simulado):
    """RA-02.6 (b): con `responder_bien()` el mismo envío real devuelve True."""
    correo_simulado.fallar()
    correo_simulado.responder_bien()

    resultado = asyncio.run(_servicio_de_correo().send_password_reset_email(DESTINO, "Nombre PRUEBA", CLAVE_DE_PRUEBA))

    assert resultado is True
    assert len(correo_simulado.intentos) == 1


def test_por_omision_el_correo_simulado_responde_bien(correo_simulado):
    assert asyncio.run(_servicio_de_correo().send_email(DESTINO, "Asunto PRUEBA", "<p>hola</p>", "hola")) is True


def test_fallar_acepta_la_excepcion_que_la_prueba_elija(correo_simulado):
    """RA-02.6 (a): el fallo llega al código que se prueba (aquí `send_email` lo atrapa y devuelve False)."""
    import aiosmtplib

    correo_simulado.fallar(aiosmtplib.SMTPConnectError("sin conexión (simulado)"))
    assert asyncio.run(_servicio_de_correo().send_email(DESTINO, "Asunto", "<p>x</p>")) is False
    # Y la excepción llega a quien llame directamente al envío de más bajo nivel.
    with pytest.raises(aiosmtplib.SMTPConnectError):
        asyncio.run(aiosmtplib.send(object()))


def test_el_registro_de_correo_oculta_las_contrasenas_y_codigos_que_la_prueba_declara(correo_simulado):
    """RA-02.6: sin guardar contraseñas ni códigos: lo declarado con `ocultar` no aparece en el registro."""
    correo_simulado.ocultar(CLAVE_DE_PRUEBA, CODIGO_DE_PRUEBA)
    servicio = _servicio_de_correo()

    asyncio.run(servicio.send_password_reset_email(DESTINO, "Nombre PRUEBA", CLAVE_DE_PRUEBA))
    asyncio.run(servicio.send_recovery_code_email(DESTINO, "Nombre PRUEBA", CODIGO_DE_PRUEBA))

    assert len(correo_simulado.intentos) == 2
    registro = json.dumps(correo_simulado.intentos, ensure_ascii=False)
    assert CLAVE_DE_PRUEBA not in registro
    assert CODIGO_DE_PRUEBA not in registro
    assert "<oculto>" in correo_simulado.intentos[0]["html"]
    assert "<oculto>" in correo_simulado.intentos[1]["texto"]


def test_el_registro_de_correo_nunca_guarda_las_credenciales_del_servidor(correo_simulado):
    """RA-02.6: ni el usuario ni la clave SMTP que recibe `aiosmtplib.send` quedan en el registro."""
    asyncio.run(_servicio_de_correo().send_email(DESTINO, "Asunto PRUEBA", "<p>hola</p>", "hola"))
    registro = json.dumps(correo_simulado.intentos, ensure_ascii=False) + repr(correo_simulado)
    assert os.environ["EMAIL_PASSWORD"] not in registro
    assert set(correo_simulado.intentos[0]) == {"a", "asunto", "html", "texto"}


def test_el_repr_de_un_intento_no_muestra_el_contenido(correo_simulado):
    """Los mensajes de aserción y los registros de pytest no deben mostrar cuerpos de correo."""
    asyncio.run(_servicio_de_correo().send_email(DESTINO, "Asunto PRUEBA", "<p>cuerpo secreto</p>", "cuerpo secreto"))
    assert "cuerpo secreto" not in repr(correo_simulado.intentos)
    assert "Asunto PRUEBA" in repr(correo_simulado.intentos)
