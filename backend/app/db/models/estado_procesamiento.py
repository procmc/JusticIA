"""
Modelo SQLAlchemy para estados de procesamiento de documentos.

Define la tabla T_Estado_procesamiento que rastrea el estado del flujo de
procesamiento de documentos y audio cargados al sistema.

Estados del flujo:
    * PENDIENTE (id=1): Documento cargado, esperando procesamiento
    * EN_PROCESAMIENTO (id=2): Worker Celery procesando activamente
    * PROCESADO (id=3): Procesamiento completo exitoso
    * ERROR (id=4): Error durante procesamiento

Flujo de procesamiento:
    1. Usuario carga documento → PENDIENTE
    2. Worker Celery toma tarea → EN_PROCESAMIENTO
    3. Extracción de texto (Tika para PDF, Whisper para audio)
    4. Chunking y limpieza de texto
    5. Generación de embeddings con BGE-M3
    6. Almacenamiento de vectores en Milvus
    7. Actualización a PROCESADO (o ERROR si falla)

Relaciones:
    * 1:N con T_Documento: Un estado tiene múltiples documentos

Usos:
    * Monitoreo de progreso de ingesta
    * Detección de documentos con errores
    * Estadísticas de procesamiento
    * Reintento de documentos en ERROR

Example:
    >>> from app.db.models import T_Estado_procesamiento
    >>> estado_pendiente = T_Estado_procesamiento(
    ...     CN_Id_estado=1,
    ...     CT_Nombre_estado="PENDIENTE"
    ... )

Note:
    * Los estados se crean en la inicialización de la BD
    * CT_Nombre_estado es único
    * Documentos en ERROR pueden reintentar procesamiento

Ver también:
    * app.services.ingesta: Procesamiento de documentos
    * app.repositories.documento_repository: Actualización de estados
    * tasks.procesar_ingesta: Tarea Celery de procesamiento

Authors:
    JusticIA Team

Version:
    1.0.0
"""
from typing import List
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class T_Estado_procesamiento(Base):
	"""
	Modelo de estado de procesamiento de documento.
	
	Attributes:
		CN_Id_estado (int): ID autoincremental (PK).
		CT_Nombre_estado (str): Nombre único del estado (max 50 chars).
		
		documentos (List[T_Documento]): Documentos en este estado.
	"""
	__tablename__ = "T_Estado_procesamiento"

	CN_Id_estado: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	CT_Nombre_estado: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

	documentos: Mapped[List["T_Documento"]] = relationship(back_populates="estado_procesamiento")