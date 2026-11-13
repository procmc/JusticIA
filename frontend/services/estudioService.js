import httpService from './httpService';

/**
 * EstudioService - Servicio del panel «Estudio» de NotebookServIA (spec 010).
 *
 * Genera un resumen, un informe o un mapa mental con las fuentes marcadas (la respuesta llega como eventos), y lista, abre,
 * guarda como nota y quita los resultados guardados del notebook. La generación se cancela cerrando la conexión: no hay un
 * endpoint de cancelar (RF-11.128).
 */
const TIEMPO_MAXIMO_DE_LA_CONEXION = 20 * 60 * 1000; // el servidor corta antes, con su propio tope (RF-11.130)

class EstudioService {
  async listarResultados(notebookId) {
    try {
      const data = await httpService.get(`/estudio/${notebookId}/resultados`);
      return { success: true, resultados: data };
    } catch (error) {
      return { error: true, status: error.status, message: error.message || 'No se pudieron cargar los resultados.' };
    }
  }

  async abrirResultado(notebookId, resultadoId) {
    try {
      const data = await httpService.get(`/estudio/${notebookId}/resultados/${resultadoId}`);
      return { success: true, resultado: data };
    } catch (error) {
      return { error: true, status: error.status, message: error.message || 'No se pudo abrir el resultado.' };
    }
  }

  async guardarNota(notebookId, { pregunta, respuesta, fuentes }) {
    try {
      const data = await httpService.post(`/estudio/${notebookId}/notas`, { pregunta, respuesta, fuentes });
      return { success: true, resultado: data };
    } catch (error) {
      return { error: true, status: error.status, message: error.message || 'No se pudo guardar la nota. Intente de nuevo.' };
    }
  }

  async quitarResultado(notebookId, resultadoId) {
    try {
      await httpService.delete(`/estudio/${notebookId}/resultados/${resultadoId}`);
      return { success: true };
    } catch (error) {
      return { error: true, status: error.status, message: error.message || 'No se pudo quitar el resultado. Intente de nuevo.' };
    }
  }

  /**
   * Genera un resultado y espera a que termine. `onProgreso({ etapa, actual, total })` se llama con cada avance.
   * Devuelve `{ success, resultado }`, `{ cancelada: true }` si se abortó con `signal`, o `{ error, status, message }`
   * (400 sin fuentes o fuentes demasiado extensas, 409 con otra generación en curso: traen el mensaje del servidor).
   */
  async generar(notebookId, tipo, documentos, { onProgreso, signal } = {}) {
    try {
      const response = await httpService.postStream(
        `/estudio/${notebookId}/generar`, { tipo, documentos }, TIEMPO_MAXIMO_DE_LA_CONEXION, { signal }
      );
      const lector = response.body.getReader();
      const decodificador = new TextDecoder();
      let resto = '';
      let resultado = null;
      let fallo = null;
      while (true) {
        const { done, value } = await lector.read();
        if (done) break;
        resto += decodificador.decode(value, { stream: true });
        const lineas = resto.split('\n');
        resto = lineas.pop() || '';
        for (const linea of lineas) {
          if (!linea.startsWith('data: ')) continue;
          let evento;
          try {
            evento = JSON.parse(linea.slice(6));
          } catch (errorDeLectura) {
            continue;
          }
          if (evento.type === 'progreso') onProgreso?.(evento);
          else if (evento.type === 'resultado') resultado = evento.resultado;
          else if (evento.type === 'error') fallo = evento;
        }
      }
      if (resultado) return { success: true, resultado };
      return { error: true, message: fallo?.mensaje || 'No se pudo generar el resultado. Intente de nuevo.' };
    } catch (error) {
      if (error.name === 'AbortError' || signal?.aborted) return { cancelada: true };
      if (error.isNetworkError) return { error: true, message: 'Error de conexión. Verifique su red.' };
      return { error: true, status: error.status, message: error.message || 'No se pudo generar el resultado. Intente de nuevo.' };
    }
  }
}

const estudioService = new EstudioService();

export default estudioService;
export { EstudioService };
