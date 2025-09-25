import httpService from './httpService';

class ConsultaService {
  constructor() {
    this.currentRequest = null;
  }

  async consultaGeneralStreaming(query, onChunk, onComplete, onError, topK = 30, conversationContext = '') {
    // Cancelar request anterior si existe
    if (this.currentRequest) {
      console.log('Cancelando consulta anterior...');
      this.currentRequest.cancelled = true;
    }

    // Crear nueva request
    const requestId = Date.now();
    this.currentRequest = { id: requestId, cancelled: false };
    const currentRequest = this.currentRequest;
    try {
      // Preparar la consulta con contexto SOLO si realmente existe y no está vacío
      const hasRealContext = Boolean(conversationContext && conversationContext.trim().length > 0);
      const queryWithContext = hasRealContext 
        ? `${conversationContext.trim()}\n\n${query.trim()}`
        : query.trim();

      // Validar que el payload esté correcto antes de enviar
      if (!queryWithContext || queryWithContext.trim().length === 0) {
        throw new Error('La consulta no puede estar vacía');
      }

      // Usar httpService.postStream para manejo de streaming con nueva ruta RAG
      const response = await httpService.postStream('/rag/consulta-general-stream', {
        query: queryWithContext,
        top_k: topK,
        has_context: hasRealContext
      }, 30000); // 30 segundos timeout

      if (currentRequest.cancelled) {
        console.log('Request cancelada antes de procesar');
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      let completed = false;

      try {
        while (true && !currentRequest.cancelled) {
          const { done, value } = await reader.read();
          
          if (done) {
            if (!completed && !currentRequest.cancelled) {
              onComplete?.();
              completed = true;
            }
            break;
          }

          if (currentRequest.cancelled) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Mantener la línea incompleta

          for (const line of lines) {
            if (currentRequest.cancelled) break;
            
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.type === 'start') {
                  console.log('Streaming RAG iniciado:', data.metadata);
                } else if (data.type === 'chunk' && data.content) {
                  onChunk(data.content);
                } else if (data.type === 'done') {
                  if (!completed && !currentRequest.cancelled) {
                    onComplete?.();
                    completed = true;
                  }
                  return;
                } else if (data.type === 'error') {
                  if (!currentRequest.cancelled) {
                    onError?.(new Error(data.content));
                  }
                  return;
                }
              } catch (parseError) {
                // Fallback para formato de texto plano (compatibilidad)
                const data = line.slice(6);
                
                if (data === '[DONE]') {
                  if (!completed && !currentRequest.cancelled) {
                    onComplete?.();
                    completed = true;
                  }
                  return;
                }
                
                if (data.startsWith('Error:')) {
                  if (!currentRequest.cancelled) {
                    onError?.(new Error(data));
                  }
                  return;
                }
                
                if (data.trim() && !currentRequest.cancelled) {
                  onChunk?.(data);
                }
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
        if (this.currentRequest === currentRequest) {
          this.currentRequest = null;
        }
      }

    } catch (error) {
      if (!currentRequest.cancelled) {
        console.error('Error en consulta streaming:', error);
        onError?.(error);
      }
      if (this.currentRequest === currentRequest) {
        this.currentRequest = null;
      }
    }
  }


}

export default new ConsultaService();
