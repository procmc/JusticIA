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
from app.constants.tipos_accion import TiposAccion
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
    # Determinar el texto de búsqueda según el modo
    texto_busqueda = data.texto_consulta if data.modo_busqueda == "descripcion" else data.numero_expediente
    
    # Obtener ID del expediente si estamos buscando por expediente (ANTES del try para capturarlo en errores)
    expediente_db_id = None
    if data.modo_busqueda == "expediente" and data.numero_expediente:
        from app.repositories.expediente_repository import ExpedienteRepository
        expediente_repo = ExpedienteRepository()
        expediente_obj = expediente_repo.obtener_por_numero(db, data.numero_expediente)
        if expediente_obj:
            expediente_db_id = expediente_obj.CN_Id_expediente
    
    try:
        similarity_service = SimilarityService()
        result = await similarity_service.search_similar_cases(data)
        
        # Registrar búsqueda exitosa en bitácora con información completa
        await bitacora_service.registrar(
            db=db,
            usuario_id=current_user["user_id"],
            tipo_accion_id=TiposAccion.BUSQUEDA_SIMILARES,
            texto=f"Búsqueda de casos similares ({data.modo_busqueda}): '{texto_busqueda[:200] if texto_busqueda else 'N/A'}'",
            expediente_id=expediente_db_id,
            info_adicional={
                "modo_busqueda": data.modo_busqueda,
                "texto_consulta": data.texto_consulta,
                "numero_expediente": data.numero_expediente,
                "limite": data.limite,
                "umbral_similitud": data.umbral_similitud,
                "total_resultados": result.total_resultados,
                "tiempo_busqueda_segundos": result.tiempo_busqueda_segundos,
                "precision_promedio": result.precision_promedio,
                "top_expedientes": [caso.CT_Num_expediente for caso in (result.casos_similares[:5] if result.casos_similares else [])]
            }
        )
        
        return result
        
    except ValueError as e:
        # Errores de validación (400 Bad Request)
        logger.warning(f"Error de validación en búsqueda: {e}")
        
        # Registrar error en bitácora (expediente_db_id ya está capturado)
        await bitacora_service.registrar(
            db=db,
            usuario_id=current_user["user_id"],
            tipo_accion_id=TiposAccion.BUSQUEDA_SIMILARES,
            texto=f"Error de validación en búsqueda: {str(e)[:200]}",
            expediente_id=expediente_db_id,
            info_adicional={
                "modo_busqueda": data.modo_busqueda,
                "texto_consulta": data.texto_consulta,
                "numero_expediente": data.numero_expediente,
                "error": str(e),
                "tipo_error": "validacion"
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
        
    except Exception as e:
        # Errores internos del servidor (500 Internal Server Error)
        logger.error(f"Error interno en búsqueda: {e}", exc_info=True)
        
        # Registrar error en bitácora (expediente_db_id ya está capturado)
        await bitacora_service.registrar(
            db=db,
            usuario_id=current_user["user_id"],
            tipo_accion_id=TiposAccion.BUSQUEDA_SIMILARES,
            texto=f"Error interno en búsqueda de casos similares: {str(e)[:150]}",
            expediente_id=expediente_db_id,
            info_adicional={
                "modo_busqueda": data.modo_busqueda,
                "texto_consulta": data.texto_consulta,
                "numero_expediente": data.numero_expediente,
                "error": str(e),
                "tipo_error": "interno"
            }
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
    # Obtener ID del expediente ANTES del try para capturarlo en errores
    expediente_db_id = None
    if data.numero_expediente:
        from app.repositories.expediente_repository import ExpedienteRepository
        expediente_repo = ExpedienteRepository()
        expediente_obj = expediente_repo.obtener_por_numero(db, data.numero_expediente)
        if expediente_obj:
            expediente_db_id = expediente_obj.CN_Id_expediente
    
    try:
        similarity_service = SimilarityService()
        result = await similarity_service.generate_case_summary(data.numero_expediente)
        
        # Registrar generación de resumen exitosa en bitácora con información completa
        await bitacora_service.registrar(
            db=db,
            usuario_id=current_user["user_id"],
            tipo_accion_id=TiposAccion.BUSQUEDA_SIMILARES,  # Usamos el mismo tipo ya que está relacionado
            texto=f"Resumen IA generado para expediente: {data.numero_expediente}",
            expediente_id=expediente_db_id,
            info_adicional={
                "numero_expediente": data.numero_expediente,
                "resumen_generado": True,
                "documentos_analizados": result.total_documentos_analizados,
                "tiempo_generacion_segundos": result.tiempo_generacion_segundos,
                "longitud_resumen": len(result.resumen_ia.resumen) if result.resumen_ia and result.resumen_ia.resumen else 0,
                "total_palabras_clave": len(result.resumen_ia.palabras_clave) if result.resumen_ia and result.resumen_ia.palabras_clave else 0,
                "total_factores_similitud": len(result.resumen_ia.factores_similitud) if result.resumen_ia and result.resumen_ia.factores_similitud else 0,
                "tiene_conclusion": bool(result.resumen_ia.conclusion) if result.resumen_ia else False
            }
        )
        
        return result
        
    except ValueError as e:
        # Errores de validación (400 Bad Request)
        logger.warning(f"Error de validación en resumen: {e}")
        
        # Registrar error en bitácora (expediente_db_id ya está capturado)
        await bitacora_service.registrar(
            db=db,
            usuario_id=current_user["user_id"],
            tipo_accion_id=TiposAccion.BUSQUEDA_SIMILARES,
            texto=f"Error de validación al generar resumen: {str(e)[:200]}",
            expediente_id=expediente_db_id,
            info_adicional={
                "numero_expediente": data.numero_expediente,
                "error": str(e),
                "tipo_error": "validacion"
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
        
    except Exception as e:
        # Errores internos del servidor (500 Internal Server Error)
        logger.error(f"Error interno en resumen: {e}", exc_info=True)
        
        # Registrar error en bitácora (expediente_db_id ya está capturado)
        await bitacora_service.registrar(
            db=db,
            usuario_id=current_user["user_id"],
            tipo_accion_id=TiposAccion.BUSQUEDA_SIMILARES,
            texto=f"Error interno al generar resumen: {data.numero_expediente} - {str(e)[:150]}",
            expediente_id=expediente_db_id,
            info_adicional={
                "numero_expediente": data.numero_expediente,
                "error": str(e),
                "tipo_error": "interno"
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error interno del servidor al generar el resumen"
        )
