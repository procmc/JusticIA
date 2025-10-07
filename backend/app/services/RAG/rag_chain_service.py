from typing import Optional
from fastapi.responses import StreamingResponse
import re
import logging
import json

from .retriever import DynamicJusticIARetriever
from .langchain_chains import (
    create_conversational_rag_chain,
    create_expediente_specific_chain,
    stream_chain_response
)
from .session_store import conversation_store

logger = logging.getLogger(__name__)


class RAGChainService:
    def __init__(self):
        pass

    # =====================================================================
    # LANGCHAIN ARCHITECTURE (Modern)
    # =====================================================================
    
    async def consulta_con_historial_streaming(
        self,
        pregunta: str,
        session_id: str,
        top_k: int = 15,
        expediente_filter: Optional[str] = None
    ):
        # Actualizar metadatos de la sesión
        conversation_store.update_metadata(session_id)
        
        # Decidir flujo según expediente
        if expediente_filter and expediente_filter.strip():
            logger.info(f" FLUJO → EXPEDIENTE ESPECÍFICO: {expediente_filter}")
            return await self._consulta_expediente_con_historial(
                pregunta=pregunta,
                session_id=session_id,
                expediente_numero=expediente_filter.strip()
            )
        else:
            logger.info(f" FLUJO → GENERAL CON HISTORIAL")
            return await self._consulta_general_con_historial(
                pregunta=pregunta,
                session_id=session_id,
                top_k=top_k
            )
    
    async def _consulta_general_con_historial(
        self,
        pregunta: str,
        session_id: str,
        top_k: int = 50  # Aumentado para más contexto
    ):
        """
        Consulta general usando LangChain chains con historial automático.
        Usa SmartRetrieverRouter (V2) que decide automáticamente el modo.
        """
        logger.info(f" GENERAL CON HISTORIAL - Pregunta: '{pregunta[:50]}...', Session: {session_id}, Top-K: {top_k}")
        
        # Crear retriever con parámetros optimizados
        retriever = DynamicJusticIARetriever(
            top_k=top_k,
            similarity_threshold=0.3
        )
        
        # Crear chain conversacional
        chain = await create_conversational_rag_chain(
            retriever=retriever,
            with_history=True
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
                logger.error(f"❌ Error en streaming con historial: {e}", exc_info=True)
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
    
    async def _consulta_expediente_con_historial(
        self,
        pregunta: str,
        session_id: str,
        expediente_numero: str
    ):
        """
        Consulta de expediente específico usando LangChain chains con historial.
        """
        logger.info(f" EXPEDIENTE CON HISTORIAL - Número: {expediente_numero}")
        
        # Validar formato (acepta YY-NNNNNN-NNNN-XX o YYYY-NNNNNN-NNNN-XX)
        expediente_pattern = r'\b\d{2,4}-\d{6}-\d{4}-[A-Z]{2}\b'
        if not re.match(expediente_pattern, expediente_numero):
            logger.error(f"❌ Formato inválido: {expediente_numero}")
            # Fallback a general
            return await self._consulta_general_con_historial(
                pregunta=pregunta,
                session_id=session_id,
                top_k=15
            )
        
        # Actualizar metadatos con número de expediente
        conversation_store.update_metadata(
            session_id=session_id,
            expediente_number=expediente_numero
        )
        
        # Crear retriever configurado para expediente específico
        retriever = DynamicJusticIARetriever(
            top_k=50,
            similarity_threshold=0.2,
            expediente_filter=expediente_numero
        )
        
        logger.info(f"✅ DynamicJusticIARetriever creado para expediente {expediente_numero}")
        
        # Crear chain especializada para expedientes
        chain = await create_expediente_specific_chain(
            retriever=retriever,
            expediente_numero=expediente_numero,
            with_history=True
        )
        
        logger.info(f"✅ Chain expediente creada")
        
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
                logger.error(f"❌ Error en streaming expediente con historial: {e}", exc_info=True)
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

_rag_service = None

async def get_rag_service() -> RAGChainService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGChainService()
    return _rag_service
