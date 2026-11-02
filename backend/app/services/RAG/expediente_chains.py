"""
Chat acotado a un tema: aporta sus instrucciones y arma la cadena de `general_chains`.

El recuperador busca por relevancia dentro del tema (RF-11.69); el armado, el presupuesto y la
transmisión son los mismos de los tres chats (spec 007, RF-11.60, RF-12.60).

Ver también:
    * app.services.RAG.general_chains: `CadenaArmada` y `stream_chain_response`
    * app.services.RAG.prompts.expediente_prompt: `instrucciones_tema`
"""
import logging

from .general_chains import CadenaArmada
from .presupuesto_contexto import CHAT_TEMA
from .prompts import instrucciones_tema
from .session_store import get_session_history_func

logger = logging.getLogger(__name__)


async def create_expediente_specific_chain(
    retriever,
    expediente_numero: str,
    with_history: bool = True
) -> CadenaArmada:
    """Crea la cadena del chat de un tema: con historial, reformula la pregunta para buscar (RF-11.66)."""
    logger.info("Cadena del tema %s creada (con historial: %s)", expediente_numero, with_history)
    return CadenaArmada(
        CHAT_TEMA, instrucciones_tema(expediente_numero), retriever,
        historial_de=get_session_history_func() if with_history else None, reformula=True,
    )
