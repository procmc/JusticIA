"""
Modelo SQLAlchemy para notebooks (NotebookServIA).

Define la tabla T_Notebook: una colección de documentos genérica que un
usuario crea y nombra, sin atarse al formato ni al vocabulario de
expediente judicial (ver antigravity-instructions.md, sección
"Contexto del proyecto"). Es el equivalente a un "notebook" de
NotebookLM, pero 100% local.

Constraints:
    * FK: CN_Id_usuario -> T_Usuario (dueño del notebook)

Relaciones:
    * N:1 con T_Usuario: Un usuario puede tener varios notebooks.

Nota de diseño:
    El notebook no tiene su propia relación M:N con T_Documento. Por
    debajo reutiliza la tubería de ingesta/Qdrant ya existente para
    expedientes, pasando una clave interna (f"NB-{CN_Id_notebook}")
    como si fuera un CT_Num_expediente — ese campo no tiene ninguna
    restricción de formato a nivel de base de datos. El notebook nunca
    se expone con vocabulario de expediente en la UI ni en los prompts.

Example:
    >>> from app.db.models import T_Notebook
    >>> notebook = T_Notebook(
    ...     CT_Nombre="Políticas de teletrabajo MICITT",
    ...     CN_Id_usuario="119120969",
    ... )

Ver también:
    * app.services.notebook_service: Lógica de negocio
    * app.repositories.notebook_repository: Acceso a datos
    * app.services.RAG.prompts.notebook_prompt: Prompt del chat de notebook

Authors:
    ServIA Team

Version:
    1.0.0
"""
from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class T_Notebook(Base):
    """
    Modelo de notebook (colección de documentos genérica).

    Attributes:
        CN_Id_notebook (int): ID autoincremental (PK, BigInt).
        CT_Nombre (str): Nombre que el usuario le da al notebook.
        CN_Id_usuario (str): Cédula del usuario dueño (FK a T_Usuario).
        CF_Fecha_creacion (datetime): Timestamp de creación (auto).
    """
    __tablename__ = "T_Notebook"

    CN_Id_notebook: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    CT_Nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    CN_Id_usuario: Mapped[str] = mapped_column(String(20), ForeignKey("T_Usuario.CN_Id_usuario"), nullable=False)
    CF_Fecha_creacion: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    @property
    def clave_interna(self) -> str:
        """Clave usada como CT_Num_expediente en la tubería de ingesta/Qdrant."""
        return f"NB-{self.CN_Id_notebook}"
