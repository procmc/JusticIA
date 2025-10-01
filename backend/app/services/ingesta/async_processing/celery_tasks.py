from celery_app import celery_app
from sqlalchemy.orm import sessionmaker
from app.db.database import engine, SessionLocal  # Reutilizar engine global configurado
from app.services.ingesta.async_processing.progress_tracker import progress_manager
from app.services.ingesta.file_management.document_processor import process_uploaded_files
from io import BytesIO
from fastapi import UploadFile
import logging
import asyncio

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def procesar_archivo_celery(self, CT_Num_expediente, archivo_data):
    """
    Tarea Celery para procesar un archivo en segundo plano.
    
    IMPORTANTE: Celery no soporta async/await directamente, pero process_uploaded_files
    es una función async. Usamos asyncio.run() para ejecutarla de forma síncrona.
    
    Args:
        CT_Num_expediente: Número de expediente
        archivo_data: Diccionario con datos del archivo
    """
    # Usar el task_id de Celery como file_process_id para tracking
    task_id = self.request.id
    tracker = progress_manager.create_tracker(task_id, total_steps=100)
    
    try:
        # Recrear objeto UploadFile desde bytes
        file_buffer = BytesIO(archivo_data["content"])
        file_obj = UploadFile(file=file_buffer, filename=archivo_data["filename"])
        
        # Usar sesión de base de datos del engine global (ya configurado con pool)
        db = SessionLocal()
        
        try:
            # Ejecutar la función async de forma síncrona usando asyncio.run()
            # Esto crea un nuevo event loop para esta tarea
            # El tracker se pasa a process_uploaded_files que maneja todo el progreso
            resultado_completo = asyncio.run(
                process_uploaded_files([file_obj], CT_Num_expediente, db, tracker)
            )
            
            # Verificar resultado (el tracker ya fue actualizado en process_uploaded_files)
            # IMPORTANTE: Verificar tanto procesados_exitosamente > 0 como status="success"
            if resultado_completo.procesados_exitosamente > 0:
                archivo_resultado = resultado_completo.archivos_procesados[0]
                
                # Verificar que realmente fue exitoso (no un error disfrazado)
                if archivo_resultado.status != "success":
                    error_msg = archivo_resultado.message or "Error en procesamiento"
                    progress_manager.schedule_task_cleanup(task_id, delay_minutes=3)
                    raise Exception(error_msg)
                progress_manager.schedule_task_cleanup(task_id, delay_minutes=5)
                
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
                error_msg = "Error en procesamiento"
                if resultado_completo.archivos_con_error:
                    archivo_error = resultado_completo.archivos_con_error[0]
                    error_msg = f"Error en procesamiento: {archivo_error.error}"
                
                # El tracker ya fue marcado como fallido en process_uploaded_files
                progress_manager.schedule_task_cleanup(task_id, delay_minutes=3)
                
                raise Exception(error_msg)
                
        finally:
            # Cerrar solo la sesión (no el engine porque es global)
            db.close()
            
    except Exception as e:
        error_msg = f"Error crítico procesando {archivo_data['filename']}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        tracker.mark_failed(error_msg, str(e))
        progress_manager.schedule_task_cleanup(task_id, delay_minutes=2)
        
        # Liberar memoria en caso de error
        if 'file_buffer' in locals():
            del file_buffer
        if 'content' in archivo_data:
            del archivo_data["content"]
        
        raise  # Re-raise para que Celery registre el error correctamente
