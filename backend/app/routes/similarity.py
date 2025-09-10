from fastapi import APIRouter, HTTPException, status
from typing import Optional

from app.schemas.similarity_schemas import (
    SimilaritySearchRequest, 
    SimilaritySearchResponse,
    SimilaritySearchError
)
from app.services.similarity_service import similarity_service

router = APIRouter()


@router.post(
    "/search", 
    response_model=SimilaritySearchResponse,
    summary="Buscar casos similares",
    description="""
    Busca expedientes similares basándose en criterios específicos.
    
    **Modos de búsqueda:**
    - `description`: Búsqueda por texto libre describiendo el caso
    - `expedient`: Búsqueda de expedientes similares a uno específico
    
    **Parámetros importantes:**
    - `similarity_threshold`: Umbral mínimo de similitud (0.0 a 1.0)
    - `limit`: Número máximo de expedientes a retornar
    
    **Respuesta:**
    - Lista de expedientes ordenados por similitud descendente
    - Cada expediente incluye documentos coincidentes y porcentaje de similitud
    - Metadatos de la búsqueda (tiempo de ejecución, documentos analizados, etc.)
    """,
    responses={
        200: {
            "description": "Búsqueda exitosa",
            "model": SimilaritySearchResponse
        },
        400: {
            "description": "Parámetros de búsqueda inválidos",
            "model": SimilaritySearchError
        },
        401: {
            "description": "No autorizado"
        },
        500: {
            "description": "Error interno del servidor",
            "model": SimilaritySearchError
        }
    }
)
async def search_similar_cases(
    request: SimilaritySearchRequest
) -> SimilaritySearchResponse:
    """
    Endpoint principal para búsqueda de casos similares
    """
    try:
        # Realizar búsqueda sin autenticación por ahora
        # TODO: Agregar autenticación cuando esté configurada
        result = await similarity_service.search_similar_cases(
            request=request,
            user_id=None  # Sin usuario por ahora
        )
        
        return result
        
    except ValueError as e:
        # Errores de validación
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "VALIDATION_ERROR",
                "error_message": str(e),
                "details": "Verifique los parámetros de búsqueda proporcionados"
            }
        )
    except Exception as e:
        # Errores internos
        print(f"Error en búsqueda de similares: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "error_message": "Error interno del servidor",
                "details": str(e) if isinstance(e, (ValueError, TypeError)) else "Error procesando búsqueda"
            }
        )


@router.get(
    "/expedient/{expedient_number}",
    response_model=SimilaritySearchResponse,
    summary="Buscar expedientes similares a uno específico",
    description="""
    Busca expedientes similares a un expediente específico usando su número.
    
    Este endpoint es una forma simplificada de usar el modo 'expedient' 
    del endpoint principal de búsqueda.
    """
)
async def search_similar_to_expedient(
    expedient_number: str,
    limit: int = 30,
    similarity_threshold: float = 0.5
) -> SimilaritySearchResponse:
    """
    Busca expedientes similares a un expediente específico
    """
    try:
        # Crear request automáticamente
        request = SimilaritySearchRequest(
            search_mode="expedient",
            expedient_number=expedient_number,
            limit=limit,
            similarity_threshold=similarity_threshold
        )
        
        # Realizar búsqueda sin autenticación por ahora
        # TODO: Agregar autenticación cuando esté configurada
        result = await similarity_service.search_similar_cases(
            request=request,
            user_id=None  # Sin usuario por ahora
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "VALIDATION_ERROR",
                "error_message": str(e),
                "details": f"Número de expediente inválido: {expedient_number}"
            }
        )
    except Exception as e:
        print(f"Error en búsqueda por expediente: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "error_message": "Error interno del servidor",
                "details": str(e) if isinstance(e, (ValueError, TypeError)) else "Error procesando búsqueda"
            }
        )


@router.get(
    "/health",
    summary="Health check del servicio de similitud",
    description="Verifica que el servicio de búsqueda de similares esté funcionando correctamente"
)
async def similarity_health_check():
    """
    Health check específico para el servicio de similitud
    """
    try:
        from app.vectorstore.vectorstore import get_vectorstore
        from app.config.config import COLLECTION_NAME
        
        # Verificar conexión con Milvus
        client = await get_vectorstore()
        stats = client.get_collection_stats(collection_name=COLLECTION_NAME)
        
        return {
            "status": "healthy",
            "service": "similarity_search",
            "vectorstore_status": "connected",
            "collection_stats": stats,
            "timestamp": "2025-09-10T14:30:00Z"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "service": "similarity_search",
                "error": str(e),
                "timestamp": "2025-09-10T14:30:00Z"
            }
        )
