
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.auth.jwt_auth import require_role
from app.services.documentos.file_management_service import file_management_service
import logging
from celery.result import AsyncResult

router = APIRouter()
logger = logging.getLogger(__name__)


# Endpoint principal para consultar progreso de tareas
@router.get("/progress/{task_id}")
async def consultar_progreso_tarea(task_id: str):
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
async def get_tasks_stats():
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
    
    # Procesar cada archivo con Celery
    task_ids = []
    from app.services.ingesta.async_processing.celery_tasks import procesar_archivo_celery
    
    for file in files:
        try:
            # Guardar archivo físicamente
            archivo_info = await file_management_service.guardar_archivo(file, CT_Num_expediente)
            
            # Enviar a Celery (genera task_id automáticamente)
            celery_task = procesar_archivo_celery.delay(
                CT_Num_expediente,
                archivo_info
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
    
    return {
        "message": f"{len(files)} archivos enviados a procesamiento",
        "task_ids": task_ids,
        "expediente": CT_Num_expediente,
        "total_files": len(files)
    }
