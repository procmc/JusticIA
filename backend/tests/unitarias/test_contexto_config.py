"""Pruebas de T1 (spec 007, RF-08.62, RF-11.63 y RF-11.65): la configuración única del contexto del chat.

Un solo origen (`app.config.contexto_config`) valida una vez los valores del entorno. Si alguno es
incoherente, escribe un aviso con el motivo y usa todos los valores por omisión. La llamada al motor
(`get_llm`) y el presupuesto leen ese mismo objeto. Los valores son inventados; no se lee el `.env` real.
"""
import asyncio
import logging

import pytest

from app.config import contexto_config as cc

LOGGER = "app.config.contexto_config"

INCOHERENTES = {
    "tamaño ≤ 0": {"FRAGMENTO_TAMANO_MAXIMO": "0"},
    "solapamiento < 0": {"FRAGMENTO_SOLAPAMIENTO": "-1"},
    "solapamiento ≥ tamaño": {"FRAGMENTO_TAMANO_MAXIMO": "500", "FRAGMENTO_SOLAPAMIENTO": "500"},
    "cantidad ≤ 0": {"CHAT_FRAGMENTOS_POR_CONSULTA": "0"},
    "caracteres ≤ 0": {"CHAT_CARACTERES_POR_TOKEN": "0"},
    "ventana ≤ 0": {"LLM_NUM_CTX": "0"},
    "reserva ≤ 0": {"LLM_NUM_PREDICT": "0"},
    "reserva ≥ ventana": {"LLM_NUM_CTX": "1024", "LLM_NUM_PREDICT": "1024"},
    "presupuesto bajo el mínimo": {"LLM_NUM_CTX": "1500", "LLM_NUM_PREDICT": "1024"},
    "intervalo ≤ 0": {"CHAT_SENAL_DE_VIDA_SEGUNDOS": "0"},
    "tope ≤ 0": {"CHAT_TIEMPO_MAXIMO_SEGUNDOS": "0"},
    "intervalo ≥ tope": {"CHAT_SENAL_DE_VIDA_SEGUNDOS": "200", "CHAT_TIEMPO_MAXIMO_SEGUNDOS": "180"},
    "no numérico": {"CHAT_FRAGMENTOS_POR_CONSULTA": "ocho"},
}


def _por_omision() -> cc.ConfiguracionContexto:
    return cc.VALORES_POR_OMISION


@pytest.mark.parametrize("caso", list(INCOHERENTES))
def test_incoherente(caso, caplog):
    """RF-08.62 · cada configuración incoherente avisa con el motivo y usa todos los valores por omisión."""
    entorno = {"LLM_NUM_CTX": "6000", "CHAT_FRAGMENTOS_POR_CONSULTA": "5"}
    entorno.update(INCOHERENTES[caso])
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        resultado = cc.construir_configuracion(entorno)
    assert resultado == _por_omision()
    avisos = [r for r in caplog.records if r.name == LOGGER and r.levelno == logging.WARNING]
    assert len(avisos) == 1
    assert len(avisos[0].getMessage()) > 20


def test_coherente_sin_aviso(caplog):
    """RF-08.62 · una configuración coherente se respeta tal cual y no escribe aviso."""
    entorno = {
        "LLM_NUM_CTX": "6000", "LLM_NUM_PREDICT": "800", "CHAT_CARACTERES_POR_TOKEN": "3",
        "CHAT_FRAGMENTOS_POR_CONSULTA": "5", "FRAGMENTO_TAMANO_MAXIMO": "1200",
        "FRAGMENTO_SOLAPAMIENTO": "100", "CHAT_SENAL_DE_VIDA_SEGUNDOS": "5",
        "CHAT_TIEMPO_MAXIMO_SEGUNDOS": "90",
    }
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        resultado = cc.construir_configuracion(entorno)
    assert [r for r in caplog.records if r.name == LOGGER] == []
    assert (resultado.ventana, resultado.reserva, resultado.presupuesto) == (6000, 800, 5200)
    assert resultado.caracteres_por_token == 3
    assert resultado.fragmentos_por_consulta == 5
    assert (resultado.fragmento_tamano_maximo, resultado.fragmento_solapamiento) == (1200, 100)
    assert (resultado.senal_de_vida_segundos, resultado.tiempo_maximo_segundos) == (5, 90)


def test_valores_por_omision(caplog):
    """RF-11.63, RF-11.65 · sin variables: 8.192/1.024, presupuesto 7.168, 8 fragmentos, 1.500/200, 10 s y 180 s."""
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        resultado = cc.construir_configuracion({})
    assert [r for r in caplog.records if r.name == LOGGER] == []
    assert resultado == cc.VALORES_POR_OMISION
    assert (resultado.ventana, resultado.reserva, resultado.presupuesto) == (8192, 1024, 7168)
    assert resultado.caracteres_por_token == 2.9
    assert resultado.fragmentos_por_consulta == 8
    assert (resultado.fragmento_tamano_maximo, resultado.fragmento_solapamiento) == (1500, 200)
    assert (resultado.senal_de_vida_segundos, resultado.tiempo_maximo_segundos) == (10, 180)


def test_rag_config_sin_valores_heredados():
    """RF-11.65 · rag_config no fija el top-k: lo lee de la configuración única (8 por omisión)."""
    from app.config.rag_config import rag_config
    esperado = cc.CONFIGURACION.fragmentos_por_consulta
    assert rag_config.TOP_K_GENERAL == rag_config.TOP_K_EXPEDIENTE == rag_config.TOP_K_FALLBACK == esperado


def test_llamada_y_presupuesto_misma_configuracion(monkeypatch):
    """RF-11.63 · `get_llm` envía a ChatOllama, como argumentos directos, la ventana y la reserva del presupuesto."""
    from app.llm import llm_service

    capturado = {}

    class ChatSimulado:
        def __init__(self, **kwargs):
            capturado.update(kwargs)

    monkeypatch.setattr(llm_service, "ChatOllama", ChatSimulado)
    monkeypatch.setattr(llm_service, "_llm", None)
    asyncio.run(llm_service.get_llm())
    configuracion = cc.CONFIGURACION
    assert capturado["num_ctx"] == configuracion.ventana
    assert capturado["num_predict"] == configuracion.reserva
    assert "model_kwargs" not in capturado
    assert configuracion.ventana - configuracion.reserva == configuracion.presupuesto
