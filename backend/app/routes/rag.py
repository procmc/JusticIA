from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.services.RAG.rag_chain_service import get_rag_service
import logging

logger = logging.getLogger(__name__)


# Clase compatible con el frontend actual
class ConsultaGeneralRequest(BaseModel):
    query: str
    top_k: int = 30
    has_context: bool = False

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
                        actual_query = request.query.strip()
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
        
        logger.info(f"Procesado - Query: '{actual_query}', Contexto: {'SÍ' if conversation_context else 'NO'}")
        if conversation_context:
            logger.info(f"📋 Contexto completo ({len(conversation_context)} chars): {conversation_context[:300]}...")
        else:
            logger.info("📋 Sin contexto de conversación")

        # Usar el servicio RAG optimizado con streaming
        return await rag_service.consulta_general_streaming(
            pregunta=actual_query,
            top_k=min(request.top_k, 6),  # Optimizado para streaming rápido
            conversation_context=conversation_context,
        )

    except Exception as e:
        logger.error(f"Error en consulta general RAG streaming: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error procesando consulta: {str(e)}"
        )
