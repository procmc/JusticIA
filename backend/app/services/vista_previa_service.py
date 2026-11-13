"""Vista previa de texto de una fuente del notebook (spec 009b, cambio II1; RF-18.100, RF-18.106, RF-18.107).

El navegador muestra por sí solo imágenes, PDF y audio, pero no un `.txt` grande ni un documento de Word o HTML. Este servicio
lee el archivo original y devuelve solo su texto, ya cortado al límite de la vista previa:

* Texto plano (`.txt`): se leen a lo sumo 1 MiB (el archivo puede pesar 1 GB) y se decodifica como UTF-8; lo que no coincide se
  muestra con símbolos de reemplazo y el archivo no se modifica.
* TIFF: el navegador no lo muestra; se convierte a PNG (primera página, reducida a 4000 px por lado) con Pillow.
* Word y HTML: el texto que extrae Apache Tika, la misma extracción de la ingesta, sin OCR y con un plazo corto (una persona
  espera). Nunca se devuelve HTML: un `.html` se muestra como el texto que contiene.

No decide quién puede ver el archivo: eso lo verifica `NotebookService.obtener_archivo_de_documento` antes de llamar aquí.

Ver también: `app.routes.notebooks` (ruta `vista-texto`), `app.services.ingesta.tika_service`.
"""
import base64
import io
import logging
from pathlib import Path
from typing import Optional, Tuple

from starlette.concurrency import run_in_threadpool

from app.services.ingesta.tika_service import TikaService

logger = logging.getLogger(__name__)

LIMITE_CARACTERES = 200_000            # lo que se muestra de un texto largo (RF-18.100)
LECTURA_MAXIMA_BYTES = 1024 * 1024     # de un .txt se lee a lo sumo 1 MiB; con más de 200.000 caracteres ya está truncado
TAMANO_MAXIMO_PARA_TIKA = 50 * 1024 * 1024  # un Word más pesado no se manda a Tika para una vista previa
LADO_MAXIMO_IMAGEN = 4000              # un TIFF mayor se reduce: acota la memoria y el tamaño de la respuesta
PLAZO_TIKA_SEGUNDOS = 30               # por intento; la ingesta usa 600 s y 3 intentos con esperas: demasiado para quien espera la vista
INTENTOS_TIKA = 2                      # un segundo intento: Tika se reinicia solo tras un archivo dañado y tarda unos 6 s en volver

EXTENSIONES_TEXTO_PLANO = frozenset({".txt"})
EXTENSIONES_CON_TIKA = frozenset({".doc", ".docx", ".html", ".htm", ".xhtml"})
EXTENSIONES_DE_IMAGEN_A_CONVERTIR = frozenset({".tif", ".tiff"})


class VistaNoDisponible(Exception):
    """No se pudo obtener la vista previa de una fuente (Tika no respondió, el archivo falta o está dañado, o el tipo no la tiene).
    Su mensaje es fijo: no repite el texto de la excepción original, que puede traer rutas internas (RNF-07.24)."""

    def __init__(self):
        super().__init__("No se pudo mostrar el documento")


def tiene_vista_de_texto(extension: str) -> bool:
    """Si una extensión (con su punto, sin distinguir mayúsculas) se muestra como vista de texto (RF-18.100, RF-18.106)."""
    extension = (extension or "").lower()
    return extension in EXTENSIONES_TEXTO_PLANO or extension in EXTENSIONES_CON_TIKA


def tiene_vista_de_imagen(extension: str) -> bool:
    """Si una extensión (con su punto, sin distinguir mayúsculas) se muestra convirtiéndola a imagen: TIFF (RF-18.108)."""
    return (extension or "").lower() in EXTENSIONES_DE_IMAGEN_A_CONVERTIR


class VistaPreviaService:
    """Texto de la vista previa de una fuente. `tika` permite sustituir el extractor en las pruebas."""

    def __init__(self, tika: Optional[TikaService] = None):
        self._tika = tika

    def _crear_tika(self) -> TikaService:
        """Un cliente de Tika con plazo corto y dos intentos: no se fija en `TikaService` para no cambiar la ingesta (D6)."""
        tika = TikaService()
        tika.timeout = PLAZO_TIKA_SEGUNDOS
        tika.max_retries = INTENTOS_TIKA
        return tika

    def vista_de_texto_sync(self, ruta: Path, extension: str) -> Tuple[str, bool]:
        """El texto de `ruta` y si se cortó.

        Returns:
            (texto, truncado): el texto, de a lo sumo `LIMITE_CARACTERES`, y si el original tenía más. Un texto sin contenido
            visible da `""`.

        Raises:
            VistaNoDisponible: Si el tipo no tiene vista de texto, el archivo no está o es demasiado pesado para Tika, o Tika falla.
        """
        extension = (extension or "").lower()
        try:
            if extension in EXTENSIONES_TEXTO_PLANO:
                return self._texto_plano(ruta)
            if extension in EXTENSIONES_CON_TIKA:
                return self._con_tika(ruta)
        except VistaNoDisponible:
            raise
        except Exception as causa:
            # El detalle queda en el registro del servidor; al usuario solo le llega el aviso fijo.
            logger.exception("No se pudo obtener la vista de texto de una fuente")
            raise VistaNoDisponible() from causa
        raise VistaNoDisponible()

    async def vista_de_texto(self, ruta: Path, extension: str) -> Tuple[str, bool]:
        """Lo mismo que `vista_de_texto_sync`, sin bloquear el servidor: la lectura y Tika son síncronas."""
        return await run_in_threadpool(self.vista_de_texto_sync, ruta, extension)

    def vista_de_imagen_sync(self, ruta: Path) -> Tuple[str, int]:
        """Un TIFF convertido a PNG (en base64) y cuántas páginas tiene; se muestra la primera.

        Returns:
            (imagen, paginas): el PNG en base64, reducido a `LADO_MAXIMO_IMAGEN` px por lado si es mayor, y el número de páginas.

        Raises:
            VistaNoDisponible: Si el archivo no está, está dañado o Pillow no puede convertirlo (también si es una «bomba de
                descompresión»: una imagen con una cantidad absurda de píxeles).
        """
        try:
            from PIL import Image  # solo la vista de imagen depende de Pillow

            with Image.open(ruta) as original:
                paginas = int(getattr(original, "n_frames", 1))
                original.seek(0)
                primera = original.convert("RGB")
            primera.thumbnail((LADO_MAXIMO_IMAGEN, LADO_MAXIMO_IMAGEN))
            memoria = io.BytesIO()
            primera.save(memoria, format="PNG")
            return base64.b64encode(memoria.getvalue()).decode("ascii"), paginas
        except Exception as causa:
            logger.exception("No se pudo convertir un TIFF para su vista previa")
            raise VistaNoDisponible() from causa

    async def vista_de_imagen(self, ruta: Path) -> Tuple[str, int]:
        """Lo mismo que `vista_de_imagen_sync`, sin bloquear el servidor."""
        return await run_in_threadpool(self.vista_de_imagen_sync, ruta)

    def _texto_plano(self, ruta: Path) -> Tuple[str, bool]:
        tamano = ruta.stat().st_size
        with open(ruta, "rb") as archivo:
            datos = archivo.read(LECTURA_MAXIMA_BYTES)
        texto = datos.decode("utf-8", errors="replace")
        truncado = tamano > LECTURA_MAXIMA_BYTES or len(texto) > LIMITE_CARACTERES
        return texto[:LIMITE_CARACTERES], truncado

    def _con_tika(self, ruta: Path) -> Tuple[str, bool]:
        if ruta.stat().st_size > TAMANO_MAXIMO_PARA_TIKA:
            raise VistaNoDisponible()
        tika = self._tika or self._crear_tika()
        texto = tika.extract_text(ruta.read_bytes(), filename=ruta.name, enable_ocr=False)
        if not texto or not texto.strip():
            return "", False
        return texto[:LIMITE_CARACTERES], len(texto) > LIMITE_CARACTERES


vista_previa_service = VistaPreviaService()
