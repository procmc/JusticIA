"""
Interdaz abtracta del backend de base de datos vectorial

Permite intercambiar el motor vectorial (Malvius, Qdrant, ...) sin cambiar
el resto del sistema (embeddings, RAG, endpoints). Todo backend concreto
debe heredar de VesctorStoreBase e implementar los métodos.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document

class VectorStoreBackend(ABC):
    """"
    Contrato que debe cumplir cualquier backend vectorial (Milvus, Qdrant, ...).
    """

    @abstractmethod
    async def search_by_vector(
        self, query_vector: List[float], top_k: int = 20, score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """"
        Búsqueda por vector precomputado
        """

    @abstractmethod
    async def search_by_text(
        self,
        query_text: str,
        top_k: int = 20,
        score_threshold: float = 0.0,
        expediente_filter: Optional[str] = None,
        db=None,
    ) -> List[Dict[str, Any]]:
        """Búsqueda semántica por texto, con filtro opcional por expediente."""

    @abstractmethod
    async def get_complete_document_by_chunks(self, document_id: int) -> List[Dict[str, Any]]:
        """Todos los chunks de un documento, ordenados."""

    @abstractmethod
    async def get_expedient_summary(self, expedient_id: str) -> str:
        """Resumen combinado del contenido de un expediente."""

    @abstractmethod
    async def search_similar_expedients(
        self, expedient_id: str, top_k: int = 20, score_threshold: float = 0.3, db=None
    ) -> List[Dict[str, Any]]:
        """Expedientes similares al expediente de referencia."""

    @abstractmethod
    async def add_documents(self, documents: List[Document]) -> List[str]:
        """Almacena documentos con embeddings automáticos."""

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Estadísticas de la colección."""

    @abstractmethod
    async def get_expedient_documents(self, expedient_id: str) -> List[Document]:
        """Todos los documentos LangChain de un expediente."""