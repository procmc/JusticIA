from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class EstadoBase(BaseModel):
    """Esquema base para el estado"""
    id: int
    nombre: str

    class Config:
        from_attributes = True


class RolBase(BaseModel):
    """Esquema base para el rol"""
    id: int
    nombre: str

    class Config:
        from_attributes = True


class UsuarioBase(BaseModel):
    """Esquema base para usuario"""
    nombre_usuario: str = Field(..., min_length=3, max_length=50, description="Nombre de usuario único")
    correo: EmailStr = Field(..., description="Correo electrónico del usuario")
    id_rol: Optional[int] = Field(None, description="ID del rol asignado al usuario")
    id_estado: Optional[int] = Field(None, description="ID del estado del usuario")


class UsuarioCrear(UsuarioBase):
    """Esquema para crear un usuario"""
    contrasenna: str = Field(..., min_length=6, max_length=255, description="Contraseña del usuario")


class UsuarioActualizar(BaseModel):
    """Esquema para actualizar un usuario"""
    nombre_usuario: Optional[str] = Field(None, min_length=3, max_length=50, description="Nombre de usuario único")
    correo: Optional[EmailStr] = Field(None, description="Correo electrónico del usuario")
    contrasenna: Optional[str] = Field(None, min_length=6, max_length=255, description="Nueva contraseña del usuario")
    id_rol: Optional[int] = Field(None, description="ID del rol asignado al usuario")
    id_estado: Optional[int] = Field(None, description="ID del estado del usuario")


class UsuarioCambiarEstado(BaseModel):
    """Esquema para cambiar el estado de un usuario"""
    id_estado: int = Field(..., description="Nuevo ID del estado del usuario")


class UsuarioRespuesta(UsuarioBase):
    """Esquema de respuesta para usuario"""
    id: int = Field(..., description="ID único del usuario")
    rol: Optional[RolBase] = None
    estado: Optional[EstadoBase] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, usuario):
        """Método personalizado para mapear desde el modelo ORM"""
        return cls(
            id=usuario.CN_Id_usuario,
            nombre_usuario=usuario.CT_Nombre_usuario,
            correo=usuario.CT_Correo,
            id_rol=usuario.CN_Id_rol,
            id_estado=usuario.CN_Id_estado,
            rol=RolBase(id=usuario.rol.CN_Id_rol, nombre=usuario.rol.CT_Nombre_rol) if usuario.rol else None,
            estado=EstadoBase(id=usuario.estado.CN_Id_estado, nombre=usuario.estado.CT_Nombre_estado) if usuario.estado else None
        )


class UsuarioLista(BaseModel):
    """Esquema para lista de usuarios con paginación"""
    usuarios: list[UsuarioRespuesta]
    total: int
    pagina: int
    tamaño_pagina: int
    total_paginas: int


class MensajeRespuesta(BaseModel):
    """Esquema para mensajes de respuesta"""
    mensaje: str
    codigo: int = 200
