/**
 * Servicio de Ingesta de Archivos con Procesamiento Asíncrono (Celery).
 * 
 * @module services/ingestaService
 * 
 * Este servicio maneja la carga de documentos y audio a expedientes, con
 * procesamiento asíncrono mediante tareas de Celery. Incluye validación de
 * archivos, reintentos automáticos para errores de red, y consulta de progreso.
 * 
 * Características:
 *   - Upload de archivos con FormData
 *   - Reintentos automáticos (exponential backoff) solo para errores de red
 *   - Validación de tamaño máximo (200MB)
 *   - Polling de progreso sin reintentos (alta frecuencia)
 *   - Consulta paralela de múltiples tareas
 *   - Cancelación de procesamiento "best effort"
 * 
 * Flujo de ingesta:
 *   1. Usuario selecciona archivos
 *   2. validateFiles() verifica tamaño y cantidad
 *   3. subirArchivos() crea tareas Celery y retorna task_ids
 *   4. Frontend hace polling con consultarProgresoTarea()
 *   5. Cuando ready=true, el procesamiento terminó
 * 
 * @example
 * ```javascript
 * import ingestaService from '@/services/ingestaService';
 * 
 * // Subir archivos
 * const result = await ingestaService.subirArchivos('00-001234-0567-PE', files);
 * console.log('Task IDs:', result.task_ids);
 * 
 * // Consultar progreso (polling cada 2 segundos)
 * const progress = await ingestaService.consultarProgresoTarea(task_ids[0]);
 * console.log(`Progreso: ${progress.progress}%`);
 * 
 * // Cancelar si es necesario
 * await ingestaService.cancelarProcesamiento(task_ids[0]);
 * ```
 * 
 * @see {@link httpService} Para llamadas HTTP configuradas
 * @see {@link backend/tasks.py} Para lógica de procesamiento Celery
 */

import httpService from './httpService';

/**
 * Servicio de ingesta de archivos con procesamiento asíncrono.
 * 
 * @class IngestaService
 * @category Services
 */
class IngestaService {
  /**
   * Inicializa el servicio de ingesta.
   * 
   * @constructor
   */
  constructor() {
    /** @type {number} Máximo de reintentos para uploads (errores de red) */
    this.maxRetries = 2;
    /** @type {number} Delay inicial para reintentos en ms (usa exponential backoff) */
    this.retryDelay = 1000;
  }

  /**
   * Sleep helper para reintentos
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Validar archivos antes de subir
   */
  validateFiles(archivos) {
    if (!archivos || archivos.length === 0) {
      throw new Error('Debe seleccionar al menos un archivo');
    }

    const maxFileSize = 200 * 1024 * 1024; // 200MB
    const invalidFiles = archivos.filter(file => file.size > maxFileSize);
    
    if (invalidFiles.length > 0) {
      throw new Error(`Algunos archivos exceden el límite de 200MB: ${invalidFiles.map(f => f.name).join(', ')}`);
    }

    return true;
  }

  /**
   * Subir archivos a un expediente con reintentos
   * @returns {Promise<{task_ids: string[], expediente: string}>}
   */
  async subirArchivos(expediente, archivos) {
    // Validar parámetros
    if (!expediente || expediente.trim() === '') {
      throw new Error('El número de expediente es requerido');
    }

    this.validateFiles(archivos);

    // Preparar FormData
    const formData = new FormData();
    formData.append('CT_Num_expediente', expediente);
    
    for (let i = 0; i < archivos.length; i++) {
      formData.append('files', archivos[i]);
    }

    // Intentar upload con reintentos SOLO para errores de red
    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        const response = await httpService.post('/ingesta/archivos', formData, {
          timeout: 120000 // 2 minutos para uploads grandes
        });

        return response;

      } catch (error) {
        const isLastAttempt = attempt === this.maxRetries;
        
        // Solo reintentar errores de red
        if (error.isNetworkError && !isLastAttempt) {
          console.log(`Upload fallido (intento ${attempt + 1}/${this.maxRetries + 1}), reintentando...`);
          const delay = this.retryDelay * Math.pow(2, attempt); // Backoff exponencial
          await this.sleep(delay);
          continue;
        }
        // Para cualquier error restante, propagar un único mensaje genérico
        throw new Error('Error al procesar la ingesta. Intente nuevamente más tarde.');
      }
    }
  }

  /**
   * Consultar progreso de una tarea Celery
   * NO reintenta (se usa en polling frecuente, reintentos harían lento el sistema)
   * @returns {Promise<{task_id: string, status: string, progress: number, message: string, ready: boolean}>}
   */
  async consultarProgresoTarea(taskId) {
    try {
      return await httpService.get(`/ingesta/progress/${taskId}`, {
        timeout: 10000 // 10 segundos (es una consulta rápida)
      });
    } catch (error) {
      // Si es timeout o red, devolver estado "pendiente" en lugar de error
      // (el polling lo reintentará automáticamente)
      if (error.isTimeout || error.isNetworkError) {
        return {
          task_id: taskId,
          status: 'pendiente',
          progress: 0,
          message: 'Consultando estado...',
          ready: false
        };
      }
      // Para otros errores, lanzar un mensaje genérico
      throw new Error('Error consultando el progreso de la ingesta.');
    }
  }

  /**
   * Consultar estado de múltiples tareas en paralelo
   * @returns {Promise<Array<{taskId: string, success: boolean, data: object}>>}
   */
  async consultarEstadoArchivos(taskIds) {
    const promesas = taskIds.map(async (taskId) => {
      try {
        const data = await this.consultarProgresoTarea(taskId);
        return {
          taskId,
          success: true,
          data
        };
      } catch (error) {
        return {
          taskId,
          success: false,
          error: 'Error al consultar el estado'
        };
      }
    });
    
    return Promise.all(promesas);
  }

  /**
   * Cancelar procesamiento de una tarea
   * Manejo "best effort" - si falla no es crítico
   */
  async cancelarProcesamiento(taskId) {
    try {
      return await httpService.post(`/ingesta/cancel/${taskId}`, null, {
        timeout: 5000 // 5 segundos
      });
    } catch (error) {
      // Log pero no throw - cancelación es "best effort"
      console.warn(`No se pudo cancelar la tarea ${taskId}:`, error.message);
      
      // Devolver respuesta indicando que se intentó cancelar
      return {
        task_id: taskId,
        status: 'cancel_attempted',
        message: 'Se intentó cancelar la tarea pero el servidor no respondió'
      };
    }
  }
}

// Exportar instancia singleton
const ingestaService = new IngestaService();

export default ingestaService;

// Exportar clase para testing o instancias personalizadas
export { IngestaService };
