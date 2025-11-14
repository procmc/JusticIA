"""
Configuración Centralizada del Sistema RAG (Retrieval-Augmented Generation).

Este módulo define parámetros críticos del sistema RAG incluyendo umbrales de similitud,
cantidades de documentos recuperados (top-k), y configuración de fallback.

Propósito:
    - Centralizar configuración RAG para consistencia en todo el sistema
    - Documentar valores optimizados y el razonamiento detrás de cada uno
    - Facilitar ajuste fino sin modificar código de múltiples archivos
    - Prevenir context overflow en el LLM (gpt-oss:20b con 32k tokens)

Parámetros principales:
    1. **Umbrales de similitud**: Filtran chunks por relevancia semántica
    2. **Top-K**: Cantidad de chunks recuperados del vectorstore
    3. **Fallback**: Estrategia de recuperación cuando búsqueda inicial falla
    4. **Historial**: Límite de mensajes enviados al LLM

Arquitectura RAG:
    ```
    Usuario → Query → Embedding
                ↓
    Milvus Vectorstore (búsqueda vectorial)
                ↓
    Filtrado (umbral) → Top-K chunks
                ↓
    Reformulación (si hay historial) → LLM
                ↓
    Generación de respuesta
    ```

Optimización para gpt-oss:20b:
    - Context window: 32,768 tokens (LLM_NUM_CTX)
    - Presupuesto de tokens:
        * Sistema + instrucciones: ~2k tokens
        * Historial conversacional: ~3-5k tokens
        * Chunks recuperados: 15-25k tokens
        * Respuesta generada: ~2-4k tokens
        * **Total**: ~28-32k tokens (margen seguro)

Historial del ajuste de parámetros:
    **Umbrales:**
        - v1: General 0.22, Expediente 0.15 → Muchos falsos negativos
        - v2: General 0.20, Expediente 0.18 → Balance mejorado
        - Fallback: 0.12 → 0.25 → Eliminó falsos positivos fuera de dominio
    
    **Top-K:**
        - v1: General 20, Expediente 15 → Context overflow en casos extremos
        - v2: General 15, Expediente 10 → Estable con documentos extensos

Estrategia de fallback:
    Si búsqueda inicial retorna < MIN_RESULTS_THRESHOLD resultados:
        1. Relajar umbral (70% del original)
        2. Buscar nuevamente con umbral más permisivo
        3. Garantizar umbral mínimo de calidad (0.25)

Example:
    ```python
    from app.config.rag_config import rag_config
    
    # Usar configuración en búsqueda
    threshold = rag_config.SIMILARITY_THRESHOLD_GENERAL  # 0.20
    top_k = rag_config.TOP_K_GENERAL  # 15
    
    # Configuración para expediente específico
    threshold = rag_config.SIMILARITY_THRESHOLD_EXPEDIENTE  # 0.18
    top_k = rag_config.TOP_K_EXPEDIENTE  # 10
    
    # Límite de historial
    historial_limitado = mensajes[-rag_config.CHAT_HISTORY_LIMIT:]
    ```

Note:
    Modificar estos valores afecta directamente:
        - Calidad de respuestas (relevancia vs exhaustividad)
        - Estabilidad del sistema (overflow de contexto)
        - Velocidad de respuesta (más chunks = más procesamiento)
        - Costos de inferencia (más tokens = más costo)

See Also:
    - app.services.rag_service: Usa esta configuración para consultas
    - app.services.similarity_service: Usa umbrales para búsqueda similar
    - app.vectorstore.retriever: Implementa recuperación con estos parámetros
"""


class RAGConfig:
    """
    Configuración unificada del sistema RAG.
    
    Todos los parámetros están optimizados para:
        - Modelo LLM: gpt-oss:20b (32k context window)
        - Modelo embeddings: BGE-M3-ES-Legal
        - Vectorstore: Milvus con búsqueda de similitud coseno
    """
    
    # ========================================
    # UMBRALES DE SIMILITUD
    # ========================================
    
    SIMILARITY_THRESHOLD_GENERAL = 0.20
    """Umbral para búsquedas generales en toda la base de datos.
    
    AJUSTADO de 0.22 → 0.20 para reducir falsos negativos:
    - Optimizado para BGE-M3 legal español
    - Rango efectivo del modelo: [0.15, 0.50] para contenido relevante
    - 0.20 captura más variaciones terminológicas legales sin incluir ruido excesivo
    - Balance entre recall (encontrar contenido) y precision (calidad)
    - Reduce casos donde chunks relevantes quedan justo por debajo del umbral
    
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
    
    SIMILARITY_THRESHOLD_FALLBACK = 0.25
    """Umbral mínimo para estrategia de fallback.
    
    AJUSTADO de 0.12 → 0.25 para evitar falsos positivos:
    - Umbral anterior (0.12) era demasiado permisivo
    - Causaba que búsquedas fuera del dominio (ej: "Donald Trump") devolvieran resultados irrelevantes
    - 0.25 mantiene el fallback funcional pero con calidad mínima aceptable
    - Previene que el sistema devuelva "cualquier cosa" por no encontrar contenido
    
    Balance: Permite fallback útil sin comprometer la relevancia de los resultados.
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
    
    MIN_RESULTS_THRESHOLD = 5
    """Mínimo de resultados para considerar la búsqueda exitosa.
    
    AJUSTADO de 3 → 5 para mejorar calidad:
    - Con 3 resultados, el sistema activaba fallback demasiado pronto
    - 5 resultados es un mejor indicador de búsqueda exitosa
    - Combinado con umbral fallback de 0.25, previene resultados irrelevantes
    """
    
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
