from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RolInfo(BaseModel):
    id: int
    nombre: str


class EstadoInfo(BaseModel):
    id: int
    nombre: str


class UsuarioCrear(BaseModel):
    cedula: str  # ID del usuario (cédula)
    nombre_usuario: str
    nombre: str
    apellido_uno: str
    apellido_dos: str  # Requerido
    correo: str
    # Contraseña se genera automáticamente - no se solicita al usuario
    id_rol: int


class UsuarioEditar(BaseModel):
    nombre_usuario: str
    nombre: str
    apellido_uno: str
    apellido_dos: str  # Requerido
    correo: str
    id_rol: int
    id_estado: int


class UsuarioRespuesta(BaseModel):
    CN_Id_usuario: str  # Cédula
    CT_Nombre_usuario: str
    CT_Nombre: str
    CT_Apellido_uno: str
    CT_Apellido_dos: str  # Requerido
    CT_Correo: str
    CN_Id_rol: int
    CN_Id_estado: int
    CF_Ultimo_acceso: Optional[datetime] = None
    CF_Fecha_creacion: Optional[datetime] = None
    rol: Optional[RolInfo] = None
    estado: Optional[EstadoInfo] = None
    
    class Config:
        from_attributes = True


class MensajeRespuesta(BaseModel):
    mensaje: str
