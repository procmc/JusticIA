from pydantic import BaseModel
from typing import Optional


class UsuarioCrear(BaseModel):
    """Schema para crear un usuario"""
    nombre_usuario: str
    correo: str
    contrasenna: str
    id_rol: int


class UsuarioEditar(BaseModel):
    """Schema para editar un usuario"""
    nombre_usuario: str
    correo: str
    id_rol: int


class UsuarioRespuesta(BaseModel):
    """Schema para respuesta de usuario"""
    CN_Id_usuario: int
    CT_Nombre_usuario: str
    CT_Correo: str
    CN_Id_rol: int
    CN_Id_estado: int
    
    class Config:
        from_attributes = True


class MensajeRespuesta(BaseModel):
    """Schema para mensajes de respuesta"""
    mensaje: str
