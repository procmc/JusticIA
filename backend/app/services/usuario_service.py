"""
Servicio de Lógica de Negocio para Gestión de Usuarios.

Este módulo implementa la capa de servicio para operaciones CRUD de usuarios,
incluye envío automático de credenciales por email, reseteo de contraseñas,
y mapeo de entidades a esquemas de respuesta.

Funciones principales:
    - obtener_todos_usuarios: Lista todos los usuarios del sistema
    - obtener_usuario: Obtiene un usuario por cédula (ID)
    - crear_usuario: Crea usuario con contraseña aleatoria y envío por email
    - editar_usuario: Actualiza datos de usuario incluyendo rol y estado
    - resetear_contrasenna_usuario: Resetea contraseña y envía nueva por email
    - actualizar_ultimo_acceso: Registra último acceso del usuario

Integración con Email:
    - Envío automático de credenciales al crear usuario
    - Notificación de contraseña reseteada
    - Configuración desde variables de entorno (Gmail, Outlook, etc.)
    - Graceful degradation si el servicio de email no está disponible

Mapeo de entidades:
    - Convierte T_Usuario (modelo DB) a UsuarioRespuesta (schema API)
    - Incluye información de relaciones (rol, estado)
    - Formato consistente para respuestas de API

Example:
    >>> service = UsuarioService()
    >>> nuevo_usuario = await service.crear_usuario(
    ...     db, '123456789', 'jperez', 'Juan', 'Pérez', 'Gómez',
    ...     'jperez@example.com', id_rol=2
    ... )
    >>> # Usuario creado y contraseña enviada por email

Note:
    - Las contraseñas se generan aleatoriamente (8 caracteres alfanuméricos)
    - El servicio de email es opcional (log warning si no está configurado)
    - Usar resetear_contrasenna_usuario solo desde endpoints de administrador
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.usuario_repository import UsuarioRepository
from app.db.models.usuario import T_Usuario
from app.schemas.usuario_schemas import UsuarioRespuesta, RolInfo, EstadoInfo
from app.email import EmailService, get_email_config_from_env
import logging

logger = logging.getLogger(__name__)


class UsuarioService:
    """
    Servicio de lógica de negocio para gestión de usuarios.
    
    Coordina operaciones entre el repositorio de usuarios y el servicio
    de email. Aplica validaciones de negocio y transforma entidades.
    
    Attributes:
        repository (UsuarioRepository): Repositorio para acceso a datos.
        email_service (EmailService): Servicio de envío de correos (opcional).
    """
    
    def __init__(self):
        self.repository = UsuarioRepository()
        
        # Inicializar servicio de correo
        try:
            email_config = get_email_config_from_env()
            self.email_service = EmailService(email_config)
        except Exception as e:
            logger.warning(f"No se pudo inicializar el servicio de correo: {e}")
            self.email_service = None
    
    def _mapear_usuario_respuesta(self, usuario: T_Usuario) -> UsuarioRespuesta:
        """
        Mapea un usuario del modelo de BD a esquema de respuesta de API.
        
        Transforma T_Usuario (modelo SQLAlchemy) a UsuarioRespuesta (schema Pydantic)
        incluyendo información de relaciones (rol, estado).
        
        Args:
            usuario (T_Usuario): Modelo de usuario de la base de datos.
        
        Returns:
            UsuarioRespuesta: Schema de respuesta con datos del usuario.
        
        Note:
            - Método privado (uso interno del servicio)
            - Incluye objetos RolInfo y EstadoInfo anidados
        """
        return UsuarioRespuesta(
            CN_Id_usuario=usuario.CN_Id_usuario,
            CT_Nombre_usuario=usuario.CT_Nombre_usuario,
            CT_Nombre=usuario.CT_Nombre,
            CT_Apellido_uno=usuario.CT_Apellido_uno,
            CT_Apellido_dos=usuario.CT_Apellido_dos,
            CT_Correo=usuario.CT_Correo,
            CN_Id_rol=usuario.CN_Id_rol,
            CN_Id_estado=usuario.CN_Id_estado,
            CF_Ultimo_acceso=usuario.CF_Ultimo_acceso,
            CF_Fecha_creacion=usuario.CF_Fecha_creacion,
            rol=RolInfo(
                id=usuario.rol.CN_Id_rol,
                nombre=usuario.rol.CT_Nombre_rol
            ) if usuario.rol else None,
            estado=EstadoInfo(
                id=usuario.estado.CN_Id_estado,
                nombre=usuario.estado.CT_Nombre_estado
            ) if usuario.estado else None
        )
    
    def obtener_todos_usuarios(self, db: Session) -> List[UsuarioRespuesta]:
        """Obtiene todos los usuarios"""
        usuarios = self.repository.obtener_usuarios(db)
        return [self._mapear_usuario_respuesta(usuario) for usuario in usuarios]
    
    def obtener_usuario(self, db: Session, usuario_id: str) -> Optional[UsuarioRespuesta]:
        """Obtiene un usuario por ID (cédula)"""
        usuario = self.repository.obtener_usuario_por_id(db, usuario_id)
        if usuario:
            return self._mapear_usuario_respuesta(usuario)
        return None
    
    async def crear_usuario(self, db: Session, cedula: str, nombre_usuario: str, nombre: str, apellido_uno: str, apellido_dos: str, correo: str, id_rol: int) -> UsuarioRespuesta:
        """
        Crea un nuevo usuario con contraseña aleatoria y envía credenciales por email.
        
        Genera una contraseña segura de 8 caracteres, crea el usuario en la base
        de datos, y envía un email con las credenciales. Si el servicio de email
        no está disponible, el usuario se crea igualmente pero sin notificación.
        
        Args:
            db (Session): Sesión de base de datos SQLAlchemy.
            cedula (str): Cédula del usuario (ID único).
            nombre_usuario (str): Nombre de usuario para login.
            nombre (str): Primer nombre del usuario.
            apellido_uno (str): Primer apellido del usuario.
            apellido_dos (str): Segundo apellido del usuario.
            correo (str): Correo electrónico del usuario.
            id_rol (int): ID del rol a asignar (1=Admin, 2=Usuario Judicial).
        
        Returns:
            UsuarioRespuesta: Objeto con datos del usuario creado incluyendo
                información de rol y estado.
        
        Example:
            >>> usuario = await service.crear_usuario(
            ...     db, '123456789', 'jperez', 'Juan', 'Pérez', 'Gómez',
            ...     'jperez@example.com', id_rol=2
            ... )
            >>> print(usuario.CT_Correo)
            'jperez@example.com'
            >>> # Email enviado automáticamente con credenciales
        
        Note:
            - La contraseña se genera aleatoriamente (8 caracteres)
            - El usuario queda en estado "Activo" por defecto
            - CF_Ultimo_acceso = NULL (requiere cambio de contraseña)
            - Si email falla, el usuario se crea pero se registra warning
        """
        # Generar contraseña aleatoria
        if self.email_service:
            contrasenna = self.email_service.generate_random_password()
        else:
            import secrets
            import string
            contrasenna = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        
        # Crear usuario en la base de datos
        usuario = self.repository.crear_usuario(db, cedula, nombre_usuario, nombre, apellido_uno, apellido_dos, correo, contrasenna, id_rol)
        
        # Enviar correo con la contraseña
        if self.email_service and usuario:
            try:
                await self.email_service.send_password_email(
                    to=correo,
                    password=contrasenna,
                    usuario_nombre=nombre_usuario
                )
                logger.info(f"Correo enviado exitosamente a {correo}")
            except Exception as e:
                logger.error(f"Error enviando correo a {correo}: {e}")
                logger.warning("Usuario creado pero correo no enviado")
        else:
            logger.warning("Sin servicio de correo configurado - Usuario creado sin notificación")
        
        return self._mapear_usuario_respuesta(usuario)
    
    def editar_usuario(self, db: Session, usuario_id: str, nombre_usuario: str, nombre: str, apellido_uno: str, apellido_dos: str, correo: str, id_rol: int, id_estado: int) -> Optional[UsuarioRespuesta]:
        """Edita un usuario incluyendo rol y estado"""
        usuario = self.repository.editar_usuario(db, usuario_id, nombre_usuario, nombre, apellido_uno, apellido_dos, correo, id_rol, id_estado)
        if usuario:
            return self._mapear_usuario_respuesta(usuario)
        return None

    def actualizar_ultimo_acceso(self, db: Session, usuario_id: str) -> Optional[UsuarioRespuesta]:
        """Actualiza el último acceso del usuario"""
        usuario = self.repository.actualizar_ultimo_acceso(db, usuario_id)
        if usuario:
            return self._mapear_usuario_respuesta(usuario)
        return None

    async def resetear_contrasenna_usuario(self, db: Session, usuario_id: str) -> Optional[UsuarioRespuesta]:
        """
        Resetea la contraseña de un usuario y envía la nueva por email.
        
        Genera una nueva contraseña aleatoria, actualiza el usuario en la base
        de datos (con CF_Ultimo_acceso=NULL para forzar cambio), y envía email
        con la nueva contraseña. Solo debe ser llamado por administradores.
        
        Args:
            db (Session): Sesión de base de datos SQLAlchemy.
            usuario_id (str): Cédula del usuario a resetear.
        
        Returns:
            Optional[UsuarioRespuesta]: Objeto con datos del usuario actualizado,
                o None si el usuario no existe.
        
        Example:
            >>> usuario = await service.resetear_contrasenna_usuario(db, '123456789')
            >>> if usuario:
            ...     print('Contraseña reseteada y email enviado')
            >>> else:
            ...     print('Usuario no encontrado')
        
        Note:
            - Solo debe ser llamado desde endpoints con rol Administrador
            - CF_Ultimo_acceso se pone en NULL (fuerza cambio obligatorio)
            - La nueva contraseña es aleatoria de 8 caracteres
            - Si email falla, la contraseña se resetea pero sin notificación
        """
        # Obtener el usuario
        usuario = self.repository.obtener_usuario_por_id(db, usuario_id)
        if not usuario:
            return None
        
        # Generar nueva contraseña aleatoria
        if self.email_service:
            nueva_contrasenna = self.email_service.generate_random_password()
        else:
            import secrets
            import string
            nueva_contrasenna = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        
        # Actualizar contraseña en la base de datos
        usuario_actualizado = self.repository.resetear_contrasenna(db, usuario_id, nueva_contrasenna)
        if not usuario_actualizado:
            return None
        
        # Enviar correo con la nueva contraseña
        if self.email_service:
            try:
                await self.email_service.send_password_email(
                    to=usuario.CT_Correo,
                    password=nueva_contrasenna,
                    usuario_nombre=usuario.CT_Nombre_usuario
                )
                logger.info(f"Contraseña reseteada y correo enviado a {usuario.CT_Correo}")
            except Exception as e:
                logger.error(f"Error enviando correo a {usuario.CT_Correo}: {e}")
                logger.warning("Contraseña reseteada pero correo no enviado")
        else:
            logger.warning("Sin servicio de correo configurado - Contraseña reseteada sin notificación")
        
        return self._mapear_usuario_respuesta(usuario_actualizado)