# Servicio de búsqueda vectorial migrado a vectorstore central

import logging
from typing import List, Optional, Dict, Any
from app.vectorstore.vectorstore import search_by_vector, search_by_text

logger = logging.getLogger(__name__)


class MilvusSearchService:
    def __init__(self):
        logger.info("MilvusSearchService inicializado con vectorstore central")
    
    async def search_by_vector(
        self,
        query_vector: List[float],
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        try:
            results = await search_by_vector(
                query_vector=query_vector,
                top_k=top_k,
                score_threshold=0.0
            )
            
            adapted_results = []
            for result in results:
                adapted_results.append({
                    "id": result.get("id"),
                    "expedient_id": result.get("expedient_id"),
                    "document_name": result.get("document_name"),
                    "content_preview": result.get("content_preview", ""),
                    "similarity_score": result.get("similarity_score", 0.0),
                    "metadata": result.get("metadata", {})
                })
            
            logger.info(f"Búsqueda vectorial central: {len(adapted_results)} resultados")
            return adapted_results
            
        except Exception as e:
            logger.error(f"Error en búsqueda vectorial central: {e}")
            raise
    
    async def search_by_expedient_vector(
        self,
        expedient_vector: List[float],
        exclude_expedient_id: Optional[str] = None,
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Busca expedientes similares excluyendo un expediente específico.
        
        Args:
            expedient_vector: Vector del expediente de consulta
            exclude_expedient_id: ID del expediente a excluir de los resultados
            top_k: Número máximo de resultados
            
        Returns:
            Lista de documentos de expedientes similares
        """
        try:
            # Buscar más resultados para filtrar después
            results = await self.search_by_vector(
                query_vector=expedient_vector,
                top_k=top_k * 2  # Obtener más para filtrar después
            )
            
            # Filtrar expediente excluido y agrupar por expediente
            filtered_results = []
            seen_expedients = set()
            
            for doc in results:
                expedient_id = doc.get("expedient_id")
                if expedient_id == exclude_expedient_id:
                    continue
                if expedient_id not in seen_expedients:
                    seen_expedients.add(expedient_id)
                    filtered_results.append(doc)
                    if len(filtered_results) >= top_k:
                        break
            
            logger.info(f"Búsqueda con exclusión: {len(filtered_results)} expedientes únicos")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error en búsqueda por expediente: {e}")
            raise
    
    async def search_by_text(
        self,
        query_text: str,
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        try:
            results = await search_by_text(
                query_text=query_text,
                top_k=top_k,
                score_threshold=0.0
            )
            
            adapted_results = []
            for result in results:
                adapted_results.append({
                    "id": result.get("id"),
                    "expedient_id": result.get("expedient_id"),
                    "document_name": result.get("document_name"),
                    "content_preview": result.get("content_preview", ""),
                    "similarity_score": result.get("similarity_score", 0.0),
                    "metadata": result.get("metadata", {})
                })
            
            logger.info(f"Búsqueda semántica central: {len(adapted_results)} resultados")
            return adapted_results
            
        except Exception as e:
            logger.error(f"Error en búsqueda semántica central: {e}")
            raise
