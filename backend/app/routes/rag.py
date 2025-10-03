from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from app.services.RAG.rag_chain_service import get_rag_service
from app.services.context_analyzer import context_analyzer
from app.utils.security_validator import validate_user_input, context_manager
import logging
import json

logger = logging.getLogger(__name__)


# Clase compatible con el frontend actual
class ConsultaGeneralRequest(BaseModel):
    query: str
    top_k: int = 30
    has_context: bool = False
    expediente_number: Optional[str] = None  # Para consultas por expediente específico

router = APIRouter(prefix="/rag", tags=["RAG - Consultas Inteligentes"])

@router.post("/consulta-general-stream")
async def consulta_general_rag_stream(
    request: ConsultaGeneralRequest, rag_service=Depends(get_rag_service)
):
    """
    Endpoint de streaming optimizado con RAG Chain.
    Migrado desde /llm/consulta-general-stream para usar el nuevo sistema RAG.
    """
    try:
        if not request.query.strip():
            raise HTTPException(
                status_code=400, detail="La consulta no puede estar vacía"
            )
        
        # Validación de seguridad
        security_result = validate_user_input(request.query)
        
        if security_result.should_block:
            # Retornar respuesta de seguridad como streaming
            async def security_response():
                response_data = {
                    "type": "chunk", 
                    "content": security_result.response_override,
                    "done": False
                }
                yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
                
                done_data = {"type": "done", "content": "", "done": True}
                yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
            
            return StreamingResponse(
                security_response(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                }
            )
        
        # Usar texto sanitizado
        query_to_use = security_result.sanitized_text if security_result.sanitized_text else request.query

        logger.info(f"Consulta general RAG streaming: {request.query}")

        # Extraer contexto de conversación SOLO si realmente está presente
        conversation_context = ""
        actual_query = request.query
        
        if request.has_context and request.query.strip():
            # Buscar el separador específico que usa el frontend
            separator = "\n\n---\nNUEVA CONSULTA:"
            if separator in request.query:
                parts = request.query.split(separator)
                if len(parts) == 2:
                    potential_context = parts[0].strip()
                    if potential_context and "HISTORIAL DE CONVERSACIÓN PREVIA:" in potential_context:
                        conversation_context = potential_context
                        actual_query = parts[1].strip()
                        logger.info(f"✅ Contexto extraído correctamente, query separada")
                    else:
                        actual_query = query_to_use.strip()
                        logger.info(f"❌ No se encontró contexto válido con el separador")
                else:
                    actual_query = request.query.strip()
                    logger.info(f"❌ Separador encontrado pero partes incorrectas: {len(parts)}")
            else:
                # Fallback al método anterior para compatibilidad
                query_parts = request.query.split("\n\n")
                if len(query_parts) > 1:
                    potential_context = query_parts[0].strip()
                    if potential_context and "HISTORIAL DE CONVERSACIÓN PREVIA:" in potential_context:
                        conversation_context = potential_context
                        actual_query = query_parts[-1].strip()
                        logger.info(f"✅ Contexto extraído con método fallback")
                    else:
                        actual_query = request.query.strip()
                        logger.info(f"❌ Fallback - no se encontró contexto válido")
                else:
                    actual_query = request.query.strip()
                    logger.info(f"❌ No hay partes suficientes para extraer contexto")
        
        # Truncar contexto si es demasiado largo
        if conversation_context:
            original_length = len(conversation_context)
            conversation_context = context_manager.truncate_context(conversation_context, query_to_use)
            if len(conversation_context) < original_length:
                logger.info(f"📏 Contexto truncado de {original_length} a {len(conversation_context)} caracteres")
        
        logger.info(f"Procesado - Query: '{actual_query}', Contexto: {'SÍ' if conversation_context else 'NO'}")
        if conversation_context:
            logger.info(f"📋 Contexto completo ({len(conversation_context)} chars): {conversation_context[:300]}...")
        else:
            logger.info("📋 Sin contexto de conversación")

        # NUEVO: Analizar intención de la consulta
        intent_analysis = context_analyzer.analyze_query_intent(
            actual_query, 
            has_context=bool(conversation_context)
        )
        
        logger.info(f"🧠 Análisis de intención: {intent_analysis}")
        
        # SEPARACIÓN DE RESPONSABILIDADES HABILITADA
        if intent_analysis['intent'] == 'context_only' and conversation_context:
            logger.info("📚 Usando SOLO contexto previo (sin búsqueda en BD)")
            return await rag_service.responder_solo_con_contexto(
                pregunta=actual_query,
                conversation_context=conversation_context
            )
        else:
            logger.info("🔍 Usando búsqueda en BD + contexto")
        
        # DIFERENCIAR ENTRE CONSULTA GENERAL Y CONSULTA POR EXPEDIENTE ESPECÍFICO
        import re
        expediente_filter = ""
        
        # 1. Si viene expediente_number del frontend (modo expediente específico)
        if request.expediente_number:
            expediente_filter = request.expediente_number.strip()
            logger.info(f"🎯 MODO EXPEDIENTE ESPECÍFICO: {expediente_filter}")
            logger.info(f"📝 Consulta sobre expediente: '{actual_query}'")
            
        # 2. Si no, buscar en la consulta si menciona un expediente (modo general con referencia)
        else:
            expediente_pattern = r'(?:Consulta sobre expediente|Expediente)\s+(\d{4}-\d{6}-\d{4}-[A-Z]{2})'
            expediente_match = re.search(expediente_pattern, actual_query)
            
            if expediente_match:
                expediente_filter = expediente_match.group(1)
                # Limpiar la consulta removiendo la referencia al expediente
                actual_query = re.sub(r'Consulta sobre expediente\s+\d{4}-\d{6}-\d{4}-[A-Z]{2}:\s*', '', actual_query)
                logger.info(f"🔍 MODO GENERAL con referencia a expediente: {expediente_filter}")
            else:
                logger.info(f"🌐 MODO GENERAL sin expediente específico")
        
        # Usar el servicio RAG completo con búsqueda
        return await rag_service.consulta_general_streaming(
            pregunta=actual_query,
            top_k=min(request.top_k, 30),
            conversation_context=conversation_context,
            expediente_filter=expediente_filter
        )

    except Exception as e:
        logger.error(f"Error en consulta general RAG streaming: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error procesando consulta: {str(e)}"
        )
