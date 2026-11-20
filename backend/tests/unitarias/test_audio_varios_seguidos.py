"""Varios audios seguidos con el mismo servicio de transcripción (spec 012, parte C; RF-07.70).

Defecto que motivó la spec: la estrategia de transcripción borraba su modelo de Whisper al terminar el primer audio
(`del self.whisper_model`) y el siguiente audio del mismo servicio fallaba con «object has no attribute 'whisper_model'».
Sin modelos reales ni archivos de audio: el modelo es un falso que devuelve un texto fijo. Datos inventados.
"""
import asyncio
from types import SimpleNamespace

import pytest


class _ModeloFalso:
    """Ocupa el lugar del `WhisperModel`: devuelve un segmento fijo y cuenta las llamadas."""

    def __init__(self):
        self.llamadas = 0

    def transcribe(self, ruta, **opciones):
        self.llamadas += 1
        segmentos = [SimpleNamespace(text=f" Texto inventado {self.llamadas}. ", start=0.0, end=1.0)]
        info = SimpleNamespace(language="es", language_probability=0.99, duration=1.0)
        return iter(segmentos), info


def _configuracion():
    from app.config.audio_config import AUDIO_CONFIG

    return AUDIO_CONFIG


@pytest.mark.requisito("RF-07.70")
def test_la_estrategia_directa_transcribe_dos_audios_seguidos():
    """RF-07.70: la misma estrategia directa (la que conserva el servicio entre audios) transcribe el segundo audio igual que
    el primero, sin quedarse sin modelo."""
    from app.services.ingesta.audio_transcription.direct_strategy import DirectTranscriptionStrategy

    modelo = _ModeloFalso()
    estrategia = DirectTranscriptionStrategy(modelo, _configuracion())

    primero = asyncio.run(estrategia.transcribe("ruta-inventada-1.mp3", "PRUEBA primero.mp3", 1.0))
    segundo = asyncio.run(estrategia.transcribe("ruta-inventada-2.mp3", "PRUEBA segundo.mp3", 1.0))

    assert "Texto inventado 1" in primero
    assert "Texto inventado 2" in segundo
    assert modelo.llamadas == 2


@pytest.mark.requisito("RF-07.70")
def test_la_estrategia_por_trozos_transcribe_dos_audios_seguidos(monkeypatch):
    """RF-07.70: lo mismo con la estrategia por fragmentos (audios grandes): el segundo audio no falla por el primero."""
    from app.services.ingesta.audio_transcription.chunking_strategy import ChunkingTranscriptionStrategy

    estrategia = ChunkingTranscriptionStrategy(_ModeloFalso(), _configuracion())

    async def _duracion(ruta):
        return 60.0

    async def _trozos(ruta, minutos, solape):
        return ["trozo-inventado.mp3"]

    async def _limpiar(rutas):
        return None

    async def _transcribir(rutas, seguimiento=None):
        return ["Texto inventado por trozos."]

    monkeypatch.setattr(estrategia.audio_utils, "get_audio_duration", _duracion)
    monkeypatch.setattr(estrategia.audio_utils, "split_audio_into_chunks", _trozos)
    monkeypatch.setattr(estrategia.audio_utils, "cleanup_chunks", _limpiar)
    monkeypatch.setattr(estrategia, "_transcribe_chunks", _transcribir)

    primero = asyncio.run(estrategia.transcribe("ruta-1.mp3", "PRUEBA primero.mp3", 200.0))
    segundo = asyncio.run(estrategia.transcribe("ruta-2.mp3", "PRUEBA segundo.mp3", 200.0))

    assert primero == segundo == "Texto inventado por trozos."
