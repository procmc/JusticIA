import httpService from './httpService';

class ConsultaService {

  async consultaGeneralStreaming(query, onChunk, onComplete, onError, topK = 30) {
    try {
      // Usar httpService.postStream para manejo de streaming
      const response = await httpService.postStream('/llm/consulta-general-stream', {
        query: query.trim(),
        top_k: topK
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            onComplete?.();
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Mantener la línea incompleta

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              
              if (data === '[DONE]') {
                onComplete?.();
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
      } finally {
        reader.releaseLock();
      }

    } catch (error) {
      console.error('Error en consulta streaming:', error);
      onError?.(error);
    }
  }
}

export default new ConsultaService();
