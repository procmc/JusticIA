from typing import Optional
from sqlalchemy.orm import Session
from app.db.models.usuario import T_Usuario
from app.db.models.rol import T_Rol
from app.db.models.estado import T_Estado
from app.schemas.auth_schemas import LoginResponse, UserInfo
from app.repositories.usuario_repository import UsuarioRepository

class AuthService:
    """Servicio de autenticación para usuarios"""
    
    def __init__(self):
        self.usuario_repo = UsuarioRepository()
    
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
            
            # Obtener datos del usuario
            datos_usuario = self._obtener_datos_usuario(db, usuario)
            
            return LoginResponse(
                success=True,
                message="Login exitoso",
                user=UserInfo(
                    id=str(usuario.CN_Id_usuario),  # Cédula como string
                    name=datos_usuario['nombre_completo'],
                    email=usuario.CT_Correo,  # Usar el correo real, no el nombre de usuario
                    role=datos_usuario['nombre_rol']
                )
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