from typing import List, Optional, Literal
from pydantic import BaseModel, Field, validator


class SimilaritySearchRequest(BaseModel):
    """Request para búsqueda de casos similares"""
    modo_busqueda: Literal["descripcion", "expediente"]
    texto_consulta: Optional[str] = None
    numero_expediente: Optional[str] = None
    limite: int = Field(default=30, ge=1, le=100)
    umbral_similitud: float = Field(default=0.3, ge=0.0, le=1.0)

    @validator('texto_consulta')
    def validate_texto_consulta(cls, v, values):
        modo_busqueda = values.get('modo_busqueda')
        if modo_busqueda == 'descripcion' and (not v or not v.strip()):
            raise ValueError('texto_consulta es requerido cuando modo_busqueda es "descripcion"')
        return v

    @validator('numero_expediente')
    def validate_numero_expediente(cls, v, values):
        modo_busqueda = values.get('modo_busqueda')
        if modo_busqueda == 'expediente' and (not v or not v.strip()):
            raise ValueError('numero_expediente es requerido cuando modo_busqueda es "expediente"')
        return v


class DocumentoCoincidente(BaseModel):
    """Documento coincidente"""
    CN_Id_documento: Optional[int] = None
    CT_Nombre_archivo: str
    puntuacion_similitud: float
    url_descarga: str
    CT_Ruta_archivo: str


class CasoSimilar(BaseModel):
    """Expediente similar encontrado"""
    expediente_id: str
    CN_Id_expediente: Optional[int] = None
    CT_Num_expediente: str
    puntuacion_similitud: float
    documentos_coincidentes: List[DocumentoCoincidente]
    total_documentos: int


class RespuestaBusquedaSimilitud(BaseModel):
    """Respuesta de búsqueda de similares"""
    criterio_busqueda: str
    modo_busqueda: str
    total_resultados: int
    casos_similares: List[CasoSimilar]
