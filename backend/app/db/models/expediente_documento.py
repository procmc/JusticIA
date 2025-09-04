from sqlalchemy import Table, Column, BigInteger, ForeignKey
from .base import Base

T_Expediente_Documento = Table(
    "T_Expediente_Documento",
    Base.metadata,
    Column("CN_Id_expediente", BigInteger, ForeignKey("T_Expediente.CN_Id_expediente"), primary_key=True),
    Column("CN_Id_documento", BigInteger, ForeignKey("T_Documento.CN_Id_documento"), primary_key=True),
)