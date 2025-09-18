"""
Servicio principal de búsqueda de similares unificado con vectorstore.
"""

import logging
from typing import List, Dict, Any
from app.schemas.similarity_schemas import (
    SimilaritySearchRequest,
    RespuestaBusquedaSimilitud,
)

from .documentos.documento_service import DocumentoService
from .documentos.documento_retrieval_service import DocumentoRetrievalService
from app.embeddings.embeddings import get_embeddings

logger = logging.getLogger(__name__)


class SimilarityService:
    """Servicio principal para búsqueda de casos legales similares unificado."""

    def __init__(self):
        self.documento_service = DocumentoService()
        self.documento_retrieval_service = DocumentoRetrievalService()
        self.embeddings_service = None

    async def _get_embeddings_service(self):
        if self.embeddings_service is None:
            self.embeddings_service = await get_embeddings()
        return self.embeddings_service

    async def search_similar_cases(
        self, request: SimilaritySearchRequest
    ) -> RespuestaBusquedaSimilitud:
        """Busca casos legales similares según el modo especificado."""
        try:
            if request.modo_busqueda == "descripcion":
                casos_similares = await self._buscar_por_descripcion(request)
                criterio_busqueda = request.texto_consulta
            else:
                casos_similares = await self._buscar_por_expediente(request)
                criterio_busqueda = request.numero_expediente

            return RespuestaBusquedaSimilitud(
                criterio_busqueda=criterio_busqueda,
                modo_busqueda=request.modo_busqueda,
                total_resultados=len(casos_similares),
                casos_similares=casos_similares,
            )

        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            raise

    async def _buscar_por_descripcion(
        self, request: SimilaritySearchRequest
    ) -> List[Dict[str, Any]]:
        """Busca casos similares por descripción usando vectorstore unificado."""
        if not request.texto_consulta:
            raise ValueError("texto_consulta es requerido")

        embeddings_service = await self._get_embeddings_service()
        query_vector = await embeddings_service.aembed_query(request.texto_consulta)

        # Usar vectorstore unificado
        from app.vectorstore.vectorstore import search_by_vector

        similar_docs = await search_by_vector(
            query_vector=query_vector,
            top_k=request.limite or 30,
            score_threshold=request.umbral_similitud,
        )

        return await self.documento_retrieval_service.procesar_casos_similares(
            similar_docs
        )

    async def _buscar_por_expediente(
        self, request: SimilaritySearchRequest
    ) -> List[Dict[str, Any]]:
        """Busca casos similares por expediente específico usando búsqueda híbrida."""
        expedient_id = request.numero_expediente
        if not expedient_id:
            raise ValueError("numero_expediente es requerido")

        from app.vectorstore.vectorstore import search_similar_expedients

        similar_docs = await search_similar_expedients(
            expedient_id=expedient_id,
            top_k=request.limite or 30,
            score_threshold=request.umbral_similitud,
        )

        return await self.documento_retrieval_service.procesar_casos_similares(
            similar_docs
        )
