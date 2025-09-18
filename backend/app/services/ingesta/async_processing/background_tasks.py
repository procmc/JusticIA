"""
Servicio para procesamiento asíncrono de archivos con seguimiento robusto.
Maneja las tareas en segundo plano con progreso granular y manejo de errores.
"""

import asyncio
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile
from io import BytesIO
import logging

from ..file_management.document_processor import process_uploaded_files
from .progress_tracker import progress_manager, ProgressTracker, TaskStatus

logger = logging.getLogger(__name__)


def procesar_archivo_individual_en_background(
    file_process_id: str,
    CT_Num_expediente: str,
    archivo_data: dict,
    db: Session,
    process_status_store: Optional[Dict[str, dict]] = None
):
    """
    Función que procesa UN archivo individual en segundo plano con progreso robusto.
    Utiliza el nuevo sistema de ProgressTracker para seguimiento granular.
    
    Args:
        file_process_id: ID único del archivo
        CT_Num_expediente: Número de expediente
        archivo_data: Diccionario con datos del archivo
        db: Sesión de base de datos
        process_status_store: (Opcional) Diccionario legacy para compatibilidad
    """
    # Crear tracker de progreso granular
    tracker = progress_manager.create_tracker(file_process_id, total_steps=100)
    
    try:
        # Paso 1: Inicialización (0-10%)
        tracker.update_progress(5, f"Iniciando procesamiento de {archivo_data['filename']}")
        
        # Compatibilidad con sistema legacy
        if process_status_store:
            process_status_store[file_process_id]["status"] = "processing"
            process_status_store[file_process_id]["message"] = f"Procesando {archivo_data['filename']}..."
            process_status_store[file_process_id]["progress"] = 5
        
        tracker.update_progress(10, "Recreando objeto de archivo")
        
        # Recrear objeto UploadFile desde los datos guardados
        file_buffer = BytesIO(archivo_data['content'])
        file_obj = UploadFile(
            file=file_buffer,
            filename=archivo_data['filename']
        )
        
        # Paso 2: Configuración de entorno async (10-20%)
        tracker.update_progress(15, "Configurando entorno de procesamiento")
        
        # Procesar como lista de un solo archivo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        tracker.update_progress(20, "Iniciando procesamiento del archivo")
        
        # Paso 3: Procesamiento principal (20-90%)
        resultado_completo = loop.run_until_complete(
            process_uploaded_files([file_obj], CT_Num_expediente, db, tracker)
        )
        
        # Paso 4: Evaluación de resultados (90-100%)
        tracker.update_progress(90, "Evaluando resultados del procesamiento")
        
        # Extraer resultado del archivo individual
        if resultado_completo.procesados_exitosamente > 0:
            archivo_resultado = resultado_completo.archivos_procesados[0]
            
            # Actualizar estado: completado
            tracker.mark_completed("Archivo procesado exitosamente")
            
            # 🔄 AUTO-LIMPIEZA: Programar eliminación de esta tarea en 5 minutos
            progress_manager.schedule_task_cleanup(file_process_id, delay_minutes=5)
            
            # Compatibilidad legacy
            if process_status_store:
                process_status_store[file_process_id].update({
                    "status": "completed",
                    "message": "Archivo procesado exitosamente",
                    "progress": 100,
                    "resultado": {
                        "filename": archivo_data['filename'],
                        "documento_id": archivo_resultado.file_id,
                        "mensaje": archivo_resultado.message,
                        "status": "success"
                    }
                })
        else:
            # Error en procesamiento
            if resultado_completo.archivos_con_error:
                archivo_error = resultado_completo.archivos_con_error[0]
                error_msg = f"Error en procesamiento: {archivo_error.error}"
                tracker.mark_failed(error_msg, archivo_error.razon)
                
                # 🔄 AUTO-LIMPIEZA: Programar eliminación de esta tarea fallida en 3 minutos
                progress_manager.schedule_task_cleanup(file_process_id, delay_minutes=3)
                
                # Compatibilidad legacy
                if process_status_store:
                    process_status_store[file_process_id].update({
                        "status": "error",
                        "message": error_msg,
                        "progress": 0
                    })
            else:
                error_msg = "Error desconocido en procesamiento"
                tracker.mark_failed(error_msg)
                
                # 🔄 AUTO-LIMPIEZA: Programar eliminación de esta tarea fallida en 3 minutos
                progress_manager.schedule_task_cleanup(file_process_id, delay_minutes=3)
                
                # Compatibilidad legacy
                if process_status_store:
                    process_status_store[file_process_id].update({
                        "status": "error",
                        "message": error_msg,
                        "progress": 0
                    })
        
    except Exception as e:
        # Manejo robusto de errores
        error_msg = f"Error crítico procesando {archivo_data['filename']}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        tracker.mark_failed(error_msg, str(e))
        
        # 🔄 AUTO-LIMPIEZA: Programar eliminación de esta tarea con error crítico en 2 minutos
        progress_manager.schedule_task_cleanup(file_process_id, delay_minutes=2)
        
        # Compatibilidad legacy
        if process_status_store:
            if file_process_id in process_status_store:
                process_status_store[file_process_id].update({
                    "status": "error",
                    "message": error_msg,
                    "progress": 0
                })
            else:
                process_status_store[file_process_id] = {
                    "status": "error",
                    "message": error_msg,
                    "progress": 0
                }
    
    finally:
        # Cerrar loop si fue creado
        try:
            if 'loop' in locals():
                loop.close()
        except:
            pass


def get_task_progress(task_id: str) -> Optional[Dict]:
    """
    Obtiene el progreso de una tarea específica.
    
    Args:
        task_id: ID de la tarea a consultar
        
    Returns:
        Diccionario con el estado de la tarea o None si no existe
    """
    return progress_manager.get_status(task_id)


def cleanup_old_tasks(max_age_hours: int = 24):
    """
    Limpia tareas completadas antiguas.
    
    Args:
        max_age_hours: Edad máxima en horas para mantener tareas completadas
    """
    progress_manager.remove_completed_tasks(max_age_hours)


def procesar_archivo_con_contenido_en_background(
    file_process_id: str,
    CT_Num_expediente: str,
    archivo_info: dict,  # Información del archivo ya guardado
    db: Session,
    process_status_store: Optional[Dict[str, dict]] = None
):
    """
    Función que procesa UN archivo que ya fue guardado en disco.
    Evita el problema de leer el archivo dos veces.
    
    Args:
        file_process_id: ID único del archivo
        CT_Num_expediente: Número de expediente
        archivo_info: Información del archivo ya guardado (incluye content)
        db: Sesión de base de datos
        process_status_store: (Opcional) Diccionario para compatibilidad
    """
    # Crear tracker de progreso granular
    tracker = progress_manager.create_tracker(file_process_id, total_steps=100)
    
    try:
        # Paso 1: Inicialización (0-10%)
        tracker.update_progress(5, f"Procesando archivo guardado: {archivo_info['filename']}")
        
        # Compatibilidad con sistema legacy
        if process_status_store:
            process_status_store[file_process_id]["status"] = "processing"
            process_status_store[file_process_id]["message"] = f"Procesando {archivo_info['filename']}..."
            process_status_store[file_process_id]["progress"] = 5
        
        tracker.update_progress(10, "Recreando objeto de archivo desde contenido guardado")
        
        # Usar el contenido ya leído y guardado
        file_buffer = BytesIO(archivo_info['content'])
        file_obj = UploadFile(
            file=file_buffer,
            filename=archivo_info['original_filename']
        )
        file_obj.content_type = archivo_info['content_type']
        
        # Paso 2: Configuración de entorno async (10-20%)
        tracker.update_progress(15, "Configurando entorno de procesamiento")
        
        # Procesar como lista de un solo archivo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        tracker.update_progress(20, "Iniciando procesamiento del archivo")
        
        # Paso 3: Procesamiento principal (20-90%)
        resultado_completo = loop.run_until_complete(
            process_uploaded_files([file_obj], CT_Num_expediente, db, tracker)
        )
        
        # Paso 4: Evaluación de resultados (90-100%)
        tracker.update_progress(90, "Evaluando resultados del procesamiento")
        
        # Extraer resultado del archivo individual
        if resultado_completo.procesados_exitosamente > 0:
            archivo_resultado = resultado_completo.archivos_procesados[0]
            
            # Actualizar estado: completado
            tracker.mark_completed("Archivo procesado exitosamente")
            
            # Auto-limpieza: Programar eliminación de esta tarea en 5 minutos
            progress_manager.schedule_task_cleanup(file_process_id, delay_minutes=5)
            
            # Compatibilidad legacy
            if process_status_store:
                process_status_store[file_process_id].update({
                    "status": "completed",
                    "message": "Archivo procesado exitosamente",
                    "progress": 100,
                    "resultado": {
                        "filename": archivo_info['filename'],
                        "documento_id": archivo_resultado.file_id,
                        "mensaje": archivo_resultado.message,
                        "status": "success"
                    }
                })
        else:
            # Error en procesamiento
            error_msg = "Error procesando el archivo"
            if resultado_completo.archivos_con_error:
                error_detalle = resultado_completo.archivos_con_error[0]
                error_msg = f"Error: {error_detalle.error_message}"
            
            tracker.mark_failed(error_msg)
            
            if process_status_store:
                process_status_store[file_process_id].update({
                    "status": "error",
                    "message": error_msg,
                    "progress": 0
                })
        
        # Limpiar loop
        loop.close()
        
    except Exception as e:
        error_msg = f"Error crítico procesando archivo: {str(e)}"
        logger.error(f"Error en background task {file_process_id}: {e}")
        
        tracker.mark_failed(error_msg)
        
        if process_status_store:
            process_status_store[file_process_id].update({
                "status": "error",
                "message": error_msg,
                "progress": 0
            })
