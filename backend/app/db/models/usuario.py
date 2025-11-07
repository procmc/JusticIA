from typing import List, Optional
from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from .base import Base

class T_Usuario(Base):
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