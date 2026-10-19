"""
Servicio centralizado para manejo de archivos (subida y descarga).
Combina la lógica de file_storage_manager y la ruta de descarga.
"""

import os
import re
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import UploadFile, HTTPException, status
from fastapi.responses import FileResponse
from datetime import datetime
import logging

from app.constants.avatar_constants import AVATAR_UPLOAD_DIR

logger = logging.getLogger(__name__)

# Carpeta de los avatares dentro de uploads/: se toma de la constante de producción para que ningún tema
# pueda llamarse igual y quedar mezclado con ella (RNF-07.21, D4-A).
CARPETA_AVATARES = Path(AVATAR_UPLOAD_DIR).name

LONGITUD_MAXIMA_TEMA = 60        # caracteres
LONGITUD_MAXIMA_NOMBRE = 255     # bytes en UTF-8, el límite de un nombre en el sistema de archivos

# Nombres que Windows reserva (con cualquier extensión) y que no deben usarse como tema ni como archivo.
_RESERVADOS_WINDOWS = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{n}" for n in range(1, 10)}
    | {f"LPT{n}" for n in range(1, 10)}
)


def es_nombre_seguro(texto: str, es_tema: bool) -> bool:
    """Indica si `texto` sirve como un solo nombre de carpeta (tema) o de archivo (RNF-07.21).

    Rechaza lo vacío, los separadores, `:` , NUL y caracteres de control, los finales en espacio o punto,
    los nombres reservados de Windows y los que superan el largo permitido. Un tema además no puede llamarse
    como la carpeta de avatares. No toca el disco.
    """
    if not isinstance(texto, str) or not texto.strip(" ."):
        return False
    if any(c in "/\\:" or ord(c) < 32 or 0x7F <= ord(c) <= 0x9F for c in texto):
        return False
    if texto.endswith((" ", ".")):
        return False
    if texto.split(".", 1)[0].upper() in _RESERVADOS_WINDOWS:
        return False
    if es_tema:
        return len(texto) <= LONGITUD_MAXIMA_TEMA and texto.casefold() != CARPETA_AVATARES
    return len(texto.encode("utf-8")) <= LONGITUD_MAXIMA_NOMBRE


# Avisos genéricos de la carga (RF-06.20, RF-05.20, RF-05.21): nunca repiten el tema ni el nombre pedidos (RNF-07.24).
MENSAJE_TEMA_NO_VALIDO = "El tema indicado no es válido"
MENSAJE_NOMBRE_NO_VALIDO = "Nombre de archivo no válido"
MENSAJE_NO_SE_PUDO_GUARDAR = "No se pudo guardar el archivo"
MENSAJE_ARCHIVO_VACIO = "El archivo está vacío"


def validar_tema(tema: str) -> None:
    """Comprueba que `tema` sirva como nombre de carpeta antes de escribir nada (RF-06.20).

    Raises:
        HTTPException: 400 «El tema indicado no es válido», sin repetir el tema.
    """
    if not es_nombre_seguro(tema, True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MENSAJE_TEMA_NO_VALIDO)


class AccesoArchivoDenegado(HTTPException):
    """404 uniforme de la descarga (RNF-07.20, RF-18.20): no distingue un documento ajeno, inexistente, no Procesado
    o fuera de la carpeta. `motivo` es la clasificación para la bitácora («ruta no permitida», «documento ajeno»,
    «documento no disponible»); nunca lleva la ruta ni el nombre pedidos y no se envía al usuario."""

    def __init__(self, motivo: str):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado")
        self.motivo = motivo


# Un notebook usa como tema su clave `NB-<id>`; la base compara sin distinguir mayúsculas, así que `nb-5` es el mismo tema.
_CLAVE_DE_NOTEBOOK = re.compile(r"nb-([1-9][0-9]*)", re.IGNORECASE | re.ASCII)   # solo dígitos ASCII y sin cero inicial
_ID_MAXIMO = 2**63 - 1       # un BIGINT de SQL Server; un id mayor no puede ser de ningún notebook


def _sin_control(texto: str) -> str:
    """Quita NUL y caracteres de control de un texto que se registra (RNF-07.24): un nombre o ruta pedidos no deben
    poder falsear una línea de la bitácora ni del registro del servidor."""
    return "".join(c for c in texto if ord(c) >= 32 and not 0x7F <= ord(c) <= 0x9F)

# Mapeo explícito de extensiones a tipos MIME para archivos de audio y documentos
# Esto garantiza la correcta detección en todos los sistemas operativos
MIME_TYPE_MAP = {
    # Audio
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.ogg': 'audio/ogg',
    '.m4a': 'audio/mp4',
    # Documentos
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.rtf': 'application/rtf',
    '.txt': 'text/plain',
    '.html': 'text/html',
    '.htm': 'text/html',
    '.xhtml': 'application/xhtml+xml',
}


class FileManagementService:
    """Servicio centralizado para manejo de archivos (subida y descarga)"""
    
    def __init__(self):
        # Asegurar que uploads esté siempre en la raíz del proyecto backend
        # Desde app/services/documentos/file_management_service.py subir 4 niveles hasta backend/
        current_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.BASE_UPLOAD_DIR = current_dir / "uploads"
    
    def _ensure_directory_exists(self, directory: Path) -> None:
        """Crea el directorio si no existe"""
        directory.mkdir(parents=True, exist_ok=True)
    
    def _get_unique_filename(self, directory: Path, filename: str) -> str:
        """Genera un nombre único para el archivo si ya existe"""
        filepath = directory / filename
        
        if not filepath.exists():
            return filename
        
        # Si existe, agregar contador
        name, ext = os.path.splitext(filename)
        counter = 1
        
        while filepath.exists():
            new_filename = f"{name}_{counter}{ext}"
            # Con el sufijo el nombre puede pasar del límite del sistema de archivos (consultarlo ya da error de disco).
            if len(new_filename.encode("utf-8")) > LONGITUD_MAXIMA_NOMBRE:
                raise HTTPException(status_code=400, detail=MENSAJE_NOMBRE_NO_VALIDO)
            filepath = directory / new_filename
            counter += 1
        
        return filepath.name
    
    async def guardar_archivo(self, file: UploadFile, expediente_numero: str) -> Dict[str, Any]:
        """
        Guarda un archivo en el servidor.
        
        Args:
            file: Archivo a guardar
            expediente_numero: Número del expediente
            
        Returns:
            Dict con información del archivo guardado
            
        Raises:
            HTTPException: 400 con el aviso genérico si el tema o el nombre no son válidos o el archivo está vacío;
                500 «No se pudo guardar el archivo» si la escritura falla (sin rutas ni texto de la excepción).
        """
        # Tema y nombre se validan antes de tocar el disco (RF-06.20, RF-05.20, RNF-07.21).
        validar_tema(expediente_numero)
        if not es_nombre_seguro(file.filename, False):
            raise HTTPException(status_code=400, detail=MENSAJE_NOMBRE_NO_VALIDO)

        try:
            base = self.BASE_UPLOAD_DIR
            self._ensure_directory_exists(base)

            # Carpeta del tema, confinada: resuelta (con enlaces) debe ser hija directa de la carpeta de documentos.
            expediente_dir = base / expediente_numero
            self._ensure_directory_exists(expediente_dir)
            real = expediente_dir.resolve()
            if real.parent != base.resolve() or real.name != expediente_numero:
                raise OSError("carpeta del tema fuera de la carpeta de documentos")

            unique_filename = self._get_unique_filename(expediente_dir, file.filename)
            filepath = expediente_dir / unique_filename

            # Leer contenido del archivo UNA SOLA VEZ
            content = await file.read()

            # Validar que el archivo no esté vacío
            if len(content) == 0:
                raise HTTPException(status_code=400, detail=MENSAJE_ARCHIVO_VACIO)

            # Modo exclusivo ("xb"): si otro archivo apareció con ese nombre, no se sobrescribe; falla y no se borra.
            creado = False
            try:
                with open(filepath, "xb") as f:
                    creado = True
                    f.write(content)
            except Exception:
                if creado:
                    # Solo se borra lo que creó esta llamada (D5): nunca un archivo ajeno ni a medias.
                    filepath.unlink(missing_ok=True)
                raise

            # Verificar que se guardó correctamente
            if not filepath.exists() or filepath.stat().st_size == 0:
                filepath.unlink(missing_ok=True)
                raise OSError("archivo guardado vacío")

            # La ruta del documento es relativa a la carpeta de documentos, sea cual sea su ubicación (RF-05.21).
            return {
                "filename": unique_filename,
                "original_filename": file.filename,
                "filepath": str(filepath),
                "relative_path": f"uploads/{expediente_numero}/{unique_filename}",
                "content_type": file.content_type,
                "size_bytes": len(content),
                "content": content  # Devolver contenido para procesamiento posterior
            }

        except HTTPException:
            raise
        except Exception as e:
            # Al registro del servidor solo va el tipo de error: su texto y su traza traen la ruta, y con ella el tema y el
            # nombre pedidos, que pueden ser nombres de personas (RNF-07.23, RNF-07.24).
            logger.error("Error guardando un archivo (%s, errno=%s)", type(e).__name__, getattr(e, "errno", None))
            raise HTTPException(status_code=500, detail=MENSAJE_NO_SE_PUDO_GUARDAR)
    
    async def obtener_documento_por_ruta(self, db, ruta: str, usuario_id: str) -> Path:
        """Resuelve la ruta de un documento (`uploads/<tema>/<nombre>`, ya decodificada) a su ubicación real, solo si es
        un documento descargable por ese usuario (RNF-07.20, RF-18.20).

        La ruta guardada no se usa para abrir nada: se toman el tema y el nombre, se comprueba que el documento esté
        registrado y Procesado, que el notebook (si es un tema `NB-<id>`) sea del usuario y que el archivo, ya resuelto,
        quede dentro de la carpeta de su tema.

        Raises:
            AccesoArchivoDenegado: 404 uniforme, con su `motivo`, ante cualquier otra cosa.
        """
        # Importados aquí para evitar ciclos entre los servicios.
        from app.repositories.documento_repository import DocumentoRepository
        from app.services.notebook_service import NotebookService

        partes = ruta.split("/") if isinstance(ruta, str) else []
        if (len(partes) != 3 or partes[0] != "uploads"
                or not es_nombre_seguro(partes[1], True) or not es_nombre_seguro(partes[2], False)):
            raise AccesoArchivoDenegado("ruta no permitida")
        _, tema, nombre = partes

        # Clave de notebook (decisión 13 del plan): todo tema que empieza por `nb-` debe ser canónico; si no, se rechaza
        # sin consultar la base (nada de normalizar con `int()`: crearía alias de `NB-5` y un id enorme desbordaría la base).
        if tema[:3].casefold() == "nb-":
            clave = _CLAVE_DE_NOTEBOOK.fullmatch(tema)
            if not clave or int(clave.group(1)) > _ID_MAXIMO:
                raise AccesoArchivoDenegado("ruta no permitida")
            if not await NotebookService().obtener_notebook_de_usuario(db, int(clave.group(1)), usuario_id):
                raise AccesoArchivoDenegado("documento ajeno")      # ajeno o inexistente: no se distinguen

        if not DocumentoRepository().verificar_esta_procesado(db, tema, nombre):
            raise AccesoArchivoDenegado("documento no disponible")

        ubicacion = self._ubicacion_confinada(tema, nombre)
        if ubicacion is None:
            raise AccesoArchivoDenegado("ruta no permitida")
        return ubicacion

    def descargar_archivo(self, ubicacion: Path) -> FileResponse:
        """
        Entrega un archivo cuya ubicación ya se comprobó (`obtener_documento_por_ruta`): no completa ni busca rutas.

        Args:
            ubicacion: Ubicación real del documento, ya confinada a la carpeta de su tema

        Returns:
            FileResponse: Respuesta con el archivo

        Raises:
            HTTPException: Si el archivo está vacío o hay un error inesperado
        """
        try:
            # Verificar que el archivo no está vacío
            if os.path.getsize(ubicacion) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=MENSAJE_ARCHIVO_VACIO
                )

            nombre_archivo = ubicacion.name

            # Detectar el tipo MIME del archivo
            # 1. Primero intentar con el mapeo explícito (más confiable)
            extension = ubicacion.suffix.lower()
            mime_type = MIME_TYPE_MAP.get(extension)

            # 2. Si no está en el mapeo, usar mimetypes.guess_type
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(str(ubicacion))

            # 3. Fallback final a application/octet-stream
            if not mime_type:
                mime_type = 'application/octet-stream'

            logger.debug(f"Descargando archivo con tipo MIME: {mime_type}")

            return FileResponse(
                path=str(ubicacion),
                filename=nombre_archivo,
                media_type=mime_type
            )

        except HTTPException:
            raise
        except Exception:
            # El detalle (con su traza) solo va al registro del servidor; la respuesta es genérica (RNF-07.23).
            logger.exception("Error inesperado al entregar un archivo")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno del servidor"
            )

    def obtener_ruta_archivo(self, expediente_numero: str, filename: str) -> Optional[Path]:
        """
        Obtiene la ruta completa de un archivo, solo si está confinada (RNF-07.21).

        Args:
            expediente_numero: Tema (carpeta) del archivo
            filename: Nombre del archivo

        Returns:
            Path: Ruta real del archivo si existe dentro de la carpeta de su tema, None si no
        """
        return self._ubicacion_confinada(expediente_numero, filename)

    def _ubicacion_confinada(self, tema: str, nombre: str) -> Optional[Path]:
        """Resuelve tema y nombre siguiendo los enlaces y devuelve la ubicación solo si queda dentro de la
        carpeta del tema y esta dentro de la de documentos; si no, None. Es la función común de la descarga,
        la previsualización y el borrado por tema y nombre."""
        if not es_nombre_seguro(tema, True) or not es_nombre_seguro(nombre, False):
            return None
        try:
            base = self.BASE_UPLOAD_DIR.resolve()
            carpeta_tema = (base / tema).resolve()
            # El nombre real debe ser el del tema: un enlace hacia la carpeta de otro tema (`NB-5`, `profiles`)
            # seguiría siendo hijo de `uploads/` y saltaría la pertenencia, que se evalúa por el texto del tema.
            if carpeta_tema.parent != base or carpeta_tema.name != tema:
                return None
            real = (carpeta_tema / nombre).resolve()
            if real.parent != carpeta_tema or not real.is_file():
                return None
        except (OSError, ValueError):
            return None
        return real
    
    def listar_archivos_expediente(self, expediente_numero: str, db=None) -> List[Dict[str, Any]]:
        """
        Lista archivos de un expediente (solo procesados por defecto).
        Usa repository centralizado para filtrar por estado.
        
        Args:
            expediente_numero: Número del expediente
            db: Sesión de BD (opcional) - para filtrar solo procesados
            
        Returns:
            Lista de archivos con información básica (solo procesados si db disponible)
        """
        from app.repositories.documento_repository import DocumentoRepository
        
        expediente_dir = self.BASE_UPLOAD_DIR / expediente_numero
        
        if not expediente_dir.exists():
            return []
        
        # Obtener nombres de archivos procesados del repository
        archivos_procesados = None
        if db:
            repo = DocumentoRepository()
            archivos_procesados = set(repo.listar_por_expediente_y_nombres(db, expediente_numero, solo_procesados=True))
        
        archivos = []
        for filepath in expediente_dir.iterdir():
            if filepath.is_file():
                # Filtrar por estado si está disponible
                if archivos_procesados is not None and filepath.name not in archivos_procesados:
                    continue
                
                stat = filepath.stat()
                archivos.append({
                    "nombre": filepath.name,
                    "ruta": str(filepath),
                    "ruta_relativa": str(filepath.relative_to(os.getcwd())),
                    "tamaño_bytes": stat.st_size,
                    "fecha_modificacion": datetime.fromtimestamp(stat.st_mtime),
                    "extension": filepath.suffix.lower(),
                    "esta_vacio": stat.st_size == 0
                })
        
        return archivos
    
    def verificar_integridad_archivo(self, ruta_archivo: str) -> Dict[str, Any]:
        """
        Verifica la integridad de un archivo.
        
        Args:
            ruta_archivo: Ruta del archivo a verificar
            
        Returns:
            Dict con información de integridad
        """
        try:
            if not os.path.exists(ruta_archivo):
                return {"existe": False, "valido": False, "error": "Archivo no encontrado"}
            
            stat = os.stat(ruta_archivo)
            size = stat.st_size
            
            return {
                "existe": True,
                "valido": size > 0,
                "tamaño_bytes": size,
                "esta_vacio": size == 0,
                "fecha_modificacion": datetime.fromtimestamp(stat.st_mtime),
                "es_archivo": os.path.isfile(ruta_archivo)
            }
            
        except Exception as e:
            return {"existe": False, "valido": False, "error": str(e)}


# Crear instancia singleton
file_management_service = FileManagementService()