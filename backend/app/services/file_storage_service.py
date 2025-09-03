import os
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile, HTTPException
from datetime import datetime
import uuid

class FileStorageService:
    """Servicio para manejo de archivos en el servidor"""
    
    BASE_UPLOAD_DIR = Path("uploads")
    
    @classmethod
    def _ensure_directory_exists(cls, directory: Path) -> None:
        """Crea el directorio si no existe"""
        directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def _get_unique_filename(cls, directory: Path, filename: str) -> str:
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
    
    @classmethod
    async def guardar_archivo(cls, file: UploadFile, expediente_numero: str) -> str:
        """
        Guarda un archivo en el servidor.
        
        Args:
            file: Archivo a guardar
            expediente_numero: Número del expediente
            
        Returns:
            str: Ruta relativa donde se guardó el archivo
            
        Raises:
            HTTPException: Si hay error guardando el archivo
        """
        try:
            # Crear directorio base
            cls._ensure_directory_exists(cls.BASE_UPLOAD_DIR)
            
            # Crear directorio del expediente
            expediente_dir = cls.BASE_UPLOAD_DIR / expediente_numero
            cls._ensure_directory_exists(expediente_dir)
            
            # Obtener nombre único
            unique_filename = cls._get_unique_filename(expediente_dir, file.filename)
            filepath = expediente_dir / unique_filename
            
            # Leer y guardar archivo
            content = await file.read()
            with open(filepath, "wb") as f:
                f.write(content)
            
            # Resetear posición del archivo
            await file.seek(0)
            
            # Retornar ruta relativa
            return str(filepath)
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error guardando archivo: {str(e)}"
            )
    
    @classmethod
    def obtener_ruta_archivo(cls, expediente_numero: str, filename: str) -> Optional[Path]:
        """
        Obtiene la ruta completa de un archivo.
        
        Args:
            expediente_numero: Número del expediente
            filename: Nombre del archivo
            
        Returns:
            Path: Ruta completa del archivo si existe, None si no existe
        """
        filepath = cls.BASE_UPLOAD_DIR / expediente_numero / filename
        return filepath if filepath.exists() else None
    
    @classmethod
    def listar_archivos_expediente(cls, expediente_numero: str) -> List[dict]:
        """
        Lista todos los archivos de un expediente.
        
        Args:
            expediente_numero: Número del expediente
            
        Returns:
            List[dict]: Lista de archivos con información básica
        """
        expediente_dir = cls.BASE_UPLOAD_DIR / expediente_numero
        
        if not expediente_dir.exists():
            return []
        
        archivos = []
        for filepath in expediente_dir.iterdir():
            if filepath.is_file():
                stat = filepath.stat()
                archivos.append({
                    "nombre": filepath.name,
                    "ruta": str(filepath),
                    "tamaño_bytes": stat.st_size,
                    "fecha_modificacion": datetime.fromtimestamp(stat.st_mtime),
                    "extension": filepath.suffix.lower()
                })
        
        return archivos
