/**
 * @fileoverview Configuración de RAG (Retrieval-Augmented Generation) para frontend.
 * 
 * Este módulo define los parámetros de configuración para las búsquedas vectoriales
 * y generación aumentada por recuperación (RAG) en el frontend de JusticIA.
 * 
 * IMPORTANTE: Estos valores DEBEN coincidir con backend/app/config/rag_config.py
 * para mantener consistencia en consultas y resultados entre cliente y servidor.
 * 
 * Configuraciones incluidas:
 * - GENERAL: Búsqueda en toda la base de documentos
 * - EXPEDIENTE: Búsqueda limitada a expediente específico
 * - SIMILARITY: Búsqueda de casos similares
 * - FALLBACK: Mecanismo de fallback automático si no hay resultados
 * 
 * Uso de configuraciones:
 * - TOP_K: Cantidad de documentos/chunks a recuperar
 * - SIMILARITY_THRESHOLD: Umbral mínimo de similitud (0.0 - 1.0)
 * - LIMIT: Límite de resultados a retornar
 * 
 * Optimización para LLM:
 * - Modelo: gpt-oss:20b (Ollama)
 * - Context window: 32K tokens
 * - TOP_K calculado para maximizar contexto sin overflow
 * 
 * @module ragConfig
 * 
 * @example
 * import RAG_CONFIG from '@/config/ragConfig';
 * 
 * // Usar en consulta general
 * const response = await fetch('/api/rag/consulta', {
 *   method: 'POST',
 *   body: JSON.stringify({
 *     pregunta: '¿Qué es la prescripción?',
 *     top_k: RAG_CONFIG.GENERAL.TOP_K,
 *     threshold: RAG_CONFIG.GENERAL.SIMILARITY_THRESHOLD
 *   })
 * });
 * 
 * @example
 * // Usar en búsqueda de expediente
 * const expedienteResponse = await consultarExpediente(
 *   expedienteId,
 *   pregunta,
 *   RAG_CONFIG.EXPEDIENTE.TOP_K,
 *   RAG_CONFIG.EXPEDIENTE.SIMILARITY_THRESHOLD
 * );
 * 
 * @example
 * // Usar en búsqueda de casos similares
 * const casosResponse = await buscarSimilares(
 *   descripcion,
 *   RAG_CONFIG.SIMILARITY.LIMIT,
 *   RAG_CONFIG.SIMILARITY.THRESHOLD
 * );
 * 
 * @see {@link ../../backend/app/config/rag_config.py} Configuración de backend (DEBE coincidir)
 * @see {@link ../services/consultaService.js} Servicio que usa esta configuración
 * @see {@link ../services/similarityService.js} Servicio de búsqueda de similares
 * 
 * @author JusticIA Team
 * @version 1.0.0
 */

/**
 * Configuración de RAG (Retrieval-Augmented Generation).
 * 
 * Objeto con parámetros optimizados para diferentes tipos de búsqueda.
 * DEBE mantenerse sincronizado con backend/app/config/rag_config.py.
 * 
 * @constant {Object}
 */
const RAG_CONFIG = {
  // ============================================
  // BÚSQUEDA GENERAL (Consulta en toda la base)
  // ============================================
  GENERAL: {
    TOP_K: 15,                    // Optimizado para gpt-oss:20b (32K ctx) = ~26.2K tokens docs
    SIMILARITY_THRESHOLD: 0.20,   // Umbral de similitud (20%)
  },

  // ============================================
  // BÚSQUEDA EN EXPEDIENTE ESPECÍFICO
  // ============================================
  EXPEDIENTE: {
    TOP_K: 10,                    // Menos chunks pero MÁS relevantes (estabilidad con docs extensos)
    SIMILARITY_THRESHOLD: 0.18,   // Umbral más alto para mejor calidad (18%)
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
    MINIMUM_THRESHOLD: 0.25,               // Ajustado de 0.05 → 0.25 para evitar falsos positivos
    TOP_K: 10,                             // Consistente con expediente (máxima estabilidad)
    MIN_RESULTS: 5,                        // Ajustado de 3 → 5 para mejor calidad
  },

  // ============================================
  // HISTORIAL DE CONVERSACIÓN
  // ============================================
  CHAT: {
    HISTORY_LIMIT: 20,                     // Límite de mensajes enviados al LLM (últimos 10 intercambios)
  },
};

export default RAG_CONFIG;
