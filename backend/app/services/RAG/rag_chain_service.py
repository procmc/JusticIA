"""
Servicio coordinador del sistema RAG (Retrieval-Augmented Generation).

Este servicio es el punto de entrada principal para el asistente virtual JusticBot.
Coordina consultas generales y específicas de expedientes, gestiona el flujo de
streaming de respuestas y mantiene el contexto conversacional.

Arquitectura RAG:
    * Retriever: DynamicJusticIARetriever busca documentos relevantes en Qdrant
    * Chains: LangChain chains procesan contexto + historial + pregunta
    * LLM: Modelo de lenguaje genera respuestas basadas en documentos
    * Streaming: Server-Sent Events (SSE) para respuestas en tiempo real

Flujos soportados:
    1. Consulta general: Búsqueda semántica en toda la BD
    2. Consulta de expediente: Análisis profundo de un expediente específico
    3. Cambio de contexto: Actualización de expediente en sesión activa

Características:
    * Streaming SSE con detección de desconexión del cliente
    * Gestión automática de títulos de conversaciones
    * Validación de formato de expedientes
    * Fallback a general si expediente inválido
    * Límites configurables de documentos (top_k)

Example:
    >>> from app.services.rag.rag_chain_service import get_rag_service
    >>> rag_service = await get_rag_service()
    >>> 
    >>> # Consulta general
    >>> response = await rag_service.consulta_con_historial_streaming(
    ...     pregunta="¿Qué es la prescripción?",
    ...     session_id="session_user@example.com_1234567890",
    ...     top_k=15
    ... )
    >>> 
    >>> # Consulta de expediente específico
    >>> response = await rag_service.consulta_con_historial_streaming(
    ...     pregunta="¿Cuál es la sentencia?",
    ...     session_id="session_user@example.com_1234567890",
    ...     expediente_filter="24-000123-0001-PE"
    ... )

Note:
    * Singleton: Una instancia global compartida (get_rag_service)
    * Config centralizada: Parámetros en app.config.rag_config
    * top_k máximo: 15 documentos para evitar overflow de contexto
    * Formato expediente: YY-NNNNNN-NNNN-XX (validación con regex)

Ver también:
    * app.services.rag.retriever: Búsqueda vectorial
    * app.services.rag.general_chains: Chains conversacionales
    * app.services.rag.expediente_chains: Chains de expedientes
    * app.services.rag.session_store: Gestión de historial

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    2.0.0 - LangChain con streaming SSE
"""
from typing import Optional
from fastapi.responses import StreamingResponse
from fastapi import Request
import re
import logging
import json

from .retriever import DynamicJusticIARetriever
from .general_chains import create_conversational_rag_chain, stream_chain_response
from .expediente_chains import create_expediente_specific_chain
from .session_store import conversation_store

# Importar configuración centralizada
from app.config.rag_config import rag_config

logger = logging.getLogger(__name__)


class RAGChainService:
    """
    Servicio coordinador de consultas RAG.
    
    Maneja routing entre consultas generales y de expedientes,
    streaming de respuestas y gestión de contexto.
    
    Methods:
        consulta_con_historial_streaming: Consulta principal con routing automático
        update_expediente_context: Actualiza contexto de expediente en sesión
    """
    def __init__(self):
        pass

    # =====================================================================
    # LANGCHAIN ARCHITECTURE (Modern)
    # =====================================================================
    
    # Consulta principal 
    async def consulta_con_historial_streaming(
        self,
        pregunta: str,
        session_id: str,
        top_k: int = 15,
        expediente_filter: Optional[str] = None,
        http_request: Optional[Request] = None
    ):
        # 1. Actualizar la información de la conversación
        conversation_store.update_metadata(session_id)
        
        # 2. AQUÍ COORDINA: Decide qué flujo seguir
        if expediente_filter and expediente_filter.strip():
            # → VA AL FLUJO DE EXPEDIENTE ESPECÍFICO
            logger.info(f"FLUJO: EXPEDIENTE ESPECÍFICO: {expediente_filter}")
            return await self._consulta_expediente_con_historial(
                pregunta=pregunta,
                session_id=session_id,
                expediente_numero=expediente_filter.strip(),
                http_request=http_request
            )
        else:
            logger.info(f"FLUJO: GENERAL CON HISTORIAL")
            # → VA AL FLUJO GENERAL
            return await self._consulta_general_con_historial(
                pregunta=pregunta,
                session_id=session_id,
                top_k=top_k,
                http_request=http_request
            )
    
    # Consulta general con historial
    async def _consulta_general_con_historial(
        self,
        pregunta: str,
        session_id: str,
        top_k: int = 15,
        http_request: Optional[Request] = None
    ):
        # Usar valor del config si no se especifica
        if top_k is None:
            top_k = rag_config.TOP_K_GENERAL
        
        # IMPORTANTE: Limitar top_k máximo para evitar sobrecarga del LLM
        # Con gpt-oss:20b (32K ctx), máximo recomendado es ~15 documentos
        MAX_TOP_K = 15
        if top_k > MAX_TOP_K:
            logger.warning(f"top_k={top_k} excede el máximo recomendado. Ajustando a {MAX_TOP_K}")
            top_k = MAX_TOP_K
        
        # Crear buscador con configuración centralizada
        retriever = DynamicJusticIARetriever(
            top_k=top_k,
            similarity_threshold=rag_config.SIMILARITY_THRESHOLD_GENERAL
        )
        
        # Crear chain conversacional
        chain = await create_conversational_rag_chain(
            retriever=retriever,
            with_history=True # "Recuerda la conversación anterior"
        )
        
        # Configuración de sesión
        config = {
            "configurable": {
                "session_id": session_id
            }
        }
        
        # Input para la chain
        input_dict = {
            "input": pregunta
        }
        
        # Streaming response
        async def event_generator():
            try:
                logger.info(f"Iniciando streaming para session: {session_id}")
                async for chunk in stream_chain_response(chain, input_dict, config, http_request):
                    yield chunk
                
                logger.info(f"Streaming finalizado para session: {session_id}")
                # Auto-generar título si es el primer mensaje
                conversation_store.auto_generate_title(session_id)
                
            except Exception as e:
                logger.error(f"Error en streaming con historial: {e}", exc_info=True)
                error_data = {
                    "type": "error",
                    "content": f"Error al procesar la consulta: {str(e)}",
                    "done": True
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    
    # Consulta de expediente específico con historial
    async def _consulta_expediente_con_historial(
        self,
        pregunta: str,
        session_id: str,
        expediente_numero: str,
        http_request: Optional[Request] = None
    ):
        logger.info(f"Expediente con historial - Número: {expediente_numero}")
        
        # Validar formato del expediente ingresado
        expediente_pattern = r'\b\d{2,4}-\d{6}-\d{4}-[A-Z]{2}\b'
        if not re.match(expediente_pattern, expediente_numero):
            logger.error(f"Formato inválido: {expediente_numero}")
            # Fallback a general
            return await self._consulta_general_con_historial(
                pregunta=pregunta,
                session_id=session_id,
                top_k=15,  # Usar valor por defecto
                http_request=http_request
            )
        
        # Actualizar la información de la conversación
        conversation_store.update_metadata(
            session_id=session_id,
            expediente_number=expediente_numero
        )
        
        # Crear retriever configurado para expediente específico con config centralizado
        retriever = DynamicJusticIARetriever(
            top_k=rag_config.TOP_K_EXPEDIENTE,
            similarity_threshold=rag_config.SIMILARITY_THRESHOLD_EXPEDIENTE,
            expediente_filter=expediente_numero
        )
        
        logger.info(
            f"DynamicJusticIARetriever creado para expediente {expediente_numero} "
            f"(top_k: {rag_config.TOP_K_EXPEDIENTE}, "
            f"threshold: {rag_config.SIMILARITY_THRESHOLD_EXPEDIENTE})"
        )
        
        # Crear chain especializada para expedientes
        chain = await create_expediente_specific_chain(
            retriever=retriever,
            expediente_numero=expediente_numero,
            with_history=True
        )
        
        logger.info(f"Chain expediente creada")
        
        # Configuración de sesión
        config = {
            "configurable": {
                "session_id": session_id
            }
        }
        
        # Input para la chain
        input_dict = {
            "input": pregunta
        }
        
        # Streaming response
        async def event_generator():
            try:
                logger.info(f"🚀 Iniciando streaming para expediente: {expediente_numero}, session: {session_id}")
                async for chunk in stream_chain_response(chain, input_dict, config, http_request):
                    yield chunk # Envía cada pedacito al frontend
                
                logger.info(f"✅ Streaming finalizado para expediente: {expediente_numero}, session: {session_id}")
                # Cuando termina, genera título automático
                conversation_store.auto_generate_title(session_id)
                
            except Exception as e:
                logger.error(f"Error en streaming expediente con historial: {e}", exc_info=True)
                # Si algo sale mal, envía error
                error_data = {
                    "type": "error",
                    "content": f"Error al procesar la consulta del expediente: {str(e)}",
                    "done": True
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    
    # Actualizar contexto de expediente en la sesión
    async def update_expediente_context(
        self,
        session_id: str,
        expediente_number: str,
        action: str = "set"
    ) -> bool:
        try:
            logger.info(f"Actualizando contexto - Session: {session_id}")
            logger.info(f"Expediente: {expediente_number}, Acción: {action}")
            
            # Actualizar metadatos de la sesión con el expediente
            conversation_store.update_metadata(
                session_id=session_id,
                expediente_number=expediente_number
            )
            
            # Obtener o crear el historial de la sesión
            session_history = conversation_store.get_session_history(session_id)
            
            # Crear mensaje del sistema para documentar el cambio
            from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
            
            if action == "change":
                # Mensaje indicando cambio de expediente
                user_message = HumanMessage(
                    content=f"Cambiar consulta a expediente: {expediente_number}"
                )
                assistant_message = AIMessage(
                    content=f"**Expediente cambiado:** {expediente_number}\n\nAhora puedes hacer cualquier consulta sobre este nuevo expediente. ¿Qué te gustaría saber?"
                )
            else:
                # Mensaje indicando establecimiento inicial del expediente
                user_message = HumanMessage(
                    content=f"Establecer consulta para expediente: {expediente_number}"
                )
                assistant_message = AIMessage(
                    content=f"**Expediente establecido:** {expediente_number}\n\nAhora puedes hacer cualquier consulta sobre este expediente. ¿Qué te gustaría saber?"
                )
            
            # Agregar mensajes al historial
            session_history.add_message(user_message)
            session_history.add_message(assistant_message)
            
            # Actualizar contador de mensajes en metadatos
            conversation_store.update_metadata(session_id)
            
            logger.info(f"Contexto de expediente {expediente_number} actualizado en sesión {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error actualizando contexto de expediente: {e}", exc_info=True)
            return False

# Inicializar servicio RAG
_rag_service = None

# Obtener instancia singleton del servicio RAG
async def get_rag_service() -> RAGChainService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGChainService()
    return _rag_service
