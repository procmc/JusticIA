from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from app.services.RAG.rag_chain_service import get_rag_service
import logging
import json

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/rag", tags=["RAG - Consultas Inteligentes"])

# =====================================================================
# NUEVA ARQUITECTURA LANGCHAIN - ÚNICO ENDPOINT
# =====================================================================


# =====================================================================
# NUEVO ENDPOINT CON SESSION MANAGEMENT
# =====================================================================

class ConsultaConHistorialRequest(BaseModel):
    """Request para consultas con gestión de historial por session_id"""
    query: str
    session_id: str
    top_k: int = 15
    expediente_number: Optional[str] = None  # Opcional, para consultas de expediente específico


@router.post("/consulta-con-historial-stream")
async def consulta_con_historial_stream(
    request: ConsultaConHistorialRequest,
    rag_service=Depends(get_rag_service)
):
    """
    🆕 Endpoint NUEVO con gestión automática de historial conversacional.
    
    Diferencias con /consulta-general-stream:
    - Recibe `session_id` en lugar de enviar todo el contexto histórico
    - Backend gestiona historial automáticamente con LangChain
    - Reformulación automática de preguntas con contexto
    - Detección mejorada de referencias ("ese caso", "el último", etc.)
    
    Request Body:
    {
        "query": "¿Qué más se menciona?",  // Solo la pregunta actual
        "session_id": "session_user@example.com_1696425015000",  // ID de sesión
        "top_k": 15,  // Opcional, default 15
        "expediente_number": "2022-123456-7890-LA"  // Opcional
    }
    
    Response:
    - Streaming SSE con chunks de respuesta
    - Historial se guarda automáticamente en backend
    - Frontend no necesita enviar mensajes previos
    
    Ventajas:
    - Payloads más pequeños (solo query + session_id)
    - Reformulación automática con LLM
    - Backend como fuente única de verdad para historial
    - Mejor detección de referencias contextuales
    """
    try:
        # Validar entrada
        if not request.query.strip():
            raise HTTPException(
                status_code=400,
                detail="La consulta no puede estar vacía"
            )
        
        if not request.session_id.strip():
            raise HTTPException(
                status_code=400,
                detail="session_id es requerido"
            )
        
        # Usar query directamente (sin validación de seguridad por ahora)
        query_to_use = request.query
        
        logger.info(f"🆕 Consulta con historial - Session: {request.session_id}")
        logger.info(f"🆕 Query: {query_to_use[:100]}...")
        logger.info(f"🆕 Expediente: {request.expediente_number or 'None'}")
        
        # Llamar al nuevo método con gestión de historial
        return await rag_service.consulta_con_historial_streaming(
            pregunta=query_to_use,
            session_id=request.session_id,
            top_k=min(request.top_k, 30),
            expediente_filter=request.expediente_number
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en consulta con historial: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando consulta con historial: {str(e)}"
        )

