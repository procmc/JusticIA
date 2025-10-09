from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.similarity_schemas import (
    SimilaritySearchRequest,
    RespuestaBusquedaSimilitud,
    GenerateResumenRequest,
    RespuestaGenerarResumen,
)
from app.services.busqueda_similares.similarity_service import SimilarityService
from app.services.bitacora_service import bitacora_service
from app.auth.jwt_auth import require_usuario_judicial
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/search", response_model=RespuestaBusquedaSimilitud)
async def search_similar_cases(
    data: SimilaritySearchRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
) -> RespuestaBusquedaSimilitud:
    """Buscar casos similares."""
    try:
        similarity_service = SimilarityService()
        result = await similarity_service.search_similar_cases(data)
        
        # Registrar búsqueda exitosa en bitácora
        await bitacora_service.registrar_busqueda_similares(
            db=db,
            usuario_id=current_user["user_id"],
            modo_busqueda=data.modo_busqueda,
            texto_consulta=data.texto_consulta,
            numero_expediente=data.numero_expediente,
            limite=data.limite,
            umbral_similitud=data.umbral_similitud,
            exito=True,
            resultado={
                "total_resultados": result.total_resultados,
                "tiempo_busqueda_segundos": result.tiempo_busqueda_segundos,
                "precision_promedio": result.precision_promedio,
                "casos_similares": [
                    {"CT_Num_expediente": caso.CT_Num_expediente} 
                    for caso in (result.casos_similares[:5] if result.casos_similares else [])
                ]
            }
        )
        
        return result
        
    except ValueError as e:
        # Errores de validación (400 Bad Request)
        logger.warning(f"Error de validación en búsqueda: {e}")
        
        # Registrar error en bitácora
        await bitacora_service.registrar_busqueda_similares(
            db=db,
            usuario_id=current_user["user_id"],
            modo_busqueda=data.modo_busqueda,
            texto_consulta=data.texto_consulta,
            numero_expediente=data.numero_expediente,
            limite=data.limite,
            umbral_similitud=data.umbral_similitud,
            exito=False,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
        
    except Exception as e:
        # Errores internos del servidor (500 Internal Server Error)
        logger.error(f"Error interno en búsqueda: {e}", exc_info=True)
        
        # Registrar error en bitácora
        await bitacora_service.registrar_busqueda_similares(
            db=db,
            usuario_id=current_user["user_id"],
            modo_busqueda=data.modo_busqueda,
            texto_consulta=data.texto_consulta,
            numero_expediente=data.numero_expediente,
            limite=data.limite,
            umbral_similitud=data.umbral_similitud,
            exito=False,
            error=f"Error interno del servidor: {str(e)}"
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error interno del servidor al realizar la búsqueda"
        )


@router.post("/generate-summary", response_model=RespuestaGenerarResumen)
async def generate_case_summary(
    data: GenerateResumenRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
) -> RespuestaGenerarResumen:
    """Generar resumen de IA para un expediente específico."""
    try:
        similarity_service = SimilarityService()
        result = await similarity_service.generate_case_summary(data.numero_expediente)
        
        # Registrar generación de resumen exitosa en bitácora
        await bitacora_service.registrar_resumen_ia(
            db=db,
            usuario_id=current_user["user_id"],
            numero_expediente=data.numero_expediente,
            exito=True,
            resultado={
                "total_documentos_analizados": result.total_documentos_analizados,
                "tiempo_generacion_segundos": result.tiempo_generacion_segundos,
                "resumen_ia": {
                    "resumen": result.resumen_ia.resumen if result.resumen_ia else "",
                    "palabras_clave": result.resumen_ia.palabras_clave if result.resumen_ia else [],
                    "factores_similitud": result.resumen_ia.factores_similitud if result.resumen_ia else [],
                    "conclusion": result.resumen_ia.conclusion if result.resumen_ia else ""
                }
            }
        )
        
        return result
        
    except ValueError as e:
        # Errores de validación (400 Bad Request)
        logger.warning(f"Error de validación en resumen: {e}")
        
        # Registrar error en bitácora
        await bitacora_service.registrar_resumen_ia(
            db=db,
            usuario_id=current_user["user_id"],
            numero_expediente=data.numero_expediente,
            exito=False,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
        
    except Exception as e:
        # Errores internos del servidor (500 Internal Server Error)
        logger.error(f"Error interno en resumen: {e}", exc_info=True)
        
        # Registrar error en bitácora
        await bitacora_service.registrar_resumen_ia(
            db=db,
            usuario_id=current_user["user_id"],
            numero_expediente=data.numero_expediente,
            exito=False,
            error=f"Error interno del servidor: {str(e)}"
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error interno del servidor al generar el resumen"
        )
