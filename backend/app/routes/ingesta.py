from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.auth.jwt_auth import require_usuario_judicial
from app.services.documentos.file_management_service import file_management_service
from app.services.bitacora.bitacora_service import bitacora_service
from app.constants.tipos_accion import TiposAccion
import logging
from celery.result import AsyncResult
from celery_app import celery_app

router = APIRouter()
logger = logging.getLogger(__name__)


# Endpoint principal para consultar progreso de tareas
@router.get("/progress/{task_id}")
async def consultar_progreso_tarea(
    task_id: str,
    current_user: dict = Depends(require_usuario_judicial),
):
    """
    Consulta el estado y progreso de una tarea Celery.
    Usa ProgressTracker para progreso granular, con fallback a Celery.
    """
    from app.services.ingesta.async_processing.progress_tracker import progress_manager
    
    # Intentar obtener progreso detallado del ProgressTracker
    progress = progress_manager.get_status(task_id)
    
    if progress:
        # ProgressTracker tiene información detallada
        return {
            "task_id": task_id,
            "status": progress.get("status"),
            "progress": progress.get("progress", 0),
            "message": progress.get("message", "Procesando..."),
            "resultado": None,
            "ready": progress.get("status") in ["completado", "fallido", "cancelado"],
        }
    
    # Fallback: Consultar Celery directamente
    result = AsyncResult(task_id)
    
    # Mapear estados de Celery a español
    if result.state == "SUCCESS":
        return {
            "task_id": task_id,
            "status": "completado",
            "progress": 100,
            "message": "Procesado exitosamente",
            "resultado": result.result,
            "ready": True,
        }
    elif result.state == "FAILURE":
        return {
            "task_id": task_id,
            "status": "fallido",
            "progress": 0,
            "message": str(result.info) if result.info else "Error en procesamiento",
            "resultado": None,
            "ready": True,
        }
    elif result.state == "STARTED":
        return {
            "task_id": task_id,
            "status": "procesando",
            "progress": 10,
            "message": "Procesando...",
            "resultado": None,
            "ready": False,
        }
    else:  # PENDING
        return {
            "task_id": task_id,
            "status": "pendiente",
            "progress": 0,
            "message": "En cola...",
            "resultado": None,
            "ready": False,
        }


@router.get("/stats")
async def get_tasks_stats(
    current_user: dict = Depends(require_usuario_judicial),
):
    """
    Obtiene estadísticas de tareas en memoria para monitoreo.
    """
    from app.services.ingesta.async_processing.progress_tracker import progress_manager
    
    stats = progress_manager.get_task_count()
    
    return {
        "message": "Estadísticas de tareas en memoria",
        "tasks_in_memory": stats,
        "memory_usage": {
            "active_tasks": stats["total_active"],
            "completed_in_history": stats["total_in_history"], 
            "history_usage_percent": stats["history_usage_percent"],
        }
    }


@router.post("/archivos")
async def ingestar_archivos(
    CT_Num_expediente: str = Form(..., description="Número de expediente"),
    files: List[UploadFile] = File(..., description="Archivos a procesar"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
):
    """
    Ingesta de archivos de forma asíncrona usando Celery.
    Devuelve task_ids para consultar progreso en tiempo real.
    """
    # Validación básica
    if not files:
        raise HTTPException(
            status_code=400, 
            detail="Debe proporcionar al menos un archivo"
        )
    
    try:
        # Procesar cada archivo con Celery
        task_ids = []
        from app.services.ingesta.async_processing.celery_tasks import procesar_archivo_celery
        
        for file in files:
            try:
                # Guardar archivo físicamente
                archivo_info = await file_management_service.guardar_archivo(file, CT_Num_expediente)
                
                # Enviar a Celery con usuario_id (genera task_id automáticamente)
                celery_task = procesar_archivo_celery.delay(
                    CT_Num_expediente,
                    archivo_info,
                    current_user["user_id"]  # Pasar usuario que inició la ingesta
                )
                task_ids.append(celery_task.id)
                
            except Exception as e:
                logger.error(f"Error guardando archivo {file.filename}: {e}")
                # Agregar error a la lista para notificar al frontend
                task_ids.append({
                    "error": True,
                    "filename": file.filename,
                    "message": f"Error al guardar: {str(e)}"
                })
        
        # Obtener ID del expediente para la bitácora
        expediente_db_id = None
        try:
            from app.repositories.expediente_repository import ExpedienteRepository
            expediente_repo = ExpedienteRepository()
            expediente_obj = expediente_repo.obtener_por_numero(db, CT_Num_expediente)
            if expediente_obj:
                expediente_db_id = expediente_obj.CN_Id_expediente
        except Exception as e:
            logger.warning(f"No se pudo obtener ID de expediente para bitácora: {e}")
        
        # Registrar en bitácora - Ingesta iniciada
        await bitacora_service.registrar(
            db=db,
            usuario_id=current_user["user_id"],
            tipo_accion_id=TiposAccion.CARGA_DOCUMENTOS,
            texto=f"Ingesta iniciada: {len(files)} archivo(s) en expediente {CT_Num_expediente}",
            expediente_id=expediente_db_id,
            info_adicional={
                "expediente": CT_Num_expediente,
                "total_archivos": len(files),
                "archivos": [f.filename for f in files],
                "task_ids": [tid for tid in task_ids if isinstance(tid, str)]
            }
        )
        
        return {
            "message": f"{len(files)} archivos enviados a procesamiento",
            "task_ids": task_ids,
            "expediente": CT_Num_expediente,
            "total_files": len(files)
        }
        
    except Exception as e:
        # Obtener ID del expediente para la bitácora (incluso en error)
        expediente_db_id = None
        try:
            from app.repositories.expediente_repository import ExpedienteRepository
            expediente_repo = ExpedienteRepository()
            expediente_obj = expediente_repo.obtener_por_numero(db, CT_Num_expediente)
            if expediente_obj:
                expediente_db_id = expediente_obj.CN_Id_expediente
        except:
            pass
        
        # Registrar error en bitácora
        await bitacora_service.registrar(
            db=db,
            usuario_id=current_user["user_id"],
            tipo_accion_id=TiposAccion.CARGA_DOCUMENTOS,
            texto=f"Error en ingesta de expediente {CT_Num_expediente}: {str(e)[:200]}",
            expediente_id=expediente_db_id,
            info_adicional={
                "expediente": CT_Num_expediente,
                "error": str(e),
                "tipo_error": "critico"
            }
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar archivos: {str(e)}"
        )


@router.post("/cancel/{task_id}")
async def cancelar_tarea(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
):
    """
    Cancela una tarea de procesamiento de archivo en ejecución.
    
    - Revoca la tarea en Celery (termina la ejecución)
    - Marca como cancelado en ProgressTracker
    - Limpia recursos asociados
    - Registra la acción en bitácora
    
    Returns:
        Dict con información de cancelación
    """
    from app.services.ingesta.async_processing.progress_tracker import progress_manager
    
    try:
        logger.info(f"Intentando cancelar tarea: {task_id}")
        
        # 1. Verificar si la tarea existe en ProgressTracker
        progress = progress_manager.get_status(task_id)
        
        if not progress:
            # Tarea no existe o ya finalizó
            result = AsyncResult(task_id, app=celery_app)
            if result.state in ['SUCCESS', 'FAILURE', 'REVOKED']:
                raise HTTPException(
                    status_code=400,
                    detail=f"La tarea ya finalizó con estado: {result.state}"
                )
        
        # 2. Verificar si ya está en estado terminal
        if progress and progress.get("status") in ["completado", "fallido", "cancelado"]:
            raise HTTPException(
                status_code=400,
                detail=f"La tarea ya está en estado terminal: {progress.get('status')}"
            )
        
        # 3. Revocar la tarea en Celery (terminar ejecución forzosamente)
        celery_app.control.revoke(task_id, terminate=True, signal='SIGTERM')
        logger.info(f"Tarea {task_id} revocada en Celery")
        
        # 4. Marcar como cancelado en ProgressTracker
        progress_manager.mark_task_cancelled(task_id, "Cancelado por el usuario")
        logger.info(f"Tarea {task_id} marcada como cancelada en ProgressTracker")
        
        # 5. Registrar cancelación en bitácora
        await bitacora_service.registrar(
            db=db,
            usuario_id=current_user["user_id"],
            tipo_accion_id=TiposAccion.CARGA_DOCUMENTOS,
            texto=f"Procesamiento cancelado - Task ID: {task_id}",
            info_adicional={
                "task_id": task_id,
                "accion": "cancelacion",
                "estado_previo": progress.get("status") if progress else "desconocido",
                "revoked_in_celery": True,
                "marked_in_tracker": True
            }
        )
        
        return {
            "success": True,
            "message": "Tarea cancelada exitosamente",
            "task_id": task_id,
            "status": "cancelado",
            "details": {
                "revoked_in_celery": True,
                "marked_in_tracker": True
            }
        }
        
    except HTTPException:
        # Re-lanzar excepciones HTTP
        raise
    except Exception as e:
        logger.error(f"Error cancelando tarea {task_id}: {e}", exc_info=True)
        
        # Registrar error de cancelación en bitácora
        try:
            await bitacora_service.registrar(
                db=db,
                usuario_id=current_user["user_id"],
                tipo_accion_id=TiposAccion.CARGA_DOCUMENTOS,
                texto=f"Error al cancelar procesamiento - Task ID: {task_id}",
                info_adicional={
                    "task_id": task_id,
                    "accion": "cancelacion_fallida",
                    "error": str(e)
                }
            )
        except:
            pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Error al cancelar la tarea: {str(e)}"
        )
