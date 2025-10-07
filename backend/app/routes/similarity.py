from fastapi import APIRouter, HTTPException, status, Request
from app.schemas.similarity_schemas import (
    SimilaritySearchRequest,
    RespuestaBusquedaSimilitud,
    GenerateResumenRequest,
    RespuestaGenerarResumen,
)
from app.services.busqueda_similares.similarity_service import SimilarityService
from app.auth.jwt_auth import require_role
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/search", response_model=RespuestaBusquedaSimilitud)
@require_role("Usuario Judicial")
async def search_similar_cases(
    request: Request,
    search_request: SimilaritySearchRequest,
    current_user: dict = None,
) -> RespuestaBusquedaSimilitud:
    """Buscar casos similares."""
    try:
        similarity_service = SimilarityService()
        result = await similarity_service.search_similar_cases(search_request)
        return result
        
    except ValueError as e:
        # Errores de validación (400 Bad Request)
        logger.warning(f"Error de validación en búsqueda: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
        
    except Exception as e:
        # Errores internos del servidor (500 Internal Server Error)
        logger.error(f"Error interno en búsqueda: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error interno del servidor al realizar la búsqueda"
        )


@router.post("/generate-summary", response_model=RespuestaGenerarResumen)
@require_role("Usuario Judicial")
async def generate_case_summary(
    request: Request,
    summary_request: GenerateResumenRequest,
    current_user: dict = None,
) -> RespuestaGenerarResumen:
    """Generar resumen de IA para un expediente específico."""
    try:
        similarity_service = SimilarityService()
        result = await similarity_service.generate_case_summary(summary_request.numero_expediente)
        return result
        
    except ValueError as e:
        # Errores de validación (400 Bad Request)
        logger.warning(f"Error de validación en resumen: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
        
    except Exception as e:
        # Errores internos del servidor (500 Internal Server Error)
        logger.error(f"Error interno en resumen: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error interno del servidor al generar el resumen"
        )
