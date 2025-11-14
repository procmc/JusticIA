/**
 * Servicio de Gestión de Historial de Conversaciones con IA.
 * 
 * @module services/conversationService
 * 
 * Este servicio maneja todas las operaciones relacionadas con el historial
 * de conversaciones del asistente de IA. Las conversaciones se persisten
 * en el servidor para mantenerlas entre sesiones.
 * 
 * Funciones principales:
 *   - getUserConversations: Lista todas las conversaciones del usuario
 *   - getConversationDetail: Obtiene detalle completo de una conversación
 *   - deleteConversation: Elimina una conversación del historial
 *   - restoreConversation: Restaura conversación desde archivo
 *   - getConversationsStats: Obtiene estadísticas del sistema
 * 
 * Estructura de conversación:
 *   - session_id: Identificador único de la sesión
 *   - user_id: ID del usuario propietario
 *   - messages: Array de mensajes (role: user/assistant, content: texto)
 *   - expediente_context: Contexto de expediente si aplica
 *   - created_at: Fecha de creación
 *   - updated_at: Última actualización
 * 
 * @example
 * ```javascript
 * import conversationService from '@/services/conversationService';
 * 
 * // Listar conversaciones
 * const result = await conversationService.getUserConversations();
 * console.log(`Total: ${result.total} conversaciones`);
 * 
 * // Obtener detalle
 * const detail = await conversationService.getConversationDetail(sessionId);
 * console.log(detail.conversation.messages);
 * 
 * // Eliminar
 * await conversationService.deleteConversation(sessionId);
 * ```
 * 
 * @see {@link useBackendConversations} Hook para usar en componentes React
 */

import httpService from './httpService';

/**
 * Servicio de gestión de conversaciones con el asistente de IA.
 * 
 * Se conecta con los endpoints de /rag/conversations del backend.
 * 
 * @class ConversationService
 * @category Services
 */
class ConversationService {
  /**
   * Obtiene todas las conversaciones del usuario autenticado.
   * 
   * @async
   * @returns {Promise<Object>} Resultado con:
   *   - success {boolean}: Si la operación fue exitosa
   *   - conversations {Array<Object>}: Lista de conversaciones
   *   - total {number}: Cantidad total de conversaciones
   *   - error {string}: Mensaje de error si falló
   * 
   * @example
   * ```javascript
   * const result = await conversationService.getUserConversations();
   * 
   * if (result.success) {
   *   result.conversations.forEach(conv => {
   *     console.log(conv.session_id, conv.created_at);
   *   });
   * }
   * ```
   */
  async getUserConversations() {
    try {
      const response = await httpService.get('/rag/conversations');
      
      if (response.success) {
        return {
          success: true,
          conversations: response.conversations || [],
          total: response.total || 0
        };
      }
      
      return {
        success: false,
        conversations: [],
        total: 0,
        error: 'No se pudieron obtener las conversaciones'
      };
    } catch (error) {
      console.error('Error obteniendo conversaciones:', error);
      return {
        success: false,
        conversations: [],
        total: 0,
        error: error.message || 'Error de conexión'
      };
    }
  }

  /**
   * Obtiene el detalle completo de una conversación específica.
   * 
   * Incluye todos los mensajes de la conversación y metadatos
   * como expediente asociado, fechas de creación/actualización.
   * 
   * @async
   * @param {string} sessionId - ID único de la sesión de conversación
   * @returns {Promise<Object>} Resultado con:
   *   - success {boolean}: Si la operación fue exitosa
   *   - conversation {Object}: Objeto con session_id, messages, expediente_context, etc.
   *   - error {string}: Mensaje de error si falló
   * 
   * @example
   * ```javascript
   * const detail = await conversationService.getConversationDetail('abc-123');
   * 
   * if (detail.success) {
   *   console.log('Expediente:', detail.conversation.expediente_context);
   *   detail.conversation.messages.forEach(msg => {
   *     console.log(`${msg.role}: ${msg.content}`);
   *   });
   * }
   * ```
   */
  async getConversationDetail(sessionId) {
    try {
      const response = await httpService.get(`/rag/conversations/${sessionId}`);
      
      if (response.success && response.conversation) {
        return {
          success: true,
          conversation: response.conversation
        };
      }
      
      return {
        success: false,
        error: 'No se pudo obtener la conversación'
      };
    } catch (error) {
      console.error('Error obteniendo detalles de conversación:', error);
      return {
        success: false,
        error: error.message || 'Error de conexión'
      };
    }
  }

  /**
   * Elimina una conversación del historial del usuario.
   * 
   * Esta operación es permanente y no se puede deshacer.
   * La conversación se elimina del servidor y ya no estará
   * disponible para el usuario.
   * 
   * @async
   * @param {string} sessionId - ID único de la sesión a eliminar
   * @returns {Promise<Object>} Resultado con:
   *   - success {boolean}: Si la operación fue exitosa
   *   - message {string}: Mensaje de confirmación si exitoso
   *   - error {string}: Mensaje de error si falló
   * 
   * @example
   * ```javascript
   * const result = await conversationService.deleteConversation('abc-123');
   * 
   * if (result.success) {
   *   console.log('Conversación eliminada:', result.message);
   * } else {
   *   console.error('Error al eliminar:', result.error);
   * }
   * ```
   */
  async deleteConversation(sessionId) {
    try {
      const response = await httpService.delete(`/rag/conversations/${sessionId}`);
      
      return {
        success: response.success || false,
        message: response.message
      };
    } catch (error) {
      console.error('Error eliminando conversación:', error);
      return {
        success: false,
        error: error.message || 'Error eliminando conversación'
      };
    }
  }

  /**
   * Restaura una conversación desde el archivo de respaldo.
   * 
   * Permite recuperar conversaciones que fueron respaldadas en el servidor.
   * La conversación restaurada aparecerá nuevamente en el historial del usuario.
   * 
   * @async
   * @param {string} sessionId - ID único de la sesión a restaurar
   * @returns {Promise<Object>} Resultado con:
   *   - success {boolean}: Si la operación fue exitosa
   *   - message {string}: Mensaje de confirmación si exitoso
   *   - conversation {Object}: Conversación restaurada
   *   - error {string}: Mensaje de error si falló
   * 
   * @example
   * ```javascript
   * const result = await conversationService.restoreConversation('abc-123');
   * 
   * if (result.success) {
   *   console.log('Conversación restaurada:', result.conversation.session_id);
   * } else {
   *   console.error('Error al restaurar:', result.error);
   * }
   * ```
   */
  async restoreConversation(sessionId) {
    try {
      const response = await httpService.post(`/rag/conversations/${sessionId}/restore`);
      
      if (response.success) {
        return {
          success: true,
          conversation: response.conversation,
          message: response.message
        };
      }
      
      return {
        success: false,
        error: 'No se pudo restaurar la conversación'
      };
    } catch (error) {
      console.error('Error restaurando conversación:', error);
      return {
        success: false,
        error: error.message || 'Error restaurando conversación'
      };
    }
  }

  /**
   * Obtiene estadísticas del sistema de conversaciones
   */
  async getConversationsStats() {
    try {
      const response = await httpService.get('/rag/conversations-stats');
      
      if (response.success) {
        return {
          success: true,
          stats: response.stats
        };
      }
      
      return {
        success: false,
        error: 'No se pudieron obtener las estadísticas'
      };
    } catch (error) {
      console.error('Error obteniendo estadísticas:', error);
      return {
        success: false,
        error: error.message || 'Error de conexión'
      };
    }
  }
}

const conversationService = new ConversationService();
export default conversationService;
