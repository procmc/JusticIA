import httpService from './httpService';

/**
 * Servicio para gestión de conversaciones del historial
 * Se conecta con los endpoints de /rag/conversations
 */
class ConversationService {
  /**
   * Obtiene todas las conversaciones del usuario autenticado
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
   * Obtiene los detalles completos de una conversación específica
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
   * Elimina una conversación
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
   * Restaura una conversación desde el archivo
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
