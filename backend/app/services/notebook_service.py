"""
Servicio de Lógica de Negocio para Notebooks (NotebookServIA).

Colección de documentos genérica, propiedad de un usuario, que se
puede consultar por chat de forma acotada a solo esos documentos —
el equivalente local a un notebook de NotebookLM.

Por debajo reutiliza la misma tubería de ingesta/Qdrant que ya existe
para expedientes (ver T_Notebook.clave_interna): el notebook nunca
aparece como "expediente" en ningún texto visible al usuario ni en los
prompts, solo internamente como clave de agrupación de documentos.

Funciones principales:
    - crear_notebook: Crea un notebook nuevo para un usuario
    - listar_notebooks_usuario: Lista los notebooks de un usuario
    - obtener_notebook_de_usuario: Busca un notebook validando propiedad

Example:
    >>> service = NotebookService()
    >>> notebook = await service.crear_notebook(db, "Políticas MICITT", "119120969")
    >>> print(notebook.clave_interna)  # "NB-1"

Ver también:
    * app.repositories.notebook_repository: Acceso a datos
    * app.routes.notebooks: Endpoints REST
    * app.services.RAG.rag_chain_service: Consulta de chat acotada a notebook
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models.notebook import T_Notebook
from app.repositories.notebook_repository import NotebookRepository


class NotebookService:
    """Servicio de lógica de negocio para notebooks."""

    def __init__(self):
        self.notebook_repo = NotebookRepository()

    async def crear_notebook(self, db: Session, nombre: str, usuario_id: str) -> T_Notebook:
        """
        Crea un notebook nuevo, validado, para un usuario.

        Args:
            db: Sesión de base de datos.
            nombre: Nombre que el usuario le da al notebook.
            usuario_id: Cédula del usuario dueño.

        Returns:
            T_Notebook: Notebook creado.

        Raises:
            Exception: Si el nombre está vacío.
        """
        if not nombre or not nombre.strip():
            raise Exception("El nombre del notebook no puede estar vacío")

        return self.notebook_repo.crear(db, nombre.strip(), usuario_id)

    async def listar_notebooks_usuario(self, db: Session, usuario_id: str) -> List[T_Notebook]:
        """Lista los notebooks de un usuario, más reciente primero."""
        return self.notebook_repo.listar_por_usuario(db, usuario_id)

    async def obtener_notebook_de_usuario(
        self, db: Session, notebook_id: int, usuario_id: str
    ) -> Optional[T_Notebook]:
        """Busca un notebook por ID, validando que pertenezca al usuario."""
        notebook = self.notebook_repo.obtener_por_id(db, notebook_id)
        if notebook and notebook.CN_Id_usuario == usuario_id:
            return notebook
        return None
