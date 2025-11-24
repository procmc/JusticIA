"""
Chains conversacionales de LangChain para consultas generales.

Implementa el pipeline completo de RAG conversacional:
1. Contextualización de pregunta con historial
2. Recuperación de documentos relevantes
3. Generación de respuesta con LLM
4. Streaming de respuesta token por token

Componentes de la chain:
    * History-aware retriever: Reformula pregunta con contexto
    * Stuff documents chain: Combina documentos en contexto único
    * Retrieval chain: Pipeline completo de recuperación + generación
    * RunnableWithMessageHistory: Añade gestión de historial

Prompts utilizados:
    * CONTEXTUALIZE_Q_PROMPT: Reformulación con expansión semántica
    * ANSWER_PROMPT: Generación de respuestas con JusticBot
    * DOCUMENT_PROMPT: Formato de documentos para el LLM

Streaming:
    * Server-Sent Events (SSE) para respuestas en tiempo real
    * Detección de desconexión del cliente
    * Mensajes fallback si respuesta vacía
    * Señal de finalización automática

Flujo de ejecución:
    1. Usuario envía pregunta + session_id
    2. Reformulación con historial (contextualize)
    3. Búsqueda vectorial en Milvus (retriever)
    4. Formateo de documentos (FormattedRetriever)
    5. Generación con LLM (streaming)
    6. SSE al frontend chunk por chunk

Example:
    >>> from app.services.rag.general_chains import create_conversational_rag_chain, stream_chain_response
    >>> 
    >>> # Crear chain conversacional
    >>> chain = await create_conversational_rag_chain(
    ...     retriever=retriever,
    ...     with_history=True
    ... )
    >>> 
    >>> # Streaming de respuesta
    >>> async for chunk in stream_chain_response(
    ...     chain=chain,
    ...     input_dict={"input": "¿Qué es la prescripción?"},
    ...     config={"configurable": {"session_id": session_id}}
    ... ):
    ...     print(chunk, end="", flush=True)

Note:
    * La chain retorna dict con clave "answer" en streaming
    * FormattedRetriever añade metadata visible en documentos
    * Detección de desconexión evita generación innecesaria
    * Fallback automático si LLM retorna respuesta vacía

Ver también:
    * app.services.rag.prompts: Definición de prompts
    * app.services.rag.formatted_retriever: Formateo de documentos
    * app.llm.llm_service: Servicio de LLM

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    2.0.0 - LangChain con streaming SSE
"""
from typing import Dict, Any
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.runnables.history import RunnableWithMessageHistory
import logging
import json

from app.llm.llm_service import get_llm
from .session_store import get_session_history_func
from .formatted_retriever import FormattedRetriever
from .prompts import (
    CONTEXTUALIZE_Q_PROMPT,
    ANSWER_PROMPT,
    DOCUMENT_PROMPT
)

logger = logging.getLogger(__name__)


async def create_conversational_rag_chain(
    retriever,
    with_history: bool = True,
    session_config_key: str = "configurable"
):
    """Crea una chain RAG conversacional completa con historial para consultas generales."""
    llm = await get_llm()
    
    # Envolver el retriever con FormattedRetriever para agregar metadata visible
    formatted_retriever = FormattedRetriever(retriever)
    
    history_aware_retriever = create_history_aware_retriever(
        llm=llm,
        retriever=formatted_retriever,
        prompt=CONTEXTUALIZE_Q_PROMPT,
    )
    
    question_answer_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=ANSWER_PROMPT,
        document_prompt=DOCUMENT_PROMPT
    )
    
    rag_chain = create_retrieval_chain(
        history_aware_retriever,
        question_answer_chain,
    )
    
    # Debug: interceptar el chain para ver el contexto enviado
    async def debug_context_wrapper(input_dict):
        """Wrapper para logging del contexto antes de enviarlo al LLM."""
        if "context" in input_dict:
            context = input_dict["context"]
            if isinstance(context, list):
                total_chars = sum(len(doc.page_content) for doc in context)
                logger.info(f"Contexto enviado al LLM: {len(context)} docs, {total_chars} chars (~{total_chars // 4} tokens)")
                # Log de los primeros 200 chars del primer doc para debugging
                if context:
                    logger.debug(f"Primer doc (preview): {context[0].page_content[:200]}...")
        return input_dict
    
    
    if with_history:
        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            get_session_history_func(),
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )
        
        return conversational_rag_chain
    
    return rag_chain


async def stream_chain_response(chain, input_dict: Dict[str, Any], config: Dict[str, Any], http_request=None):
    total_chars = 0
    client_disconnected = False
    
    try:
        # Stream desde la chain
        async for chunk in chain.astream(input_dict, config=config):
            # Verificar si el cliente se desconectó ANTES de procesar el chunk
            if http_request:
                try:
                    # Verificar si el cliente sigue conectado
                    if await http_request.is_disconnected():
                        logger.warning("Cliente desconectado detectado - Deteniendo generación de respuesta")
                        client_disconnected = True
                        break
                except Exception as e:
                    # Si hay algún error verificando la conexión, continuar
                    logger.debug(f"No se pudo verificar estado de conexión: {e}")
            
            # Las chains de LangChain emiten dicts, extraer 'answer'
            if isinstance(chunk, dict) and "answer" in chunk:
                content = chunk["answer"]
                
                # Convertir a string si es necesario
                if content is not None:
                    content_str = str(content) if not isinstance(content, str) else content
                    
                    # Emitir solo si hay contenido (permitir espacios y saltos de línea)
                    if content_str:
                        total_chars += len(content_str)
                        chunk_data = {
                            "type": "chunk",
                            "content": content_str,
                            "done": False
                        }
                        try:
                            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                        except Exception as yield_error:
                            # Si falla el yield, probablemente el cliente se desconectó
                            logger.warning(f"Error al enviar chunk (cliente desconectado): {yield_error}")
                            client_disconnected = True
                            break
        
        # Log final dependiendo de si se completó o se detuvo
        if client_disconnected:
            logger.info(f"Streaming detenido por desconexión del cliente - {total_chars} caracteres generados antes de detener")
        else:
            logger.info(f"Streaming completado: {total_chars} caracteres generados")
        
        # Solo enviar mensajes finales si el cliente NO se desconectó
        if not client_disconnected:
            # Detectar respuestas vacías y enviar fallback ANTES del done
            if total_chars == 0:
                logger.warning("No se generó contenido, enviando mensaje de fallback")
                fallback_message = "No encontré información relevante en los documentos recuperados para responder tu pregunta."
                fallback_data = {
                    "type": "chunk",
                    "content": fallback_message,
                    "done": False
                }
                try:
                    yield f"data: {json.dumps(fallback_data, ensure_ascii=False)}\n\n"
                except:
                    pass  # Cliente ya desconectado
            
            # Señal de finalización SIEMPRE al final
            done_data = {"type": "done", "content": "", "done": True}
            try:
                yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
            except:
                pass  # Cliente ya desconectado
        
    except Exception as e:
        logger.error(f"Error en streaming: {e}", exc_info=True)
        
        error_data = {
            "type": "error",
            "content": f"Error al procesar la consulta: {str(e)}",
            "done": True
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        done_data = {"type": "done", "content": "", "done": True}
        yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"