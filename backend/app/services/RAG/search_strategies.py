import logging
from typing import List, Dict, Any, Optional

from app.config.rag_config import rag_config
from app.vectorstore.vectorstore import search_by_text

logger = logging.getLogger(__name__)

class SearchStrategyManager:
    
    def __init__(self):
        self.config = rag_config
        self.fallback_attempts = 0
        self.total_searches = 0
    
    async def search_with_fallback(
        self,
        query_text: str,
        top_k: int,
        threshold: float,
        expediente_filter: Optional[str] = None,
        min_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:

        self.total_searches += 1
        
        if min_results is None:
            min_results = self.config.MIN_RESULTS_THRESHOLD
        
        # Estrategia 1: Búsqueda normal
        logger.info(f"Búsqueda con threshold={threshold:.2f}, top_k={top_k}")
        results = await search_by_text(query_text, top_k, threshold, expediente_filter)
        
        if len(results) >= min_results:
            logger.info(f"Búsqueda exitosa: {len(results)} resultados")
            return results
        
        if not self.config.ENABLE_FALLBACK:
            logger.warning(f"Fallback deshabilitado. Resultados: {len(results)}")
            return results
        
        # Estrategia 2: Relajar umbral
        self.fallback_attempts += 1
        relaxed_threshold = threshold * self.config.FALLBACK_THRESHOLD_MULTIPLIER
        logger.info(f"Fallback: relajando umbral a {relaxed_threshold:.2f}")
        
        results = await search_by_text(query_text, top_k, relaxed_threshold, expediente_filter)
        
        if len(results) >= min_results:
            logger.info(f"Fallback exitoso: {len(results)} resultados")
            return results
        
        # Estrategia 3: Umbral mínimo con más resultados
        logger.info(f"Fallback final: umbral mínimo {self.config.SIMILARITY_THRESHOLD_FALLBACK}")
        results = await search_by_text(
            query_text,
            self.config.TOP_K_FALLBACK,
            self.config.SIMILARITY_THRESHOLD_FALLBACK,
            expediente_filter
        )
        
        if len(results) > 0:
            logger.info(f"Fallback final encontró: {len(results)} resultados")
            return results[:top_k]
        
        if len(results) == 0:
            logger.warning(f"Sin resultados después de todas las estrategias")
        
        return results


# Instancia global
search_manager = SearchStrategyManager()
