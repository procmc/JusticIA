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
    """Umbral para búsquedas generales en toda la base de datos.
    
    Optimizado para BGE-M3 legal español:
    - Rango efectivo del modelo: [0.15, 0.50] para contenido relevante
    - 0.22 captura variaciones terminológicas legales sin incluir ruido
    - Balance entre recall (encontrar contenido) y precision (calidad)
    
    Demasiado alto (>0.30): Pierde documentos relevantes con vocabulario diferente
    Demasiado bajo (<0.18): Incluye demasiado ruido y contexto irrelevante
    """
    
    SIMILARITY_THRESHOLD_EXPEDIENTE = 0.18
    """Umbral para búsquedas en expediente específico.
    
    SUBIDO de 0.15 → 0.18 para mejor calidad:
    - Aunque sea del mismo expediente, queremos los chunks MÁS relevantes
    - 0.15 era demasiado permisivo (incluía texto tangencial)
    - 0.18 enfoca en las partes del expediente que realmente responden la pregunta
    
    Ventaja:
    - Mejor precisión: Respuestas más enfocadas
    - Menos ruido: Evita chunks poco útiles del expediente
    - Con TOP_K=10 + umbral 0.18 = contexto relevante y manejable
    
    Más permisivo que general (0.18 < 0.22) porque el expediente ya está acotado.
    """
    
    SIMILARITY_THRESHOLD_FALLBACK = 0.12
    """Umbral mínimo para estrategia de fallback.
    
    Último recurso cuando búsqueda principal no encuentra resultados:
    - Muy permisivo intencionalmente (0.12 = ~50% de similitud)
    - Previene respuestas "no se encontró información"
    - Mejor dar contexto amplio que ninguna respuesta
    
    Solo se activa si la búsqueda normal falla (< MIN_RESULTS_THRESHOLD).
    """
    
    # ========================================
    # TOP-K (CANTIDAD DE RESULTADOS)
    # ========================================
    
    TOP_K_GENERAL = 15
    """Cantidad de chunks para búsquedas generales.
    
    Optimizado para gpt-oss:20b con LLM_NUM_CTX=32768:
    - Cada chunk: ~7,000 caracteres (~1,750 tokens promedio)
    - TOP_K=15: ~26.2k tokens de chunks
    - + Sistema + historial + respuesta = ~32.5k tokens total
    
    SEGURO para búsquedas generales porque:
    - Los chunks provienen de múltiples expedientes diferentes
    - Mayor diversidad = chunks más cortos en promedio
    - Menor probabilidad de chunks excepcionalmente largos
    
    Proporciona buen balance entre contexto amplio y estabilidad.
    """
    
    TOP_K_EXPEDIENTE = 10
    """Cantidad de chunks para expediente específico.
    
    Optimizado para MÁXIMA ESTABILIDAD con documentos extensos (LLM_NUM_CTX=32768):
    - TOP_K=10: ~17.5k tokens de chunks (promedio)
    - Peor caso (chunks muy largos): ~25k tokens
    - + Sistema + historial + respuesta = ~29k tokens total
    - **Margen de seguridad: 3-7k tokens**
    
    REDUCIDO a 10 (vs 12 o 15) para GARANTIZAR estabilidad cuando:
    - Expediente tiene múltiples documentos de 50-100+ páginas
    - Todos los chunks del expediente son excepcionalmente largos
    - Historial conversacional es extenso (muchas preguntas previas)
    
    BALANCE ÓPTIMO:
    - Suficiente contexto para análisis profundo del expediente
    - Margen amplio previene errores "reduce tokens" incluso en casos extremos
    - Enfoque en los 10 chunks MÁS relevantes = mejor calidad de respuesta
    
    NOTA: 10 chunks de un expediente extenso ya contiene información muy valiosa.
    La calidad de la respuesta depende más de la RELEVANCIA que de la CANTIDAD.
    """
    
    TOP_K_FALLBACK = 10
    """Cantidad para estrategia de fallback.
    
    Mismo valor que expediente para mantener consistencia y máxima seguridad.
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
    # HISTORIAL DE CONVERSACIÓN
    # ========================================
    
    CHAT_HISTORY_LIMIT = 20
    """Límite de mensajes del historial enviados al LLM.
    
    Controla cuántos mensajes del historial se envían al modelo de lenguaje:
    - Redis guarda TODO el historial sin límites (persistencia completa)
    - El frontend puede ver todo el historial
    - Solo el LLM recibe los últimos N mensajes para optimizar contexto
    
    Valor recomendado: 20 mensajes (10 intercambios usuario-asistente)
    - Suficiente para mantener contexto conversacional relevante
    - Previene exceder límites de tokens del modelo
    - Permite conversaciones largas sin perder rendimiento
    
    Ajustar según necesidades:
    - Más alto (30-40): Conversaciones muy largas con contexto extenso
    - Más bajo (10-15): Optimizar velocidad y reducir uso de tokens
    """


# ========================================
# INSTANCIA GLOBAL
# ========================================

rag_config = RAGConfig()
