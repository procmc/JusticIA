"""
Gestor de estrategias de búsqueda con fallback automático.

Implementa un sistema de fallback de 3 niveles para garantizar resultados relevantes
inclu cuando el threshold inicial es muy restrictivo.

Estrategias de fallback:
    1. Búsqueda normal: threshold y top_k configurados
    2. Threshold relajado: threshold * multiplier (ej: 0.30 → 0.15)
    3. Threshold mínimo: threshold mínimo global con top_k aumentado

Configuración:
    * ENABLE_FALLBACK: Habilitar/deshabilitar fallback (rag_config)
    * FALLBACK_THRESHOLD_MULTIPLIER: Factor de relajación (0.5 = mitad)
    * SIMILARITY_THRESHOLD_FALLBACK: Threshold mínimo absoluto (0.10)
    * TOP_K_FALLBACK: Número de docs en fallback final (30)
    * MIN_RESULTS_THRESHOLD: Mínimo de resultados aceptables (3)

Flujo de fallback:
    1. Búsqueda con threshold original
    2. Si resultados < MIN_RESULTS_THRESHOLD → relajar threshold
    3. Si aún insuficiente → buscar con threshold mínimo
    4. Retornar los mejores resultados disponibles

Uso en RAG:
    * Evita respuestas vacías por threshold muy estricto
    * Prioriza precisión (threshold alto) sobre recall (threshold bajo)
    * Log completo para debugging de relevancia

Example:
    >>> from app.services.rag.search_strategies import search_manager
    >>> 
    >>> # Búsqueda con fallback automático
    >>> results = await search_manager.search_with_fallback(
    ...     query_text="¿Qué es la prescripción?",
    ...     top_k=15,
    ...     threshold=0.30  # Estricto inicialmente
    ... )
    >>> # Si falla: intenta threshold 0.15, luego 0.10 con top_k=30

Note:
    * Fallback SOLO se activa si resultados < MIN_RESULTS_THRESHOLD
    * Cada fallback se registra en logs para análisis
    * Estadísticas: total_searches, fallback_attempts
    * El fallback NO afecta búsquedas de expedientes específicos

Ver también:
    * app.config.rag_config: Configuración de fallback
    * app.vectorstore.vectorstore: Búsqueda en Milvus
    * app.services.rag.retriever: Usa search_manager

Authors:
    JusticIA Team

Version:
    1.0.0 - Sistema de fallback de 3 niveles
"""
import logging
from typing import List, Dict, Any, Optional

from app.config.rag_config import rag_config
from app.vectorstore.vectorstore import search_by_text

logger = logging.getLogger(__name__)

class SearchStrategyManager:
    """
    Gestor de estrategias de búsqueda con fallback.
    
    Implementa 3 niveles de fallback para garantizar resultados.
    
    Attributes:
        config: Configuración RAG global.
        fallback_attempts (int): Contador de fallbacks ejecutados.
        total_searches (int): Contador total de búsquedas.
    """
    
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
        min_results: Optional[int] = None,
        db = None  # Sesión de BD para filtrar por estado
    ) -> List[Dict[str, Any]]:

        self.total_searches += 1
        
        if min_results is None:
            min_results = self.config.MIN_RESULTS_THRESHOLD
        
        # Estrategia 1: Búsqueda normal
        logger.info(f"Búsqueda con threshold={threshold:.2f}, top_k={top_k}")
        results = await search_by_text(query_text, top_k, threshold, expediente_filter, db)
        
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
        
        results = await search_by_text(query_text, top_k, relaxed_threshold, expediente_filter, db)
        
        if len(results) >= min_results:
            logger.info(f"Fallback exitoso: {len(results)} resultados")
            return results
        
        # Estrategia 3: Umbral mínimo con más resultados
        logger.info(f"Fallback final: umbral mínimo {self.config.SIMILARITY_THRESHOLD_FALLBACK}")
        results = await search_by_text(
            query_text,
            self.config.TOP_K_FALLBACK,
            self.config.SIMILARITY_THRESHOLD_FALLBACK,
            expediente_filter,
            db
        )
        
        if len(results) > 0:
            logger.info(f"Fallback final encontró: {len(results)} resultados")
            return results[:top_k]
        
        if len(results) == 0:
            logger.warning(f"Sin resultados después de todas las estrategias")
        
        return results


# Instancia global
search_manager = SearchStrategyManager()
