"""
Configuración para el procesamiento OCR.
Contiene parámetros optimizados para extracción de texto de imágenes y documentos escaneados.
"""

# Configuración de EasyOCR
OCR_CONFIG = {
    # Idiomas soportados por defecto
    "languages": ["es", "en"],
    
    # Configuración de hardware
    "gpu": False,  # Usar CPU por defecto para mayor compatibilidad
    
    # Configuración de calidad para PDFs
    "pdf_dpi": 200,  # DPI para conversión de PDF a imagen
    "max_pages": 20,  # Máximo de páginas a procesar por eficiencia
    
    # Umbrales para detección de documentos escaneados
    "min_text_length": 50,  # Longitud mínima de texto esperada
    "min_alnum_ratio": 0.7,  # Ratio mínimo de caracteres alfanuméricos
    
    # Configuración de procesamiento
    "paragraph_mode": True,  # Extraer texto en modo párrafo
    "detail_mode": False,    # No devolver coordenadas detalladas
    
    # Configuración de imágenes temporales
    "temp_image_format": "PNG",  # Formato para imágenes temporales
    
    # Configuración de logging
    "log_ocr_results": True,  # Loggear resultados de OCR
}

# Extensiones de imagen soportadas
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp']

# Extensiones que pueden necesitar OCR como fallback
OCR_FALLBACK_EXTENSIONS = ['.pdf']

# Tipos MIME de imagen
IMAGE_MIME_TYPES = [
    'image/jpeg',
    'image/png', 
    'image/tiff',
    'image/bmp'
]