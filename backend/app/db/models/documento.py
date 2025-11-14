"""
Modelo SQLAlchemy para documentos judiciales.

Define la tabla T_Documento que almacena documentos PDF y archivos de audio
asociados a expedientes. Rastrea estado de procesamiento (extracción de texto,
transcripción, embeddings, almacenamiento vectorial).

Relaciones:
    * M:N con T_Expediente: Un documento puede pertenecer a múltiples expedientes
    * N:1 con T_Estado_procesamiento: Un documento tiene un estado de procesamiento

Tipos de archivo soportados:
    * application/pdf: Documentos PDF (con/sin OCR)
    * audio/mpeg: Archivos MP3
    * audio/wav: Archivos WAV
    * audio/x-wav: WAV alternativo

Estados de procesamiento:
    * PENDIENTE: Documento cargado, pendiente de procesamiento
    * EN_PROCESAMIENTO: Worker Celery procesando
    * PROCESADO: Texto extraído y embeddings generados
    * ERROR: Error durante procesamiento

Flujo de procesamiento:
    1. Carga de archivo → PENDIENTE
    2. Worker inicia → EN_PROCESAMIENTO
    3. Extracción de texto (Tika/Whisper)
    4. Generación de embeddings (BGE-M3)
    5. Almacenamiento en Milvus
    6. Actualización a PROCESADO

Example:
    >>> from app.db.models import T_Documento
    >>> documento = T_Documento(
    ...     CT_Nombre_archivo="demanda.pdf",
    ...     CT_Tipo_archivo="application/pdf",
    ...     CT_Ruta_archivo="uploads/exp123/demanda.pdf",
    ...     CN_Id_estado=1  # PENDIENTE
    ... )
    >>> # Asociar a expediente
    >>> documento.expedientes.append(expediente)

Note:
    * CT_Ruta_archivo es relativa a la carpeta uploads/
    * CF_Fecha_carga se establece automáticamente
    * El procesamiento lo manejan tareas Celery asíncronas

Ver también:
    * app.services.ingesta: Procesamiento de documentos
    * app.repositories.documento_repository: Acceso a datos
    * tasks.procesar_ingesta: Tarea Celery de procesamiento

Authors:
    JusticIA Team

Version:
    1.0.0
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from .expediente_documento import T_Expediente_Documento

class T_Documento(Base):
    """
    Modelo de documento judicial.
    
    Attributes:
        CN_Id_documento (int): ID autoincremental (PK, BigInt).
        CT_Nombre_archivo (str): Nombre original del archivo (max 255 chars).
        CT_Tipo_archivo (str): MIME type del archivo (max 50 chars).
        CT_Ruta_archivo (str|None): Ruta relativa en uploads/ (max 500 chars).
        CF_Fecha_carga (datetime): Timestamp de carga (auto).
        CN_Id_estado (int|None): FK a T_Estado_procesamiento.
        
        expedientes (List[T_Expediente]): Expedientes asociados al documento.
        estado_procesamiento (T_Estado_procesamiento|None): Estado de procesamiento actual.
    """
    __tablename__ = "T_Documento"

    CN_Id_documento: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    CT_Nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    CT_Tipo_archivo: Mapped[str] = mapped_column(String(50), nullable=False)
    CT_Ruta_archivo: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    CF_Fecha_carga: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # M:N con Expediente (Contiene)
    expedientes: Mapped[List["T_Expediente"]] = relationship(
        secondary=T_Expediente_Documento,
        back_populates="documentos"
    )

    # N:1 con Estado_procesamiento
    CN_Id_estado: Mapped[Optional[int]] = mapped_column(ForeignKey("T_Estado_procesamiento.CN_Id_estado"))
    estado_procesamiento: Mapped[Optional["T_Estado_procesamiento"]] = relationship(back_populates="documentos")
