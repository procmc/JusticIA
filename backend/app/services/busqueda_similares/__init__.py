"""
Módulo de Búsqueda de Similares

Este módulo proporciona funcionalidades para la búsqueda de casos legales similares
utilizando análisis semántico y vectorial.

Estructura modular:
- busqueda/: Servicios de búsqueda vectorial y embeddings
- resumen/: Generación de resúmenes semánticos
- documentos/: Manejo de documentos y metadatos
- validacion/: Validación de datos y parámetros
"""

from .similarity_service import SimilarityService

__all__ = ['SimilarityService']
