"""
Rutas de Consulta y Estadísticas de la Bitácora de Auditoría.

Este módulo define endpoints REST para consultar y analizar los registros de bitácora
del sistema JusticIA. Todos los eventos críticos del sistema (login, logout, consultas RAG,
modificaciones de usuarios, acceso a archivos, etc.) se registran en la bitácora.

Arquitectura de bitácora:
    - Registro automático de eventos críticos en toda la aplicación
    - Filtrado múltiple: usuario, tipo de acción, expediente, rango de fechas
    - Paginación server-side para eficiencia con grandes volúmenes
    - Estadísticas agregadas para dashboards administrativos
    - Historial personal para usuarios no administradores

Endpoints principales:
    - GET /bitacora/registros: Consulta con filtros y paginación (admin)
    - GET /bitacora/estadisticas: Estadísticas generales del sistema (admin)
    - GET /bitacora/estadisticas-rag: Estadísticas específicas de RAG (admin)
    - GET /bitacora/mi-historial: Historial del usuario autenticado (todos)
    - GET /bitacora/expediente/{numero}: Historial de un expediente (todos)
    - POST /bitacora/registrar-exportacion: Registra exportación de reporte (admin)

Filtros soportados:
    - usuario: Búsqueda por nombre o correo
    - tipoAccion: ID del tipo de acción (1-15, ver TiposAccion)
    - expediente: Número de expediente
    - fechaInicio, fechaFin: Rango de fechas
    - limite, offset: Paginación

Tipos de acción (TiposAccion):
    1: LOGIN, 2: LOGOUT, 3: CREAR_USUARIO, 4: EDITAR_USUARIO,
    5: RESETEAR_PASSWORD, 6: CONSULTA_RAG, 7: LISTAR_ARCHIVOS,
    8: DESCARGAR_ARCHIVO, 9: EXPORTAR_BITACORA, etc.

Example:
    ```python
    # Consultar registros con filtros (administrador)
    response = await client.get("/bitacora/registros", params={
        "usuario": "jperez",
        "tipoAccion": 6,  # CONSULTA_RAG
        "fechaInicio": "2024-01-01T00:00:00",
        "fechaFin": "2024-01-31T23:59:59",
        "limite": 50,
        "offset": 0
    }, headers={"Authorization": f"Bearer {admin_token}"})
    
    print(f"Total: {response['total']} registros")
    print(f"Página {response['page']} de {response['pages']}")
    
    # Obtener estadísticas RAG
    stats = await client.get("/bitacora/estadisticas-rag", params={"dias": 30})
    print(f"Total consultas RAG: {stats['totalConsultasRAG']}")
    print(f"Consultas generales: {stats['consultasGenerales']}")
    print(f"Consultas por expediente: {stats['consultasExpediente']}")
    
    # Ver mi historial (usuario)
    mi_historial = await client.get("/bitacora/mi-historial",
        params={"limite": 100},
        headers={"Authorization": f"Bearer {user_token}"})
    ```

Note:
    Importante: Los endpoints de consulta de bitácora NO registran su propia
    consulta para evitar loops infinitos de auditoría.

Compatibilidad Frontend:
    Diseñado para funcionar con:
    - frontend/components/administracion/bitacora/Bitacora.jsx
    - frontend/components/administracion/bitacora/FiltrosBitacora.jsx
    - frontend/components/administracion/bitacora/DashboardEstadisticas.jsx

See Also:
    - app.services.bitacora.bitacora_service: Registro de eventos
    - app.services.bitacora.bitacora_stats_service: Consultas y estadísticas
    - app.constants.tipos_accion.TiposAccion: Catálogo de tipos de acción
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
    tipoAccion: Optional[int] = Query(None, ge=1, le=15, description="Filtrar por tipo de acción (ID)"),
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
    - tipoAccion: ID del tipo de acción (1-15)
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


@router.get("/estadisticas-rag", response_model=dict)
async def obtener_estadisticas_rag(
    dias: int = Query(30, ge=1, le=365, description="Número de días hacia atrás"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_administrador)
):
    """
    Obtiene estadísticas específicas de consultas RAG distinguiendo entre
    consultas generales y consultas por expediente específico.
    
    Retorna:
    - totalConsultasRAG: Total de consultas RAG
    - consultasGenerales: Consultas sin expediente específico
    - consultasExpediente: Consultas con expediente específico
    - porcentajeGenerales: % de consultas generales
    - porcentajeExpedientes: % de consultas por expediente
    - usuariosActivosRAG: Usuarios únicos que usan RAG
    - expedientesConsultadosRAG: Expedientes únicos consultados
    - expedientesMasConsultadosRAG: Top 5 expedientes más consultados
    - actividadRAGPorDia: Actividad diaria últimos 7 días
    """
    try:
        estadisticas_rag = bitacora_stats_service.obtener_estadisticas_rag(db=db, dias=dias)
        return estadisticas_rag
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas RAG: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas RAG: {str(e)}"
        )


@router.get("/mi-historial", response_model=List[dict])
async def obtener_mi_historial(
    limite: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    tipoAccion: Optional[int] = Query(None, ge=1, le=15, description="Filtrar por tipo de acción"),
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
