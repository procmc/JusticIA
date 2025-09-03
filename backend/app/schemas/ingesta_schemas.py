from pydantic import BaseModel, Field, validator
from typing import List, Optional
from app.schemas.schemas import ArchivoSimplificado

class IngestaArchivosRequest(BaseModel):
    """Schema para la solicitud de ingesta de archivos"""
    CT_Num_expediente: str = Field(..., description="Número de expediente")
    
    @validator('CT_Num_expediente')
    def validar_formato_expediente(cls, v):
        from app.utils.expediente_validator import validar_expediente
        
        if not validar_expediente(v):
            raise ValueError(f'Formato de expediente inválido: {v}')
        return v.strip().upper()


class IngestaArchivosResponse(BaseModel):
    """Schema para la respuesta de ingesta de archivos"""
    expediente: str
    total_archivos: int
    archivos_exitosos: int
    archivos_fallidos: int
    archivos: List[ArchivoSimplificado]
