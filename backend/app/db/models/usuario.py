"""
Modelo SQLAlchemy para usuarios del sistema JusticIA.

Define la tabla T_Usuario que almacena información de usuarios con autenticación,
perfiles, roles y estados. Utiliza cédula costarricense como primary key.

Constraints:
    * Unique: CT_Correo (email único por usuario)
    * Unique: CT_Nombre_usuario (username único)

Relaciones:
    * N:1 con T_Rol: Un usuario tiene un rol (ADMIN, USER)
    * N:1 con T_Estado: Un usuario tiene un estado (ACTIVO, INACTIVO)
    * 1:N con T_Bitacora: Un usuario tiene múltiples registros de bitácora

Autenticación:
    * Contraseña hasheada con bcrypt
    * JWT tokens para sesiones
    * Recuperación por email con código de 6 dígitos

Avatar:
    * CT_Avatar_ruta: Ruta de imagen personalizada (uploads/profiles/{id}.{ext})
    * CT_Avatar_tipo: Tipo de avatar (CUSTOM, HOMBRE, MUJER, NEUTRO, INITIALS)

Example:
    >>> from app.db.models import T_Usuario
    >>> usuario = T_Usuario(
    ...     CN_Id_usuario="112340567",
    ...     CT_Nombre_usuario="jperez",
    ...     CT_Nombre="Juan",
    ...     CT_Apellido_uno="Pérez",
    ...     CT_Correo="jperez@example.com",
    ...     CT_Contrasenna="$2b$12$...",  # bcrypt hash
    ...     CN_Id_rol=2  # USER
    ... )

Note:
    * CN_Id_usuario usa cédula sin guiones (ej: "112340567")
    * CT_Contrasenna DEBE ser hash bcrypt, nunca texto plano
    * CF_Ultimo_acceso se actualiza en cada login

Ver también:
    * app.services.usuario_service: Lógica de negocio
    * app.repositories.usuario_repository: Acceso a datos
    * app.routes.usuarios: Endpoints REST

Authors:
    JusticIA Team

Version:
    1.0.0
"""
from typing import List, Optional
from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from .base import Base

class T_Usuario(Base):
    """
    Modelo de usuario del sistema.
    
    Attributes:
        CN_Id_usuario (str): Cédula costarricense (PK, max 20 chars).
        CT_Nombre_usuario (str): Username único (max 50 chars).
        CT_Nombre (str): Primer nombre (max 100 chars).
        CT_Apellido_uno (str): Primer apellido (max 100 chars).
        CT_Apellido_dos (str|None): Segundo apellido opcional (max 100 chars).
        CT_Correo (str): Email único (max 100 chars).
        CT_Contrasenna (str): Hash bcrypt de contraseña (max 255 chars).
        CT_Avatar_ruta (str|None): Ruta de avatar personalizado (max 255 chars).
        CT_Avatar_tipo (str|None): Tipo de avatar (max 50 chars).
        CF_Ultimo_acceso (datetime|None): Timestamp de último login.
        CF_Fecha_creacion (datetime): Timestamp de creación (auto).
        CN_Id_rol (int|None): FK a T_Rol.
        CN_Id_estado (int|None): FK a T_Estado.
        
        rol (T_Rol|None): Relación con rol del usuario.
        estado (T_Estado|None): Relación con estado del usuario.
        bitacoras (List[T_Bitacora]): Registros de auditoría del usuario.
    """
    __tablename__ = "T_Usuario"
    __table_args__ = (
        UniqueConstraint("CT_Correo", name="uq_usuario_correo"),
        UniqueConstraint("CT_Nombre_usuario", name="uq_usuario_nombre"),
    )

    CN_Id_usuario: Mapped[str] = mapped_column(String(20), primary_key=True, autoincrement=False)  # Cédula como PK
    CT_Nombre_usuario: Mapped[str] = mapped_column(String(50), nullable=False)
    CT_Nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    CT_Apellido_uno: Mapped[str] = mapped_column(String(100), nullable=False)  
    CT_Apellido_dos: Mapped[str] = mapped_column(String(100), nullable=True)
    CT_Correo: Mapped[str] = mapped_column(String(100), nullable=False)
    CT_Contrasenna: Mapped[str] = mapped_column(String(255), nullable=False)
    CT_Avatar_ruta: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Ruta de la imagen de perfil
    CT_Avatar_tipo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)   # Tipo de avatar preferido
    CF_Ultimo_acceso: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    CF_Fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    # Rol (N:1)
    CN_Id_rol: Mapped[Optional[int]] = mapped_column(ForeignKey("T_Rol.CN_Id_rol"))
    rol: Mapped[Optional["T_Rol"]] = relationship(back_populates="usuarios")

    # Estado (N:1)  — usuario posee un estado
    CN_Id_estado: Mapped[Optional[int]] = mapped_column(ForeignKey("T_Estado.CN_Id_estado"))
    estado: Mapped[Optional["T_Estado"]] = relationship(back_populates="usuarios")

    bitacoras: Mapped[List["T_Bitacora"]] = relationship(back_populates="usuario")