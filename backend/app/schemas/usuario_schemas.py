from pydantic import BaseModel
from typing import Optional


class RolInfo(BaseModel):
    id: int
    nombre: str


class EstadoInfo(BaseModel):
    id: int
    nombre: str


class UsuarioCrear(BaseModel):
    nombre_usuario: str
    correo: str
    contrasenna: str
    id_rol: int


class UsuarioEditar(BaseModel):
    nombre_usuario: str
    correo: str
    id_rol: int


class UsuarioRespuesta(BaseModel):
    CN_Id_usuario: int
    CT_Nombre_usuario: str
    CT_Correo: str
    CN_Id_rol: int
    CN_Id_estado: int
    rol: Optional[RolInfo] = None
    estado: Optional[EstadoInfo] = None
    
    class Config:
        from_attributes = True


class MensajeRespuesta(BaseModel):
    mensaje: str
