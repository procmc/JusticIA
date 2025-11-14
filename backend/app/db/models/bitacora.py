"""
Modelo SQLAlchemy para bitácora de auditoría.

Define la tabla T_Bitacora que registra todas las acciones de usuarios en el sistema
para cumplimiento de auditoría, GDPR y trazabilidad.

Relaciones:
    * N:1 con T_Usuario: Usuario que realizó la acción (nullable para acciones del sistema)
    * N:1 con T_Tipo_accion: Tipo de acción realizada
    * N:1 con T_Expediente: Expediente relacionado (nullable si no aplica)

Tipos de acción registrados:
    * LOGIN (3), LOGOUT (4)
    * BUSQUEDA_SIMILARES (1)
    * CARGA_DOCUMENTOS (2)
    * CONSULTA_RAG (12)
    * GENERAR_RESUMEN (13)
    * Y más (ver constants.tipos_accion)

Información adicional:
    * CT_Informacion_adicional almacena JSON con metadata específica
    * Ejemplos: session_id, expediente_numero, tiempo_procesamiento, etc.

Uso:
    * Auditoría de acciones de usuarios
    * Análisis de patrones de uso
    * Cumplimiento normativo (GDPR)
    * Trazabilidad de operaciones
    * Estadísticas de sistema

Example:
    >>> from app.db.models import T_Bitacora
    >>> import json
    >>> bitacora = T_Bitacora(
    ...     CN_Id_usuario="112340567",
    ...     CN_Id_tipo_accion=12,  # CONSULTA_RAG
    ...     CT_Texto="Consulta RAG: ¿Qué es la prescripción?",
    ...     CN_Id_expediente=None,  # Consulta general
    ...     CT_Informacion_adicional=json.dumps({
    ...         "session_id": "abc123",
    ...         "tipo_consulta": "general",
    ...         "tiempo_procesamiento": 2.5
    ...     })
    ... )

Note:
    * CF_Fecha_hora se establece automáticamente
    * CN_Id_usuario puede ser NULL para acciones del sistema
    * CT_Informacion_adicional debe ser JSON válido o NULL
    * Los servicios especializados de auditoría gestionan el formato

Ver también:
    * app.services.bitacora: Servicios de auditoría
    * app.repositories.bitacora_repository: Acceso a datos
    * app.routes.bitacora: Endpoints de consulta
    * app.constants.tipos_accion: Catálogo de tipos de acción

Authors:
    JusticIA Team

Version:
    1.0.0
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class T_Bitacora(Base):
	"""
	Modelo de registro de bitácora de auditoría.
	
	Attributes:
		CN_Id_bitacora (int): ID autoincremental (PK, BigInt).
		CF_Fecha_hora (datetime): Timestamp de la acción (auto).
		CT_Texto (str): Descripción legible de la acción (Text).
		CT_Informacion_adicional (str|None): JSON con metadata adicional (Text).
		CN_Id_usuario (str|None): FK a T_Usuario (nullable para sistema).
		CN_Id_tipo_accion (int|None): FK a T_Tipo_accion.
		CN_Id_expediente (int|None): FK a T_Expediente (nullable si no aplica).
		
		usuario (T_Usuario|None): Usuario que realizó la acción.
		tipo_accion (T_Tipo_accion|None): Tipo de acción realizada.
		expediente (T_Expediente|None): Expediente relacionado si aplica.
	"""
	__tablename__ = "T_Bitacora"

	CN_Id_bitacora: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
	CF_Fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
	CT_Texto: Mapped[str] = mapped_column(Text, nullable=False)
	CT_Informacion_adicional: Mapped[Optional[str]] = mapped_column(Text)

    # Relaciones
	CN_Id_usuario: Mapped[Optional[str]] = mapped_column(ForeignKey("T_Usuario.CN_Id_usuario"), nullable=True)
	usuario: Mapped[Optional["T_Usuario"]] = relationship(back_populates="bitacoras")

	CN_Id_tipo_accion: Mapped[Optional[int]] = mapped_column(ForeignKey("T_Tipo_accion.CN_Id_tipo_accion"))
	tipo_accion: Mapped[Optional["T_Tipo_accion"]] = relationship(back_populates="bitacoras")

	CN_Id_expediente: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("T_Expediente.CN_Id_expediente"), nullable=True)
	expediente: Mapped[Optional["T_Expediente"]] = relationship(back_populates="bitacoras")
