from typing import Optional
from fastapi.responses import StreamingResponse
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
        expediente_filter: Optional[str] = None
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
                expediente_numero=expediente_filter.strip()
            )
        else:
            logger.info(f"FLUJO: GENERAL CON HISTORIAL")
            # → VA AL FLUJO GENERAL
            return await self._consulta_general_con_historial(
                pregunta=pregunta,
                session_id=session_id,
                top_k=top_k
            )
    
    # Consulta general con historial
    async def _consulta_general_con_historial(
        self,
        pregunta: str,
        session_id: str,
        top_k: int = None  # None = usar valor del config
    ):
        # Usar valor del config si no se especifica
        if top_k is None:
            top_k = rag_config.TOP_K_GENERAL
        
        # IMPORTANTE: Limitar top_k máximo para evitar sobrecarga del LLM
        # Con gpt-oss:20b (32K ctx), máximo recomendado es ~15 documentos
        MAX_TOP_K = 15
        if top_k > MAX_TOP_K:
            print(f" top_k={top_k} excede el máximo recomendado. Limitando a {MAX_TOP_K}")
            top_k = MAX_TOP_K
        
        print(f"🔍 Consulta: '{pregunta[:60]}...' | Top-K: {top_k}")
        
        logger.info(
            f"General con historial - Pregunta: '{pregunta[:50]}...', "
            f"Session: {session_id}, Top-K: {top_k} "
            f"(threshold: {rag_config.SIMILARITY_THRESHOLD_GENERAL})"
        )
        
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
                async for chunk in stream_chain_response(chain, input_dict, config):
                    yield chunk
                
                # Auto-generar título si es el primer mensaje
                conversation_store.auto_generate_title(session_id)
                
            except Exception as e:
                print(f"❌ Error en streaming: {e}")
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
        expediente_numero: str
    ):
        """
        Consulta de expediente específico usando LangChain chains con historial.
        Usa configuración optimizada para expedientes específicos.
        """
        logger.info(f"Expediente con historial - Número: {expediente_numero}")
        
        # Validar formato del expediente ingresado
        expediente_pattern = r'\b\d{2,4}-\d{6}-\d{4}-[A-Z]{2}\b'
        if not re.match(expediente_pattern, expediente_numero):
            logger.error(f"Formato inválido: {expediente_numero}")
            # Fallback a general
            return await self._consulta_general_con_historial(
                pregunta=pregunta,
                session_id=session_id,
                top_k=None  # Usar valor del config
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
                async for chunk in stream_chain_response(chain, input_dict, config):
                    yield chunk # Envía cada pedacito al frontend
                
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
