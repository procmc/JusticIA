"""
Rutas para gestión de archivos de expedientes
"""
from fastapi import APIRouter, HTTPException, Depends, Path as PathParam
from fastapi.responses import FileResponse
from typing import List
from sqlalchemy.orm import Session

from app.services.ingesta.file_management.file_storage_manager import FileStorageService
from app.db.database import get_db
from app.utils.expediente_validator import validar_expediente

router = APIRouter()

@router.get("/expediente/{expediente_numero}/archivos")
async def listar_archivos_expediente(
    expediente_numero: str = PathParam(..., description="Número del expediente"),
    db: Session = Depends(get_db)
):
    """
    Lista todos los archivos de un expediente específico.
    """
    # Validar formato del expediente
    if not validar_expediente(expediente_numero):
        raise HTTPException(
            status_code=400,
            detail="Formato de expediente inválido"
        )
    
    try:
        storage_service = FileStorageService()
        archivos = storage_service.listar_archivos_expediente(expediente_numero)
        return {
            "expediente": expediente_numero,
            "total_archivos": len(archivos),
            "archivos": archivos
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listando archivos: {str(e)}"
        )

@router.get("/expediente/{expediente_numero}/archivo/{nombre_archivo}")
async def descargar_archivo(
    expediente_numero: str = PathParam(..., description="Número del expediente"),
    nombre_archivo: str = PathParam(..., description="Nombre del archivo"),
    db: Session = Depends(get_db)
):
    """
    Descarga un archivo específico de un expediente.
    """
    # Validar formato del expediente
    if not validar_expediente(expediente_numero):
        raise HTTPException(
            status_code=400,
            detail="Formato de expediente inválido"
        )
    
    try:
        storage_service = FileStorageService()
        ruta_archivo = storage_service.obtener_ruta_archivo(expediente_numero, nombre_archivo)
        
        if not ruta_archivo:
            raise HTTPException(
                status_code=404,
                detail="Archivo no encontrado"
            )
        
        return FileResponse(
            path=str(ruta_archivo),
            filename=nombre_archivo,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error descargando archivo: {str(e)}"
        )