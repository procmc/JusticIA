import httpService from './httpService';

/**
 * NotebookService - Servicio para NotebookServIA
 *
 * Maneja la creación y listado de notebooks (colecciones de documentos
 * genéricas que el usuario crea y nombra). La carga de documentos a un
 * notebook reutiliza ingestaService.subirArchivos() pasando la
 * clave_interna del notebook como número de expediente, y el chat
 * reutiliza consultaService.consultaGeneralStreaming() con notebookId.
 */
class NotebookService {
  /**
   * Crear un notebook nuevo
   */
  async crearNotebook(nombre) {
    try {
      const data = await httpService.post('/notebooks', { nombre });
      return { success: true, notebook: data };
    } catch (error) {
      console.error('Error al crear notebook:', error);
      return { error: true, message: error.message || 'Error al crear el notebook' };
    }
  }

  /**
   * Listar los notebooks del usuario autenticado
   */
  async listarNotebooks() {
    try {
      const data = await httpService.get('/notebooks');
      return { success: true, notebooks: data };
    } catch (error) {
      console.error('Error al listar notebooks:', error);
      if (error.isNetworkError) {
        return { error: true, message: 'Error de conexión. Verifique su red.' };
      }
      return { error: true, message: error.message || 'Error al listar notebooks' };
    }
  }

  /**
   * Listar los documentos ya subidos y procesados de un notebook
   */
  async listarDocumentos(notebookId) {
    try {
      const data = await httpService.get(`/notebooks/${notebookId}/documentos`);
      return { success: true, documentos: data };
    } catch (error) {
      console.error('Error al listar documentos del notebook:', error);
      return { error: true, message: error.message || 'Error al listar documentos' };
    }
  }

  /**
   * Obtener el archivo original de un documento como blob, para previsualizarlo
   * (imagen o PDF) sin forzar una descarga.
   */
  async obtenerArchivoPreview(notebookId, documentoId) {
    try {
      const response = await httpService.get(`/notebooks/${notebookId}/documentos/${documentoId}/archivo`);
      const blob = await response.blob();
      return { success: true, url: URL.createObjectURL(blob), tipo: blob.type };
    } catch (error) {
      console.error('Error al obtener el archivo del documento:', error);
      return { error: true, message: error.message || 'Error al obtener el archivo' };
    }
  }

  /**
   * Quitar un documento de un notebook (Qdrant, archivo físico y BD)
   */
  async eliminarDocumento(notebookId, documentoId) {
    try {
      await httpService.delete(`/notebooks/${notebookId}/documentos/${documentoId}`);
      return { success: true };
    } catch (error) {
      console.error('Error al eliminar documento del notebook:', error);
      return { error: true, message: error.message || 'Error al eliminar el documento' };
    }
  }
}

const notebookService = new NotebookService();

export default notebookService;
export { NotebookService };
