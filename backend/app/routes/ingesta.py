from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from app.schemas.ingesta_schemas import (
    IngestaArchivosRequest,
    IngestaArchivosResponse
)
from app.services.file_processing_service import process_uploaded_files, generar_respuesta_simplificada
from app.db.database import get_db
from app.auth.jwt_auth import require_role

router = APIRouter()

@router.post("/archivos", response_model=IngestaArchivosResponse)
@require_role("Usuario_Judicial")
async def ingestar_archivos(
    CT_Num_expediente: str = Form(..., description="Número de expediente"),
    files: List[UploadFile] = File(..., description="Archivos a procesar"),
    db: Session = Depends(get_db)
):
    """
    Ingesta de archivos para un expediente específico.
    Crea/busca expediente en BD y almacena documentos.
    """
    # Validar expediente
    try:
        request_validado = IngestaArchivosRequest(CT_Num_expediente=CT_Num_expediente)
        CT_Num_expediente = request_validado.CT_Num_expediente
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not files:
        raise HTTPException(status_code=400, detail="Debe proporcionar al menos un archivo")
    
    # Procesar archivos con conexión a BD
    resultado_completo = await process_uploaded_files(files, CT_Num_expediente, db)
    
    # Generar respuesta simplificada
    respuesta_simplificada = generar_respuesta_simplificada(resultado_completo, CT_Num_expediente)
    
    return respuesta_simplificada
