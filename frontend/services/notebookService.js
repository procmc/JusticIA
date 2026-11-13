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
      // Sin console.error: el mensaje del servidor (en español) lo muestra la página bajo el campo (RF-17.85).
      return { error: true, status: error.status, message: error.message || 'Error al crear el notebook' };
    }
  }

  /**
   * Renombrar un notebook (RF-17.80). El error lleva `status`: 400 trae el mensaje de validación del servidor.
   */
  async renombrarNotebook(notebookId, nombre) {
    try {
      const data = await httpService.put(`/notebooks/${notebookId}`, { nombre });
      return { success: true, notebook: data };
    } catch (error) {
      return { error: true, status: error.status, message: error.message || 'No se pudo renombrar el notebook. Intente de nuevo.' };
    }
  }

  /**
   * Eliminar un notebook (eliminación lógica, RF-17.87).
   */
  async eliminarNotebook(notebookId) {
    try {
      await httpService.delete(`/notebooks/${notebookId}`);
      return { success: true };
    } catch (error) {
      return { error: true, status: error.status, message: error.message || 'No se pudo eliminar el notebook. Intente de nuevo.' };
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
   * El texto de una fuente (`.txt`, Word o HTML) para su vista previa (spec 009b, RF-18.100 y RF-18.106). El servidor lo corta a
   * 200.000 caracteres (`truncado`) y nunca devuelve HTML. Si no se puede obtener, `error` trae el aviso para la ventana.
   */
  async obtenerVistaTexto(notebookId, documentoId) {
    try {
      const data = await httpService.get(`/notebooks/${notebookId}/documentos/${documentoId}/vista-texto`);
      return { success: true, texto: data.texto, truncado: data.truncado };
    } catch (error) {
      return { error: true, status: error.status, message: 'No se pudo mostrar el documento. Intente de nuevo.' };
    }
  }

  /**
   * Un TIFF convertido a PNG para su vista previa, porque el navegador no lo muestra (spec 009b, RF-18.108). `imagen` viene en
   * base64 y `paginas` dice cuántas tiene el original: se muestra la primera.
   */
  async obtenerVistaImagen(notebookId, documentoId) {
    try {
      const data = await httpService.get(`/notebooks/${notebookId}/documentos/${documentoId}/vista-imagen`);
      return { success: true, imagen: data.imagen, paginas: data.paginas };
    } catch (error) {
      return { error: true, status: error.status, message: 'No se pudo mostrar el documento. Intente de nuevo.' };
    }
  }

  /**
   * Cambiar el nombre de una fuente del notebook (RF-19.102). Se envía solo la base: el servidor añade la extensión. El error
   * lleva `status`: 400 trae el mensaje de validación del servidor (RF-19.106, 19.107) y 404, que la fuente ya no está.
   */
  async renombrarDocumento(notebookId, documentoId, nombre) {
    try {
      const data = await httpService.put(`/notebooks/${notebookId}/documentos/${documentoId}`, { nombre });
      return { success: true, documento: data };
    } catch (error) {
      return { error: true, status: error.status, message: error.message || 'No se pudo cambiar el nombre de la fuente. Intente de nuevo.' };
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
      // Sin console.error: el mensaje del servidor (en español) lo muestra la página como aviso (RF-19.30).
      return { error: true, message: error.message || 'No se pudo quitar el documento. Intente de nuevo.' };
    }
  }
}

const notebookService = new NotebookService();

export default notebookService;
export { NotebookService };
