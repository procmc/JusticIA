"""
Servicio para procesamiento asíncrono de archivos.
Maneja las tareas en segundo plano y el estado de procesos.
"""

import asyncio
from typing import List, Dict
from sqlalchemy.orm import Session
from fastapi import UploadFile
from io import BytesIO

from ..file_management.document_processor import process_uploaded_files


def procesar_archivo_individual_en_background(
    file_process_id: str,
    CT_Num_expediente: str,
    archivo_data: dict,
    db: Session,
    process_status_store: Dict[str, dict]
):
    """
    Función que procesa UN archivo individual en segundo plano.
    Actualiza el estado en process_status_store.
    
    Args:
        file_process_id: ID único del archivo
        CT_Num_expediente: Número de expediente
        archivo_data: Diccionario con datos del archivo
        db: Sesión de base de datos
        process_status_store: Diccionario para almacenar estados
    """
    try:
        # Actualizar estado: procesando
        process_status_store[file_process_id]["status"] = "procesando"
        process_status_store[file_process_id]["message"] = f"Procesando {archivo_data['filename']}..."
        process_status_store[file_process_id]["progress"] = 50
        
        # Recrear objeto UploadFile desde los datos guardados
        file_buffer = BytesIO(archivo_data['content'])
        file_obj = UploadFile(
            file=file_buffer,
            filename=archivo_data['filename']
        )
        
        # Procesar como lista de un solo archivo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        resultado_completo = loop.run_until_complete(
            process_uploaded_files([file_obj], CT_Num_expediente, db)
        )
        
        # Extraer resultado del archivo individual
        if resultado_completo.procesados_exitosamente > 0:
            archivo_resultado = resultado_completo.archivos_procesados[0]
            
            # Actualizar estado: completado
            process_status_store[file_process_id]["status"] = "completado"
            process_status_store[file_process_id]["message"] = "Archivo procesado exitosamente"
            process_status_store[file_process_id]["progress"] = 100
            process_status_store[file_process_id]["resultado"] = {
                "filename": archivo_data['filename'],
                "documento_id": archivo_resultado.file_id,
                "mensaje": archivo_resultado.message,
                "status": "success"
            }
        else:
            # Error en procesamiento
            if resultado_completo.archivos_con_error:
                archivo_error = resultado_completo.archivos_con_error[0]
                process_status_store[file_process_id]["status"] = "error"
                process_status_store[file_process_id]["message"] = archivo_error.error
                process_status_store[file_process_id]["progress"] = 0
            else:
                process_status_store[file_process_id]["status"] = "error"
                process_status_store[file_process_id]["message"] = "Error desconocido en procesamiento"
                process_status_store[file_process_id]["progress"] = 0
        
    except Exception as e:
        # Actualizar estado: error
        process_status_store[file_process_id]["status"] = "error"
        process_status_store[file_process_id]["message"] = f"Error: {str(e)}"
        process_status_store[file_process_id]["progress"] = 0
