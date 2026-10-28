"""
Tareas Celery para procesamiento asíncrono con idempotencia.

Implementa tareas Celery para procesamiento de archivos con verificación
de idempotencia, cancelación y bitácora completa.

Características:
    * Idempotencia: Verificación doble (Redis + BD)
    * Cancelación: Check en Celery REVOKED + Redis status
    * Bitácora: Logging inicio/completado/error
    * Exception handling: Terminated, SoftTimeLimitExceeded
    * Cleanup: Scheduling de limpieza con delays
    * Progress tracking: Integrado con Redis

Tarea principal:
    procesar_archivo_celery:
        * Procesa lista de archivos para expediente
        * Verifica si ya fue procesada (idempotencia)
        * Actualiza progress tracker
        * Registra en bitácora
        * Limpia recursos al finalizar

Idempotencia:
    1. Check en Redis: task_progress:{task_id}
    2. Check en BD: Documentos ya procesados
    3. Si ya completado: retorna sin procesar
    4. Evita reintentos duplicados de Celery

Cancelación:
    * Celery: AsyncResult.state == 'REVOKED'
    * Redis: EstadoTarea.CANCELADO
    * Verificación periódica durante procesamiento
    * Excepción Terminated si cancelado

Bitácora:
    * Inicio: Usuario, expediente, archivos
    * Completado: Archivos exitosos/fallidos
    * Error: Traceback completo
    * Integración con ingesta_audit_service

Example:
    >>> from app.services.ingesta.async_processing.celery_tasks import procesar_archivo_celery
    >>> from app.schemas.schemas import ArchivoSimplificado
    >>> 
    >>> # Crear tarea
    >>> archivos = [
    ...     ArchivoSimplificado(
    ...         id="doc_1",
    ...         nombre="sentencia.pdf",
    ...         ruta_archivo="/uploads/sentencia.pdf"
    ...     )
    ... ]
    >>> 
    >>> # Ejecutar tarea asíncrona
    >>> result = procesar_archivo_celery.apply_async(
    ...     args=[
    ...         "00-000001-0001-PE",
    ...         [archivo.dict() for archivo in archivos],
    ...         "user_123"
    ...     ],
    ...     task_id="task_123"
    ... )
    >>> 
    >>> # Verificar estado
    >>> print(result.state)  # PENDING, STARTED, SUCCESS, FAILURE, REVOKED

Note:
    * task_id debe ser único por expediente
    * Archivos quedan en disco aunque falle
    * Redis tracking TTL 3600s (1 hora)
    * Celery result backend: Redis
    * Broker: Redis con prefetch_multiplier=1

Ver también:
    * app.services.ingesta.document_processor: Procesamiento principal
    * app.services.ingesta.progress_tracker: Tracking de progreso
    * app.services.bitacora_service: Auditoría de operaciones
    * app.celery_app: Configuración de Celery

Authors:
    ServIA Team

Version:
    2.0.0 - Idempotencia y cancelación robusta
"""
from celery_app import celery_app
from celery.exceptions import Terminated, SoftTimeLimitExceeded
from sqlalchemy.orm import sessionmaker
from app.db.database import engine, SessionLocal
from app.services.ingesta.async_processing.progress_tracker import progress_manager
from app.services.ingesta.file_management.document_processor import process_uploaded_files
from io import BytesIO
from fastapi import UploadFile
import logging
import asyncio

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def procesar_archivo_celery(self, CT_Num_expediente, archivo_data, usuario_id):
    """
    Tarea Celery para procesar archivos en segundo plano.
    
    Procesa lista de archivos con verificación de idempotencia,
    progress tracking y bitácora completa.
    
    Args:
        self: Task instance (bind=True).
        CT_Num_expediente (str): Número de expediente.
        archivo_data (List[Dict]): Lista de archivos simplificados.
        usuario_id: ID del usuario que inició la ingesta
    """
    # Usar el task_id de Celery como file_process_id para tracking
    task_id = self.request.id
    
    # VERIFICAR SI YA SE PROCESÓ (idempotencia con doble verificación)
    existing_tracker = progress_manager.get_status(task_id)
    if existing_tracker and existing_tracker.get("status") == "completado":
        logger.warning(f"REINTENTO DETECTADO: Tarea {task_id} ya completada. Retornando resultado previo.")
        metadata = existing_tracker.get("metadata", {})
        return {
            "status": "completado",
            "progress": 100,
            "resultado": {
                "filename": archivo_data.get("filename", "unknown"),
                "documento_id": metadata.get("documento_id"),
                "mensaje": metadata.get("mensaje", "Archivo procesado previamente"),
                "status": "exitoso",
            },
            "note": "Resultado de ejecución previa (reintento evitado)"
        }
    
    tracker = progress_manager.create_tracker(task_id, total_steps=100)

    # RF-07.51: un reintento interno (misma tarea, mismo id) se reconoce por el documento que esa tarea ya registró;
    # una carga nueva del usuario es otra tarea con otro id y siempre crea su propia fila.
    id_documento_previo = None
    try:
        id_documento_previo = progress_manager.documento_de_tarea(task_id)
    except Exception as redis_error:
        logger.warning(f"No se pudo consultar el documento previo de la tarea {task_id}: {redis_error}")
    if id_documento_previo:
        db_previo = SessionLocal()
        try:
            from app.repositories.documento_repository import DocumentoRepository
            previo = DocumentoRepository().obtener_por_id(db_previo, id_documento_previo)
            estado_previo = previo.estado_procesamiento.CT_Nombre_estado if previo and previo.estado_procesamiento else None
        finally:
            db_previo.close()
        if estado_previo == "Procesado":
            logger.warning(f"REINTENTO DETECTADO: Tarea {task_id} ya dejó el documento {id_documento_previo} Procesado.")
            tracker.mark_completed("Archivo procesado previamente")
            return {
                "status": "completado",
                "progress": 100,
                "resultado": {
                    "filename": archivo_data.get("filename", "unknown"),
                    "documento_id": str(id_documento_previo),
                    "mensaje": "Documento ya procesado previamente",
                    "status": "exitoso",
                },
                "note": "Documento ya existe en BD (reintento evitado)"
            }
        if estado_previo == "Error":
            logger.warning(f"REINTENTO DETECTADO: Tarea {task_id} ya dejó el documento {id_documento_previo} en Error.")
            tracker.marcar_fallo("El documento quedó en Error en un intento anterior")
            return {
                "status": "fallido",
                "progress": 100,
                "resultado": {
                    "filename": archivo_data.get("filename", "unknown"),
                    "documento_id": str(id_documento_previo),
                    "status": "error",
                },
                "note": "Documento en Error (reintento evitado)"
            }
    
    # Función para verificar si la tarea fue cancelada
    def check_if_cancelled():
        """Verifica si la tarea fue cancelada verificando Celery y Redis."""
        from celery.result import AsyncResult
        
        # 1. Verificar estado en Celery (confiable con prefork pool)
        task_result = AsyncResult(task_id, app=celery_app)
        if task_result.state == 'REVOKED':
            logger.warning(f"Cancelación detectada: tarea {task_id} revocada en Celery")
            raise Terminated("Tarea cancelada por el usuario")
        
        # 2. Verificar tracker en Redis (actualización inmediata desde endpoint)
        progress = progress_manager.get_status(task_id)
        if progress and progress.get("status") == "cancelado":
            logger.warning(f"Cancelación detectada: tarea {task_id} marcada en Redis")
            raise Terminated("Tarea cancelada por el usuario")
    
    try:
        # Verificar cancelación al inicio
        check_if_cancelled()
        
        # Recrear objeto UploadFile desde bytes
        file_buffer = BytesIO(archivo_data["content"])
        file_obj = UploadFile(file=file_buffer, filename=archivo_data["filename"])
        
        # Verificar cancelación antes de procesar
        check_if_cancelled()
        
        # Usar sesión de base de datos del engine global (ya configurado con pool)
        db = SessionLocal()
        
        try:
            # Registrar inicio en bitácora
            from app.services.bitacora.ingesta_audit_service import ingesta_audit_service as bitacora_service
            try:
                asyncio.run(bitacora_service.registrar_ingesta(
                    db, usuario_id, CT_Num_expediente, archivo_data['filename'], task_id, "inicio"
                ))
            except Exception as bitacora_error:
                # RF-21.50: si la bitácora falla, el procesamiento continúa.
                logger.warning(f"No se pudo registrar el inicio en bitácora: {bitacora_error}")
            
            # Ejecutar la función async de forma síncrona usando asyncio.run()
            # Esto crea un nuevo event loop para esta tarea
            # El tracker se pasa a process_uploaded_files que maneja todo el progreso
            documento_previo = None
            if id_documento_previo:
                from app.repositories.documento_repository import DocumentoRepository
                documento_previo = DocumentoRepository().obtener_por_id(db, id_documento_previo)
            resultado_completo = asyncio.run(
                process_uploaded_files([file_obj], CT_Num_expediente, db, usuario_id, tracker, check_if_cancelled,
                                       documento_previo)
            )
            
            # Verificar cancelación después del procesamiento
            check_if_cancelled()
            
            # Verificar resultado (el tracker ya fue actualizado en process_uploaded_files)
            # IMPORTANTE: Verificar tanto procesados_exitosamente > 0 como status="success"
            if resultado_completo.procesados_exitosamente > 0:
                archivo_resultado = resultado_completo.archivos_procesados[0]
                
                # Verificar que realmente fue exitoso (no un error disfrazado)
                if archivo_resultado.status != "success":
                    error_msg = archivo_resultado.message or "Error en procesamiento"
                    progress_manager.schedule_task_cleanup(task_id, delay_minutes=3)
                    raise Exception(error_msg)
                
                # Registrar éxito en bitácora
                asyncio.run(bitacora_service.registrar_ingesta(
                    db, usuario_id, CT_Num_expediente, archivo_data['filename'], 
                    task_id, "completado", archivo_resultado.file_id
                ))
                
                # Programar limpieza con delay largo (30 min) para prevenir reintentos
                progress_manager.schedule_task_cleanup(task_id, delay_minutes=30)
                
                # Liberar memoria
                del file_buffer
                del archivo_data["content"]
                
                return {
                    "status": "completado",
                    "progress": 100,
                    "resultado": {
                        "filename": archivo_data["filename"],
                        "documento_id": archivo_resultado.file_id,
                        "mensaje": archivo_resultado.message,
                        "status": "exitoso",
                    }
                }
            else:
                # Usar el mensaje de error original sin agregar prefijos
                error_msg = "Error desconocido en procesamiento"
                if resultado_completo.archivos_con_error:
                    archivo_error = resultado_completo.archivos_con_error[0]
                    error_msg = archivo_error.error  # Ya contiene el mensaje completo
                
                # El tracker ya fue marcado como fallido en process_uploaded_files
                progress_manager.schedule_task_cleanup(task_id, delay_minutes=3)
                
                raise Exception(error_msg)
                
        finally:
            # Cerrar solo la sesión (no el engine porque es global)
            db.close()
    
    except Terminated:
        # Tarea cancelada por el usuario
        logger.warning(f"Tarea cancelada: {archivo_data['filename']}")
        tracker.mark_failed("Procesamiento cancelado por el usuario", "cancelado")
        progress_manager.schedule_task_cleanup(task_id, delay_minutes=2)
        
        # Liberar memoria
        if 'file_buffer' in locals():
            del file_buffer
        if 'content' in archivo_data:
            del archivo_data["content"]
        
        raise  # Re-raise para que el exception handler en document_processor lo capture
    
    except SoftTimeLimitExceeded:
        # Timeout de tarea (si se configura)
        error_msg = f"Timeout procesando {archivo_data['filename']}"
        logger.error(error_msg)
        tracker.mark_failed(error_msg, "Tiempo límite excedido")
        progress_manager.schedule_task_cleanup(task_id, delay_minutes=2)
        raise
            
    except Exception as e:
        error_msg = f"Error crítico procesando {archivo_data['filename']}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        # RF-07.52: el usuario ve el texto fijo con la causa; el texto crudo queda solo en el log y la bitácora.
        tracker.marcar_fallo(str(e))
        progress_manager.schedule_task_cleanup(task_id, delay_minutes=2)
        
        # Registrar error en bitácora para auditoría
        try:
            if 'db' in locals():
                from app.services.bitacora.ingesta_audit_service import ingesta_audit_service as bitacora_service
                asyncio.run(bitacora_service.registrar_ingesta(
                    db, usuario_id, CT_Num_expediente, archivo_data['filename'], 
                    task_id, "error", error_details=str(e)
                ))
        except Exception as bitacora_error:
            # No fallar por error en bitácora, solo loggear
            logger.warning(f"No se pudo registrar error en bitácora: {bitacora_error}")
        
        # Liberar memoria en caso de error
        if 'file_buffer' in locals():
            del file_buffer
        if 'content' in archivo_data:
            del archivo_data["content"]
        
        raise  # Re-raise para que Celery registre el error correctamente
