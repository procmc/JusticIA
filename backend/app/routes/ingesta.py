"""
Endpoints de Ingesta de Documentos con Procesamiento Asíncrono.

Este módulo expone los endpoints de la API para la carga y procesamiento
asíncrono de documentos y audio. Usa Celery para procesar archivos en
background y proporciona endpoints para consultar el progreso en tiempo real.

Endpoints principales:
    POST /ingesta/archivos: Sube archivos y crea tareas Celery
    GET /ingesta/progress/{task_id}: Consulta progreso de una tarea
    GET /ingesta/stats: Estadísticas de tareas en memoria
    POST /ingesta/cancel/{task_id}: Cancela una tarea en procesamiento

Flujo de ingesta:
    1. Usuario sube archivo(s) con número de expediente
    2. Backend guarda archivo físicamente en /uploads
    3. Crea tarea Celery para procesamiento asíncrono
    4. Retorna task_id al frontend
    5. Frontend hace polling con /progress/{task_id}
    6. Worker de Celery procesa: extracción, chunking, embeddings, Qdrant
    7. Actualiza estado del documento en BD (Pendiente -> Procesado/Error)

Formatos soportados:
    - Documentos: PDF, DOC, DOCX, RTF, TXT, HTML
    - Audio: MP3, WAV (transcripción con Faster-Whisper)
    - OCR: Automático para PDFs escaneados (Tesseract)

Progreso granular:
    - Usa ProgressTracker para actualizar progreso en pasos
    - Estados: pendiente, procesando, completado, fallido, cancelado
    - Progreso: 0-100% con mensajes descriptivos

Auditoría:
    - Registra todas las ingestas en bitácora (T_Bitacora_acciones)
    - Incluye: usuario, archivo, expediente, tiempo, estado final

Example:
    >>> # Subir archivos
    >>> files = [('files', open('doc.pdf', 'rb'))]
    >>> data = {'CT_Num_expediente': '00-001234-0567-PE'}
    >>> response = requests.post('/ingesta/archivos', files=files, data=data)
    >>> task_ids = response.json()['task_ids']
    >>> 
    >>> # Consultar progreso (polling)
    >>> for task_id in task_ids:
    ...     progress = requests.get(f'/ingesta/progress/{task_id}').json()
    ...     print(f"{progress['progress']}% - {progress['message']}")

Note:
    - Tamaño máximo por archivo: configurado en file_config.py
    - Concurrency de workers: configurado en docker-compose.yml
    - Los task_ids son UUIDs generados por Celery
    - Requiere autenticación JWT (usuario judicial)
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.auth.jwt_auth import require_usuario_judicial
from app.services.documentos.file_management_service import (
    file_management_service, validar_tema
)
from app.services.bitacora.ingesta_audit_service import (
    ingesta_audit_service, MOTIVOS_DE_RECHAZO, MOTIVOS_DE_FALLO_INTERNO, MOTIVO_TEMA_NO_VALIDO, MOTIVO_ERROR_INTERNO
)
from app.services.bitacora.notebooks_audit_service import notebooks_audit_service, MOTIVO_NOTEBOOK_NO_DISPONIBLE
from app.services.notebook_service import NotebookService, NO_DISPONIBLE, PROPIO
from app.constants.tipos_accion import TiposAccion
import logging
from celery.result import AsyncResult
from celery_app import celery_app

router = APIRouter()
logger = logging.getLogger(__name__)


def _confirmacion_de_carga(aceptados: int) -> str:
    """Texto de confirmación de la carga (RF-05.22): cuenta solo los archivos aceptados y, si no hubo ninguno, no dice
    que se enviaron archivos."""
    if aceptados == 0:
        return "No se aceptó ningún archivo. Revise el motivo de cada uno."
    if aceptados == 1:
        return "1 archivo enviado a procesamiento"
    return f"{aceptados} archivos enviados a procesamiento"


async def _registrar_rechazo(db: Session, usuario_id: str, rechazados: list, posicion: int, motivo: str) -> None:
    """Anota el archivo rechazado (su posición y su motivo) y deja su fila de rechazo en la bitácora, sin el nombre ni
    el tema (RF-05.22, RF-21, RNF-07.24). Si el registro falla, la carga continúa."""
    rechazados.append({"posicion": posicion, "motivo": motivo})
    await ingesta_audit_service.registrar_carga_rechazada(
        db=db,
        usuario_id=usuario_id,
        motivo=motivo,
        tipo_error="interno" if motivo in MOTIVOS_DE_FALLO_INTERNO else "validacion",
    )


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
    
    # Un tema con forma de clave de notebook se comprueba primero, antes de escribir o encolar nada (RF-17.4): si no es la clave
    # de un notebook del usuario (ajeno, inexistente o con una grafía que no es la canónica) la carga se rechaza con el mismo
    # 404, sin repetir la clave pedida; si es la suya, en otra grafía, se carga con su clave canónica `NB-<id>`.
    clasificacion = await NotebookService().clasificar_clave(db, CT_Num_expediente, current_user["user_id"])
    if clasificacion.tipo == NO_DISPONIBLE:
        await notebooks_audit_service.registrar_intento_fallido(
            db=db,
            usuario_id=current_user["user_id"],
            tipo_accion_id=TiposAccion.CARGA_DOCUMENTOS,
            motivo=MOTIVO_NOTEBOOK_NO_DISPONIBLE
        )
        raise HTTPException(status_code=404, detail="Notebook no encontrado")
    if clasificacion.tipo == PROPIO:
        CT_Num_expediente = clasificacion.notebook.clave_interna

    # El tema se comprueba antes de escribir o encolar nada: si no sirve como nombre de carpeta se rechaza la carga
    # completa, sin repetirlo en la respuesta ni en la bitácora (RF-06.20, RF-21.20, RNF-07.24).
    try:
        validar_tema(CT_Num_expediente)
    except HTTPException:
        await ingesta_audit_service.registrar_carga_rechazada(
            db=db, usuario_id=current_user["user_id"], motivo=MOTIVO_TEMA_NO_VALIDO
        )
        raise

    try:
        # Procesar cada archivo con Celery
        task_ids = []
        # Además de `task_ids` (uno por archivo, en el orden enviado, que la interfaz consume por posición), se entregan
        # los aceptados y los rechazados con su posición (desde 1) y su motivo en español (RF-05.22).
        aceptados = []
        rechazados = []
        from app.services.ingesta.async_processing.celery_tasks import procesar_archivo_celery

        for posicion, file in enumerate(files, start=1):
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
                aceptados.append({"posicion": posicion, "id_tarea": celery_task.id})

            except HTTPException as e:
                # Rechazo de ese archivo (RF-05.20, RF-05.21): su `detail` es un aviso genérico del servicio, se identifica
                # por su posición en la lista y no lleva el nombre pedido (RNF-07.24).
                task_ids.append({"error": True, "message": e.detail})
                await _registrar_rechazo(
                    db, current_user["user_id"], rechazados, posicion, MOTIVOS_DE_RECHAZO.get(e.detail, MOTIVO_ERROR_INTERNO)
                )
            except Exception:
                # El detalle va solo al registro del servidor, sin el nombre del archivo (RNF-07.23, RNF-07.24).
                logger.exception("Error inesperado al guardar o encolar un archivo")
                task_ids.append({"error": True, "message": "Error interno del servidor"})
                await _registrar_rechazo(db, current_user["user_id"], rechazados, posicion, MOTIVO_ERROR_INTERNO)

        # Registrar en bitácora - Ingesta iniciada, solo si hubo al menos un archivo aceptado y contándolos (RF-05.22)
        if aceptados:
            await ingesta_audit_service.registrar_ingesta(
                db=db,
                usuario_id=current_user["user_id"],
                expediente_num=CT_Num_expediente,
                filename=f"{len(aceptados)} archivo(s)",
                task_id=",".join([tid for tid in task_ids if isinstance(tid, str)]),
                fase="iniciado",
                archivos_aceptados=len(aceptados),
                archivos_rechazados=len(rechazados)
            )

        return {
            "message": _confirmacion_de_carga(len(aceptados)),
            "task_ids": task_ids,
            "expediente": CT_Num_expediente,
            "total_files": len(aceptados),
            "aceptados": {"cantidad": len(aceptados), "tareas": aceptados},
            "rechazados": {"cantidad": len(rechazados), "archivos": rechazados},
        }
        
    except Exception:
        logger.exception("Error inesperado en la carga de archivos")
        # Registrar error en bitácora
        await ingesta_audit_service.registrar_ingesta(
            db=db,
            usuario_id=current_user["user_id"],
            expediente_num=CT_Num_expediente,
            filename="Error general",
            task_id="N/A",
            fase="error"
        )
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
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
        
        # 4. Actualizar estado del documento si existe (dejar en Pendiente si se cancela)
        # No actualizamos el documento - queda en "Pendiente" para que usuario decida
        documento_actualizado = False
        
        # 5. Marcar como cancelado en ProgressTracker
        progress_manager.mark_task_cancelled(task_id, "Cancelado por el usuario")
        logger.info(f"Tarea {task_id} marcada como cancelada en ProgressTracker")
        
        # 6. Registrar cancelación en bitácora
        await ingesta_audit_service.registrar_ingesta(
            db=db,
            usuario_id=current_user["user_id"],
            expediente_num="N/A",
            filename=f"Task {task_id}",
            task_id=task_id,
            fase="cancelado"
        )
        
        return {
            "success": True,
            "message": "Tarea cancelada exitosamente",
            "task_id": task_id,
            "status": "cancelado",
            "details": {
                "revoked_in_celery": True,
                "marked_in_tracker": True,
                "documento_actualizado": documento_actualizado
            }
        }
        
    except HTTPException:
        # Re-lanzar excepciones HTTP
        raise
    except Exception as e:
        logger.error(f"Error cancelando tarea {task_id}: {e}", exc_info=True)
        
        # Registrar error de cancelación en bitácora
        try:
            await ingesta_audit_service.registrar_ingesta(
                db=db,
                usuario_id=current_user["user_id"],
                expediente_num="N/A",
                filename=f"Task {task_id}",
                task_id=task_id,
                fase="error_cancelacion"
            )
        except:
            pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Error al cancelar la tarea: {str(e)}"
        )
