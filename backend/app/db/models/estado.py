from typing import List
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class T_Estado(Base):
    __tablename__ = "T_Estado"

    CN_Id_estado: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    CT_Nombre_estado: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    usuarios: Mapped[List["T_Usuario"]] = relationship(back_populates="estado")