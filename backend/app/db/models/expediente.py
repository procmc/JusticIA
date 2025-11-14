"""
Modelo SQLAlchemy para expedientes judiciales.

Define la tabla T_Expediente que almacena expedientes del Poder Judicial de Costa Rica.
Utiliza formato estándar: YY-NNNNNN-NNNN-XX (ej: 24-000123-0001-PE).

Constraints:
    * Unique: CT_Num_expediente (número único de expediente)

Relaciones:
    * M:N con T_Documento: Un expediente contiene múltiples documentos
    * 1:N con T_Bitacora: Un expediente tiene múltiples registros de auditoría

Formato de número de expediente:
    * YY: Año (2 dígitos)
    * NNNNNN: Consecutivo (6 dígitos)
    * NNNN: Oficina (4 dígitos)
    * XX: Materia (2 letras)

Materias comunes:
    * PE: Penal
    * CI: Civil
    * LA: Laboral
    * CA: Contencioso Administrativo
    * NO: Notarial
    * FA: Familia

Example:
    >>> from app.db.models import T_Expediente
    >>> expediente = T_Expediente(
    ...     CT_Num_expediente="24-000123-0001-PE",
    ...     CF_Fecha_creacion=datetime.utcnow()
    ... )
    >>> # Asociar documentos
    >>> expediente.documentos.append(documento1)
    >>> expediente.documentos.append(documento2)

Note:
    * CT_Num_expediente debe validarse con utils.expediente_validator
    * CF_Fecha_creacion se establece automáticamente
    * La relación M:N con documentos usa tabla intermedia T_Expediente_Documento

Ver también:
    * app.services.expediente_service: Lógica de negocio
    * app.repositories.expediente_repository: Acceso a datos
    * app.utils.expediente_validator: Validación de formato

Authors:
    JusticIA Team

Version:
    1.0.0
"""
from typing import List
from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from .expediente_documento import T_Expediente_Documento

class T_Expediente(Base):
    """
    Modelo de expediente judicial.
    
    Attributes:
        CN_Id_expediente (int): ID autoincremental (PK, BigInt).
        CT_Num_expediente (str): Número único de expediente formato estándar (max 60 chars).
        CF_Fecha_creacion (datetime): Timestamp de creación en sistema (auto).
        
        documentos (List[T_Documento]): Documentos asociados al expediente.
        bitacoras (List[T_Bitacora]): Registros de auditoría del expediente.
    """
    __tablename__ = "T_Expediente"
    __table_args__ = (UniqueConstraint("CT_Num_expediente", name="uq_expediente_num"),)

    CN_Id_expediente: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    CT_Num_expediente: Mapped[str] = mapped_column(String(60), nullable=False)
    CF_Fecha_creacion: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # M:N con Documento (Contiene)
    documentos: Mapped[List["T_Documento"]] = relationship(
        secondary=T_Expediente_Documento,
        back_populates="expedientes"
    )

    # N:1 desde Bitácora
    bitacoras: Mapped[List["T_Bitacora"]] = relationship(back_populates="expediente")
