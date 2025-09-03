from sqlalchemy import Table, Column, Integer, ForeignKey
from .base import Base

T_Expediente_Documento = Table(
    "T_Expediente_Documento",
    Base.metadata,
    Column("CN_Id_expediente", Integer, ForeignKey("T_Expediente.CN_Id_expediente"), primary_key=True),
    Column("CN_Id_documento", Integer, ForeignKey("T_Documento.CN_Id_documento"), primary_key=True),
)