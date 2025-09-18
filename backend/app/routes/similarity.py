from fastapi import APIRouter, HTTPException, status
from app.schemas.similarity_schemas import (
    SimilaritySearchRequest,
    RespuestaBusquedaSimilitud,
)
from app.services.busqueda_similares.similarity_service import SimilarityService

router = APIRouter()

@router.post("/search", response_model=RespuestaBusquedaSimilitud)
async def search_similar_cases(
    request: SimilaritySearchRequest,
) -> RespuestaBusquedaSimilitud:
    """Buscar casos similares."""
    try:
        similarity_service = SimilarityService()
        result = await similarity_service.search_similar_cases(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
