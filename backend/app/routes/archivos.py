"""
Rutas para gestión de archivos de expedientes
"""
from fastapi import APIRouter, HTTPException, Depends, Path as PathParam
from fastapi.responses import FileResponse
from typing import List
from sqlalchemy.orm import Session
import logging

from app.services.documentos.file_management_service import file_management_service
from app.db.database import get_db
from app.utils.expediente_validator import validar_expediente

router = APIRouter()
logger = logging.getLogger(__name__)

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
        archivos = file_management_service.listar_archivos_expediente(expediente_numero)
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
async def descargar_archivo_expediente(
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
        ruta_archivo = file_management_service.obtener_ruta_archivo(expediente_numero, nombre_archivo)
        
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

@router.get("/download")
async def descargar_archivo_por_ruta(ruta_archivo: str):
    """
    Descarga un archivo específico usando su ruta completa.
    Funcionalidad migrada desde /documentos/file para centralizar descargas.
    
    Args:
        ruta_archivo: Ruta completa del archivo a descargar
    """
    try:
        return file_management_service.descargar_archivo(ruta_archivo)
    except Exception as e:
        logger.error(f"Error descargando archivo {ruta_archivo}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error descargando archivo: {str(e)}"
        )