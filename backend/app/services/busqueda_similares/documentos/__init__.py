"""
Módulo de servicios de documentos para búsqueda similares.

Incluye servicios para:
- Gestión de documentos y expedientes (documento_service.py)
- Obtención y procesamiento de documentos coincidentes (documento_retrieval_service.py)
"""

from .documento_service import DocumentoService
from .documento_retrieval_service import DocumentoRetrievalService

__all__ = [
    'DocumentoService',
    'DocumentoRetrievalService'
]
