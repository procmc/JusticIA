from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List
from app.schemas.schemas import (
    IngestaItem, 
    IngestaBatch, 
    FileProcessingStatus
)
from app.services.file_processing_service import process_uploaded_files

router = APIRouter()

# Ruta dinámica para ingesta de archivos (uno o múltiples)
@router.post("/archivos", response_model=FileProcessingStatus)
async def ingestar_archivos(
    expediente: str = Form(..., description="Número de expediente (requerido)"),
    files: List[UploadFile] = File(..., description="Uno o más archivos a procesar")
):
    """
    Ingesta dinámica de archivos para un expediente específico.
    
    - Puede recibir uno o múltiples archivos
    - Formatos soportados: PDF, DOC, DOCX, RTF, TXT, MP3
    - Cada archivo se procesa individualmente
    - Retorna status detallado de cada archivo
    """
    if not expediente.strip():
        raise HTTPException(
            status_code=400, 
            detail="El número de expediente es obligatorio"
        )
    
    if not files:
        raise HTTPException(
            status_code=400, 
            detail="Debe proporcionar al menos un archivo"
        )
    
    # Procesar archivos dinámicamente
    result = await process_uploaded_files(files, expediente)
    return result
