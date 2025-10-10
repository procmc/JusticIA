/**
 * Configuración de RAG (Retrieval-Augmented Generation)
 * 
 * Valores unificados que deben coincidir con el backend (backend/app/config/rag_config.py)
 * para mantener consistencia en las consultas y búsquedas.
 */

const RAG_CONFIG = {
  // ============================================
  // BÚSQUEDA GENERAL (Consulta en toda la base)
  // ============================================
  GENERAL: {
    TOP_K: 10,                    // Optimizado para gpt-oss:20b (32K ctx) = ~17.5K tokens docs (mejor calidad)
    SIMILARITY_THRESHOLD: 0.22,   // Umbral de similitud (22%)
  },

  // ============================================
  // BÚSQUEDA EN EXPEDIENTE ESPECÍFICO
  // ============================================
  EXPEDIENTE: {
    TOP_K: 20,                    // Más documentos para expediente específico (análisis profundo)
    SIMILARITY_THRESHOLD: 0.15,   // Umbral más permisivo (15%)
  },

  // ============================================
  // BÚSQUEDA DE CASOS SIMILARES
  // ============================================
  SIMILARITY: {
    LIMIT: 30,                    // Máximo de casos similares a retornar
    THRESHOLD: 0.3,               // Umbral de similitud (30%)
  },

  // ============================================
  // FALLBACK AUTOMÁTICO
  // ============================================
  FALLBACK: {
    ENABLED: true,                         // Habilitar fallback automático
    THRESHOLD_MULTIPLIER: 0.7,             // Multiplicador para relajar umbral (70%)
    MINIMUM_THRESHOLD: 0.05,               // Umbral mínimo en último intento
    TOP_K: 50,                             // Top-K aumentado en fallback final
    MIN_RESULTS: 3,                        // Mínimo de resultados para considerar exitosa
  },
};

export default RAG_CONFIG;
