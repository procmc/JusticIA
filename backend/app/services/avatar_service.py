"""
Servicio para gestión de avatares de usuarios.
Maneja la subida, actualización, eliminación y validación de avatares.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.usuario_repository import UsuarioRepository
from app.services.bitacora.usuarios_audit_service import usuarios_audit_service
from app.constants.avatar_constants import (
    MAX_AVATAR_SIZE_BYTES,
    ALLOWED_IMAGE_TYPES,
    ALLOWED_IMAGE_EXTENSIONS,
    AVATAR_UPLOAD_DIR,
    AVATAR_TYPES
)

logger = logging.getLogger(__name__)


class AvatarService:
    """Servicio centralizado para gestión de avatares de usuarios"""
    
    def __init__(self):
        # Obtener ruta base del proyecto (desde app/services subir 2 niveles)
        current_dir = Path(__file__).resolve().parent.parent.parent
        self.upload_dir = current_dir / AVATAR_UPLOAD_DIR
        self.usuario_repo = UsuarioRepository()
        self._ensure_directory_exists()
    
    def _ensure_directory_exists(self) -> None:
        """Crea el directorio de avatares si no existe"""
        try:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directorio de avatares asegurado: {self.upload_dir}")
        except Exception as e:
            logger.error(f"Error creando directorio de avatares: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creando directorio de avatares"
            )
    
    def _validar_tipo_archivo(self, file: UploadFile) -> None:
        """
        Valida que el archivo sea un tipo de imagen permitido.
        
        Args:
            file: Archivo a validar
            
        Raises:
            HTTPException: Si el tipo no es permitido
        """
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de archivo no permitido. Use: {', '.join(ALLOWED_IMAGE_TYPES)}"
            )
        
        # Validar también la extensión
        if file.filename:
            extension = Path(file.filename).suffix.lower()
            if extension not in ALLOWED_IMAGE_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Extensión no permitida. Use: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
                )
    
    async def _validar_tamaño_archivo(self, file: UploadFile) -> bytes:
        """
        Valida que el archivo no exceda el tamaño máximo y retorna su contenido.
        
        Args:
            file: Archivo a validar
            
        Returns:
            bytes: Contenido del archivo
            
        Raises:
            HTTPException: Si el tamaño excede el máximo o está vacío
        """
        # Leer contenido
        content = await file.read()
        
        # Validar que no esté vacío
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo está vacío"
            )
        
        # Validar tamaño máximo
        if len(content) > MAX_AVATAR_SIZE_BYTES:
            max_mb = MAX_AVATAR_SIZE_BYTES / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Archivo excede el tamaño máximo de {max_mb}MB"
            )
        
        return content
    
    def _limpiar_avatar_anterior(self, usuario_id: str) -> None:
        """
        Elimina el avatar anterior de un usuario si existe.
        
        Args:
            usuario_id: ID del usuario
        """
        try:
            # Buscar archivos existentes con el ID del usuario
            for ext in ALLOWED_IMAGE_EXTENSIONS:
                file_path = self.upload_dir / f"{usuario_id}{ext}"
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Avatar anterior eliminado: {file_path}")
        except Exception as e:
            logger.warning(f"Error limpiando avatar anterior para {usuario_id}: {e}")
            # No lanzar excepción, es un error no crítico
    
    def _generar_ruta_avatar(self, usuario_id: str, extension: str) -> Path:
        """
        Genera la ruta completa para guardar el avatar.
        
        Args:
            usuario_id: ID del usuario
            extension: Extensión del archivo (con punto)
            
        Returns:
            Path: Ruta completa del archivo
        """
        return self.upload_dir / f"{usuario_id}{extension}"
    
    def _obtener_extension_archivo(self, filename: Optional[str]) -> str:
        """
        Obtiene la extensión del archivo.
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            str: Extensión con punto (.jpg, .png, etc.)
        """
        if filename:
            extension = Path(filename).suffix.lower()
            if extension in ALLOWED_IMAGE_EXTENSIONS:
                return extension
        
        # Por defecto usar .jpg
        return ".jpg"
    
    async def subir_avatar(
        self,
        usuario_id: str,
        file: UploadFile,
        db: Session
    ) -> Dict[str, Any]:
        """
        Sube y guarda un avatar para un usuario.
        
        Args:
            usuario_id: ID del usuario
            file: Archivo de imagen
            db: Sesión de base de datos
            
        Returns:
            Dict con información del avatar guardado
            
        Raises:
            HTTPException: Si hay error en validación o guardado
        """
        try:
            # Validar tipo de archivo
            self._validar_tipo_archivo(file)
            
            # Validar tamaño y obtener contenido
            content = await self._validar_tamaño_archivo(file)
            
            # Obtener usuario de la BD usando el repositorio
            usuario = self.usuario_repo.obtener_usuario_por_id(db, usuario_id)
            if not usuario:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado"
                )
            
            # Limpiar avatar anterior
            self._limpiar_avatar_anterior(usuario_id)
            
            # Generar ruta del nuevo avatar
            extension = self._obtener_extension_archivo(file.filename)
            file_path = self._generar_ruta_avatar(usuario_id, extension)
            
            # Guardar archivo
            with file_path.open("wb") as buffer:
                buffer.write(content)
            
            # Verificar que se guardó correctamente
            if not file_path.exists() or file_path.stat().st_size == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error guardando el archivo"
                )
            
            # Guardar ruta relativa en BD usando el repositorio
            ruta_relativa = f"{AVATAR_UPLOAD_DIR}/{usuario_id}{extension}"
            usuario_actualizado = self.usuario_repo.actualizar_avatar_ruta(db, usuario_id, ruta_relativa)
            
            if not usuario_actualizado:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error actualizando usuario en BD"
                )
            
            # Registrar en bitácora
            await usuarios_audit_service.registrar_cambio_avatar(
                db=db,
                usuario_id=usuario_id,
                tipo_cambio="upload",
                detalles={
                    "ruta": ruta_relativa,
                    "tamaño_bytes": len(content),
                    "extension": extension
                }
            )
            
            logger.info(f"Avatar subido exitosamente para usuario {usuario_id}")
            
            return {
                "mensaje": "Avatar subido exitosamente",
                "ruta": ruta_relativa,
                "tamaño_bytes": len(content)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al subir avatar para {usuario_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al subir avatar"
            )
    
    async def actualizar_tipo_avatar(
        self,
        usuario_id: str,
        avatar_tipo: str,
        db: Session
    ) -> Dict[str, str]:
        """
        Actualiza el tipo de avatar sin subir imagen (avatar predefinido o iniciales).
        
        Args:
            usuario_id: ID del usuario
            avatar_tipo: Tipo de avatar (initials, hombre, mujer)
            db: Sesión de base de datos
            
        Returns:
            Dict con mensaje de confirmación
            
        Raises:
            HTTPException: Si hay error en validación o actualización
        """
        try:
            # Validar tipo de avatar
            if avatar_tipo not in AVATAR_TYPES.values():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tipo de avatar no válido. Use: {', '.join(AVATAR_TYPES.values())}"
                )
            
            # Actualizar tipo de avatar usando el repositorio
            usuario_actualizado = self.usuario_repo.actualizar_avatar_tipo(db, usuario_id, avatar_tipo)
            
            if not usuario_actualizado:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado"
                )
            
            # Registrar en bitácora
            await usuarios_audit_service.registrar_cambio_avatar(
                db=db,
                usuario_id=usuario_id,
                tipo_cambio="tipo",
                detalles={"avatar_tipo": avatar_tipo}
            )
            
            logger.info(f"Tipo de avatar actualizado a '{avatar_tipo}' para usuario {usuario_id}")
            
            return {"mensaje": "Preferencia de avatar actualizada"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al actualizar tipo de avatar para {usuario_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al actualizar avatar"
            )
    
    async def eliminar_avatar(
        self,
        usuario_id: str,
        db: Session
    ) -> Dict[str, str]:
        """
        Elimina completamente el avatar de un usuario (archivo y registros BD).
        
        Args:
            usuario_id: ID del usuario
            db: Sesión de base de datos
            
        Returns:
            Dict con mensaje de confirmación
            
        Raises:
            HTTPException: Si hay error en eliminación
        """
        try:
            # Obtener usuario de la BD usando el repositorio
            usuario = self.usuario_repo.obtener_usuario_por_id(db, usuario_id)
            
            if not usuario:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado"
                )
            
            # Eliminar archivo si existe
            if usuario.CT_Avatar_ruta:
                file_path = Path(usuario.CT_Avatar_ruta)
                if file_path.exists():
                    try:
                        file_path.unlink()
                        logger.info(f"Archivo de avatar eliminado: {file_path}")
                    except Exception as e:
                        logger.warning(f"Error eliminando archivo de avatar: {e}")
                        # Continuar aunque falle la eliminación del archivo
            
            # Limpiar base de datos usando el repositorio
            usuario_actualizado = self.usuario_repo.limpiar_avatar(db, usuario_id)
            
            if not usuario_actualizado:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error actualizando usuario en BD"
                )
            
            # Registrar en bitácora
            await usuarios_audit_service.registrar_cambio_avatar(
                db=db,
                usuario_id=usuario_id,
                tipo_cambio="eliminar",
                detalles={"ruta_anterior": usuario.CT_Avatar_ruta if usuario else None}
            )
            
            logger.info(f"Avatar eliminado exitosamente para usuario {usuario_id}")
            
            return {"mensaje": "Avatar eliminado exitosamente"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al eliminar avatar para {usuario_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al eliminar avatar"
            )
    
    def validar_permiso_usuario(
        self,
        current_user_id,
        target_user_id: str
    ) -> None:
        """
        Valida que un usuario solo pueda modificar su propio avatar.
        
        Args:
            current_user_id: ID del usuario actual (puede ser int o str)
            target_user_id: ID del usuario objetivo (siempre str desde URL)
            
        Raises:
            HTTPException: Si el usuario no tiene permiso
        """
        # Convertir ambos a string para comparación consistente
        if str(current_user_id) != str(target_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes modificar el avatar de otro usuario"
            )


# Crear instancia singleton
avatar_service = AvatarService()
