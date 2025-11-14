"""
Modelo SQLAlchemy para tipos de acción de auditoría.

Define la tabla T_Tipo_accion que almacena los tipos de acciones registrables
en la bitácora para auditoría y cumplimiento normativo.

Tipos de acción principales:
    * BUSQUEDA_SIMILARES (1): Búsqueda de casos similares
    * CARGA_DOCUMENTOS (2): Carga de documentos al sistema
    * LOGIN (3): Inicio de sesión
    * LOGOUT (4): Cierre de sesión
    * CONSULTA_RAG (12): Consulta al asistente virtual
    * GENERAR_RESUMEN (13): Generación de resumen con IA

Relaciones:
    * 1:N con T_Bitacora: Un tipo de acción tiene múltiples registros

Usos:
    * Clasificación de registros de auditoría
    * Filtrado de bitácora por tipo de acción
    * Estadísticas de uso del sistema
    * Análisis de patrones de usuario

Example:
    >>> from app.db.models import T_Tipo_accion
    >>> tipo_login = T_Tipo_accion(
    ...     CN_Id_tipo_accion=3,
    ...     CT_Nombre_tipo_accion="LOGIN"
    ... )

Note:
    * Los tipos de acción se crean en la inicialización de la BD
    * CT_Nombre_tipo_accion es único
    * Los IDs deben coincidir con app.constants.tipos_accion

Ver también:
    * app.constants.tipos_accion: Constantes de tipos de acción
    * app.services.bitacora: Servicios de auditoría
    * app.repositories.bitacora_repository: Consultas por tipo

Authors:
    JusticIA Team

Version:
    1.0.0
"""
from typing import List
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class T_Tipo_accion(Base):
	"""
	Modelo de tipo de acción de auditoría.
	
	Attributes:
		CN_Id_tipo_accion (int): ID autoincremental (PK).
		CT_Nombre_tipo_accion (str): Nombre único del tipo de acción (max 50 chars).
		
		bitacoras (List[T_Bitacora]): Registros de bitácora de este tipo.
	"""
	__tablename__ = "T_Tipo_accion"

	CN_Id_tipo_accion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	CT_Nombre_tipo_accion: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Relación con Bitácora
	bitacoras: Mapped[List["T_Bitacora"]] = relationship(back_populates="tipo_accion")