"""
Modelo SQLAlchemy de los resultados de estudio de un notebook (spec 010, NotebookServIA).

Define la tabla T_Resultado_Estudio: lo que el panel «Estudio» guarda en un notebook (un resumen, un informe, un mapa mental o
una nota). Todo lo que se genera se guarda; quitarlo es una baja lógica (RN-01, RNF-10): la fila se conserva con
`CF_Fecha_eliminacion`.

Constraints:
    * FK: CN_Id_notebook -> T_Notebook (el notebook al que pertenece)
    * FK: CN_Id_usuario -> T_Usuario (el dueño; redundante con el del notebook, para filtrar sin unir)

Contenido por tipo (`CT_Tipo`):
    * resumen, informe: texto Markdown.
    * mapa_mental: JSON {"titulo": ..., "ramas": [...]}.
    * nota: JSON {"pregunta": ..., "respuesta": ...}.
`CT_Fuentes` es siempre un JSON con la lista de {"id", "nombre"} de las fuentes usadas, con el nombre que se mostraba cuando se
generó (en una nota, `id` es null: las citas del chat solo traen el nombre).

Ver también:
    * app.services.estudio_service: Lógica de negocio
    * app.repositories.resultado_estudio_repository: Acceso a datos
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Unicode, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class T_Resultado_Estudio(Base):
    """Resultado de estudio de un notebook (resumen, informe, mapa mental o nota)."""
    __tablename__ = "T_Resultado_Estudio"

    CN_Id_resultado: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    CN_Id_notebook: Mapped[int] = mapped_column(BigInteger, ForeignKey("T_Notebook.CN_Id_notebook"), nullable=False, index=True)
    CN_Id_usuario: Mapped[str] = mapped_column(String(20), ForeignKey("T_Usuario.CN_Id_usuario"), nullable=False)
    CT_Tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    CT_Titulo: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    CT_Contenido: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    CT_Fuentes: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    CF_Fecha_creacion: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    # Baja lógica (RF-14.124): NULL = visible; con fecha = quitado de la lista, la fila no se borra.
    CF_Fecha_eliminacion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
