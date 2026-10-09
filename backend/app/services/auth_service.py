"""
Servicio de Autenticación y Gestión de Contraseñas para ServIA.

Este módulo implementa el sistema completo de autenticación, autorización y
gestión de credenciales para usuarios del sistema ServIA. Provee funcionalidades
de login y cambio de contraseña. La recuperación de contraseña por código vive en
`app/services/recuperacion_service.py` y el restablecimiento por el Administrador, en el servicio de usuarios.

Arquitectura de Seguridad:
    - Encriptación: Bcrypt con salt automático (passlib)
    - Tokens JWT: HS256 con SECRET_KEY de entorno
    - Validación: Estado activo del usuario en cada operación

Flujos principales:

1. Autenticación (Login):
    └─ Validar email y contraseña
    └─ Verificar estado "Activo"
    └─ Generar token JWT
    └─ Detectar si requiere cambio obligatorio (CF_Ultimo_acceso=NULL)
    └─ Actualizar último acceso (solo si no requiere cambio)

2. Cambio de contraseña (por usuario):
    └─ Validar contraseña actual
    └─ Verificar que nueva sea diferente
    └─ Actualizar CF_Ultimo_acceso si era NULL (completa cambio obligatorio)

Funciones públicas:
    - autenticar_usuario(): Login con credenciales
    - cambiar_contrasenna(): Cambio por usuario autenticado

Seguridad implementada:
    - Bcrypt: Hash de contraseñas con salt automático
    - JWT tokens: Firma HMAC SHA-256 con clave secreta
    - Validación de estado: Solo usuarios "Activo" pueden autenticarse
    - Cambio obligatorio: CF_Ultimo_acceso=NULL fuerza cambio en próximo login

Integración con otros módulos:
    - UsuarioRepository: Acceso a datos de usuarios
    - UsuarioService: Lógica de negocio de usuarios
    - EmailService: Envío de códigos y contraseñas temporales
    - jwt_auth: Creación de tokens JWT
    - Bitácora: Registro de eventos de autenticación

Modelos de respuesta (Schemas):
    - LoginResponse: Datos de usuario + access_token JWT

Estados de usuario:
    - "Activo": Puede autenticarse y operar normalmente
    - "Inactivo": No puede autenticarse (credenciales inválidas)
    - CF_Ultimo_acceso=NULL: Requiere cambio obligatorio de contraseña

Example:
    >>> from app.services.auth_service import AuthService
    >>> auth_service = AuthService()
    >>> 
    >>> # Login normal
    >>> response = await auth_service.autenticar_usuario(
    ...     db, 'usuario@poderjudicial.go.cr', 'password123'
    ... )
    >>> print(response.user.name)
    'Juan Pérez'
    >>> print(response.access_token)
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    >>> 

Note:
    - JWT_SECRET_KEY debe configurarse en variables de entorno (producción)
    - Las contraseñas deben tener mínimo 6 caracteres
    - CF_Ultimo_acceso=NULL indica cambio de contraseña obligatorio

Ver también:
    - app.repositories.usuario_repository: Operaciones CRUD de usuarios
    - app.services.usuario_service: Lógica de negocio de usuarios
    - app.email.core.email_service: Envío de emails
    - app.auth.jwt_auth: Creación y validación de tokens JWT
    - app.schemas.auth_schemas: Modelos de respuesta

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    1.0.0
"""

import os
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models.usuario import T_Usuario
from app.db.models.rol import T_Rol
from app.db.models.estado import T_Estado
from app.schemas.auth_schemas import LoginResponse, UserInfo
from app.repositories.usuario_repository import UsuarioRepository
from app.services.usuario_service import UsuarioService
from app.auth.jwt_auth import create_token

class AuthService:
    """
    Servicio de autenticación y gestión de contraseñas para usuarios.
    
    Maneja el inicio de sesión y el cambio de contraseña del propio usuario.
    
    Attributes:
        usuario_repo (UsuarioRepository): Repositorio para operaciones de usuario.
        usuario_service (UsuarioService): Servicio de negocio de usuarios.
        jwt_secret (str): Clave secreta para firmar tokens JWT.
    """
    
    def __init__(self):
        """
        Inicializa el servicio de autenticación.
        
        Carga la clave JWT desde variables de entorno.
        """
        self.usuario_repo = UsuarioRepository()
        self.usuario_service = UsuarioService()
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-in-production")
    
    async def autenticar_usuario(self, db: Session, email: str, password: str) -> Optional[LoginResponse]:
        """
        Autentica un usuario mediante email y contraseña.
        
        Verifica las credenciales del usuario, valida que esté activo,
        genera un token JWT y devuelve la información de sesión.
        
        Args:
            db (Session): Sesión de base de datos SQLAlchemy.
            email (str): Correo electrónico del usuario.
            password (str): Contraseña en texto plano.
        
        Returns:
            Optional[LoginResponse]: Objeto con información del usuario autenticado,
                incluyendo access_token JWT. Contiene:
                - success (bool): True si la autenticación fue exitosa
                - message (str): Mensaje descriptivo
                - user (UserInfo): Datos del usuario autenticado
                - access_token (str): Token JWT para autenticación
        
        Raises:
            ValueError: Si las credenciales son inválidas, el usuario está inactivo,
                o hay un error interno.
        
        Example:
            >>> response = await auth_service.autenticar_usuario(
            ...     db, 'usuario@ejemplo.com', 'password123'
            ... )
            >>> print(response.user.name)
            'Juan Pérez'
            >>> print(response.user.role)
            'Usuario Judicial'
            >>> print(response.user.requiere_cambio_password)
            False
        
        Note:
            - Si CF_Ultimo_acceso es NULL, requiere cambio obligatorio de contraseña
            - Solo actualiza CF_Ultimo_acceso si NO requiere cambio
            - El token JWT expira según configuración (default: 8 horas)
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
        """
        Cambia la contraseña de un usuario autenticado.
        
        Valida la contraseña actual, verifica que la nueva sea diferente,
        y actualiza el campo CF_Ultimo_acceso si era NULL (cambio obligatorio).
        
        Args:
            db (Session): Sesión de base de datos SQLAlchemy.
            cedula_usuario (str): Cédula (ID) del usuario.
            contrasenna_actual (str): Contraseña actual en texto plano.
            nueva_contrasenna (str): Nueva contraseña en texto plano (mínimo 6 caracteres).
        
        Returns:
            bool: True si el cambio fue exitoso.
        
        Raises:
            ValueError: Si:
                - Algún campo está vacío
                - La nueva contraseña tiene menos de 6 caracteres
                - El usuario no existe
                - La contraseña actual es incorrecta
                - La nueva contraseña es igual a la actual
                - Hay un error interno del servidor
        
        Example:
            >>> success = await auth_service.cambiar_contrasenna(
            ...     db, '123456789', 'oldPass123', 'newPass456'
            ... )
            >>> assert success == True
        
        Note:
            - Si CF_Ultimo_acceso es NULL, se actualiza (significa cambio obligatorio completado)
            - Las contraseñas se encriptan con bcrypt
        """
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
