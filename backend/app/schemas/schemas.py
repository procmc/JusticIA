from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class IngestaItem(BaseModel):
    id: str
    texto: str
    metadata: Optional[dict] = None

class IngestaBatch(BaseModel):
    items: List[IngestaItem]

class ConsultaReq(BaseModel):
    query: str
    k: int = 3

# Esquemas para ingesta de archivos
class FileUploadResponse(BaseModel):
    status: str
    message: str
    file_id: Optional[str] = None
    expediente: str
    nombre_archivo: str
    tipo_archivo: str
    fecha_procesamiento: datetime
    texto_extraido_preview: Optional[str] = None  # Primeros 200 caracteres
    metadatos: Optional[dict] = None
    error_detalle: Optional[str] = None

class FileValidationError(BaseModel):
    error: str
    archivo: str
    razon: str
    formatos_permitidos: List[str]

class FileProcessingStatus(BaseModel):
    total_archivos: int
    procesados_exitosamente: int
    errores: int
    archivos_procesados: List[FileUploadResponse]
    archivos_con_error: List[FileValidationError]
