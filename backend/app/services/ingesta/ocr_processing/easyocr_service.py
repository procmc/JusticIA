"""
Servicio de OCR usando EasyOCR para extraer texto de imágenes y documentos escaneados.
Este módulo actúa como fallback cuando Apache Tika no puede extraer texto de documentos.

EasyOCR es una biblioteca multiplataforma que funciona en Windows y Linux sin
dependencias complejas del sistema.
"""

import logging
import tempfile
import os
from typing import List, Optional, Tuple
from pathlib import Path
import io

from app.config.ocr_config import OCR_CONFIG, IMAGE_EXTENSIONS, OCR_FALLBACK_EXTENSIONS

logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    Procesador OCR usando EasyOCR para extraer texto de imágenes y documentos escaneados.
    """

    def __init__(self):
        self._reader = None
        self._is_initialized = False

    def _initialize_reader(self):
        """Inicializa el lector OCR de forma lazy."""
        if self._is_initialized:
            return

        try:
            import easyocr
            # Inicializar con idiomas de configuración
            self._reader = easyocr.Reader(
                OCR_CONFIG.get("languages", ["es", "en"]),
                gpu=OCR_CONFIG.get("gpu", False),
            )
            self._is_initialized = True
            logger.info(f"EasyOCR inicializado correctamente con soporte para {OCR_CONFIG.get('languages', ['es','en'])}")
        except ImportError:
            raise ImportError("EasyOCR no está instalado. Instalar con: pip install easyocr")
        except Exception as e:
            logger.error(f"Error inicializando EasyOCR: {str(e)}")
            raise

    async def extract_text_from_pdf_images(self, content: bytes, filename: str, progress_tracker=None) -> str:
        """
        Extrae texto de un PDF usando OCR.
        Convierte las páginas del PDF a imágenes y aplica OCR usando PyMuPDF (fitz).

        Args:
            content: Contenido del archivo PDF en bytes
            filename: Nombre del archivo para logging
        Returns:
            str: Texto extraído del PDF
        """
        # Inicializar reader EasyOCR
        self._initialize_reader()

        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PyMuPDF no está instalado. Instalar con: pip install pymupdf")

        logger.info(f"Iniciando OCR para PDF (PyMuPDF): {filename}")

        # Actualizar progreso: inicialización OCR
        if progress_tracker:
            progress_tracker.update_progress(60, f"Inicializando OCR para PDF: {filename}")

        # Guardar PDF temporalmente
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf.write(content)
            temp_pdf_path = temp_pdf.name

        try:
            doc = fitz.open(temp_pdf_path)
            logger.info(f"PyMuPDF versión instalada: {getattr(fitz, '__version__', 'desconocida')}")

            texto_completo = []
            num_pages = min(len(doc), OCR_CONFIG.get("max_pages", 20))

            # Actualizar progreso: comenzando procesamiento de páginas
            if progress_tracker:
                progress_tracker.update_progress(65, f"Procesando {num_pages} páginas con OCR")

            for i in range(num_pages):
                page = doc.load_page(i)
                # Compatibilidad con distintas versiones de PyMuPDF
                # Nota: Pylance no reconoce los métodos de PyMuPDF, pero existen en runtime
                if hasattr(page, "get_pixmap"):
                    pix = page.get_pixmap(dpi=OCR_CONFIG.get("pdf_dpi", 200))  # type: ignore
                elif hasattr(page, "getPixmap"):
                    pix = page.getPixmap(dpi=OCR_CONFIG.get("pdf_dpi", 200))  # type: ignore
                else:
                    raise RuntimeError(
                        "La clase Page de PyMuPDF no tiene métodos compatibles para obtener imagen. "
                        "Actualiza pymupdf: pip install --upgrade pymupdf"
                    )

                img_bytes = pix.tobytes("png")
                texto_pagina = await self._extract_text_from_image_bytes(img_bytes, f"{filename}_page_{i+1}")

                if texto_pagina.strip():
                    texto_completo.append(f"--- Página {i+1} ---\n{texto_pagina}")

                # Actualizar progreso por cada página procesada
                if progress_tracker and num_pages > 1:
                    page_progress = 70 + int((i + 1) / num_pages * 25)  # 70-95% para páginas
                    progress_tracker.update_progress(
                        page_progress,
                        f"OCR completado página {i+1}/{num_pages} de {filename}"
                    )

            resultado = "\n\n".join(texto_completo)
            logger.info(f"OCR completado para {filename}: {len(resultado)} caracteres extraídos de {num_pages} páginas")

            # Actualizar progreso: OCR completado
            if progress_tracker:
                progress_tracker.update_progress(95, f"OCR completado: {len(resultado)} caracteres de {num_pages} páginas")

            return resultado
        finally:
            try:
                os.unlink(temp_pdf_path)
            except Exception:
                pass

    async def extract_text_from_image(self, content: bytes, filename: str) -> str:
        """
        Extrae texto de una imagen usando OCR.

        Args:
            content: Contenido de la imagen en bytes
            filename: Nombre del archivo para logging

        Returns:
            str: Texto extraído de la imagen
        """
        try:
            self._initialize_reader()
            return await self._extract_text_from_image_bytes(content, filename)
        except Exception as e:
            logger.error(f"Error en OCR de imagen {filename}: {str(e)}")
            raise ValueError(f"Error procesando imagen con OCR: {str(e)}")

    async def _extract_text_from_image_bytes(self, image_bytes: bytes, filename: str) -> str:
        """
        Función interna para extraer texto de bytes de imagen.
        """
        try:
            if not self._reader:
                raise ValueError("OCR reader no está inicializado")

            # EasyOCR puede trabajar directamente con bytes de imagen
            result = self._reader.readtext(image_bytes, detail=0, paragraph=OCR_CONFIG.get("paragraph_mode", True))
            texto = ' '.join(result) if result else ''
            if OCR_CONFIG.get("log_ocr_results", False):
                logger.debug(f"OCR extraído de {filename}: {len(texto)} caracteres")
            return texto.strip()
        except Exception as e:
            logger.error(f"Error procesando imagen {filename}: {str(e)}")
            return ""

    def is_text_likely_scanned(self, text: str, min_length: Optional[int] = None) -> bool:
        """
        Determina si un texto parece provenir de un documento escaneado
        basándose en heurísticas.

        Args:
            text: Texto a evaluar
            min_length: Longitud mínima esperada (usa configuración por defecto)

        Returns:
            bool: True si parece texto escaneado (poco contenido útil)
        """
        effective_min_length = min_length if min_length is not None else OCR_CONFIG.get("min_text_length", 50)

        if not text or len(text.strip()) < effective_min_length:
            return True

        text_clean = text.strip()
        if not text_clean:
            return True

        total_chars = len(text_clean)
        alnum_chars = sum(1 for c in text_clean if c.isalnum() or c.isspace())
        ratio = alnum_chars / total_chars if total_chars > 0 else 0

        is_too_short = total_chars < effective_min_length
        is_low_quality = ratio < OCR_CONFIG.get("min_alnum_ratio", 0.7)

        return is_too_short or is_low_quality


# Instancia global del procesador OCR
ocr_processor = OCRProcessor()


async def extract_text_with_ocr_fallback(content: bytes, filename: str, content_type: str, tika_text: str = "", progress_tracker=None) -> str:
    """
    Función de conveniencia para aplicar OCR como fallback.

    Args:
        content: Contenido del archivo
        filename: Nombre del archivo
        content_type: Tipo MIME del archivo
        tika_text: Texto extraído por Tika (puede estar vacío)

    Returns:
        str: Texto extraído (Tika + OCR si es necesario)
    """
    file_extension = Path(filename).suffix.lower()

    needs_ocr = False
    if file_extension == '.pdf':
        if not tika_text or ocr_processor.is_text_likely_scanned(tika_text):
            needs_ocr = True
            logger.info(f"PDF {filename} parece escaneado, aplicando OCR como fallback")
    elif file_extension in IMAGE_EXTENSIONS:
        needs_ocr = True
        logger.info(f"Imagen {filename} detectada, aplicando OCR")

    if needs_ocr:
        try:
            if file_extension == '.pdf':
                ocr_text = await ocr_processor.extract_text_from_pdf_images(content, filename, progress_tracker)
            else:
                ocr_text = await ocr_processor.extract_text_from_image(content, filename)

            if tika_text and tika_text.strip():
                return f"{tika_text}\n\n--- Texto extraído por OCR ---\n{ocr_text}"
            else:
                return ocr_text
        except Exception as e:
            logger.warning(f"OCR falló para {filename}: {str(e)}")
            if tika_text and tika_text.strip():
                return tika_text
            else:
                raise ValueError(f"No se pudo extraer texto ni con Tika ni con OCR: {str(e)}")

    return tika_text or ""