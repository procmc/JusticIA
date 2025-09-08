from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.usuario_repository import UsuarioRepository
from app.db.models.usuario import T_Usuario
from app.schemas.usuario_schemas import UsuarioRespuesta, RolInfo, EstadoInfo
from app.email import EmailService, get_email_config_from_env
import os


class UsuarioService:
    """Servicio para usuarios con funcionalidad de email"""
    
    def __init__(self):
        self.repository = UsuarioRepository()
        
        # Inicializar servicio de correo (como nodemailer transporter)
        try:
            email_config = get_email_config_from_env()
            self.email_service = EmailService(email_config)
        except Exception as e:
            print(f"Warning: No se pudo inicializar el servicio de correo: {e}")
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
    
    async def crear_usuario(self, db: Session, cedula: str, nombre_usuario: str, nombre: str, apellido_uno: str, apellido_dos: Optional[str], correo: str, id_rol: int) -> UsuarioRespuesta:
        """
        Crea un nuevo usuario con contraseña automática y envía correo
        Siempre genera contraseña y envía correo (como en Node.js con nodemailer)
        """
        # Siempre generar contraseña aleatoria
        if self.email_service:
            contrasenna = self.email_service.generate_random_password()
        else:
            # Fallback si no hay servicio de correo
            import secrets
            import string
            contrasenna = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        
        # Crear usuario en la base de datos
        usuario = self.repository.crear_usuario(db, cedula, nombre_usuario, nombre, apellido_uno, apellido_dos, correo, contrasenna, id_rol)
        
        # Siempre enviar correo con la contraseña (async correcto)
        if self.email_service and usuario:
            try:
                # Envío async correcto (sin loops anidados)
                await self.email_service.send_password_email(
                    to=correo,
                    password=contrasenna,
                    usuario_nombre=nombre_usuario
                )
                print(f"✅ Correo enviado exitosamente a {correo}")
                
                # Solo para debug en desarrollo (comentar en producción)
                debug_mode = os.getenv("DEBUG_PASSWORDS", "false").lower() == "true"
                if debug_mode:
                    print(f"🐛 [DEBUG] Contraseña generada: {contrasenna}")
                    
            except Exception as e:
                print(f"❌ Error enviando correo a {correo}: {e}")
                print(f"⚠️ Usuario creado pero correo no enviado - Verificar configuración de email")
                # El usuario se crea de todas formas, solo falla el correo
        else:
            print(f"⚠️ Sin servicio de correo configurado - Usuario creado sin notificación")
        
        return self._mapear_usuario_respuesta(usuario)
    
    def editar_usuario(self, db: Session, usuario_id: str, nombre_usuario: str, nombre: str, apellido_uno: str, apellido_dos: Optional[str], correo: str, id_rol: int, id_estado: int) -> Optional[UsuarioRespuesta]:
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