"""
Servicio Especializado de Auditoría para el Módulo de Gestión de Usuarios.

Este módulo registra todas las operaciones administrativas sobre usuarios
del sistema JusticIA, proporcionando trazabilidad completa de acciones CRUD
y cambios de configuración para auditoría, seguridad y cumplimiento normativo.

Eventos auditados:

    1. **Consulta de usuarios** (TiposAccion.CONSULTAR_USUARIOS):
       - Administrador lista todos los usuarios
       - Registra: admin_id, timestamp
       - Info adicional: accion="listar_usuarios"

    2. **Consulta de usuario individual** (TiposAccion.CONSULTAR_USUARIO):
       - Consulta de perfil de un usuario específico
       - Registra: admin_id, usuario_consultado_id
       - Info adicional: usuario_consultado, email_consultado

    3. **Creación de usuario** (TiposAccion.CREAR_USUARIO):
       - Administrador crea nuevo usuario
       - Registra: admin_id, nuevo_usuario_id, email, rol
       - Info adicional: rol_asignado, estado_inicial

    4. **Edición de usuario** (TiposAccion.EDITAR_USUARIO):
       - Modificación de datos del usuario
       - Registra: admin_id, usuario_editado_id, cambios realizados
       - Info adicional: cambios={campo: {antes, despues}}

    5. **Cambio de rol** (TiposAccion.CAMBIAR_ROL_USUARIO):
       - Promoción/degradación de rol
       - Registra: admin_id, usuario_id, rol_anterior, rol_nuevo
       - Info adicional: rol_anterior, rol_nuevo

    6. **Cambio de estado** (TiposAccion.CAMBIAR_ESTADO_USUARIO):
       - Activación/desactivación de cuenta
       - Registra: admin_id, usuario_id, estado_anterior, estado_nuevo
       - Info adicional: estado_anterior, estado_nuevo

    7. **Cambio de avatar** (cambios de perfil):
       - Subida/actualización/eliminación de avatar
       - Registra: usuario_id, tipo_cambio (upload/tipo/eliminar)
       - Info adicional: ruta, tamaño_bytes, extension, avatar_tipo

Arquitectura de auditoría:

    UsuariosAuditService (este módulo)
    └─> BitacoraService (orquestador general)
        └─> BitacoraRepository (acceso a datos)
            └─> T_Bitacora (modelo de BD)

Responsabilidades:

    **Este servicio**:
    - Construir mensajes descriptivos para cada operación CRUD
    - Capturar estado "antes" y "después" de cambios
    - Agregar info_adicional específica de usuarios
    - Manejar cambios de avatar (tipos: upload, tipo, eliminar)

    **BitacoraService**:
    - Convertir info_adicional a JSON
    - Validar tipos de acción
    - Delegar a repository

    **BitacoraRepository**:
    - Insertar registros en T_Bitacora
    - Manejar transacciones

Estructura de info_adicional (JSON):

    Creación de usuario:
    {
        "nuevo_usuario_id": "123456789",
        "email": "nuevo@ejemplo.com",
        "rol_asignado": "Usuario Judicial",
        "estado_inicial": "Activo",
        "modulo": "administracion_usuarios",
        "timestamp": "2025-11-24T10:30:00Z"
    }

    Edición de usuario:
    {
        "usuario_editado": "123456789",
        "cambios": {
            "nombre": {"antes": "Juan", "despues": "Juan Carlos"},
            "email": {"antes": "viejo@ejemplo.com", "despues": "nuevo@ejemplo.com"}
        },
        "modulo": "administracion_usuarios",
        "timestamp": "2025-11-24T10:30:00Z"
    }

    Cambio de rol:
    {
        "usuario_afectado": "123456789",
        "email": "usuario@ejemplo.com",
        "rol_anterior": "Usuario Judicial",
        "rol_nuevo": "Administrador",
        "modulo": "administracion_usuarios",
        "timestamp": "2025-11-24T10:30:00Z"
    }

    Cambio de avatar:
    {
        "tipo_cambio": "upload",
        "ruta": "uploads/avatars/123456789.jpg",
        "tamaño_bytes": 245680,
        "extension": ".jpg"
    }

Integración con otros módulos:
    - UsuarioService: Llama a métodos de auditoría en operaciones CRUD
    - AvatarService: Registra cambios de avatar
    - Routes (usuarios.py): Registra accesos administrativos

Casos de uso de auditoría:

    1. **Trazabilidad de privilegios**:
       - Historial de cambios de rol
       - Quién otorgó permisos administrativos

    2. **Auditoría de creación de cuentas**:
       - Quién creó cada usuario
       - Roles asignados inicialmente

    3. **Seguimiento de desactivaciones**:
       - Usuarios desactivados y por quién
       - Motivos de desactivación

    4. **Registro de modificaciones**:
       - Cambios en datos personales
       - Estado "antes" y "después"

    5. **Gestión de perfiles**:
       - Cambios de avatar
       - Actualizaciones de información

Example:
    >>> from app.services.bitacora.usuarios_audit_service import usuarios_audit_service
    >>> 
    >>> # Crear usuario
    >>> await usuarios_audit_service.registrar_creacion_usuario(
    ...     db=db,
    ...     admin_id="987654321",
    ...     nuevo_usuario_id="123456789",
    ...     email="nuevo@ejemplo.com",
    ...     rol="Usuario Judicial"
    ... )
    >>> 
    >>> # Cambio de rol
    >>> await usuarios_audit_service.registrar_cambio_rol(
    ...     db=db,
    ...     admin_id="987654321",
    ...     usuario_id="123456789",
    ...     email="usuario@ejemplo.com",
    ...     rol_anterior="Usuario Judicial",
    ...     rol_nuevo="Administrador"
    ... )
    >>> 
    >>> # Cambio de avatar
    >>> await usuarios_audit_service.registrar_cambio_avatar(
    ...     db=db,
    ...     usuario_id="123456789",
    ...     tipo_cambio="upload",
    ...     detalles={"ruta": "uploads/avatars/123456789.jpg", "tamaño_bytes": 245680}
    ... )

Manejo de errores:
    - Captura excepciones y retorna None
    - Logging de errores (warning level)
    - No propaga errores (auditoría no debe romper flujo)

Note:
    - Cambios de datos personales requieren GDPR compliance
    - Los registros de edición capturan estado "antes" y "después"
    - Timestamps en UTC para consistencia
    - Singleton: Use instancia global `usuarios_audit_service`

Ver también:
    - app.services.bitacora.bitacora_service: Servicio base
    - app.services.usuario_service: Consumidor principal
    - app.services.avatar_service: Auditoría de avatares
    - app.constants.tipos_accion: Catálogo de tipos

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    1.0.0
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
        usuario_admin_id: str
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
        usuario_admin_id: str,
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
        usuario_admin_id: str,
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
        usuario_admin_id: str,
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
        usuario_admin_id: str,
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
            logger.info(f"Iniciando registro de reseteo de contraseña. Admin: {usuario_admin_id}, Usuario: {usuario_reseteado_id}")
            
            resultado = await self.bitacora_service.registrar(
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
            
            logger.info(f"Registro de reseteo de contraseña completado exitosamente. ID bitácora: {resultado.CN_Id_bitacora if resultado else 'None'}")
            return resultado
            
        except Exception as e:
            logger.error(f"Error registrando reseteo de contraseña: {e}", exc_info=True)
            return None
    
    
    async def registrar_actualizacion_ultimo_acceso(
        self,
        db: Session,
        usuario_admin_id: str,
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
