"""
Servicio para comunicarse con Apache Tika Server.
Reemplaza el wrapper tika-python con llamadas HTTP directas.
"""
import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class TikaService:
    """Cliente HTTP para Apache Tika Server con OCR (Tesseract)"""
    
    def __init__(self, tika_url: Optional[str] = None):
        """
        Args:
            tika_url: URL del servidor Tika. Por defecto usa TIKA_SERVER_URL del .env
        """
        self.tika_url = tika_url or os.getenv('TIKA_SERVER_URL', 'http://tika:9998')
        self.timeout = int(os.getenv('TIKA_TIMEOUT', '300'))  # 5 minutos
        self.max_retries = 3
        
    def is_available(self) -> bool:
        """Verifica si el servidor Tika está disponible"""
        try:
            response = requests.get(f"{self.tika_url}/tika", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Tika no disponible: {e}")
            return False
    
    def extract_text(
        self, 
        content: bytes, 
        filename: str = "",
        enable_ocr: bool = True
    ) -> str:
        """
        Extrae texto de un archivo.
        
        Args:
            content: Contenido del archivo en bytes
            filename: Nombre del archivo (para logs)
            enable_ocr: Si True, habilita OCR automático para PDFs escaneados
            
        Returns:
            str: Texto extraído limpio
            
        Raises:
            Exception: Si falla la extracción
        """
        headers = {
            'Accept': 'text/plain',
            'Content-Type': 'application/octet-stream',
        }
        
        # Configurar OCR en español si está habilitado
        if enable_ocr:
            headers['X-Tika-OCRLanguage'] = 'spa'
            headers['X-Tika-PDFOcrStrategy'] = 'auto'
        
        endpoint = f"{self.tika_url}/tika"
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Extrayendo texto de '{filename}' (intento {attempt + 1}/{self.max_retries})")
                
                response = requests.put(
                    endpoint,
                    data=content,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    text = response.text
                    
                    if not text or not text.strip():
                        logger.warning(f"Tika no extrajo texto de '{filename}'")
                        return ""
                    
                    # Limpiar texto (remover espacios múltiples y saltos de línea)
                    text_limpio = ' '.join(text.split())
                    logger.info(f"Texto extraído: {len(text_limpio)} caracteres")
                    return text_limpio
                    
                elif response.status_code == 422:
                    logger.error(f"Tipo de archivo no soportado: {filename}")
                    raise ValueError("Tipo de archivo no soportado por Tika")
                    
                elif response.status_code == 500:
                    error_msg = response.text[:200] if response.text else "Error interno"
                    logger.error(f"Tika error: {error_msg}")
                    
                    if attempt < self.max_retries - 1:
                        continue
                    else:
                        raise Exception(f"Tika falló después de {self.max_retries} intentos")
                else:
                    raise Exception(f"Error de Tika: HTTP {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout procesando '{filename}' (intento {attempt + 1})")
                if attempt < self.max_retries - 1:
                    continue
                else:
                    raise Exception("Timeout procesando archivo con Tika")
                    
            except requests.exceptions.ConnectionError:
                logger.error("No se pudo conectar a Tika")
                raise Exception("Servidor Tika no disponible")
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Error en intento {attempt + 1}: {e}")
                    continue
                else:
                    raise
        
        raise Exception("Error procesando archivo con Tika")


# Instancia global del servicio (singleton)
tika_service = TikaService()
