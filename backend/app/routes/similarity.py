from fastapi import APIRouter, HTTPException, status
from typing import List
from datetime import datetime
import logging

from app.schemas.similarity_schemas import (
    SimilaritySearchRequest, 
    SimilaritySearchResponse,
    SimilarCase,
    DocumentMatch
)
from app.services.busqueda_similares import SimilarityService

# Instancia global del servicio
similarity_service = SimilarityService()
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/search", 
    response_model=SimilaritySearchResponse,
    summary="Buscar casos similares",
    description="Busca expedientes similares basándose en criterios específicos (por descripción o por expediente)."
)
async def search_similar_cases(
    request: SimilaritySearchRequest
) -> SimilaritySearchResponse:
    """
    Endpoint principal para búsqueda de casos similares
    """
    try:
        import time
        start_time = time.time()
        
        # Realizar búsqueda usando el nuevo servicio modular
        casos_similares_dict = await similarity_service.search_similar_cases(request)
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Adaptar resultados al esquema esperado
        adapted_cases = []
        for case_dict in casos_similares_dict:
            # Adaptar documentos coincidentes
            matched_documents = []
            for i, doc in enumerate(case_dict.get("matching_documents", [])[:5]):
                matched_doc = DocumentMatch(
                    document_id=i + 1,
                    document_name=doc.get("document_name", "Documento sin nombre"),
                    similarity_score=doc.get("similarity_score", 0.0),
                    text_fragment=doc.get("content_preview", "")[:500],
                    page_number=None
                )
                matched_documents.append(matched_doc)
            
            # Crear caso adaptado
            try:
                expedient_id_int = int(case_dict.get("expedient_id", 0))
            except (ValueError, TypeError):
                expedient_id_int = hash(str(case_dict.get("expedient_id", ""))) % 1000000
            
            adapted_case = SimilarCase(
                expedient_id=expedient_id_int,
                expedient_number=str(case_dict.get("expedient_id", "")),
                similarity_percentage=case_dict.get("similarity_score", 0.0) * 100,
                document_count=len(case_dict.get("matching_documents", [])),
                matched_documents=matched_documents,
                creation_date=datetime.now(),
                last_activity_date=None,
                court_instance=None
            )
            adapted_cases.append(adapted_case)
        
        # Construir respuesta completa
        search_criteria = (
            request.expedient_number if request.search_mode == "expedient" 
            else request.query_text
        )
        
        response = SimilaritySearchResponse(
            search_criteria=search_criteria or "",
            search_mode=request.search_mode,
            total_results=len(adapted_cases),
            execution_time_ms=execution_time_ms,
            similarity_threshold=request.similarity_threshold,
            similar_cases=adapted_cases,
            total_documents_analyzed=sum(case.document_count for case in adapted_cases)
        )
        
        return response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "VALIDATION_ERROR",
                "error_message": str(e),
                "details": "Verifique los parámetros de búsqueda proporcionados"
            }
        )
    except Exception as e:
        logger.error(f"Error en búsqueda de similares: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "error_message": "Error interno del servidor",
                "details": str(e) if isinstance(e, (ValueError, TypeError)) else "Error procesando búsqueda"
            }
        )
