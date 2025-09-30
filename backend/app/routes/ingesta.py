
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks, Request
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.auth.jwt_auth import require_role
from app.services.documentos.file_management_service import file_management_service
import uuid
import logging
from celery.result import AsyncResult

router = APIRouter()
logger = logging.getLogger(__name__)

# Almacén temporal para estados de procesos (en memoria)
process_status_store = {}


@router.get("/status/{process_id}")
async def get_process_status(process_id: str):
    """
    Consulta el estado de un proceso asíncrono (versión legacy).
    """
    # Si el proceso no existe, devolver error
    if process_id not in process_status_store:
        raise HTTPException(
            status_code=404,
            detail=f"Proceso {process_id} no encontrado"
        )
    
    # Devolver el estado actual
    return process_status_store[process_id]



# Endpoint para consultar progreso de una tarea Celery (simple)
@router.get("/progress/{task_id}")
async def consultar_progreso_tarea(task_id: str):
    """
    Consulta el estado y progreso de una tarea Celery por su ID.
    """
    result = AsyncResult(task_id)
    response = {
        "task_id": task_id,
        "state": result.state,
        "info": result.info if result.info else {},
        "ready": result.ready(),
        "successful": result.successful(),
    }
    return response

# Endpoint para consultar progreso detallado (nuevo sistema)
@router.get("/progress-detailed/{task_id}")
async def get_task_progress_detailed(task_id: str):
    """
    Consulta el progreso granular y detallado de una tarea.
    Utiliza el nuevo sistema de ProgressTracker para información completa.
    """
    from app.services.ingesta.async_processing.background_tasks import get_task_progress
    progress_data = get_task_progress(task_id)
    if not progress_data:
        raise HTTPException(
            status_code=404,
            detail=f"Tarea {task_id} no encontrada"
        )
    return progress_data


@router.get("/stats")
async def get_tasks_stats():
    """
    Obtiene estadísticas de tareas en memoria para monitoreo.
    """
    from app.services.ingesta.async_processing.background_tasks import progress_manager
    
    stats = progress_manager.get_task_count()
    
    return {
        "message": "Estadísticas de tareas en memoria",
        "tasks_in_memory": stats,
        "memory_usage": {
            "active_tasks": stats["total_active"],
            "completed_in_history": stats["total_in_history"], 
            "history_limit": stats["history_limit"],
            "history_usage_percent": stats["history_usage_percent"],
            "currently_processing": stats["pending"] + stats["processing"], 
            "completed_active": stats["completed"] + stats["failed"] + stats["cancelled"]
        },
        "memory_optimization": {
            "max_history_entries": stats["history_limit"],
            "current_history_entries": stats["total_in_history"],
            "estimated_memory_per_entry": "~80 bytes",
            "estimated_total_memory": f"~{stats['total_in_history'] * 80} bytes"
        }
    }


@router.post("/archivos")
#@require_role("Usuario Judicial")
async def ingestar_archivos(
    request: Request,
    background_tasks: BackgroundTasks,
    CT_Num_expediente: str = Form(..., description="Número de expediente"),
    files: List[UploadFile] = File(..., description="Archivos a procesar"),
    db: Session = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = None,
):
    """
    Ingesta de archivos de forma asíncrona.
    Devuelve inmediatamente IDs individuales para consultar el progreso de cada archivo.
    """
        
    # Validaciones básicas (rápidas)
    if not files:
        raise HTTPException(
            status_code=400, detail="Debe proporcionar al menos un archivo"
        )
    
    # Procesar cada archivo individualmente usando Celery
    celery_task_ids = []
    from app.services.ingesta.async_processing.celery_tasks import procesar_archivo_celery
    for file in files:
        try:
            archivo_info = await file_management_service.guardar_archivo(file, CT_Num_expediente)
            celery_task = procesar_archivo_celery.delay(
                str(uuid.uuid4()),
                CT_Num_expediente,
                archivo_info,
                str(db.bind.url)
            )
            celery_task_ids.append(celery_task.id)
        except Exception as e:
            error_message = "Error al guardar el archivo"
            if "subpath" in str(e).lower() or "relative" in str(e).lower():
                error_message = "Error de configuración de directorio"
            elif "permission" in str(e).lower():
                error_message = "Sin permisos para guardar el archivo"
            elif "space" in str(e).lower() or "disk" in str(e).lower():
                error_message = "Espacio insuficiente en disco"
            logger.error(f"Error guardando archivo {file.filename}: {e}")
            celery_task_ids.append({
                "status": "error",
                "message": f"{error_message}: {file.filename}",
                "filename": file.filename
            })
    
    # Devolver lista de IDs de tareas Celery
    return {
        "message": f"{len(files)} archivos enviados para procesamiento",
        "celery_task_ids": celery_task_ids,
        "expediente": CT_Num_expediente,
        "total_files": len(files)
    }


@router.post("/cancel/{process_id}")
async def cancel_process(process_id: str):
    """
    Cancela el procesamiento de un archivo.
    """
    # Verificar si el proceso existe
    if process_id not in process_status_store:
        raise HTTPException(
            status_code=404,
            detail=f"Proceso {process_id} no encontrado"
        )
    
    # Obtener el estado actual
    current_status = process_status_store[process_id]
    
    # Solo cancelar si está en progreso
    if current_status.get("status") in ["completed", "failed"]:
        return {
            "message": f"El proceso {process_id} ya está finalizado",
            "status": current_status.get("status")
        }
    
    # Marcar como cancelado
    process_status_store[process_id] = {
        **current_status,
        "status": "cancelled",
        "progress": 0,
        "message": "Cancelado por el usuario",
        "cancelled_at": uuid.uuid4().hex  # Timestamp simple
    }
    
    # 🔄 AUTO-LIMPIEZA: Programar eliminación de esta tarea cancelada en 1 minuto
    from app.services.ingesta.async_processing.background_tasks import progress_manager
    progress_manager.schedule_task_cleanup(process_id, delay_minutes=1)
    
    return {
        "message": f"Proceso {process_id} cancelado exitosamente",
        "status": "cancelled"
    }
