from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ConsultaRAGRequest(BaseModel):
    """Esquema para consultas RAG generales"""
    pregunta: str = Field(..., min_length=3, max_length=1000, description="Pregunta o consulta del usuario")
    top_k: Optional[int] = Field(15, ge=1, le=50, description="Número de documentos a recuperar")
    incluir_metadatos: Optional[bool] = Field(True, description="Si incluir metadatos detallados en la respuesta")

class ConsultaExpedienteRAGRequest(BaseModel):
    """Esquema para consultas RAG específicas de expediente"""
    expediente_numero: str = Field(..., min_length=1, description="Número del expediente a consultar")
    pregunta: str = Field(..., min_length=3, max_length=1000, description="Pregunta específica sobre el expediente")
    top_k: Optional[int] = Field(10, ge=1, le=30, description="Número de documentos a recuperar del expediente")

class BusquedaSimilaresRAGRequest(BaseModel):
    """Esquema para búsqueda de casos similares usando RAG"""
    descripcion_caso: str = Field(..., min_length=10, max_length=2000, description="Descripción del caso para buscar similares")
    expediente_excluir: Optional[str] = Field(None, description="Expediente a excluir de la búsqueda")
    top_k: Optional[int] = Field(20, ge=1, le=50, description="Número de casos similares a buscar")

class FuenteDocumento(BaseModel):
    """Esquema para información de fuentes de documentos"""
    expediente: str
    archivo: str
    relevancia: float = Field(..., ge=0.0, le=1.0)
    fragmento: str

class CasoSimilar(BaseModel):
    """Esquema para casos similares encontrados"""
    expediente: str
    relevancia_total: float = Field(..., ge=0.0)
    documentos: List[str]
    resumen_fragmentos: List[str]

class RAGResponse(BaseModel):
    """Esquema base para respuestas RAG"""
    respuesta: str
    success: bool = True
    error: Optional[str] = None

class ConsultaGeneralRAGResponse(RAGResponse):
    """Esquema para respuestas de consultas generales RAG"""
    expedientes_consultados: int
    expedientes: List[str]
    fuentes: List[FuenteDocumento]
    total_documentos: int

class ConsultaExpedienteRAGResponse(RAGResponse):
    """Esquema para respuestas de consultas específicas de expediente"""
    expediente: str
    fuentes: List[FuenteDocumento]
    documentos_analizados: int

class BusquedaSimilaresRAGResponse(RAGResponse):
    """Esquema para respuestas de búsqueda de casos similares"""
    casos_similares: List[CasoSimilar]
    total_casos: int
    descripcion_busqueda: str

class AnalisisExpedienteRAGRequest(BaseModel):
    """Esquema para análisis completo de expediente"""
    expediente_numero: str = Field(..., min_length=1, description="Número del expediente a analizar")
    tipo_analisis: Optional[str] = Field("completo", description="Tipo de análisis: completo, resumen, cronologia")

class AnalisisExpedienteRAGResponse(RAGResponse):
    """Esquema para respuesta de análisis de expediente"""
    expediente: str
    tipo_proceso: Optional[str] = None
    partes: List[str] = []
    estado_procesal: Optional[str] = None
    documentos_principales: List[str] = []
    proximas_actuaciones: List[str] = []
    resumen_cronologico: Optional[str] = None

class BusquedaAvanzadaRAGRequest(BaseModel):
    """Esquema para búsquedas avanzadas con filtros"""
    consulta: str = Field(..., min_length=3, max_length=1000)
    filtros: Optional[Dict[str, Any]] = Field(None, description="Filtros adicionales como tipo_proceso, fecha_desde, etc.")
    tipo_proceso: Optional[str] = Field(None, description="Filtrar por tipo: PN, FA, CV, etc.")
    fecha_desde: Optional[str] = Field(None, description="Fecha desde en formato YYYY-MM-DD")
    fecha_hasta: Optional[str] = Field(None, description="Fecha hasta en formato YYYY-MM-DD")
    top_k: Optional[int] = Field(20, ge=1, le=100)

class TendenciaRAG(BaseModel):
    """Esquema para análisis de tendencias"""
    periodo: str
    tipo_proceso: Optional[str] = None
    total_casos: int
    casos_mas_comunes: List[Dict[str, Any]]
    resumen_tendencia: str

class EstadisticasRAGResponse(RAGResponse):
    """Esquema para respuestas estadísticas"""
    total_expedientes: int
    distribucion_por_tipo: Dict[str, int]
    tendencias: List[TendenciaRAG]
    insights: List[str]

class SugerenciaLegalRAGRequest(BaseModel):
    """Esquema para solicitar sugerencias legales basadas en precedentes"""
    situacion_legal: str = Field(..., min_length=10, max_length=2000)
    tipo_proceso: Optional[str] = None
    buscar_precedentes: Optional[bool] = Field(True)

class SugerenciaLegalRAGResponse(RAGResponse):
    """Esquema para respuestas de sugerencias legales"""
    sugerencias: List[str]
    precedentes: List[CasoSimilar]
    estrategias_recomendadas: List[str]
    documentos_modelo: List[FuenteDocumento]