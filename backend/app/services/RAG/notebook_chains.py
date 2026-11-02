"""
Chat acotado a un notebook (NotebookServIA): aporta sus instrucciones y arma la cadena de `general_chains`.

La lista de archivos del notebook sale de los fragmentos enviados en esa llamada (spec 007, RF-12.62), sin una
búsqueda aparte.

Ver también:
    * app.services.RAG.general_chains: `CadenaArmada` y `stream_chain_response`
    * app.services.RAG.prompts.notebook_prompt: `instrucciones_notebook`
"""
import logging

from .general_chains import CadenaArmada
from .presupuesto_contexto import CHAT_NOTEBOOK
from .prompts import instrucciones_notebook
from .session_store import get_session_history_func

logger = logging.getLogger(__name__)


async def create_notebook_specific_chain(
    retriever,
    nombre_notebook: str,
    with_history: bool = True
) -> CadenaArmada:
    """Crea la cadena del chat de un notebook: con historial, reformula la pregunta (ya adaptada) para buscar (RF-11.66)."""
    logger.info("Cadena del notebook '%s' creada (con historial: %s)", nombre_notebook, with_history)
    return CadenaArmada(
        CHAT_NOTEBOOK, instrucciones_notebook(nombre_notebook), retriever,
        historial_de=get_session_history_func() if with_history else None, reformula=True,
    )
