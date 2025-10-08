import httpService from './httpService';

class ConsultaService {
  constructor() {
    this.abortController = null; // AbortController para cancelar streaming
  }

  /**
   * Consulta con gestión de historial conversacional.
   * 
   * NUEVO: Usa session_id para gestión automática de historial en backend.
   * El backend maneja la reformulación y persistencia de mensajes.
   * 
   * @param {string} query - Pregunta del usuario (solo la actual, sin contexto)
   * @param {Function} onChunk - Callback para cada chunk de respuesta
   * @param {Function} onComplete - Callback al completar
   * @param {Function} onError - Callback en caso de error
   * @param {number} topK - Número de documentos a recuperar (default: 15)
   * @param {string} sessionId - ID de sesión para gestión de historial
   * @param {string} expedienteNumber - Número de expediente (opcional)
   */
  async consultaGeneralStreaming(query, onChunk, onComplete, onError, topK = 15, sessionId = null, expedienteNumber = null) {
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
   * Cancelar consulta en progreso
   */
  cancelConsulta() {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

}

export default new ConsultaService();
