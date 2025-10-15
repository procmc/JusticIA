"""
Servicio especializado de auditoría para el módulo de AUTENTICACIÓN.
Registra acciones de login, cambios de contraseña y recuperación de cuentas.
"""
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from app.db.models.bitacora import T_Bitacora
from app.constants.tipos_accion import TiposAccion
from .bitacora_service import BitacoraService

logger = logging.getLogger(__name__)


class AuthAuditService:
    """Servicio especializado para auditoría del módulo de AUTENTICACIÓN"""
    
    def __init__(self):
        self.bitacora_service = BitacoraService()
    
    async def registrar_login_exitoso(
        self,
        db: Session,
        usuario_id: str,
        email: str,
        rol: str
    ) -> Optional[T_Bitacora]:
        """
        Registra un inicio de sesión EXITOSO.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario (cédula)
            email: Correo electrónico del usuario
            rol: Rol del usuario
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=TiposAccion.LOGIN,
                texto=f"Inicio de sesión exitoso: {email}",
                info_adicional={
                    "email": email,
                    "rol": rol,
                    "resultado": "exitoso",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"⚠️ Error registrando login exitoso: {e}")
            return None
    
    
    async def registrar_login_fallido(
        self,
        db: Session,
        email: str,
        motivo: str
    ) -> Optional[T_Bitacora]:
        """
        Registra un intento de inicio de sesión FALLIDO.
        
        Args:
            db: Sesión de base de datos
            email: Correo electrónico intentado
            motivo: Razón del fallo ("usuario_no_encontrado", "password_incorrecto", "usuario_inactivo", etc.)
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=None,  # No hay usuario autenticado
                tipo_accion_id=TiposAccion.LOGIN,
                texto=f"Intento de login fallido: {email}",
                info_adicional={
                    "email": email,
                    "motivo": motivo,
                    "resultado": "fallido",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"⚠️ Error registrando login fallido: {e}")
            return None
    
    
    async def registrar_cambio_password(
        self,
        db: Session,
        usuario_id: str,
        tipo_cambio: str = "cambio_usuario"
    ) -> Optional[T_Bitacora]:
        """
        Registra un cambio de contraseña.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario (cédula)
            tipo_cambio: Tipo de cambio ("cambio_usuario" o "recuperacion")
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            texto = (
                "Contraseña cambiada por el usuario"
                if tipo_cambio == "cambio_usuario"
                else "Contraseña restablecida (recuperación)"
            )
            
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=TiposAccion.EDITAR_USUARIO,
                texto=texto,
                info_adicional={
                    "tipo_cambio": tipo_cambio,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"⚠️ Error registrando cambio de contraseña: {e}")
            return None
    
    
    async def registrar_solicitud_recuperacion(
        self,
        db: Session,
        usuario_id: str,
        email: str,
        token: str
    ) -> Optional[T_Bitacora]:
        """
        Registra una solicitud de recuperación de contraseña.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario (cédula)
            email: Correo electrónico del usuario
            token: Token de recuperación generado (se guarda solo parcialmente)
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=TiposAccion.EDITAR_USUARIO,
                texto="Solicitud de recuperación de contraseña",
                info_adicional={
                    "email": email,
                    "token_generado": token[:10] + "...",  # Solo primeros caracteres por seguridad
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"⚠️ Error registrando solicitud de recuperación: {e}")
            return None
    
    
    async def registrar_verificacion_codigo(
        self,
        db: Session,
        usuario_id: str,
        email: str,
        exitoso: bool
    ) -> Optional[T_Bitacora]:
        """
        Registra la verificación de código de recuperación.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario (cédula)
            email: Correo electrónico del usuario
            exitoso: Si la verificación fue exitosa
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            texto = (
                "Código de recuperación verificado exitosamente"
                if exitoso
                else "Intento fallido de verificación de código"
            )
            
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=TiposAccion.EDITAR_USUARIO,
                texto=texto,
                info_adicional={
                    "email": email,
                    "resultado": "exitoso" if exitoso else "fallido",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"⚠️ Error registrando verificación de código: {e}")
            return None


# Instancia singleton del servicio especializado
auth_audit_service = AuthAuditService()
