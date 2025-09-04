from sqlalchemy import Table, Column, Integer, String, ForeignKey
from .base import Base

T_Usuario_Expediente = Table(
    "T_Usuario_Expediente",
    Base.metadata,
    Column("CN_Id_usuario", String(20), ForeignKey("T_Usuario.CN_Id_usuario"), primary_key=True),
    Column("CN_Id_expediente", Integer, ForeignKey("T_Expediente.CN_Id_expediente"), primary_key=True),
)