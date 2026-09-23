"""
Chain especializada para análisis de un notebook específico (NotebookServIA).

Calcada de expediente_chains.py — misma estructura (retrieval chain +
FormattedRetriever + historial), pero usa el prompt genérico de
notebook_prompt.py en vez del prompt judicial.

Ver también:
    * app.services.rag.prompts.notebook_prompt: Prompt especializado
    * app.services.rag.expediente_chains: Chain equivalente para expedientes

Authors:
    ServIA Team

Version:
    1.0.0
"""
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.runnables.history import RunnableWithMessageHistory
import logging

from app.llm.llm_service import get_llm
from .session_store import get_session_history_func
from .prompts import get_notebook_prompt, DOCUMENT_PROMPT
from .formatted_retriever import FormattedRetriever

logger = logging.getLogger(__name__)


async def create_notebook_specific_chain(
    retriever,
    nombre_notebook: str,
    with_history: bool = True,
    pregunta: str = ""
):
    """Crea una chain especializada para análisis de un notebook específico.

    Args:
        pregunta: La pregunta de este turno. Se pasa al prompt para que
            agregue el recordatorio reforzado contra negar imágenes solo
            cuando la pregunta menciona un archivo de ese tipo.
    """
    llm = await get_llm()

    formatted_retriever = FormattedRetriever(retriever)

    NOTEBOOK_PROMPT = get_notebook_prompt(nombre_notebook, pregunta)

    question_answer_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=NOTEBOOK_PROMPT,
        document_prompt=DOCUMENT_PROMPT
    )

    rag_chain = create_retrieval_chain(
        formatted_retriever,
        question_answer_chain,
    )

    if with_history:
        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            get_session_history_func(),
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )

        logger.info(f"Chain notebook '{nombre_notebook}' con historial creado")
        return conversational_rag_chain

    logger.info(f"Chain notebook '{nombre_notebook}' creado")
    return rag_chain
