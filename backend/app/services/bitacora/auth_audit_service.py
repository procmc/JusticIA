"""
Servicio Especializado de Auditoría para el Módulo de Autenticación.

Este módulo registra todas las acciones relacionadas con autenticación,
autorización y gestión de credenciales en la bitácora del sistema JusticIA,
proporcionando trazabilidad completa para seguridad y cumplimiento normativo.

Eventos auditados:

    1. **LOGIN exitoso** (TiposAccion.LOGIN):
       - Usuario se autentica correctamente
       - Registra: email, rol, timestamp
       - Info adicional: resultado="exitoso"

    2. **LOGIN fallido** (TiposAccion.LOGIN):
       - Intento de autenticación rechazado
       - Registra: email intentado, motivo de rechazo
       - Motivos: usuario_no_encontrado, password_incorrecto, usuario_inactivo
       - Info adicional: resultado="fallido"
       - **Sin usuario_id** (no autenticado)

    3. **LOGOUT** (TiposAccion.LOGOUT):
       - Cierre de sesión voluntario
       - Registra: email, timestamp
       - Info adicional: accion="logout"

    4. **Cambio de contraseña** (TiposAccion.CAMBIAR_PASSWORD):
       - Usuario cambia su propia contraseña
       - Tipo: "cambio_usuario" o "recuperacion"
       - Registra: tipo de cambio, timestamp

    5. **Recuperación de contraseña** (TiposAccion.RECUPERAR_PASSWORD):
       - Solicitud de código de recuperación
       - Código de verificación enviado por email
       - Registra: email, timestamp
       - Info adicional: accion="solicitar_recuperacion"

    6. **Reset por administrador** (TiposAccion.RESET_PASSWORD):
       - Administrador restablece contraseña de otro usuario
       - Registra: admin_id, usuario_afectado_id, email
       - Info adicional: accion="reset_por_admin", admin_rol

Arquitectura de auditoría:

    AuthAuditService (este módulo)
    └─> BitacoraService (orquestador general)
        └─> BitacoraRepository (acceso a datos)
            └─> T_Bitacora (modelo de BD)

Responsabilidades:

    **Este servicio**:
    - Construir mensajes descriptivos para cada evento
    - Agregar info_adicional específica de autenticación
    - Seleccionar TiposAccion apropiado
    - Manejar casos especiales (login sin usuario_id)

    **BitacoraService**:
    - Convertir info_adicional a JSON
    - Validar tipos de acción
    - Delegar a repository

    **BitacoraRepository**:
    - Insertar registros en T_Bitacora
    - Manejar transacciones y rollback

Estructura de info_adicional (JSON):

    Login exitoso:
    {
        "email": "usuario@ejemplo.com",
        "rol": "Usuario Judicial",
        "resultado": "exitoso",
        "timestamp": "2025-11-24T10:30:00Z"
    }

    Login fallido:
    {
        "email": "usuario@ejemplo.com",
        "motivo": "password_incorrecto",
        "resultado": "fallido",
        "timestamp": "2025-11-24T10:30:00Z"
    }

    Reset por admin:
    {
        "usuario_afectado": "123456789",
        "email_afectado": "usuario@ejemplo.com",
        "admin_rol": "Administrador",
        "accion": "reset_por_admin",
        "timestamp": "2025-11-24T10:30:00Z"
    }

Integración con otros módulos:
    - AuthService: Llama a métodos de auditoría en cada operación
    - UsuarioService: Registra cambios de contraseña
    - auth_audit_service (este): Proporciona API de auditoría

Casos de uso de seguridad:

    1. **Detección de intentos de intrusión**:
       - Múltiples login_fallido del mismo email
       - Alertar administradores

    2. **Auditoría de acceso**:
       - Quién inició sesión y cuándo
       - Roles accedidos

    3. **Trazabilidad de credenciales**:
       - Historial de cambios de contraseña
       - Resets administrativos realizados

    4. **Cumplimiento normativo**:
       - Registro inmutable de eventos
       - Timestamps UTC para consistencia

Example:
    >>> from app.services.bitacora.auth_audit_service import auth_audit_service
    >>> 
    >>> # Login exitoso
    >>> await auth_audit_service.registrar_login_exitoso(
    ...     db=db,
    ...     usuario_id="123456789",
    ...     email="usuario@ejemplo.com",
    ...     rol="Usuario Judicial"
    ... )
    >>> 
    >>> # Login fallido
    >>> await auth_audit_service.registrar_login_fallido(
    ...     db=db,
    ...     email="intruso@malicious.com",
    ...     motivo="password_incorrecto"
    ... )
    >>> 
    >>> # Reset por admin
    >>> await auth_audit_service.registrar_reset_password(
    ...     db=db,
    ...     admin_id="987654321",
    ...     usuario_afectado_id="123456789",
    ...     email_afectado="usuario@ejemplo.com",
    ...     admin_rol="Administrador"
    ... )

Manejo de errores:
    - Captura excepciones y retorna None
    - Logging de errores (warning level)
    - No propaga errores (auditoría no debe romper flujo principal)

Note:
    - Los timestamps se registran en UTC
    - Login fallido no tiene usuario_id (no autenticado)
    - Los registros son inmutables (no se modifican/eliminan)
    - Singleton: Use instancia global `auth_audit_service`

Ver también:
    - app.services.bitacora.bitacora_service: Servicio base de auditoría
    - app.services.auth_service: Consumidor principal
    - app.constants.tipos_accion: Catálogo de tipos de acción
    - app.db.models.bitacora: Modelo de datos

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    1.0.0
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
            logger.warning(f"Error registrando login exitoso: {e}")
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
            logger.warning(f"Error registrando login fallido: {e}")
            return None
    
    
    async def registrar_logout(
        self,
        db: Session,
        usuario_id: str,
        email: str
    ) -> Optional[T_Bitacora]:
        """
        Registra un cierre de sesión.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario (cédula)
            email: Correo electrónico del usuario
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=TiposAccion.LOGOUT,
                texto=f"Cierre de sesión: {email}",
                info_adicional={
                    "email": email,
                    "accion": "logout",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Error registrando logout: {e}")
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
                tipo_accion_id=TiposAccion.CAMBIO_CONTRASENA,
                texto=texto,
                info_adicional={
                    "tipo_cambio": tipo_cambio,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Error registrando cambio de contraseña: {e}")
            return None
    
    
    async def registrar_solicitud_recuperacion(
        self,
        db: Session,
        email: str
    ) -> Optional[T_Bitacora]:
        """
        Registra una solicitud de recuperación de contraseña.
        
        Args:
            db: Sesión de base de datos
            email: Correo electrónico del usuario
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=None,  # No tenemos usuario autenticado
                tipo_accion_id=TiposAccion.RECUPERACION_CONTRASENA,
                texto=f"Solicitud de recuperación de contraseña para: {email}",
                info_adicional={
                    "email": email,
                    "accion": "solicitud_recuperacion",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Error registrando solicitud de recuperación: {e}")
            return None
    
    
    async def registrar_verificacion_codigo(
        self,
        db: Session,
        email: str,
        exitoso: bool
    ) -> Optional[T_Bitacora]:
        """
        Registra la verificación de código de recuperación.
        
        Args:
            db: Sesión de base de datos
            email: Correo electrónico del usuario
            exitoso: Si la verificación fue exitosa
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            texto = (
                f"Código de recuperación verificado exitosamente para: {email}"
                if exitoso
                else f"Intento fallido de verificación de código para: {email}"
            )
            
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=None,  # No tenemos usuario autenticado
                tipo_accion_id=TiposAccion.RECUPERACION_CONTRASENA,
                texto=texto,
                info_adicional={
                    "email": email,
                    "resultado": "exitoso" if exitoso else "fallido",
                    "accion": "verificacion_codigo",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Error registrando verificación de código: {e}")
            return None


# Instancia singleton del servicio especializado
auth_audit_service = AuthAuditService()
