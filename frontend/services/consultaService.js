/**
 * Servicio de Consultas con IA mediante RAG (Retrieval-Augmented Generation).
 * 
 * @module services/consultaService
 * 
 * Gestiona las consultas interactivas con el asistente de IA basado en RAG,
 * incluyendo streaming de respuestas, gestión de historial conversacional,
 * y contexto de expedientes judiciales.
 * 
 * Funciones principales:
 *   - consultaGeneralStreaming: Consulta con respuesta progresiva (SSE)
 *   - updateExpedienteContext: Asociar/desasociar expediente a la sesión
 *   - cancelConsulta: Cancelar consulta en progreso
 * 
 * Arquitectura:
 *   - Backend maneja el historial conversacional usando session_id
 *   - Streaming mediante Server-Sent Events (SSE) para respuestas progresivas
 *   - Reformulación automática de preguntas según contexto en backend
 *   - Soporte para consultas generales y específicas de expediente
 * 
 * Gestión de historial:
 *   El backend persiste automáticamente el historial usando session_id.
 *   El frontend solo envía la pregunta actual sin contexto explícito.
 * 
 * @example
 * ```javascript
 * import consultaService from '@/services/consultaService';
 * 
 * // Consulta con streaming
 * consultaService.consultaGeneralStreaming(
 *   '¿Qué es el debido proceso?',
 *   (chunk) => console.log(chunk),           // Cada chunk
 *   () => console.log('Completado'),         // Al finalizar
 *   (err) => console.error(err),             // Si hay error
 *   5,                                       // top_k
 *   'session-abc-123',                       // session_id
 *   '00-000123-0456-PE'                      // expediente (opcional)
 * );
 * 
 * // Asociar expediente a sesión
 * await consultaService.updateExpedienteContext(
 *   'session-abc-123',
 *   '00-000123-0456-PE',
 *   'set'
 * );
 * ```
 * 
 * @see {@link RAG_CONFIG} Configuración de top_k por tipo de consulta
 */

import httpService from './httpService';
import RAG_CONFIG from '../config/ragConfig';

/**
 * Servicio de consultas con IA mediante RAG.
 * 
 * Gestiona consultas interactivas con streaming, historial conversacional,
 * y contexto de expedientes judiciales. Singleton exportado.
 * 
 * @class ConsultaService
 * @category Services
 */
class ConsultaService {
  /**
   * Construye el servicio de consultas con IA.
   * 
   * @constructor
   * Inicializa el AbortController para gestión de cancelación de streaming.
   */
  constructor() {
    /**
     * @private
     * @type {AbortController|null}
     * AbortController para cancelar consulta en progreso
     */
    this.abortController = null;
  }

  /**
   * Realiza una consulta con IA mediante streaming con gestión de historial.
   * 
   * Envía consultas al backend RAG que retorna respuestas progresivas
   * mediante Server-Sent Events (SSE). El backend gestiona automáticamente
   * el historial conversacional usando session_id, reformulando preguntas
   * según contexto y persistiendo mensajes.
   * 
   * Cancelación: Si hay una consulta en progreso, se cancela automáticamente.
   * 
   * @async
   * @param {string} query - Pregunta del usuario (solo la actual, sin historial)
   * @param {Function} onChunk - Callback invocado por cada chunk de respuesta (chunk: string) => void
   * @param {Function} onComplete - Callback invocado al completar respuesta () => void
   * @param {Function} onError - Callback invocado en caso de error (error: Error) => void
   * @param {number|null} [topK=null] - Número de documentos a recuperar (null = usar config según tipo)
   * @param {string|null} [sessionId=null] - ID único de sesión para gestión de historial (requerido)
   * @param {string|null} [expedienteNumber=null] - Número de expediente judicial (opcional, para contexto específico)
   * @throws {Error} Si query está vacío o sessionId no se proporciona
   * 
   * @example
   * ```javascript
   * let respuesta = '';
   * 
   * await consultaService.consultaGeneralStreaming(
   *   '¿Qué es el debido proceso?',
   *   (chunk) => {
   *     respuesta += chunk;
   *     console.log(chunk);
   *   },
   *   () => {
   *     console.log('Respuesta completa:', respuesta);
   *   },
   *   (error) => {
   *     console.error('Error:', error.message);
   *   },
   *   5,                    // top_k
   *   'session-abc-123',    // session_id
   *   '00-000123-0456-PE'   // expediente
   * );
   * ```
   * 
   * @note El backend maneja reformulación automática de preguntas ambiguas usando el historial
   */
  async consultaGeneralStreaming(query, onChunk, onComplete, onError, topK = null, sessionId = null, expedienteNumber = null, notebookId = null) {
    // Cancelar consulta anterior si existe
    if (this.abortController) {
      this.abortController.abort();
    }

    // Crear nuevo AbortController para esta consulta
    this.abortController = new AbortController();
    const signal = this.abortController.signal;
    
    try {
      // Validar que la consulta no esté vacía
      if (!query || query.trim().length === 0) {
        throw new Error('La consulta no puede estar vacía');
      }

      // Validar que haya session_id
      if (!sessionId) {
        throw new Error('session_id es requerido para gestión de historial');
      }

      // Determinar top_k según el tipo de consulta (si no se especifica)
      if (topK === null) {
        topK = expedienteNumber ? RAG_CONFIG.EXPEDIENTE.TOP_K : RAG_CONFIG.GENERAL.TOP_K;
      }

      // Preparar el payload con el nuevo formato
      const payload = {
        query: query.trim(),  // Solo la pregunta actual, sin contexto
        session_id: sessionId,  // Backend gestiona historial con este ID
        top_k: topK
      };

      // Agregar número de expediente si está disponible
      if (expedienteNumber) {
        payload.expediente_number = expedienteNumber;
      }

      // Agregar notebook si está disponible (NotebookServIA)
      if (notebookId) {
        payload.notebook_id = notebookId;
      }

      console.log('📤 Enviando consulta con historial:', {
        query: query.substring(0, 50) + '...',
        session_id: sessionId,
        expediente: expedienteNumber || 'ninguno'
      });

      // Usar el nuevo endpoint con gestión de historial
      const response = await httpService.postStream('/rag/consulta-con-historial-stream', payload, 300000, {
        signal
      }); // 300 segundos timeout

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      let completed = false;

      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            if (!completed) {
              onComplete?.();
              completed = true;
            }
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Mantener la línea incompleta

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.type === 'start') {
                  // Streaming iniciado
                } else if (data.type === 'chunk' && data.content) {
                  onChunk(data.content);
                } else if (data.type === 'done') {
                  if (!completed) {
                    onComplete?.();
                    completed = true;
                  }
                  return;
                } else if (data.type === 'error') {
                  onError?.(new Error(data.content));
                  return;
                }
              } catch (parseError) {
                // Fallback para formato de texto plano (compatibilidad)
                const data = line.slice(6);
                
                if (data === '[DONE]') {
                  if (!completed) {
                    onComplete?.();
                    completed = true;
                  }
                  return;
                }
                
                if (data.startsWith('Error:')) {
                  onError?.(new Error(data));
                  return;
                }
                
                if (data.trim()) {
                  onChunk?.(data);
                }
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
        // Limpiar timeout del streaming
        if (response._clearTimeout) {
          response._clearTimeout();
        }
      }

    } catch (error) {
      // Si fue abortado, no es un error real
      if (error.name === 'AbortError') {
        return;
      }
      console.error('Error en consulta streaming:', error);
      onError?.(error);
    } finally {
      // Limpiar referencia al controller
      this.abortController = null;
    }
  }

  /**
   * Actualiza el contexto de expediente asociado a una sesión.
   * 
   * Permite asociar o desasociar un expediente judicial a la sesión
   * de conversación, filtrando las búsquedas RAG a documentos
   * específicos de ese expediente.
   * 
   * @async
   * @param {string} sessionId - ID único de la sesión
   * @param {string} expedienteNumber - Número del expediente judicial
   * @param {string} [action='set'] - Acción: 'set' (asociar) o 'clear' (desasociar)
   * @returns {Promise<boolean>} true si se actualizó correctamente, false si falló
   * @throws {Error} Si sessionId o expedienteNumber no se proporcionan
   * 
   * @example
   * ```javascript
   * // Asociar expediente a sesión
   * const success = await consultaService.updateExpedienteContext(
   *   'session-abc-123',
   *   '00-000123-0456-PE',
   *   'set'
   * );
   * 
   * if (success) {
   *   console.log('Ahora las consultas se filtran a este expediente');
   * }
   * 
   * // Desasociar expediente (volver a búsqueda general)
   * await consultaService.updateExpedienteContext(
   *   'session-abc-123',
   *   '00-000123-0456-PE',
   *   'clear'
   * );
   * ```
   */
  async updateExpedienteContext(sessionId, expedienteNumber, action = 'set') {
    try {
      if (!sessionId || !expedienteNumber) {
        throw new Error('sessionId y expedienteNumber son requeridos');
      }

      const payload = {
        session_id: sessionId,
        expediente_number: expedienteNumber,
        action: action
      };

      const response = await httpService.post('/rag/update-expediente-context', payload);
      
      if (response.success) {
        console.log('Contexto de expediente actualizado en backend');
        return true;
      } else {
        console.error('Error actualizando contexto:', response.message);
        return false;
      }
      
    } catch (error) {
      console.error('Error actualizando contexto de expediente:', error);
      return false;
    }
  }

  /**
   * Cancela la consulta en progreso si existe.
   * 
   * Utiliza AbortController para cancelar el streaming de manera limpia.
   * Si no hay consulta en progreso, no hace nada.
   * 
   * @example
   * ```javascript
   * // Iniciar consulta
   * consultaService.consultaGeneralStreaming(
   *   'Pregunta larga...',
   *   onChunk,
   *   onComplete,
   *   onError,
   *   5,
   *   sessionId
   * );
   * 
   * // Cancelar después de 5 segundos
   * setTimeout(() => {
   *   consultaService.cancelConsulta();
   *   console.log('Consulta cancelada');
   * }, 5000);
   * ```
   */
  cancelConsulta() {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

}

export default new ConsultaService();
