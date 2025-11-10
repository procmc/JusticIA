import jwt
import secrets
import string
import os
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models.usuario import T_Usuario
from app.db.models.rol import T_Rol
from app.db.models.estado import T_Estado
from app.schemas.auth_schemas import (
    LoginResponse, UserInfo, SolicitarRecuperacionResponse, 
    VerificarCodigoResponse, MensajeExito, RestablecerContrasenaResponse
)
from app.repositories.usuario_repository import UsuarioRepository
from app.services.usuario_service import UsuarioService
from app.auth.jwt_auth import create_token

class AuthService:
    """Servicio de autenticación para usuarios"""
    
    def __init__(self):
        self.usuario_repo = UsuarioRepository()
        self.usuario_service = UsuarioService()
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-in-production")
    
    async def autenticar_usuario(self, db: Session, email: str, password: str) -> Optional[LoginResponse]:
        """
        Autentica un usuario y devuelve información del usuario autenticado
        Similar al loginUsuario de MiLoker pero adaptado para JusticIA
        """
        if not email or not password:
            raise ValueError('Email y contraseña son requeridos')
        
        try:
            # Buscar usuario por correo electrónico
            usuario = (
                db.query(T_Usuario)
                .filter(T_Usuario.CT_Correo == email)
                .first()
            )
            
            if not usuario:
                raise ValueError('Credenciales inválidas')
            
            # Verificar la contraseña usando el mismo método del repositorio
            if not self.usuario_repo.pwd_context.verify(password, usuario.CT_Contrasenna):
                raise ValueError('Credenciales inválidas')
            
            # Validar que el usuario esté activo
            if not self._usuario_activo(db, usuario):
                raise ValueError('Credenciales inválidas')
            
            # Verificar si requiere cambio de contraseña
            requiere_cambio_password = usuario.CF_Ultimo_acceso is None
            
            # IMPORTANTE: Solo actualizar CF_Ultimo_acceso si NO requiere cambio de contraseña
            # Si requiere cambio, se actualizará al momento de cambiar la contraseña
            if not requiere_cambio_password:
                usuario.CF_Ultimo_acceso = datetime.utcnow()
                db.commit()
            
            # Obtener datos del usuario
            datos_usuario = self._obtener_datos_usuario(db, usuario)
            
            # Generar access token JWT
            access_token = create_token(
                user_id=usuario.CN_Id_usuario,
                role=datos_usuario['nombre_rol'],
                username=usuario.CT_Correo
            )
            
            return LoginResponse(
                success=True,
                message="Login exitoso",
                user=UserInfo(
                    id=str(usuario.CN_Id_usuario),  # Cédula como string
                    name=datos_usuario['nombre_completo'],
                    email=usuario.CT_Correo,  # Usar el correo real, no el nombre de usuario
                    role=datos_usuario['nombre_rol'],
                    avatar_ruta=usuario.CT_Avatar_ruta,
                    avatar_tipo=usuario.CT_Avatar_tipo,
                    requiere_cambio_password=requiere_cambio_password
                ),
                access_token=access_token  # Incluir el token en la respuesta
            )
            
        except ValueError:
            raise
        except Exception as e:
            print(f"Error en autenticación: {e}")
            raise ValueError('Error interno del servidor')
    
    async def cambiar_contrasenna(self, db: Session, cedula_usuario: str, 
                                contrasenna_actual: str, nueva_contrasenna: str) -> bool:
        """Cambia la contraseña de un usuario"""
        if not cedula_usuario or not contrasenna_actual or not nueva_contrasenna:
            raise ValueError('Todos los campos son requeridos')
        
        if len(nueva_contrasenna) < 6:
            raise ValueError('La nueva contraseña debe tener al menos 6 caracteres')
        
        try:
            # Buscar usuario por cédula
            usuario = db.query(T_Usuario).filter(T_Usuario.CN_Id_usuario == cedula_usuario).first()
            if not usuario:
                raise ValueError('Usuario no encontrado')
            
            # Verificar contraseña actual usando el mismo método del repositorio
            if not self.usuario_repo.pwd_context.verify(contrasenna_actual, usuario.CT_Contrasenna):
                raise ValueError('La contraseña actual es incorrecta')
            
            # Verificar que la nueva contraseña sea diferente
            if self.usuario_repo.pwd_context.verify(nueva_contrasenna, usuario.CT_Contrasenna):
                raise ValueError('La nueva contraseña debe ser diferente a la actual')
            
            # Encriptar nueva contraseña usando el mismo método del repositorio
            nueva_contrasenna_hash = self.usuario_repo._hash_password(nueva_contrasenna)
            
            # Actualizar contraseña
            usuario.CT_Contrasenna = nueva_contrasenna_hash
            
            # Si CF_Ultimo_acceso es NULL, actualizarlo (significa que es cambio obligatorio completado)
            if usuario.CF_Ultimo_acceso is None:
                usuario.CF_Ultimo_acceso = datetime.utcnow()
            
            db.commit()
            
            return True
            
        except ValueError:
            raise
        except Exception as e:
            db.rollback()
            print(f"Error cambiando contraseña: {e}")
            raise ValueError('Error interno del servidor')
    
    def _usuario_activo(self, db: Session, usuario: T_Usuario) -> bool:
        """Verifica si el usuario está activo"""
        if not usuario.CN_Id_estado:
            return False
        
        estado = db.query(T_Estado).filter(T_Estado.CN_Id_estado == usuario.CN_Id_estado).first()
        return estado and estado.CT_Nombre_estado.lower() == 'activo'
    
    def _obtener_datos_usuario(self, db: Session, usuario: T_Usuario) -> dict:
        """Obtiene los datos completos del usuario"""
        # Nombre completo del usuario
        nombre_completo = f"{usuario.CT_Nombre} {usuario.CT_Apellido_uno}"
        if usuario.CT_Apellido_dos:
            nombre_completo += f" {usuario.CT_Apellido_dos}"
        
        # Nombre del rol
        nombre_rol = "Usuario"  # Valor por defecto
        if usuario.CN_Id_rol:
            rol = db.query(T_Rol).filter(T_Rol.CN_Id_rol == usuario.CN_Id_rol).first()
            if rol:
                nombre_rol = rol.CT_Nombre_rol
        
        return {
            'nombre_completo': nombre_completo.strip(),
            'nombre_rol': nombre_rol
        }
    
    async def solicitar_recuperacion_contrasenna(self, db: Session, email: str) -> SolicitarRecuperacionResponse:
        """Solicita recuperación de contraseña enviando código por correo"""
        if not email:
            raise ValueError('El correo electrónico es requerido')
        
        try:
            # Buscar el usuario por correo
            usuario = db.query(T_Usuario).filter(T_Usuario.CT_Correo == email).first()
            if not usuario:
                # Por seguridad, no revelamos si el email existe o no
                return SolicitarRecuperacionResponse(
                    success=True,
                    message='Si el correo existe en nuestro sistema, recibirás un email con las instrucciones'
                )
            
            # Generar código de 6 dígitos
            codigo_recuperacion = f"{secrets.randbelow(900000) + 100000}"
            
            # Crear token JWT con el código y datos del usuario (expira en 15 minutos)
            payload = {
                'cedula': usuario.CN_Id_usuario,
                'email': usuario.CT_Correo,
                'codigo': codigo_recuperacion,
                'timestamp': datetime.utcnow().timestamp(),
                'exp': datetime.utcnow() + timedelta(minutes=15)
            }
            token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
            
            # Obtener nombre completo para personalizar el email
            datos_usuario = self._obtener_datos_usuario(db, usuario)
            
            # Enviar email con el código
            if hasattr(self.usuario_service, 'email_service') and self.usuario_service.email_service:
                try:
                    await self.usuario_service.email_service.send_recovery_code_email(
                        to_email=email,
                        user_name=datos_usuario['nombre_completo'],
                        recovery_code=codigo_recuperacion
                    )
                except Exception as e:
                    print(f"Error enviando email de recuperación: {e}")
                    raise ValueError('Error enviando email de recuperación')
            
            return SolicitarRecuperacionResponse(
                success=True,
                message='Si el correo existe en nuestro sistema, recibirás un email con las instrucciones',
                token=token
            )
            
        except ValueError:
            raise
        except Exception as e:
            print(f"Error en solicitar_recuperacion_contrasenna: {e}")
            raise ValueError('Error interno del servidor')
    
    async def verificar_codigo_recuperacion(self, db: Session, token: str, codigo: str) -> VerificarCodigoResponse:
        """Verifica el código de recuperación enviado por correo"""
        if not token or not codigo:
            raise ValueError('Token y código son requeridos')
        
        try:
            # Verificar y decodificar el token JWT
            try:
                decoded = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            except jwt.ExpiredSignatureError:
                raise ValueError('El código ha expirado. Por favor, solicita un nuevo código de recuperación')
            except jwt.InvalidTokenError:
                raise ValueError('Token inválido. El enlace de recuperación no es válido')
            
            # Verificar que el código coincida
            if decoded['codigo'] != codigo:
                raise ValueError('Código de verificación incorrecto')
            
            # Buscar el usuario para asegurarse de que existe
            usuario = db.query(T_Usuario).filter(T_Usuario.CN_Id_usuario == decoded['cedula']).first()
            if not usuario:
                raise ValueError('Usuario no encontrado')
            
            # Crear un nuevo token de verificación válido para cambiar contraseña (válido por 10 minutos)
            verification_payload = {
                'cedula': decoded['cedula'],
                'email': decoded['email'],
                'verified': True,
                'timestamp': datetime.utcnow().timestamp(),
                'exp': datetime.utcnow() + timedelta(minutes=10)
            }
            verification_token = jwt.encode(verification_payload, self.jwt_secret, algorithm="HS256")
            
            return VerificarCodigoResponse(
                success=True,
                message='Código verificado correctamente',
                verificationToken=verification_token
            )
            
        except ValueError:
            raise
        except Exception as e:
            print(f"Error en verificar_codigo_recuperacion: {e}")
            raise ValueError('Error interno del servidor')
    
    async def cambiar_contrasenna_recuperacion(self, db: Session, verification_token: str, nueva_contrasenna: str) -> MensajeExito:
        """Cambia la contraseña después de verificación exitosa"""
        if not verification_token or not nueva_contrasenna:
            raise ValueError('Token de verificación y nueva contraseña son requeridos')
        
        if len(nueva_contrasenna) < 6:
            raise ValueError('La nueva contraseña debe tener al menos 6 caracteres')
        
        try:
            # Verificar y decodificar el token de verificación
            try:
                decoded = jwt.decode(verification_token, self.jwt_secret, algorithms=["HS256"])
            except jwt.ExpiredSignatureError:
                raise ValueError('El token de verificación ha expirado. Por favor, inicia el proceso de recuperación nuevamente')
            except jwt.InvalidTokenError:
                raise ValueError('Token de verificación inválido')
            
            # Verificar que el token esté marcado como verificado
            if not decoded.get('verified'):
                raise ValueError('Token no verificado. Primero debes verificar el código de recuperación')
            
            # Buscar el usuario
            usuario = db.query(T_Usuario).filter(T_Usuario.CN_Id_usuario == decoded['cedula']).first()
            if not usuario:
                raise ValueError('Usuario no encontrado')
            
            # Verificar que la nueva contraseña sea diferente a la actual
            if self.usuario_repo.pwd_context.verify(nueva_contrasenna, usuario.CT_Contrasenna):
                raise ValueError('La nueva contraseña debe ser diferente a la actual')
            
            # Encriptar nueva contraseña
            nueva_contrasenna_hash = self.usuario_repo._hash_password(nueva_contrasenna)
            
            # Actualizar contraseña
            usuario.CT_Contrasenna = nueva_contrasenna_hash
            db.commit()
            
            return MensajeExito(
                success=True,
                message='Contraseña recuperada exitosamente'
            )
            
        except ValueError:
            raise
        except Exception as e:
            db.rollback()
            print(f"Error en cambiar_contrasenna_recuperacion: {e}")
            raise ValueError('Error interno del servidor')
    
    async def restablecer_contrasenna(self, db: Session, cedula: str) -> RestablecerContrasenaResponse:
        """Restablece la contraseña de un usuario (función para administradores)"""
        if not cedula:
            raise ValueError('La cédula del usuario es requerida')
        
        try:
            # Buscar el usuario por cédula
            usuario = db.query(T_Usuario).filter(T_Usuario.CN_Id_usuario == cedula).first()
            if not usuario:
                raise ValueError('Usuario no encontrado')
            
            # Generar nueva contraseña temporal (8 caracteres alfanuméricos)
            nueva_contrasenna = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            
            # Encriptar la nueva contraseña
            nueva_contrasenna_hash = self.usuario_repo._hash_password(nueva_contrasenna)
            
            # Actualizar la contraseña y forzar cambio obligatorio
            usuario.CT_Contrasenna = nueva_contrasenna_hash
            
            # IMPORTANTE: Poner CF_Ultimo_acceso en NULL para forzar cambio de contraseña
            usuario.CF_Ultimo_acceso = None
            
            # Forzar que SQLAlchemy detecte los cambios
            db.flush()
            db.commit()
            
            # Verificar que el cambio se aplicó correctamente
            db.refresh(usuario)
            print(f"✅ Usuario {cedula} reseteado - CF_Ultimo_acceso: {usuario.CF_Ultimo_acceso}")
            
            # Obtener datos del usuario para personalizar el email
            datos_usuario = self._obtener_datos_usuario(db, usuario)
            
            # Enviar email con la nueva contraseña
            if hasattr(self.usuario_service, 'email_service') and self.usuario_service.email_service:
                try:
                    await self.usuario_service.email_service.send_password_reset_email(
                        to_email=usuario.CT_Correo,
                        user_name=datos_usuario['nombre_completo'],
                        new_password=nueva_contrasenna
                    )
                except Exception as e:
                    print(f"Error enviando email de restablecimiento: {e}")
                    # No fallar la operación si el email falla
            
            return RestablecerContrasenaResponse(
                success=True,
                message='Contraseña restablecida exitosamente',
                data={
                    'correoEnviado': usuario.CT_Correo,
                    'nombreUsuario': datos_usuario['nombre_completo']
                }
            )
            
        except ValueError:
            raise
        except Exception as e:
            db.rollback()
            print(f"Error en restablecer_contrasenna: {e}")
            raise ValueError('Error interno del servidor')