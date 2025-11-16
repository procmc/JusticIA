"""
Limpieza y normalización de texto extraído de documentos.

Proporciona funciones especializadas para limpiar texto de documentos PDF,
HTML y OCR, corrigiendo problemas comunes de encoding, espacios excesivos
y caracteres extraños.

Problemas corregidos:
    * Doble encoding UTF-8 → Latin-1 (Ã© → é, Ãº → ú, etc.)
    * Caracteres de control (excepto \n y \t)
    * Espacios no-breaking ( ) y Unicode raros
    * Múltiples espacios/saltos de línea
    * Espacios alrededor de puntuación
    * Artefactos de OCR ([image], [graphic])
    * Comillas y guiones mal codificados (â€œ → ")

Funciones principales:
    * clean_extracted_text: Limpieza general completa
    * fix_encoding_issues: Corrección de encoding UTF-8/Latin-1
    * clean_pdf_text: Especializada para PDFs
    * clean_ocr_text: Especializada para OCR
    * validate_cleaned_text: Validación de calidad

Pipeline de limpieza (10 pasos):
    1. Normalización Unicode (NFKC)
    2. Remoción de caracteres de control
    3. Corrección de encoding
    4. Limpieza de espacios Unicode
    5. Reducción de espacios múltiples
    6. Reducción de saltos de línea
    7. Trim de espacios en líneas
    8. Limpieza de líneas vacías
    9. Espaciado de puntuación
    10. Remoción de artefactos OCR

Example:
    >>> from app.services.ingesta.file_management.text_cleaner import clean_extracted_text
    >>> 
    >>> # Texto con problemas
    >>> texto_sucio = "Ã Ã San JosÃ©, a las diez   horas..."
    >>> 
    >>> # Limpiar
    >>> texto_limpio = clean_extracted_text(texto_sucio, "documento.pdf")
    >>> print(texto_limpio)
    "San José, a las diez horas..."
    >>> 
    >>> # Validar calidad
    >>> is_valid, msg = validate_cleaned_text(texto_limpio)

Note:
    * Optimizado con regex para alto rendimiento
    * Logging automático de reducciones >10%
    * Detección de problemas persistentes
    * Funciones especializadas por tipo de documento

Ver también:
    * app.services.ingesta.tika_service: Genera texto sucio
    * app.services.ingesta.document_processor: Usa text_cleaner
    * app.services.rag.retriever: Usa fix_encoding_issues

Authors:
    JusticIA Team

Version:
    2.0.0 - Corrección de encoding optimizada
"""
"""Helper para limpieza y normalización de texto extraído de documentos.

Este módulo proporciona funciones para limpiar texto extraído de documentos,
corrigiendo problemas comunes de encoding, espacios excesivos, y caracteres extraños.
"""
import re
import unicodedata
import logging

logger = logging.getLogger(__name__)


def clean_extracted_text(text: str, filename: str = "") -> str:
    """
    Limpia el texto extraído de documentos para remover caracteres extraños,
    espacios excesivos y problemas de encoding.
    
    Args:
        text: Texto sin procesar extraído del documento
        filename: Nombre del archivo (opcional, para logging)
        
    Returns:
        str: Texto limpio y normalizado
        
    Example:
        >>> text = "Â Â Â San JosÃ©, a las diez horas..."
        >>> clean_text = clean_extracted_text(text)
        >>> print(clean_text)
        "San José, a las diez horas..."
    """
    if not text:
        return ""
    
    original_length = len(text)
    
    # 1. Normalizar Unicode (NFKC): Convierte caracteres compatibles a su forma estándar
    #    Ejemplo: "Â " → " ", caracteres de espacio especiales → espacio normal
    text = unicodedata.normalize('NFKC', text)
    
    # 2. Remover caracteres de control (excepto saltos de línea y tabuladores)
    text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or char in '\n\t')
    
    # 3. Corregir problemas comunes de encoding (doble encoding UTF-8 → Latin-1)
    text = fix_encoding_issues(text)
    
    # 4. Remover múltiples espacios no-breaking (Â) y espacios Unicode raros
    text = re.sub(r'[\u00A0\u2000-\u200B\u202F\u205F\u3000]+', ' ', text)
    
    # 5. Remover espacios múltiples (3 o más seguidos) reemplazándolos por uno solo
    text = re.sub(r' {3,}', ' ', text)
    
    # 6. Remover saltos de línea múltiples (3 o más seguidos) dejando máximo 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 7. Remover espacios al inicio y final de cada línea (optimizado con regex)
    text = re.sub(r'[ \t]+\n', '\n', text)  # Espacios al final de línea
    text = re.sub(r'\n[ \t]+', '\n', text)  # Espacios al inicio de línea
    
    # 8. Remover líneas vacías múltiples
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    
    # 9. Limpiar espacios alrededor de puntuación
    text = clean_punctuation_spacing(text)
    
    # 10. Remover caracteres de imagen/gráfico comunes en OCR
    text = remove_ocr_artifacts(text)
    
    # 11. Trim final
    text = text.strip()
    
    # Log de resultados
    cleaned_length = len(text)
    reduction_percent = ((original_length - cleaned_length) / original_length * 100) if original_length > 0 else 0
    
    if reduction_percent > 10:  # Solo log si hay reducción significativa
        logger.info(
            f"Texto limpiado{' de ' + filename if filename else ''}: "
            f"{original_length} → {cleaned_length} caracteres "
            f"({reduction_percent:.1f}% reducción)"
        )
    
    return text


def fix_encoding_issues(text: str) -> str:
    """
    Corrige problemas comunes de encoding (doble encoding UTF-8 → Latin-1).
    Optimizado con regex para mejor rendimiento.
    
    Args:
        text: Texto con posibles problemas de encoding
        
    Returns:
        str: Texto con encoding corregido
    """
    # Optimización: Solo procesar si hay caracteres problemáticos
    if not any(char in text for char in ['Ã', 'â', 'Â']):
        return text
    
    # Diccionario de correcciones comunes
    encoding_fixes = {
        # Vocales con acento (minúsculas)
        'Ã©': 'é',   # e con acento
        'Ã­': 'í',   # i con acento
        'Ã¡': 'á',   # a con acento
        'Ã³': 'ó',   # o con acento
        'Ãº': 'ú',   # u con acento
        'Ã±': 'ñ',   # ñ
        
        # Vocales con acento (mayúsculas)
        'Ã': 'Á',    # A con acento
        'Ã': 'É',    # E con acento
        'Ã': 'Í',    # I con acento
        'Ã': 'Ó',    # O con acento
        'Ã': 'Ú',    # U con acento
        'Ã': 'Ñ',    # Ñ mayúscula
        
        # Símbolos y puntuación
        'Â¢': '¢',   # símbolo de centavo
        'Â°': '°',   # símbolo de grado
        'Â±': '±',   # más-menos
        'Â§': '§',   # símbolo de sección
        'Â¶': '¶',   # símbolo de párrafo
        
        # Comillas y guiones (diferentes variantes)
        'â€œ': '"',  # comillas dobles apertura
        'â€': '"',   # comillas dobles cierre
        'â€˜': "'",  # comillas simples apertura
        'â€™': "'",  # comillas simples cierre
        'â€"': '–',  # guion largo (en dash)
        'â€"': '—',  # guion extra largo (em dash)
        'â€¢': '•',  # bullet point
        'â€¦': '...',# puntos suspensivos
        
        # Variantes más cortas (por si están truncadas)
        'â': '"',    # comillas dobles
        'â': '"',    # comillas dobles cierre
        'â': "'",    # comillas simples
        'â': '–',    # guion largo
        'â': '—',    # guion extra largo
    }
    
    # Aplicar todas las correcciones
    for wrong, correct in encoding_fixes.items():
        if wrong in text:  # Solo reemplazar si existe
            text = text.replace(wrong, correct)
    
    return text


def clean_punctuation_spacing(text: str) -> str:
    """
    Limpia espacios incorrectos alrededor de puntuación.
    
    Args:
        text: Texto con posibles espacios incorrectos
        
    Returns:
        str: Texto con puntuación correctamente espaciada
    """
    # Remover espacios antes de puntuación final
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    
    # Remover espacios después de puntuación de apertura
    text = re.sub(r'([¿¡])\s+', r'\1', text)
    
    # Asegurar un espacio después de puntuación (excepto al final de línea)
    text = re.sub(r'([,.;:!?])([^\s\n])', r'\1 \2', text)
    
    return text


def remove_ocr_artifacts(text: str) -> str:
    """
    Remueve artefactos comunes de OCR como marcadores de imagen y gráficos.
    
    Args:
        text: Texto con posibles artefactos de OCR
        
    Returns:
        str: Texto sin artefactos
    """
    # Remover marcadores de imagen con diferentes formatos
    patterns = [
        r'\[image:.*?\]',           # [image: graphic] o [image: logo]
        r'\[graphic\]',             # [graphic]
        r'\[pic\]',                 # [pic]
        r'\[photo\]',               # [photo]
        r'\[figure\s*\d*\]',        # [figure] o [figure 1]
        r'<image>.*?</image>',      # <image>...</image>
        r'\[img:.*?\]',             # [img:...]
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text


def detect_encoding_problems(text: str) -> bool:
    """
    Detecta si el texto tiene problemas de encoding no resueltos.
    
    Args:
        text: Texto a analizar
        
    Returns:
        bool: True si se detectan problemas de encoding
    """
    # Caracteres que indican problemas de encoding
    problematic_chars = [
        '茅', '谩', '帽', '贸',  # Caracteres chinos que aparecen con mal encoding
        'iacute', 'aacute', 'eacute', 'oacute', 'uacute',  # Entidades HTML sin procesar
        'Ã', 'â',  # Prefijos comunes de mal encoding
    ]
    
    return any(char in text for char in problematic_chars)


def validate_cleaned_text(text: str, min_length: int = 10, filename: str = "") -> tuple[bool, str]:
    """
    Valida que el texto limpiado sea útil.
    
    Args:
        text: Texto limpiado a validar
        min_length: Longitud mínima requerida
        filename: Nombre del archivo (opcional, para mensajes de error)
        
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if not text:
        return False, f"Texto vacío{' en ' + filename if filename else ''}"
    
    if len(text.strip()) < min_length:
        return False, f"Texto muy corto{' en ' + filename if filename else ''}: {len(text.strip())} caracteres (mínimo: {min_length})"
    
    # Verificar que no sea solo espacios y saltos de línea
    if not text.replace(' ', '').replace('\n', '').replace('\t', ''):
        return False, f"Texto solo contiene espacios{' en ' + filename if filename else ''}"
    
    # Verificar problemas de encoding persistentes
    if detect_encoding_problems(text):
        logger.warning(f"Detectados problemas de encoding persistentes{' en ' + filename if filename else ''}")
        # No retornar False, solo advertir
    
    return True, ""


# Funciones de conveniencia para casos específicos

def clean_pdf_text(text: str, filename: str = "") -> str:
    """
    Limpieza especializada para texto extraído de PDFs.
    
    Args:
        text: Texto extraído de PDF
        filename: Nombre del archivo
        
    Returns:
        str: Texto limpiado con consideraciones específicas de PDF
    """
    # Aplicar limpieza general
    text = clean_extracted_text(text, filename)
    
    # Limpiezas específicas de PDF
    # Remover números de página aislados al final de líneas
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    
    # Remover guiones de separación de palabras al final de línea
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    
    return text


def clean_html_text(text: str, filename: str = "") -> str:
    """
    Limpieza especializada para texto extraído de HTML.
    
    Args:
        text: Texto extraído de HTML
        filename: Nombre del archivo
        
    Returns:
        str: Texto limpiado con consideraciones específicas de HTML
    """
    # Aplicar limpieza general
    text = clean_extracted_text(text, filename)
    
    # Limpiezas específicas de HTML
    # Remover entidades HTML residuales
    html_entities = {
        '&nbsp;': ' ',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&apos;': "'",
        '&copy;': '©',
        '&reg;': '®',
    }
    
    for entity, replacement in html_entities.items():
        text = text.replace(entity, replacement)
    
    return text


def clean_ocr_text(text: str, filename: str = "") -> str:
    """
    Limpieza especializada para texto extraído con OCR.
    
    Args:
        text: Texto extraído con OCR
        filename: Nombre del archivo
        
    Returns:
        str: Texto limpiado con consideraciones específicas de OCR
    """
    # Aplicar limpieza general
    text = clean_extracted_text(text, filename)
    
    # Limpiezas específicas de OCR
    # Corregir confusiones comunes de OCR
    ocr_fixes = {
        ' l ': ' I ',      # 'l' minúscula confundida con 'I' mayúscula
        ' O ': ' 0 ',      # 'O' confundida con '0' en contextos numéricos
        '|': 'I',          # Barra vertical confundida con I
        '~': '-',          # Tilde confundida con guion
    }
    
    for wrong, correct in ocr_fixes.items():
        text = text.replace(wrong, correct)
    
    return text
