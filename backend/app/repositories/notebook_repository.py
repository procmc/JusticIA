"""Repositorio de Acceso a Datos de Notebooks (NotebookServIA).

Implementa el patrón Repository para la tabla T_Notebook, siguiendo el
mismo patrón que ExpedienteRepository.

Operaciones principales:
    - crear: Crear un nuevo notebook
    - listar_por_usuario: Notebooks de un usuario, más reciente primero
    - obtener_por_id: Buscar un notebook por su ID
    - pertenece_a_usuario: Verificación de propiedad

Ver también:
    - app.db.models.notebook.T_Notebook: Modelo SQLAlchemy
    - app.services.notebook_service.NotebookService: Lógica de negocio
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from app.db.models.notebook import T_Notebook


class NotebookRepository:
    """Repositorio de acceso a datos para notebooks."""

    def crear(self, db: Session, nombre: str, usuario_id: str, auto_commit: bool = True) -> T_Notebook:
        """Crea un nuevo notebook."""
        try:
            notebook = T_Notebook(
                CT_Nombre=nombre,
                CN_Id_usuario=usuario_id,
                CF_Fecha_creacion=datetime.utcnow(),
            )
            db.add(notebook)

            if auto_commit:
                db.commit()
                db.refresh(notebook)
            else:
                db.flush()

            return notebook
        except Exception as e:
            if auto_commit:
                db.rollback()
            raise Exception(f"Error creando notebook: {str(e)}")

    def listar_por_usuario(self, db: Session, usuario_id: str) -> List[T_Notebook]:
        """Lista los notebooks de un usuario, más reciente primero."""
        stmt = (
            select(T_Notebook)
            .where(T_Notebook.CN_Id_usuario == usuario_id)
            .order_by(T_Notebook.CF_Fecha_creacion.desc())
        )
        result = db.execute(stmt)
        return list(result.scalars().all())

    def obtener_por_id(self, db: Session, notebook_id: int) -> Optional[T_Notebook]:
        """Busca un notebook por su ID."""
        stmt = select(T_Notebook).where(T_Notebook.CN_Id_notebook == notebook_id)
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def pertenece_a_usuario(self, db: Session, notebook_id: int, usuario_id: str) -> bool:
        """Valida que el notebook exista y pertenezca al usuario dado."""
        notebook = self.obtener_por_id(db, notebook_id)
        return notebook is not None and notebook.CN_Id_usuario == usuario_id
