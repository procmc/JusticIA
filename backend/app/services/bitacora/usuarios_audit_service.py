"""
Servicio especializado de auditoría para el módulo de USUARIOS.
Registra operaciones CRUD sobre usuarios del sistema.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from app.db.models.bitacora import T_Bitacora
from app.constants.tipos_accion import TiposAccion
from .bitacora_service import BitacoraService

logger = logging.getLogger(__name__)


class UsuariosAuditService:
    """Servicio especializado para auditoría del módulo de USUARIOS"""
    
    def __init__(self):
        self.bitacora_service = BitacoraService()
    
    async def registrar_consulta_usuarios(
        self,
        db: Session,
        usuario_admin_id: int
    ) -> Optional[T_Bitacora]:
        """
        Registra la consulta de la lista de todos los usuarios.
        
        Args:
            db: Sesión de base de datos
            usuario_admin_id: ID del administrador que consulta
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=str(usuario_admin_id),
                tipo_accion_id=TiposAccion.CONSULTAR_USUARIOS,
                texto=f"Consulta de lista de usuarios del sistema",
                info_adicional={
                    "accion": "listar_usuarios",
                    "modulo": "administracion_usuarios",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Error registrando consulta de usuarios: {e}")
            return None
    
    
    async def registrar_consulta_usuario_especifico(
        self,
        db: Session,
        usuario_admin_id: int,
        usuario_consultado_id: str
    ) -> Optional[T_Bitacora]:
        """
        Registra la consulta de un usuario específico.
        
        Args:
            db: Sesión de base de datos
            usuario_admin_id: ID del administrador que consulta
            usuario_consultado_id: ID (cédula) del usuario consultado
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=str(usuario_admin_id),
                tipo_accion_id=TiposAccion.CONSULTAR_USUARIOS,
                texto=f"Consulta de usuario: {usuario_consultado_id}",
                info_adicional={
                    "usuario_consultado_id": usuario_consultado_id,
                    "accion": "consultar_usuario",
                    "modulo": "administracion_usuarios",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Error registrando consulta de usuario: {e}")
            return None
    
    
    async def registrar_creacion_usuario(
        self,
        db: Session,
        usuario_admin_id: int,
        usuario_creado_cedula: str,
        datos_usuario: Dict[str, Any]
    ) -> Optional[T_Bitacora]:
        """
        Registra la creación de un nuevo usuario.
        
        Args:
            db: Sesión de base de datos
            usuario_admin_id: ID del admin que crea
            usuario_creado_cedula: Cédula del usuario creado
            datos_usuario: Datos del usuario (nombre, email, rol)
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            nombre_completo = datos_usuario.get('nombre_completo', usuario_creado_cedula)
            
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=str(usuario_admin_id),
                tipo_accion_id=TiposAccion.CREAR_USUARIO,
                texto=f"Creación de usuario: {nombre_completo} (Cédula: {usuario_creado_cedula})",
                info_adicional={
                    "usuario_creado_cedula": usuario_creado_cedula,
                    "nombre_usuario": datos_usuario.get("nombre_usuario"),
                    "email": datos_usuario.get("correo"),
                    "rol_id": datos_usuario.get("id_rol"),
                    "nombre_completo": nombre_completo,
                    "modulo": "administracion_usuarios",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Error registrando creación de usuario: {e}")
            return None
    
    
    async def registrar_edicion_usuario(
        self,
        db: Session,
        usuario_admin_id: int,
        usuario_editado_id: str,
        cambios: Dict[str, Any]
    ) -> Optional[T_Bitacora]:
        """
        Registra la edición de un usuario.
        
        Args:
            db: Sesión de base de datos
            usuario_admin_id: ID del admin que edita
            usuario_editado_id: ID (cédula) del usuario editado
            cambios: Diccionario con los cambios realizados
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            # Construir resumen de cambios
            campos_modificados = list(cambios.keys())
            resumen_cambios = f"Campos modificados: {', '.join(campos_modificados)}"
            
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=str(usuario_admin_id),
                tipo_accion_id=TiposAccion.EDITAR_USUARIO,
                texto=f"Edición de usuario: {usuario_editado_id} - {resumen_cambios}",
                info_adicional={
                    "usuario_editado_id": usuario_editado_id,
                    "cambios": cambios,
                    "campos_modificados": campos_modificados,
                    "modulo": "administracion_usuarios",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Error registrando edición de usuario: {e}")
            return None
    
    
    async def registrar_reseteo_contrasena(
        self,
        db: Session,
        usuario_admin_id: int,
        usuario_reseteado_id: str
    ) -> Optional[T_Bitacora]:
        """
        Registra el reseteo de contraseña de un usuario por un admin.
        
        Args:
            db: Sesión de base de datos
            usuario_admin_id: ID del admin que resetea
            usuario_reseteado_id: ID (cédula) del usuario cuya contraseña se resetea
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=str(usuario_admin_id),
                tipo_accion_id=TiposAccion.EDITAR_USUARIO,
                texto=f"Reseteo de contraseña de usuario: {usuario_reseteado_id}",
                info_adicional={
                    "usuario_reseteado_id": usuario_reseteado_id,
                    "accion": "reseteo_contrasena",
                    "tipo_reseteo": "admin",
                    "modulo": "administracion_usuarios",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Error registrando reseteo de contraseña: {e}")
            return None
    
    
    async def registrar_actualizacion_ultimo_acceso(
        self,
        db: Session,
        usuario_admin_id: int,
        usuario_actualizado_id: str
    ) -> Optional[T_Bitacora]:
        """
        Registra la actualización manual del último acceso de un usuario.
        
        Args:
            db: Sesión de base de datos
            usuario_admin_id: ID del admin que actualiza
            usuario_actualizado_id: ID (cédula) del usuario actualizado
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=str(usuario_admin_id),
                tipo_accion_id=TiposAccion.EDITAR_USUARIO,
                texto=f"Actualización de último acceso de usuario: {usuario_actualizado_id}",
                info_adicional={
                    "usuario_actualizado_id": usuario_actualizado_id,
                    "accion": "actualizar_ultimo_acceso",
                    "modulo": "administracion_usuarios",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Error registrando actualización de último acceso: {e}")
            return None
    
    
    async def registrar_cambio_avatar(
        self,
        db: Session,
        usuario_id: str,
        tipo_cambio: str,
        detalles: Optional[Dict[str, Any]] = None
    ) -> Optional[T_Bitacora]:
        """
        Registra cambios en el avatar de un usuario.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario que cambia su avatar
            tipo_cambio: Tipo de cambio (upload, tipo, eliminar)
            detalles: Detalles adicionales del cambio
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            textos = {
                "upload": f"Usuario {usuario_id} subió imagen de avatar personalizada",
                "tipo": f"Usuario {usuario_id} cambió tipo de avatar a {detalles.get('avatar_tipo', 'N/A')}",
                "eliminar": f"Usuario {usuario_id} eliminó su avatar"
            }
            
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=str(usuario_id),
                tipo_accion_id=TiposAccion.EDITAR_USUARIO,
                texto=textos.get(tipo_cambio, f"Usuario {usuario_id} modificó su avatar"),
                info_adicional={
                    "usuario_id": usuario_id,
                    "accion": f"cambio_avatar_{tipo_cambio}",
                    "tipo_cambio": tipo_cambio,
                    "modulo": "perfil_usuario",
                    **(detalles or {}),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Error registrando cambio de avatar: {e}")
            return None


# Instancia singleton del servicio especializado
usuarios_audit_service = UsuariosAuditService()
