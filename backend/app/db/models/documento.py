from typing import List, Optional
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from .expediente_documento import T_Expediente_Documento  # <-- nueva asociación

class T_Documento(Base):
    __tablename__ = "T_Documento"

    CN_Id_documento: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    CT_Nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    CT_Tipo_archivo: Mapped[str] = mapped_column(String(50), nullable=False)
    CT_Ruta_archivo: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    CF_Fecha_carga: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # M:N con Expediente (Contiene)
    expedientes: Mapped[List["T_Expediente"]] = relationship(
        secondary=T_Expediente_Documento,
        back_populates="documentos"
    )

    # N:1 con Estado_procesamiento
    CN_Id_estado: Mapped[Optional[int]] = mapped_column(ForeignKey("T_Estado_procesamiento.CN_Id_estado"))
    estado_procesamiento: Mapped[Optional["T_Estado_procesamiento"]] = relationship(back_populates="documentos")
