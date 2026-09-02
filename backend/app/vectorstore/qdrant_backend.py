"""
Implementación de VectorStoreBackend usando Qdrant.

Arquitectura dual, igual que Milvus:
    * QdrantClient: administración (colección, índices)
    * QdrantVectorStore (LangChain): búsquedas y almacenamiento con embeddings automáticos

A diferencia de Milvus, Qdrant no usa un schema fijo de campos: toda la metadata
(numero_expediente, id_documento, indice_chunk, etc.) vive en el "payload" (JSON)
de cada punto, sin necesidad de declarar cada campo por adelantado.

Componentes:
    * QdrantBackend: clase que implementa VectorStoreBackend con la API de Qdrant
    * _get_client / _get_langchain_vectorstore: clientes singleton (lazy loading)
    * _payload_to_result: formatea el payload de Qdrant al formato común del sistema

Tecnologías:
    * qdrant-client: administración y búsquedas de bajo nivel (query_points, scroll)
    * langchain-qdrant: integración con la interfaz Embeddings de LangChain
    * multilingual-e5-large: modelo de embeddings (vía LangChainEmbeddingsAdapter)

Funcionalidades principales:
    * Los 7 métodos del contrato VectorStoreBackend, reimplementados con
      Filter/FieldCondition/MatchValue de Qdrant en vez del filtro de Milvus
    * Creación automática de la colección (VectorParams con distancia coseno)
    * Reutiliza _filter_by_processed_status de vectorstore.py (mismo filtro
      de estado "Procesado" que usa Milvus, sin duplicar esa lógica)

Example:
    >>> from app.vectorstore.qdrant_backend import QdrantBackend
    >>> backend = QdrantBackend()
    >>> results = await backend.search_by_text("¿Qué es la prescripción?")

Ver también:
    * app.vectorstore.base: Contrato VectorStoreBackend
    * app.vectorstore.milvus_backend: Backend alternativo (motor original)
    * app.vectorstore.__init__: Selector get_vectorstore_backend()
    * Registro_Indicaciones_2026/16_Investigacion_Modelo_Embeddings.md: justificación del modelo

Authors:
    Andrés Araya Agüero

Version:
    1.0.0 - Implementación inicial, probada end-to-end)
"""

from typing import List, Dict, Any, Optional
import logging

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, Filter, FieldCondition, MatchValue
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document

from app.config.config import QDRANT_URL, QDRANT_COLLECTION_NAME
from app.vectorstore.schema import DIM
from app.vectorstore.base import VectorStoreBackend
from app.vectorstore.vectorstore import _filter_by_processed_status

logger = logging.getLogger(__name__)

_qdrant_client = None
_langchain_vectorstore = None


def _get_client() -> QdrantClient:
    """Cliente QdrantClient singleton. Crea la colección si no existe."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(url=QDRANT_URL)

        if not _qdrant_client.collection_exists(QDRANT_COLLECTION_NAME):
            logger.info(f"Creando colección Qdrant: {QDRANT_COLLECTION_NAME}")
            _qdrant_client.create_collection(
                collection_name=QDRANT_COLLECTION_NAME,
                vectors_config=VectorParams(size=DIM, distance=Distance.COSINE),
            )
    return _qdrant_client


async def _get_langchain_vectorstore() -> QdrantVectorStore:
    """VectorStore LangChain para búsquedas y almacenamiento con embeddings automáticos."""
    global _langchain_vectorstore
    if _langchain_vectorstore is None:
        client = _get_client()
        from app.embeddings.langchain_adapter import LangChainEmbeddingsAdapter

        _langchain_vectorstore = QdrantVectorStore(
            client=client,
            collection_name=QDRANT_COLLECTION_NAME,
            embedding=LangChainEmbeddingsAdapter(),
        )
    return _langchain_vectorstore


def _payload_to_result(payload: Dict[str, Any], score: float, point_id) -> Dict[str, Any]:
    """Formatea un payload de Qdrant al mismo formato que usa el resto del sistema."""
    return {
        "id": payload.get("id_chunk", str(point_id)),
        "expedient_id": payload.get("numero_expediente", ""),
        "document_name": payload.get("nombre_archivo", ""),
        "content_preview": (payload.get("texto", "") or "")[:500],
        "similarity_score": score,
        "documento_id": payload.get("id_documento"),
        "metadata": {
            "indice_chunk": payload.get("indice_chunk", 0),
            "pagina_inicio": payload.get("pagina_inicio", 1),
            "pagina_fin": payload.get("pagina_fin", 1),
            "tipo_documento": payload.get("tipo_documento", ""),
            "ruta_archivo": (payload.get("meta") or {}).get("ruta_archivo", ""),
        },
    }


class QdrantBackend(VectorStoreBackend):
    """Backend vectorial basado en Qdrant."""

    async def search_by_vector(
        self, query_vector: List[float], top_k: int = 20, score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        client = _get_client()
        results = client.query_points(
            collection_name=QDRANT_COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        ).points

        return [
            _payload_to_result(hit.payload, hit.score, hit.id)
            for hit in results
            if hit.score >= score_threshold
        ]

    async def add_documents(self, documents: List[Document]) -> List[str]:
        vectorstore = await _get_langchain_vectorstore()
        return vectorstore.add_documents(documents)

    async def get_stats(self) -> Dict[str, Any]:
        client = _get_client()
        info = client.get_collection(QDRANT_COLLECTION_NAME)
        return {
            "collection_name": QDRANT_COLLECTION_NAME,
            "stats": {"points_count": info.points_count},
            "langchain_enabled": True,
        }

    async def search_by_text(
        self,
        query_text: str,
        top_k: int = 20,
        score_threshold: float = 0.0,
        expediente_filter: Optional[str] = None,
        db=None,
    ) -> List[Dict[str, Any]]:
        vectorstore = await _get_langchain_vectorstore()

        qdrant_filter = None
        if expediente_filter:
            qdrant_filter = Filter(
                must=[FieldCondition(key="numero_expediente", match=MatchValue(value=expediente_filter))]
            )

        results_with_scores = vectorstore.similarity_search_with_score(
            query=query_text, k=top_k, filter=qdrant_filter
        )

        formatted_results = []
        for doc, score in results_with_scores:
            if score >= score_threshold:
                metadata = doc.metadata
                formatted_results.append({
                    "id": metadata.get("id_chunk"),
                    "expedient_id": metadata.get("numero_expediente"),
                    "document_name": metadata.get("nombre_archivo"),
                    "content_preview": doc.page_content,
                    "similarity_score": score,
                    "metadata": metadata,
                    "documento_id": metadata.get("id_documento"),
                })

        return _filter_by_processed_status(formatted_results, db)

    async def get_complete_document_by_chunks(self, document_id: int) -> List[Dict[str, Any]]:
        client = _get_client()
        points, _ = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="id_documento", match=MatchValue(value=document_id))]
            ),
            limit=1000,
            with_payload=True,
        )
        chunks = [p.payload for p in points]
        return sorted(chunks, key=lambda x: x.get("indice_chunk", 0))

    async def get_expedient_summary(self, expedient_id: str) -> str:
        client = _get_client()
        points, _ = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="numero_expediente", match=MatchValue(value=expedient_id))]
            ),
            limit=1000,
            with_payload=True,
        )

        if not points:
            return f"Expediente {expedient_id} sin contenido"

        texto_parts = [expedient_id]
        for p in points:
            texto = (p.payload.get("texto", "") or "").strip()
            if texto:
                texto_parts.append(texto[:300])

        return " ".join(texto_parts)

    async def search_similar_expedients(
        self, expedient_id: str, top_k: int = 20, score_threshold: float = 0.3, db=None
    ) -> List[Dict[str, Any]]:
        client = _get_client()

        ref_points, _ = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="numero_expediente", match=MatchValue(value=expedient_id))]
            ),
            limit=100,
            with_payload=True,
            with_vectors=True,
        )

        if not ref_points:
            return []

        all_results: Dict[str, Dict[str, Any]] = {}

        for ref_point in ref_points:
            vector = ref_point.vector
            if not vector:
                continue

            hits = client.query_points(
                collection_name=QDRANT_COLLECTION_NAME,
                query=vector,
                limit=top_k * 2,
                with_payload=True,
            ).points

            for hit in hits:
                result_expedient_id = hit.payload.get("numero_expediente", "")
                if result_expedient_id == expedient_id or not result_expedient_id:
                    continue
                if hit.score < score_threshold:
                    continue

                doc_name = hit.payload.get("nombre_archivo", "")
                bucket = all_results.setdefault(result_expedient_id, {"docs": []})
                if not any(d.get("document_name") == doc_name for d in bucket["docs"]):
                    bucket["docs"].append(_payload_to_result(hit.payload, hit.score, hit.id))

        final_results = [doc for bucket in all_results.values() for doc in bucket["docs"]]
        final_results.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
        final_results = _filter_by_processed_status(final_results, db)
        return final_results[:top_k]

    async def get_expedient_documents(self, expedient_id: str) -> List[Document]:
        client = _get_client()
        points, _ = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="numero_expediente", match=MatchValue(value=expedient_id))]
            ),
            limit=1000,
            with_payload=True,
        )

        sorted_points = sorted(points, key=lambda p: p.payload.get("indice_chunk", 0))

        langchain_docs = []
        for p in sorted_points:
            content = p.payload.get("texto", "")
            if content and content.strip():
                metadata = {
                    "numero_expediente": p.payload.get("numero_expediente", expedient_id),
                    "id_expediente": p.payload.get("numero_expediente", expedient_id),
                    "archivo": p.payload.get("nombre_archivo", ""),
                    "chunk_id": p.payload.get("id_chunk", ""),
                    "indice_chunk": p.payload.get("indice_chunk", 0),
                    "tipo_documento": p.payload.get("tipo_documento", ""),
                    "ruta_archivo": (p.payload.get("meta") or {}).get("ruta_archivo", ""),
                }
                langchain_docs.append(Document(page_content=content, metadata=metadata))

        return langchain_docs