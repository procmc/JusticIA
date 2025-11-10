from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequest(BaseModel):
    email: str
    password: str

class UserInfo(BaseModel):
    id: str  # Cédula del usuario
    name: str  # Nombre completo
    email: str  # Correo/username
    role: str  # Rol del usuario
    avatar_ruta: Optional[str] = None  # Ruta de la imagen de perfil
    avatar_tipo: Optional[str] = None  # Tipo de avatar preferido
    requiere_cambio_password: bool = False  # Si debe cambiar contraseña (NULL en CF_Ultimo_acceso)

class LoginResponse(BaseModel):
    success: bool
    message: str
    user: UserInfo
    access_token: Optional[str] = None  # Token JWT para autenticación

class CambiarContrasenaRequest(BaseModel):
    cedula_usuario: str
    contrasenna_actual: str
    nueva_contrasenna: str

class MensajeExito(BaseModel):
    success: bool
    message: str

class LogoutRequest(BaseModel):
    usuario_id: str  # Cédula del usuario
    email: str  # Email del usuario

class SolicitarRecuperacionRequest(BaseModel):
    email: str

class SolicitarRecuperacionResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None

class VerificarCodigoRequest(BaseModel):
    token: str
    codigo: str

class VerificarCodigoResponse(BaseModel):
    success: bool
    message: str
    verificationToken: str

class CambiarContrasenaRecuperacionRequest(BaseModel):
    verificationToken: str
    nuevaContrasenna: str

class RestablecerContrasenaRequest(BaseModel):
    cedula: str

class RestablecerContrasenaResponse(BaseModel):
    success: bool
    message: str
    data: dict
