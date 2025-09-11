import httpService from './httpService';

class ConsultaService {
  constructor() {
    this.currentRequest = null;
  }

  async consultaGeneralStreaming(query, onChunk, onComplete, onError, topK = 30) {
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
      // Usar httpService.postStream para manejo de streaming
      const response = await httpService.postStream('/llm/consulta-general-stream', {
        query: query.trim(),
        top_k: topK
      });

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
