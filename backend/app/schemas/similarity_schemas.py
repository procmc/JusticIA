from typing import List, Optional, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime


class SimilaritySearchRequest(BaseModel):
    """Request para búsqueda de casos similares"""
    search_mode: Literal["description", "expedient"] = Field(
        ..., 
        description="Modo de búsqueda: 'description' para texto libre, 'expedient' para número de expediente"
    )
    query_text: Optional[str] = Field(
        None, 
        max_length=2000,
        description="Texto libre para búsqueda por descripción (requerido si search_mode='description')"
    )
    expedient_number: Optional[str] = Field(
        None, 
        max_length=60,
        description="Número de expediente para búsqueda (requerido si search_mode='expedient')"
    )
    limit: int = Field(
        30, 
        ge=1, 
        le=100,
        description="Número máximo de expedientes similares a retornar"
    )
    similarity_threshold: float = Field(
        0.5, 
        ge=0.0, 
        le=1.0,
        description="Umbral mínimo de similitud (0.0 a 1.0)"
    )

    @validator('query_text')
    def validate_query_text(cls, v, values):
        search_mode = values.get('search_mode')
        if search_mode == 'description' and (not v or not v.strip()):
            raise ValueError('query_text es requerido cuando search_mode es "description"')
        return v

    @validator('expedient_number')
    def validate_expedient_number(cls, v, values):
        search_mode = values.get('search_mode')
        if search_mode == 'expedient' and (not v or not v.strip()):
            raise ValueError('expedient_number es requerido cuando search_mode es "expedient"')
        return v


class DocumentMatch(BaseModel):
    """Documento individual que hace match"""
    document_id: int
    document_name: str
    similarity_score: float
    text_fragment: str = Field(..., max_length=500, description="Fragmento de texto relevante")
    page_number: Optional[int] = None


class SimilarCase(BaseModel):
    """Expediente similar encontrado"""
    expedient_id: int
    expedient_number: str
    similarity_percentage: float = Field(..., description="Porcentaje de similitud (0-100)")
    document_count: int = Field(..., description="Número total de documentos en el expediente")
    matched_documents: List[DocumentMatch] = Field(..., description="Documentos que hicieron match")
    creation_date: datetime
    last_activity_date: Optional[datetime] = None
    
    # Metadatos adicionales para el frontend
    matter_type: Optional[str] = None
    court_instance: Optional[str] = None


class SimilaritySearchResponse(BaseModel):
    """Respuesta completa de búsqueda de similares"""
    search_criteria: str = Field(..., description="Criterio de búsqueda utilizado")
    search_mode: str = Field(..., description="Modo de búsqueda utilizado")
    total_results: int = Field(..., description="Número total de expedientes encontrados")
    execution_time_ms: float = Field(..., description="Tiempo de ejecución en milisegundos")
    similarity_threshold: float = Field(..., description="Umbral de similitud aplicado")
    
    similar_cases: List[SimilarCase] = Field(..., description="Lista de expedientes similares")
    
    # Metadatos de la búsqueda
    search_timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_documents_analyzed: int = Field(..., description="Total de documentos analizados")
    
    class Config:
        schema_extra = {
            "example": {
                "search_criteria": "accidente de tránsito indemnización",
                "search_mode": "description",
                "total_results": 5,
                "execution_time_ms": 234.5,
                "similarity_threshold": 0.75,
                "similar_cases": [
                    {
                        "expedient_id": 123,
                        "expedient_number": "2024-001-01-CI",
                        "similarity_percentage": 87.5,
                        "document_count": 12,
                        "matched_documents": [
                            {
                                "document_id": 456,
                                "document_name": "demanda_inicial.pdf",
                                "similarity_score": 0.89,
                                "text_fragment": "El accidente de tránsito ocurrió en la intersección...",
                                "page_number": 3
                            }
                        ],
                        "creation_date": "2024-01-15T10:30:00Z",
                        "matter_type": "Civil"
                    }
                ],
                "search_timestamp": "2025-09-10T14:30:00Z",
                "total_documents_analyzed": 1547
            }
        }


class SimilaritySearchError(BaseModel):
    """Error en búsqueda de similares"""
    error_code: str
    error_message: str
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
