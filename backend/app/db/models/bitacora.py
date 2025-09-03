from typing import Optional
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class T_Bitacora(Base):
	__tablename__ = "T_Bitacora"

	CN_Id_bitacora: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	CF_Fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
	CT_Texto: Mapped[str] = mapped_column(Text, nullable=False)
	CT_Informacion_adicional: Mapped[Optional[str]] = mapped_column(Text)

    # Relaciones
	CN_Id_usuario: Mapped[int] = mapped_column(ForeignKey("T_Usuario.CN_Id_usuario"), nullable=False)
	usuario: Mapped["T_Usuario"] = relationship(back_populates="bitacoras")

	CN_Id_tipo_accion: Mapped[Optional[int]] = mapped_column(ForeignKey("T_Tipo_accion.CN_Id_tipo_accion"))
	tipo_accion: Mapped[Optional["T_Tipo_accion"]] = relationship(back_populates="bitacoras")

	CN_Id_expediente: Mapped[int] = mapped_column(ForeignKey("T_Expediente.CN_Id_expediente"))
	expediente: Mapped["T_Expediente"] = relationship(back_populates="bitacoras")
