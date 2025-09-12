"""
Servicio de búsqueda vectorial en Milvus.

Este módulo maneja todas las operaciones de búsqueda vectorial en la base de datos Milvus,
incluyendo la búsqueda por similitud de embeddings y la recuperación de metadatos.
"""

import logging
from typing import List, Optional, Dict, Any
from app.vectorstore.vectorstore import get_vectorstore
from app.config.config import COLLECTION_NAME

logger = logging.getLogger(__name__)


class MilvusSearchService:
    """Servicio para búsquedas vectoriales en Milvus."""
    
    def __init__(self):
        self.client = None
        self.collection_name = COLLECTION_NAME
    
    async def _get_client(self):
        """Obtiene el cliente de Milvus de forma lazy."""
        if self.client is None:
            self.client = await get_vectorstore()
        return self.client
    
    async def search_by_vector(
        self,
        query_vector: List[float],
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca documentos similares usando un vector de consulta.
        
        Args:
            query_vector: Vector de embedding para la búsqueda
            top_k: Número máximo de resultados a retornar
            filters: Filtros opcionales para la búsqueda
            
        Returns:
            Lista de documentos similares con sus metadatos y scores
        """
        try:
            client = await self._get_client()
            
            # Construir filtros de expresión si se proporcionan
            expr = None
            if filters:
                expr_parts = []
                for key, value in filters.items():
                    if isinstance(value, str):
                        expr_parts.append(f'{key} == "{value}"')
                    else:
                        expr_parts.append(f'{key} == {value}')
                expr = " and ".join(expr_parts) if expr_parts else None
            
            # Preparar parámetros de búsqueda
            search_params = {
                "metric_type": "COSINE",
                "params": {"ef": 100}
            }
            
            search_kwargs = {
                "collection_name": self.collection_name,
                "data": [query_vector],
                "anns_field": "embedding",
                "search_params": search_params,
                "limit": top_k,
                "output_fields": ["id_expediente", "nombre_archivo", "texto", "numero_expediente"]
            }
            
            if expr:
                search_kwargs["expr"] = expr
            
            # Realizar búsqueda
            results = client.search(**search_kwargs)
            
            if not results or len(results) == 0:
                logger.info("No se obtuvieron resultados de la búsqueda")
                return []
            
            hits = results[0]
            if not hits or len(hits) == 0:
                logger.info("No hay hits en los resultados")
                return []
            
            # Procesar resultados
            similar_docs = []
            for hit in hits:
                try:
                    if hasattr(hit, 'entity') and hasattr(hit, 'distance'):
                        entity_data = getattr(hit, 'entity', {})
                        distance = getattr(hit, 'distance', 1.0)
                        
                        # Convertir distance a similarity score (1 - distance para COSINE)
                        similarity_score = max(0.0, 1.0 - distance)
                        
                        similar_docs.append({
                            "id": getattr(hit, 'id', None),
                            "expedient_id": entity_data.get("numero_expediente") or entity_data.get("id_expediente"),
                            "document_name": entity_data.get("nombre_archivo"),
                            "content_preview": entity_data.get("texto", "")[:500] if entity_data.get("texto") else "",
                            "similarity_score": similarity_score
                        })
                except Exception as e:
                    logger.warning(f"Error procesando hit individual: {e}")
                    continue
            
            logger.info(f"Encontrados {len(similar_docs)} documentos similares")
            return similar_docs
            
        except Exception as e:
            logger.error(f"Error en búsqueda vectorial: {e}")
            raise
    
    async def search_by_expedient_vector(
        self,
        expedient_vector: List[float],
        exclude_expedient_id: Optional[str] = None,
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Busca expedientes similares usando el vector del expediente.
        
        Args:
            expedient_vector: Vector del expediente de consulta
            exclude_expedient_id: ID del expediente a excluir de los resultados
            top_k: Número máximo de resultados
            
        Returns:
            Lista de documentos de expedientes similares
        """
        filters = {}
        if exclude_expedient_id:
            # Nota: Milvus no soporta != directamente, 
            # esto se manejará en el post-procesamiento
            pass
        
        results = await self.search_by_vector(
            query_vector=expedient_vector,
            top_k=top_k * 2,  # Obtener más para filtrar después
            filters=filters
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
        
        return filtered_results
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la colección.
        
        Returns:
            Diccionario con estadísticas de la colección
        """
        try:
            client = await self._get_client()
            stats = client.get_collection_stats(collection_name=self.collection_name)
            return stats if isinstance(stats, dict) else {}
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de la colección: {e}")
            return {}
    
    def disconnect(self):
        """Cierra la conexión con Milvus."""
        # El cliente Milvus maneja las conexiones automáticamente
        # No necesitamos desconectar manualmente
        self.client = None
        logger.info("Cliente Milvus limpiado")
