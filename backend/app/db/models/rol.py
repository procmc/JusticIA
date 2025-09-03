from typing import List
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class T_Rol(Base):
	__tablename__ = "T_Rol"

	CN_Id_rol: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	CT_Nombre_rol: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

	# Relaciones
	usuarios: Mapped[List["T_Usuario"]] = relationship(back_populates="rol")