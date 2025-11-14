"""
Tabla de asociación Many-to-Many entre Expedientes y Documentos.

Define la tabla intermedia T_Expediente_Documento que implementa la relación
M:N entre expedientes judiciales y documentos.

Relación:
    * Un expediente puede contener múltiples documentos
    * Un documento puede pertenecer a múltiples expedientes

Uso:
    * Permite que un mismo documento (ej: sentencia) se asocie a varios expedientes
    * Facilita consultas de documentos por expediente
    * Soporta casos donde documentos son compartidos entre expedientes relacionados

Estructura:
    * CN_Id_expediente (BigInt, FK, PK): Referencia a T_Expediente
    * CN_Id_documento (BigInt, FK, PK): Referencia a T_Documento
    * Clave primaria compuesta por ambos campos

Example:
    >>> # SQLAlchemy maneja automáticamente esta tabla
    >>> expediente.documentos.append(documento)  # Crea registro en tabla
    >>> documento.expedientes.append(otro_exp)   # Asocia a otro expediente

Note:
    * Esta es una tabla SQLAlchemy Table, no un modelo declarativo
    * SQLAlchemy gestiona automáticamente inserts/deletes
    * No tiene campos adicionales más allá de las FKs

Ver también:
    * app.db.models.expediente: Modelo de expediente
    * app.db.models.documento: Modelo de documento
    * app.services.expediente_service: Gestión de asociaciones

Authors:
    JusticIA Team

Version:
    1.0.0
"""
from sqlalchemy import Table, Column, BigInteger, ForeignKey
from .base import Base

# Tabla de asociación M:N entre Expediente y Documento
T_Expediente_Documento = Table(
    "T_Expediente_Documento",
    Base.metadata,
    Column("CN_Id_expediente", BigInteger, ForeignKey("T_Expediente.CN_Id_expediente"), primary_key=True),
    Column("CN_Id_documento", BigInteger, ForeignKey("T_Documento.CN_Id_documento"), primary_key=True),
)