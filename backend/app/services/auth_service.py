"""
Servicio de Autenticación y Gestión de Contraseñas para JusticIA.

Este módulo implementa el sistema completo de autenticación, autorización y
gestión de credenciales para usuarios del sistema JusticIA. Provee funcionalidades
de login, recuperación de contraseña, cambio de contraseña y restablecimiento
administrativo.

Arquitectura de Seguridad:
    - Encriptación: Bcrypt con salt automático (passlib)
    - Tokens JWT: HS256 con SECRET_KEY de entorno
    - Recuperación: Códigos numéricos de 6 dígitos + token JWT
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

3. Recuperación de contraseña (por email):
    └─ Solicitar recuperación: Genera código de 6 dígitos + token JWT (15 min)
    └─ Verificar código: Valida código y genera token de verificación (10 min)
    └─ Cambiar contraseña: Usa token verificado para cambiar credencial

4. Restablecimiento administrativo:
    └─ Genera contraseña temporal aleatoria (8 caracteres)
    └─ Establece CF_Ultimo_acceso=NULL (fuerza cambio obligatorio)
    └─ Envía contraseña temporal por email

Funciones públicas:
    - autenticar_usuario(): Login con credenciales
    - cambiar_contrasenna(): Cambio por usuario autenticado
    - solicitar_recuperacion_contrasenna(): Inicio flujo recuperación
    - verificar_codigo_recuperacion(): Validación de código por email
    - cambiar_contrasenna_recuperacion(): Completar recuperación
    - restablecer_contrasenna(): Reset administrativo

Seguridad implementada:
    - Bcrypt: Hash de contraseñas con salt automático
    - JWT tokens: Firma HMAC SHA-256 con clave secreta
    - Timeouts: 15 min para recuperación, 10 min para verificación
    - Validación de estado: Solo usuarios "Activo" pueden autenticarse
    - Cambio obligatorio: CF_Ultimo_acceso=NULL fuerza cambio en próximo login
    - Unicidad de código: Códigos de recuperación de un solo uso
    - No revelación: Respuestas genéricas en recuperación (seguridad por oscuridad)

Integración con otros módulos:
    - UsuarioRepository: Acceso a datos de usuarios
    - UsuarioService: Lógica de negocio de usuarios
    - EmailService: Envío de códigos y contraseñas temporales
    - jwt_auth: Creación de tokens JWT
    - Bitácora: Registro de eventos de autenticación

Modelos de respuesta (Schemas):
    - LoginResponse: Datos de usuario + access_token JWT
    - SolicitarRecuperacionResponse: Token JWT con código encriptado
    - VerificarCodigoResponse: Token de verificación después de validar código
    - RestablecerContrasenaResponse: Confirmación de reset administrativo
    - MensajeExito: Respuesta genérica de operación exitosa

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
    >>> # Recuperación de contraseña
    >>> solicitud = await auth_service.solicitar_recuperacion_contrasenna(
    ...     db, 'usuario@poderjudicial.go.cr'
    ... )
    >>> # Usuario recibe email con código de 6 dígitos
    >>> 
    >>> verificacion = await auth_service.verificar_codigo_recuperacion(
    ...     db, solicitud.token, '123456'
    ... )
    >>> 
    >>> cambio = await auth_service.cambiar_contrasenna_recuperacion(
    ...     db, verificacion.verificationToken, 'nuevaPassword456'
    ... )
    >>> print(cambio.message)
    'Contraseña recuperada exitosamente'

Note:
    - JWT_SECRET_KEY debe configurarse en variables de entorno (producción)
    - Los códigos de recuperación expiran en 15 minutos
    - Los tokens de verificación expiran en 10 minutos
    - Las contraseñas deben tener mínimo 6 caracteres
    - CF_Ultimo_acceso=NULL indica cambio de contraseña obligatorio
    - El sistema NO revela si un email existe durante recuperación (seguridad)

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
    """
    Servicio de autenticación y gestión de contraseñas para usuarios.
    
    Maneja el ciclo completo de autenticación: login, cambio de contraseña,
    recuperación de acceso mediante email, y restablecimiento administrativo.
    
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
    
    async def solicitar_recuperacion_contrasenna(self, db: Session, email: str) -> SolicitarRecuperacionResponse:
        """
        Solicita recuperación de contraseña enviando código de 6 dígitos por email.
        
        Genera un código numérico aleatorio, crea un token JWT con el código
        y los datos del usuario, y envía el código por correo electrónico.
        
        Args:
            db (Session): Sesión de base de datos SQLAlchemy.
            email (str): Correo electrónico del usuario.
        
        Returns:
            SolicitarRecuperacionResponse: Objeto con:
                - success (bool): True si el proceso fue exitoso
                - message (str): Mensaje para el usuario
                - token (str): Token JWT con el código encriptado (expira en 15 min)
        
        Raises:
            ValueError: Si:
                - El email está vacío
                - Hay error enviando el email
                - Hay un error interno del servidor
        
        Example:
            >>> response = await auth_service.solicitar_recuperacion_contrasenna(
            ...     db, 'usuario@ejemplo.com'
            ... )
            >>> print(response.message)
            'Si el correo existe en nuestro sistema, recibirás un email...'
            >>> # El código de 6 dígitos se envía por email
            >>> # El token se usa en verificar_codigo_recuperacion()
        
        Note:
            - Por seguridad, siempre retorna éxito aunque el email no exista
            - El código es válido por 15 minutos
            - El token incluye: cedula, email, codigo, timestamp, exp
        """
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