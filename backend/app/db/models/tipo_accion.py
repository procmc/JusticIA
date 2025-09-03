from typing import List
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class T_Tipo_accion(Base):
	__tablename__ = "T_Tipo_accion"

	CN_Id_tipo_accion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	CT_Nombre_tipo_accion: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Relación con Bitácora
	bitacoras: Mapped[List["T_Bitacora"]] = relationship(back_populates="tipo_accion")