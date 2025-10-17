"""
Rutas para gestión y consulta de bitácora de acciones.
Endpoints compatibles con los componentes del frontend en:
- frontend/components/administracion/bitacora/
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from app.db.database import get_db
from app.auth.jwt_auth import require_administrador, require_usuario_judicial
from app.services.bitacora.bitacora_service import bitacora_service
from app.services.bitacora.bitacora_stats_service import bitacora_stats_service
from app.schemas.bitacora_schemas import BitacoraRespuesta, EstadisticasBitacora
from app.constants.tipos_accion import TiposAccion

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/registros", response_model=dict)
async def obtener_registros(
    usuario: Optional[str] = Query(None, description="Filtrar por nombre o correo de usuario"),
    tipoAccion: Optional[int] = Query(None, ge=1, le=8, description="Filtrar por tipo de acción (ID)"),
    expediente: Optional[str] = Query(None, description="Filtrar por número de expediente"),
    fechaInicio: Optional[datetime] = Query(None, description="Fecha de inicio del rango"),
    fechaFin: Optional[datetime] = Query(None, description="Fecha de fin del rango"),
    limite: int = Query(10, ge=1, le=100, description="Registros por página (default: 10, max: 100)"),
    offset: int = Query(0, ge=0, description="Registros a saltar para paginación (default: 0)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_administrador)
):
    """
    Obtiene registros de bitácora con filtros múltiples y paginación server-side.
    Endpoint principal para el componente Bitacora.jsx
    Solo accesible para administradores.
    
    Query params compatibles con FiltrosBitacora.jsx:
    - usuario: Nombre o correo del usuario
    - tipoAccion: ID del tipo de acción (1-8)
    - expediente: Número de expediente
    - fechaInicio, fechaFin: Rango de fechas
    - limite: Registros por página (default: 10, max: 100)
    - offset: Registros a saltar (default: 0, calculado automáticamente por frontend)
    
    Returns:
        {
            "items": [...],      // Lista de registros
            "total": 1523,       // Total de registros que coinciden con filtros
            "page": 2,           // Página actual
            "pages": 31,         // Total de páginas
            "limit": 50,         // Registros por página
            "offset": 50         // Offset usado
        }
    """
    try:
        resultado = bitacora_stats_service.obtener_con_filtros(
            db=db,
            usuario_id=usuario,
            tipo_accion_id=tipoAccion,
            expediente_numero=expediente,
            fecha_inicio=fechaInicio,
            fecha_fin=fechaFin,
            limite=limite,
            offset=offset
        )
        
        # NOTA: NO se registra la consulta de bitácora para evitar loop infinito
        # (consultar bitácora → registrar consulta → aparece en bitácora → registrar consulta → ...)
        
        return resultado
        
    except Exception as e:
        logger.error(f"Error obteniendo registros de bitácora: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener registros: {str(e)}"
        )


@router.get("/estadisticas", response_model=dict)
async def obtener_estadisticas(
    dias: int = Query(30, ge=1, le=365, description="Número de días hacia atrás"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_administrador)
):
    """
    Obtiene estadísticas agregadas de la bitácora.
    Endpoint para el componente DashboardEstadisticas.jsx
    
    Retorna:
    - registrosHoy: Conteo de registros de hoy
    - registros7Dias: Conteo últimos 7 días
    - registros30Dias: Conteo últimos 30 días
    - totalRegistros: Total histórico
    - usuariosUnicos: Usuarios únicos activos
    - expedientesUnicos: Expedientes únicos
    - accionesPorTipo: Array con {tipo, cantidad}
    """
    try:
        estadisticas = bitacora_stats_service.obtener_estadisticas(db=db, dias=dias)
        return estadisticas
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )


@router.get("/mi-historial", response_model=List[dict])
async def obtener_mi_historial(
    limite: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    tipoAccion: Optional[int] = Query(None, ge=1, le=8, description="Filtrar por tipo de acción"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial)
):
    """
    Obtiene el historial de bitácora del usuario autenticado.
    Endpoint para que usuarios vean sus propias acciones.
    Accesible para usuarios judiciales y administradores.
    """
    try:
        registros = bitacora_stats_service.obtener_con_filtros(
            db=db,
            usuario_id=current_user["user_id"],
            tipo_accion_id=tipoAccion,
            limite=limite
        )
        
        return registros
        
    except Exception as e:
        logger.error(f"Error obteniendo historial propio: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener historial: {str(e)}"
        )


@router.get("/expediente/{expediente_numero}", response_model=List[dict])
async def obtener_historial_expediente(
    expediente_numero: str,
    limite: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial)
):
    """
    Obtiene el historial de bitácora de un expediente específico.
    Muestra todas las acciones realizadas sobre ese expediente.
    Útil para auditoría de expedientes.
    """
    try:
        registros = bitacora_stats_service.obtener_con_filtros(
            db=db,
            expediente_numero=expediente_numero,
            limite=limite
        )
        
        return registros
        
    except Exception as e:
        logger.error(f"Error obteniendo historial de expediente {expediente_numero}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener historial: {str(e)}"
        )


@router.post("/registrar-exportacion")
async def registrar_exportacion(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_administrador)
):
    """
    Registra la acción de exportación de bitácora a PDF.
    Se llama desde el frontend después de generar el PDF exitosamente.
    """
    try:
        await bitacora_service.registrar(
            db=db,
            usuario_id=current_user["user_id"],
            tipo_accion_id=TiposAccion.EXPORTAR_BITACORA,
            texto="Exportación de reporte de bitácora a PDF"
        )
        
        return {"success": True, "message": "Exportación registrada en bitácora"}
        
    except Exception as e:
        logger.error(f"Error registrando exportación: {e}")
        # No lanzamos error para no bloquear la exportación
        return {"success": False, "message": "Error al registrar exportación"}
