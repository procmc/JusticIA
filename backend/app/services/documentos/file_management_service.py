"""
Servicio centralizado para manejo de archivos (subida y descarga).
Combina la lógica de file_storage_manager y la ruta de descarga.
"""

import os
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import UploadFile, HTTPException, status
from fastapi.responses import FileResponse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FileManagementService:
    """Servicio centralizado para manejo de archivos (subida y descarga)"""
    
    def __init__(self):
        self.BASE_UPLOAD_DIR = Path("uploads")
    
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
            HTTPException: Si hay error guardando el archivo
        """
        try:
            # Crear directorio base
            self._ensure_directory_exists(self.BASE_UPLOAD_DIR)
            
            # Crear directorio del expediente
            expediente_dir = self.BASE_UPLOAD_DIR / expediente_numero
            self._ensure_directory_exists(expediente_dir)
            
            # Validar filename
            if not file.filename:
                raise HTTPException(status_code=400, detail="Nombre de archivo requerido")
            
            # Obtener nombre único
            unique_filename = self._get_unique_filename(expediente_dir, file.filename)
            filepath = expediente_dir / unique_filename
            
            # Leer contenido del archivo UNA SOLA VEZ
            content = await file.read()
            
            # Validar que el archivo no esté vacío
            if len(content) == 0:
                raise HTTPException(status_code=400, detail="El archivo está vacío")
            
            # Guardar archivo
            with open(filepath, "wb") as f:
                f.write(content)
            
            # Verificar que se guardó correctamente
            if not filepath.exists() or filepath.stat().st_size == 0:
                raise HTTPException(status_code=500, detail="Error: archivo guardado está vacío")
            
            # Retornar información completa del archivo
            return {
                "filename": unique_filename,
                "original_filename": file.filename,
                "filepath": str(filepath),
                "relative_path": str(filepath.relative_to(os.getcwd())),
                "content_type": file.content_type,
                "size_bytes": len(content),
                "content": content  # Devolver contenido para procesamiento posterior
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error guardando archivo {file.filename}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error guardando archivo: {str(e)}"
            )
    
    def descargar_archivo(self, ruta_archivo: str) -> FileResponse:
        """
        Descarga un archivo específico usando su ruta completa.
        
        Args:
            ruta_archivo: Ruta completa del archivo a descargar
            
        Returns:
            FileResponse: Respuesta con el archivo
            
        Raises:
            HTTPException: Si hay error con el archivo
        """
        try:
            # Verificar que la ruta no esté vacía
            if not ruta_archivo or ruta_archivo.strip() == "":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ruta de archivo requerida"
                )

            # Si la ruta es relativa, convertirla a absoluta
            ruta_final = ruta_archivo
            if not os.path.isabs(ruta_archivo):
                ruta_final = os.path.join(os.getcwd(), ruta_archivo)

            # Verificar que el archivo existe
            if not os.path.exists(ruta_final):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Archivo no encontrado"
                )

            # Verificar que es un archivo regular
            if not os.path.isfile(ruta_final):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La ruta no corresponde a un archivo válido"
                )

            # Verificar que el archivo no está vacío
            if os.path.getsize(ruta_final) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El archivo está vacío"
                )

            # Obtener nombre del archivo
            nombre_archivo = os.path.basename(ruta_final)

            # Detectar el tipo MIME real del archivo
            mime_type, _ = mimetypes.guess_type(ruta_final)
            if not mime_type:
                mime_type = 'application/octet-stream'

            return FileResponse(
                path=ruta_final,
                filename=nombre_archivo,
                media_type=mime_type
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error descargando archivo: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno del servidor"
            )
    
    def obtener_ruta_archivo(self, expediente_numero: str, filename: str) -> Optional[Path]:
        """
        Obtiene la ruta completa de un archivo.
        
        Args:
            expediente_numero: Número del expediente
            filename: Nombre del archivo
            
        Returns:
            Path: Ruta completa del archivo si existe, None si no existe
        """
        filepath = self.BASE_UPLOAD_DIR / expediente_numero / filename
        return filepath if filepath.exists() else None
    
    def listar_archivos_expediente(self, expediente_numero: str) -> List[Dict[str, Any]]:
        """
        Lista todos los archivos de un expediente.
        
        Args:
            expediente_numero: Número del expediente
            
        Returns:
            Lista de archivos con información básica
        """
        expediente_dir = self.BASE_UPLOAD_DIR / expediente_numero
        
        if not expediente_dir.exists():
            return []
        
        archivos = []
        for filepath in expediente_dir.iterdir():
            if filepath.is_file():
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