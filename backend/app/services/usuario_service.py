from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.usuario_repository import UsuarioRepository
from app.db.models.usuario import T_Usuario
from app.schemas.usuario_schemas import UsuarioRespuesta, RolInfo, EstadoInfo
from app.email import EmailService, get_email_config_from_env
import logging

logger = logging.getLogger(__name__)


class UsuarioService:
    """Servicio para usuarios con funcionalidad de email"""
    
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
        """Mapea un usuario del modelo a la respuesta con objetos de rol y estado"""
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
        Crea un nuevo usuario con contraseña automática y envía correo
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
        Resetea la contraseña de un usuario y envía la nueva por correo
        Solo para uso de administradores
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