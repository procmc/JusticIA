from typing import List
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class T_Estado_procesamiento(Base):
	__tablename__ = "T_Estado_procesamiento"

	CN_Id_estado: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	CT_Nombre_estado: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

	documentos: Mapped[List["T_Documento"]] = relationship(back_populates="estado_procesamiento")