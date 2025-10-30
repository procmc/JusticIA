from typing import Dict, Any
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.runnables.history import RunnableWithMessageHistory
import logging

from app.llm.llm_service import get_llm
from .session_store import get_session_history_func
from .prompts import get_expediente_prompt, DOCUMENT_PROMPT
from .formatted_retriever import FormattedRetriever

logger = logging.getLogger(__name__)


async def create_expediente_specific_chain(
    retriever,
    expediente_numero: str,
    with_history: bool = True
):
    """Crea una chain especializada para análisis de expediente específico."""
    llm = await get_llm()
    
    # Envolver el retriever con FormattedRetriever para agregar metadata visible (igual que consulta general)
    formatted_retriever = FormattedRetriever(retriever)
    
    EXPEDIENTE_PROMPT = get_expediente_prompt(expediente_numero)
    
    question_answer_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=EXPEDIENTE_PROMPT,
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
        
        logger.info(f" Chain expediente {expediente_numero} con historial creado")
        return conversational_rag_chain
    
    logger.info(f" Chain expediente {expediente_numero} creado")
    return rag_chain