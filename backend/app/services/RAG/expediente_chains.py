"""
Chains especializadas para análisis de expedientes específicos.

Crea chains de LangChain optimizadas para consultas sobre un expediente particular.
A diferencia de consultas generales, estas chains:
- NO reformulan la pregunta (no hay contextualización)
- Recuperan TODOS los documentos del expediente (no solo similares)
- Usan prompts especializados para análisis profundo

Características:
    * Prompt personalizado por expediente (con número en system prompt)
    * Sin contextualización (pregunta directa)
    * Recuperación completa del expediente (no búsqueda semántica)
    * Metadata visible con FormattedRetriever
    * Soporte de historial conversacional

Diferencias con general_chains:
    * General: contextualize + semantic search
    * Expediente: NO contextualize + full retrieval

Flujo de ejecución:
    1. Usuario pregunta sobre expediente específico
    2. NO reformulación (pregunta directa)
    3. Recuperación completa de documentos del expediente
    4. Formateo con metadata (FormattedRetriever)
    5. Generación con LLM usando prompt especializado
    6. Streaming al frontend

Prompt especializado:
    * Incluye número de expediente en system prompt
    * Instruye al LLM a analizar SOLO ese expediente
    * Documenta que documentos se recuperaron automáticamente
    * Previene invención de información

Example:
    >>> from app.services.rag.expediente_chains import create_expediente_specific_chain
    >>> 
    >>> # Crear chain para expediente específico
    >>> chain = await create_expediente_specific_chain(
    ...     retriever=retriever,  # Ya filtrado por expediente
    ...     expediente_numero="24-000123-0001-PE",
    ...     with_history=True
    ... )
    >>> 
    >>> # Usar con stream_chain_response de general_chains
    >>> async for chunk in stream_chain_response(chain, input_dict, config):
    ...     print(chunk)

Note:
    * El retriever YA debe estar filtrado por expediente
    * El número de expediente se usa SOLO en el prompt
    * Usa mismo streaming que general_chains (stream_chain_response)
    * FormattedRetriever añade headers de expediente

Ver también:
    * app.services.rag.prompts.expediente_prompt: Prompt especializado
    * app.services.rag.general_chains: stream_chain_response
    * app.services.rag.formatted_retriever: Formateo de documentos

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    2.0.0 - Chains especializadas para expedientes
"""
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