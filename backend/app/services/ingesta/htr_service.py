"""
Cliente HTTP del servidor de HTR (reconocimiento de escritura a mano).

Cliente HTTP del servidor de HTR (reconocimiento de escritura a mano).
Calcado de `tika_service.py`: misma forma, mismo estilo, mismas
convenciones — configuración por variable de entorno, `is_available()`,
reintentos y logging.

Igual que Tika, el HTR corre en su propio contenedor y el backend lo
consume por HTTP. No es lógica de dominio: es infraestructura.

Configuración:
    * HTR_SERVER_URL: URL del servidor (default: http://servidor-htr:9100)
    * HTR_TIMEOUT:    timeout en segundos (default: 300)
"""

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class HTRService:
    """Cliente HTTP para el servidor de reconocimiento de manuscrito."""

    def __init__(self, htr_url: Optional[str] = None):
        """
        Args:
            htr_url: URL del servidor HTR. Por defecto usa HTR_SERVER_URL del .env
        """
        self.htr_url = htr_url or os.getenv('HTR_SERVER_URL', 'http://servidor-htr:9100')
        self.timeout = int(os.getenv('HTR_TIMEOUT', '300'))
        self.max_retries = 2

    def is_available(self) -> bool:
        """Verifica si el servidor HTR está disponible y con el modelo cargado."""
        try:
            respuesta = requests.get(f"{self.htr_url}/salud", timeout=5)
            if respuesta.status_code != 200:
                return False
            # El servidor responde antes de terminar de cargar el modelo
            # (la carga toma 60-150s), así que "arriba" no alcanza.
            return bool(respuesta.json().get("listo"))
        except Exception as e:
            logger.warning(f"HTR no disponible: {e}")
            return False

    def extract_text(self, content: bytes, filename: str = "") -> str:
        """
        Extrae texto manuscrito de una imagen.

        Args:
            content: Contenido de la imagen en bytes
            filename: Nombre del archivo (para logs)

        Returns:
            str: Texto reconocido, una línea por renglón detectado

        Raises:
            Exception: Si falla el reconocimiento tras los reintentos
        """
        endpoint = f"{self.htr_url}/htr"
        headers = {'Content-Type': 'application/octet-stream'}
        ultimo_error: Optional[Exception] = None

        for intento in range(self.max_retries):
            try:
                logger.info(
                    f"Reconociendo manuscrito de '{filename}' "
                    f"(intento {intento + 1}/{self.max_retries})"
                )
                respuesta = requests.post(
                    endpoint, data=content, headers=headers, timeout=self.timeout
                )
                respuesta.raise_for_status()
                datos = respuesta.json()

                texto = datos.get("texto", "")
                logger.info(
                    f"HTR completado: {datos.get('lineas', 0)} línea(s), "
                    f"{len(texto)} caracteres, {datos.get('segundos', 0)}s "
                    f"(modelo: {datos.get('modelo')})"
                )
                return texto

            except Exception as e:
                ultimo_error = e
                logger.warning(f"Intento {intento + 1} falló: {e}")

        raise Exception(
            f"No se pudo reconocer el manuscrito de '{filename}' "
            f"tras {self.max_retries} intentos: {ultimo_error}"
        )


# Instancia a nivel de módulo, igual que el resto de servicios del proyecto.
htr_service = HTRService()
