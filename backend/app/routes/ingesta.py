from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from typing import List
from sqlalchemy.orm import Session
from app.schemas.ingesta_schemas import IngestaArchivosRequest
from app.services.file_processing_service import (
    process_uploaded_files,
    generar_respuesta_simplificada,
)
from app.services.async_processing_service import procesar_archivo_individual_en_background
from app.db.database import get_db
import uuid

router = APIRouter()

# Almacén temporal para estados de procesos (en memoria)
process_status_store = {}


@router.get("/status/{process_id}")
async def get_process_status(process_id: str):
    """
    Consulta el estado de un proceso asíncrono.
    """
    # Si el proceso no existe, devolver error
    if process_id not in process_status_store:
        raise HTTPException(
            status_code=404,
            detail=f"Proceso {process_id} no encontrado"
        )
    
    # Devolver el estado actual
    return process_status_store[process_id]


@router.post("/archivos")
async def ingestar_archivos(
    background_tasks: BackgroundTasks,
    CT_Num_expediente: str = Form(..., description="Número de expediente"),
    files: List[UploadFile] = File(..., description="Archivos a procesar"),
    db: Session = Depends(get_db),
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
    
    # Procesar cada archivo individualmente
    file_process_ids = []
    
    for file in files:
        # Generar ID único para este archivo
        file_process_id = str(uuid.uuid4())
        file_process_ids.append(file_process_id)
        
        # Leer contenido del archivo
        contenido = await file.read()
        archivo_data = {
            'filename': file.filename,
            'content_type': file.content_type,
            'content': contenido
        }
        
        # Guardar estado inicial para este archivo
        process_status_store[file_process_id] = {
            "status": "iniciando",
            "progress": 0,
            "message": f"Archivo {file.filename} en cola",
            "expediente": CT_Num_expediente,
            "filename": file.filename
        }
        
        # Crear función wrapper para este archivo
        def crear_wrapper(fid, exp, data):
            def ejecutar_procesamiento_individual():
                procesar_archivo_individual_en_background(
                    fid, exp, data, db, process_status_store
                )
            return ejecutar_procesamiento_individual
        
        # Ejecutar procesamiento individual en segundo plano
        wrapper = crear_wrapper(file_process_id, CT_Num_expediente, archivo_data)
        background_tasks.add_task(wrapper)
    
    # Devolver lista de IDs de archivos
    return {
        "message": f"{len(files)} archivos enviados para procesamiento",
        "file_process_ids": file_process_ids,
        "expediente": CT_Num_expediente,
        "total_files": len(files)
    }
