import httpService from './httpService';

class ConsultaService {
  constructor() {
    this.abortController = null; // AbortController para cancelar streaming
  }

  async consultaGeneralStreaming(query, onChunk, onComplete, onError, topK = 30, conversationContext = '', expedienteNumber = null) {
    // Cancelar consulta anterior si existe
    if (this.abortController) {
      console.log('Cancelando consulta anterior...');
      this.abortController.abort();
    }

    // Crear nuevo AbortController para esta consulta
    this.abortController = new AbortController();
    const signal = this.abortController.signal;
    try {
      // Preparar la consulta con contexto SOLO si realmente existe y no está vacío
      const hasRealContext = Boolean(conversationContext && conversationContext.trim().length > 0);
      
      // Si hay número de expediente, incluirlo en la consulta
      let finalQuery = query.trim();
      if (expedienteNumber) {
        finalQuery = `Consulta sobre expediente ${expedienteNumber}: ${query.trim()}`;
      }
      
      const queryWithContext = hasRealContext 
        ? `${conversationContext.trim()}\n\n${finalQuery}`
        : finalQuery;

      // Validar que el payload esté correcto antes de enviar
      if (!queryWithContext || queryWithContext.trim().length === 0) {
        throw new Error('La consulta no puede estar vacía');
      }

      // Preparar el payload con información del expediente si está disponible
      const payload = {
        query: queryWithContext,
        top_k: topK,
        has_context: hasRealContext
      };

      // Agregar número de expediente al payload si está disponible
      if (expedienteNumber) {
        payload.expediente_number = expedienteNumber;
      }

      // Usar httpService.postStream para manejo de streaming con nueva ruta RAG
      const response = await httpService.postStream('/rag/consulta-general-stream', payload, 300000, {
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
                  console.log('Streaming RAG iniciado:', data.metadata);
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
        console.log('Consulta cancelada por el usuario');
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
   * Cancelar consulta en progreso
   */
  cancelConsulta() {
    if (this.abortController) {
      console.log('Cancelando consulta en progreso...');
      this.abortController.abort();
      this.abortController = null;
    }
  }

}

export default new ConsultaService();
