"""
Modelos de base de datos del sistema JusticIA.

Este paquete contiene todos los modelos SQLAlchemy 2.0 que definen el esquema
de la base de datos SQL Server del sistema.

Arquitectura del modelo de datos:
    * Usuarios y autenticación: T_Usuario, T_Rol, T_Estado
    * Documentos judiciales: T_Expediente, T_Documento, T_Expediente_Documento
    * Auditoría: T_Bitacora, T_Tipo_accion
    * Procesamiento: T_Estado_procesamiento

Modelos principales:
    * Base: Clase base declarativa SQLAlchemy 2.0
    * T_Usuario: Usuarios del sistema con roles y estados
    * T_Expediente: Expedientes judiciales
    * T_Documento: Documentos PDF y audio asociados a expedientes
    * T_Bitacora: Registro de auditoría de acciones
    
Modelos de catálogo:
    * T_Rol: Roles de usuario (ADMIN, USER)
    * T_Estado: Estados de usuario (ACTIVO, INACTIVO)
    * T_Tipo_accion: Tipos de acciones auditables
    * T_Estado_procesamiento: Estados de procesamiento de documentos

Tablas de asociación:
    * T_Expediente_Documento: Relación M:N entre expedientes y documentos

Convenciones de nomenclatura:
    * Tablas: T_{Nombre}
    * IDs numéricos: CN_Id_{tabla}
    * Campos de texto: CT_{nombre}
    * Campos de fecha: CF_{nombre}

Características SQLAlchemy 2.0:
    * Mapped[] types para type hints
    * mapped_column() para definición de columnas
    * relationship() con back_populates para relaciones bidireccionales
    * DeclarativeBase como base class

Example:
    >>> from app.db.models import T_Usuario, T_Rol
    >>> # Crear usuario con rol
    >>> usuario = T_Usuario(
    ...     CN_Id_usuario="112340567",
    ...     CT_Nombre_usuario="jperez",
    ...     CN_Id_rol=2  # USER
    ... )
    
    >>> from app.db.models import T_Expediente, T_Documento
    >>> # Asociar documento a expediente
    >>> expediente.documentos.append(documento)

Note:
    * Todos los modelos usan SQLAlchemy 2.0 syntax
    * Las migraciones se gestionan con Alembic
    * Los modelos soportan type hints completos para IDE support

Ver también:
    * app.db.database: Configuración de conexión a BD
    * alembic/: Sistema de migraciones
    * app.repositories: Capa de acceso a datos

Authors:
    JusticIA Team

Version:
    1.0.0 - SQLAlchemy 2.0+ with type hints
"""
from .base import Base
from .rol import T_Rol
from .usuario import T_Usuario
from .estado import T_Estado
from .estado_procesamiento import T_Estado_procesamiento
from .expediente import T_Expediente
from .documento import T_Documento
from .tipo_accion import T_Tipo_accion
from .bitacora import T_Bitacora
from .expediente_documento import T_Expediente_Documento

__all__ = [
    "Base",
    "T_Rol",
    "T_Usuario",
    "T_Estado",
    "T_Estado_procesamiento",
    "T_Expediente",
    "T_Documento",
    "T_Tipo_accion",
    "T_Bitacora",
    "T_Expediente_Documento",
]