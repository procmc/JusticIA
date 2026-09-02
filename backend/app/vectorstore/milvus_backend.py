"""
Implementación de VectorStoreBackend usando Milvus (motor original del sistema).

Envuelve, sin modificarlas, las funciones existentes de app.vectorstore.vectorstore,
para no arriesgar el código que ya está en producción durante la migración a Qdrant.

Componentes:
    * MilvusBackend: clase que implementa VectorStoreBackend delegando a vectorstore.py

Tecnologías:
    * Milvus + LangChain (vía app.vectorstore.vectorstore, sin cambios)

Funcionalidades principales:
    * Los 7 métodos del contrato VectorStoreBackend, cada uno delegando 1:1
      a la función equivalente ya existente en vectorstore.py

Example:
    >>> from app.vectorstore.milvus_backend import MilvusBackend
    >>> backend = MilvusBackend()
    >>> results = await backend.search_by_text("¿Qué es la prescripción?")

Ver también:
    * app.vectorstore.base: Contrato VectorStoreBackend
    * app.vectorstore.vectorstore: Implementación real que se envuelve aquí
    * app.vectorstore.qdrant_backend: Backend alternativo (Fase 2)

Authors:
    Andrés Araya Agüero

Version:
    1.0.0 - Wrapper inicial (Fase 2, backend conmutable)
"""


from typing import List, Dict, Any, Optional
from langchain_core.documents import Document

from app.vectorstore.base import VectorStoreBackend
from app.vectorstore import vectorstore as milvus

class MilvusBackend(VectorStoreBackend):
    """Backend vectorial basado en Milvus (implementación actual)."""

    async def search_by_vector(
        self, query_vector: List[float], top_k: int = 20, score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        return await milvus.search_by_vector(query_vector, top_k, score_threshold)

    async def search_by_text(
        self,
        query_text: str,
        top_k: int = 20,
        score_threshold: float = 0.0,
        expediente_filter: Optional[str] = None,
        db=None,
    ) -> List[Dict[str, Any]]:
        return await milvus.search_by_text(query_text, top_k, score_threshold, expediente_filter, db)

    async def get_complete_document_by_chunks(self, document_id: int) -> List[Dict[str, Any]]:
        return await milvus.get_complete_document_by_chunks(document_id)

    async def get_expedient_summary(self, expedient_id: str) -> str:
        return await milvus.get_expedient_summary(expedient_id)

    async def search_similar_expedients(
        self, expedient_id: str, top_k: int = 20, score_threshold: float = 0.3, db=None
    ) -> List[Dict[str, Any]]:
        return await milvus.search_similar_expedients(expedient_id, top_k, score_threshold, db)

    async def add_documents(self, documents: List[Document]) -> List[str]:
        return await milvus.add_documents(documents)

    async def get_stats(self) -> Dict[str, Any]:
        return await milvus.get_stats()

    async def get_expedient_documents(self, expedient_id: str) -> List[Document]:
        return await milvus.get_expedient_documents(expedient_id)