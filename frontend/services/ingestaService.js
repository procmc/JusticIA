/**
 * Servicio simplificado para ingesta de archivos con Celery
 */

import httpService from './httpService';

/**
 * Subir archivos a un expediente
 * @returns {Promise<{task_ids: string[], expediente: string}>}
 */
const subirArchivos = async (expediente, archivos) => {
  const formData = new FormData();
  formData.append('CT_Num_expediente', expediente);
  
  for (let i = 0; i < archivos.length; i++) {
    formData.append('files', archivos[i]);
  }
  
  return httpService.post('/ingesta/archivos', formData);
};

/**
 * Consultar progreso de una tarea Celery
 * @returns {Promise<{task_id: string, status: string, progress: number, message: string, ready: boolean}>}
 */
const consultarProgresoTarea = async (taskId) => {
  return httpService.get(`/ingesta/progress/${taskId}`);
};

/**
 * Consultar estado de múltiples tareas en paralelo
 * @returns {Promise<Array<{taskId: string, success: boolean, data: object}>>}
 */
const consultarEstadoArchivos = async (taskIds) => {
  const promesas = taskIds.map(async (taskId) => {
    try {
      const data = await consultarProgresoTarea(taskId);
      return {
        taskId,
        success: true,
        data
      };
    } catch (error) {
      return {
        taskId,
        success: false,
        error: error.message || 'Error consultando estado'
      };
    }
  });
  
  return Promise.all(promesas);
};

/**
 * Cancelar procesamiento de una tarea (si el backend lo soporta)
 */
const cancelarProcesamiento = async (taskId) => {
  return httpService.post(`/ingesta/cancel/${taskId}`);
};

export default {
  subirArchivos,
  consultarProgresoTarea,
  consultarEstadoArchivos,
  cancelarProcesamiento
};
