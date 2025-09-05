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

class LoginResponse(BaseModel):
    success: bool
    message: str
    user: UserInfo

class CambiarContrasenaRequest(BaseModel):
    cedula_usuario: str
    contrasenna_actual: str
    nueva_contrasenna: str

class MensajeExito(BaseModel):
    success: bool
    message: str
