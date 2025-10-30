"""
Configuración centralizada para el sistema RAG (Retrieval-Augmented Generation).

Centraliza umbrales de similitud y top-k para garantizar consistencia.
"""


class RAGConfig:
    """Configuración unificada del sistema RAG."""
    
    # ========================================
    # UMBRALES DE SIMILITUD
    # ========================================
    
    SIMILARITY_THRESHOLD_GENERAL = 0.22
    """Umbral para búsquedas generales en toda la base de datos."""
    
    SIMILARITY_THRESHOLD_EXPEDIENTE = 0.15
    """Umbral para búsquedas en expediente específico (más permisivo)."""
    
    SIMILARITY_THRESHOLD_FALLBACK = 0.12
    """Umbral mínimo para estrategia de fallback."""
    
    # ========================================
    # TOP-K (CANTIDAD DE RESULTADOS)
    # ========================================
    
    TOP_K_GENERAL = 15
    """Cantidad de chunks para búsquedas generales.
    
    Optimizado para gpt-oss:20b con LLM_NUM_CTX=32768:
    - Cada chunk: ~7,000 caracteres (~1,750 tokens)
    - TOP_K=10: ~70k caracteres (~17.5k tokens)
    - Deja espacio para: sistema (500t) + historial (1k-2k) + respuesta (4k)
    - Total usado: ~17.5k + 7.5k = ~25k tokens (dentro de 32k)
    - VENTAJA: Mantiene similarity scores más altos (mejor calidad)
    
    Alternativas según necesidad:
    - TOP_K=8: ~14k tokens - Más rápido, menos contexto
    - TOP_K=15: ~26k tokens - Máximo contexto, más lento
    """
    
    TOP_K_EXPEDIENTE = 20
    """Cantidad de chunks para expediente específico.
    
    Mayor que general porque:
    - Búsqueda enfocada en un solo expediente (menor espacio de búsqueda)
    - Usuario espera análisis más profundo de ese expediente específico
    - Documentos están más relacionados entre sí (mismo caso)
    
    Con LLM_NUM_CTX=32768:
    - TOP_K=20: ~35k tokens (factible, más exhaustivo)
    - Permite cubrir expediente completo
    """
    
    TOP_K_FALLBACK = 20
    """Cantidad aumentada para estrategia de fallback.
    
    Mismo valor que expediente para mantener consistencia.
    """
    
    # ========================================
    # FALLBACK
    # ========================================
    
    ENABLE_FALLBACK = True
    """Habilitar sistema de fallback multi-estrategia."""
    
    MIN_RESULTS_THRESHOLD = 3
    """Mínimo de resultados para considerar la búsqueda exitosa."""
    
    FALLBACK_THRESHOLD_MULTIPLIER = 0.7
    """Factor para relajar el umbral en fallback (70% del original)."""


# ========================================
# INSTANCIA GLOBAL
# ========================================

rag_config = RAGConfig()
