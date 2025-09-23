"""
Módulo de procesamiento OCR para archivos escaneados.
Fallback para cuando Tika no puede extraer texto de documentos.

Uso:
- from app.services.ingesta.ocr_processing.easyocr_service import ocr_processor
"""

__all__ = [
    'ocr_processor'
]