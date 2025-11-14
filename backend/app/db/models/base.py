"""
Clase base declarativa para modelos SQLAlchemy.

Define la clase Base que todos los modelos del sistema heredan.
Utiliza SQLAlchemy 2.0+ DeclarativeBase para type safety y mejor IDE support.

Características:
    * Type hints completos con Mapped[] para todos los campos
    * Metadata centralizado para todas las tablas
    * Soporte para migraciones con Alembic

Convenciones de nomenclatura:
    * Tablas: T_{Nombre} (ej: T_Usuario, T_Expediente)
    * Columnas ID: CN_Id_{tabla} (ej: CN_Id_usuario)
    * Columnas texto: CT_{nombre} (ej: CT_Nombre, CT_Correo)
    * Columnas fecha: CF_{nombre} (ej: CF_Fecha_creacion)

Uso:
    >>> from .base import Base
    >>> class MiModelo(Base):
    ...     __tablename__ = "T_MiModelo"
    ...     id: Mapped[int] = mapped_column(primary_key=True)

Note:
    * Usar Mapped[] en lugar de Column() para type safety
    * Preferir mapped_column() sobre Column()
    * relationship() para relaciones entre modelos

Ver también:
    * app.db.models: Todos los modelos del sistema
    * alembic/: Sistema de migraciones

Authors:
    JusticIA Team

Version:
    1.0.0 - SQLAlchemy 2.0+
"""
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    Clase base declarativa para todos los modelos SQLAlchemy.
    
    Todos los modelos del sistema heredan de esta clase para:
    - Compartir metadata centralizado
    - Soporte de migraciones con Alembic
    - Type safety con Mapped[] types
    """
    pass
