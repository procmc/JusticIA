from typing import List
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from .expediente_documento import T_Expediente_Documento

class T_Expediente(Base):
    __tablename__ = "T_Expediente"
    __table_args__ = (UniqueConstraint("CT_Num_expediente", name="uq_expediente_num"),)

    CN_Id_expediente: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    CT_Num_expediente: Mapped[str] = mapped_column(String(60), nullable=False)
    CF_Fecha_creacion: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # M:N con Documento (Contiene)
    documentos: Mapped[List["T_Documento"]] = relationship(
        secondary=T_Expediente_Documento,
        back_populates="expedientes"
    )

    # N:1 desde Bitácora
    bitacoras: Mapped[List["T_Bitacora"]] = relationship(back_populates="expediente")
