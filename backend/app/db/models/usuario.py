from typing import List, Optional
from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from .usuario_expediente import T_Usuario_Expediente

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

    # Rol (N:1)
    CN_Id_rol: Mapped[Optional[int]] = mapped_column(ForeignKey("T_Rol.CN_Id_rol"))
    rol: Mapped[Optional["T_Rol"]] = relationship(back_populates="usuarios")

    # Estado (N:1)  — usuario posee un estado
    CN_Id_estado: Mapped[Optional[int]] = mapped_column(ForeignKey("T_Estado.CN_Id_estado"))
    estado: Mapped[Optional["T_Estado"]] = relationship(back_populates="usuarios")

    # Gestiona (M:N) — expedientes que gestiona este usuario
    expedientes: Mapped[List["T_Expediente"]] = relationship(
        secondary=T_Usuario_Expediente,
        back_populates="usuarios"
    )

    bitacoras: Mapped[List["T_Bitacora"]] = relationship(back_populates="usuario")