/**
 * Servicio para subida de archivos con soporte para progreso granular
 */

import httpService from './httpService';

/**
 * Subir archivos a un expediente (modo asíncrono con IDs individuales)
 */
const subirArchivos = async (expediente, archivos) => {
  const formData = new FormData();
  
  // Agregar expediente
  formData.append('CT_Num_expediente', expediente);
  
  // Agregar archivos
  for (let i = 0; i < archivos.length; i++) {
    formData.append('files', archivos[i]);
  }

  return httpService.post('/ingesta/archivos', formData);
};

/**
 * Consultar estado de un archivo individual (legacy)
 */
const consultarEstadoArchivo = async (fileProcessId) => {
  return httpService.get(`/ingesta/status/${fileProcessId}`);
};

/**
 * Consultar progreso granular de una tarea (nuevo endpoint)
 */
const consultarProgresoDetallado = async (taskId) => {
  return httpService.get(`/ingesta/progress/${taskId}`);
};

/**
 * Consultar estado de múltiples archivos (legacy con fallback a nuevo sistema)
 * Optimizado con caché temporal para evitar consultas excesivas
 */
const consultarEstadoArchivos = async (fileProcessIds) => {
  // Caché temporal para evitar consultas duplicadas inmediatas
  const cache = consultarEstadoArchivos._cache || (consultarEstadoArchivos._cache = new Map());
  const cacheTimeout = 1000; // 1 segundo de caché
  const now = Date.now();
  
  const promesas = fileProcessIds.map(async (id) => {
    // Verificar caché
    const cached = cache.get(id);
    if (cached && (now - cached.timestamp) < cacheTimeout) {
      return cached.result;
    }
    
    try {
      // Intentar primero el nuevo endpoint de progreso
      const response = await consultarProgresoDetallado(id);
      const result = {
        fileProcessId: id,
        success: true,
        data: response,
        isGranular: true
      };
      
      // Guardar en caché solo si es exitoso
      cache.set(id, { result, timestamp: now });
      return result;
    } catch (error) {
      // Si es 404, no hacer fallback inmediatamente para evitar spam
      if (error?.response?.status === 404) {
        const result = {
          fileProcessId: id,
          success: false,
          data: null,
          error: error,
          isGranular: false,
          is404: true
        };
        
        // Caché más corto para 404s para reintentarlo pronto
        cache.set(id, { result, timestamp: now - (cacheTimeout * 0.7) });
        return result;
      }
      
      // Fallback al endpoint legacy para otros errores
      try {
        const response = await consultarEstadoArchivo(id);
        const result = {
          fileProcessId: id,
          success: true,
          data: response,
          isGranular: false
        };
        
        cache.set(id, { result, timestamp: now });
        return result;
      } catch (legacyError) {
        const result = {
          fileProcessId: id,
          success: false,
          data: null,
          error: legacyError,
          isGranular: false
        };
        
        // No cachear errores persistentes
        return result;
      }
    }
  });
  
  const resultados = await Promise.allSettled(promesas);
  
  // Limpiar caché antiguo periódicamente
  if (cache.size > 50 || Math.random() < 0.1) {
    for (const [key, value] of cache.entries()) {
      if (now - value.timestamp > cacheTimeout * 5) {
        cache.delete(key);
      }
    }
  }
  
  return resultados.map((resultado, index) => ({
    fileProcessId: fileProcessIds[index],
    success: resultado.status === 'fulfilled' && resultado.value.success,
    data: resultado.status === 'fulfilled' ? resultado.value.data : null,
    error: resultado.status === 'rejected' ? resultado.reason : resultado.value?.error,
    isGranular: resultado.status === 'fulfilled' ? resultado.value.isGranular : false,
    is404: resultado.status === 'fulfilled' ? resultado.value.is404 : false
  }));
};

/**
 * Cancelar procesamiento de un archivo
 */
const cancelarProcesamiento = async (fileProcessId) => {
  return httpService.post(`/ingesta/cancel/${fileProcessId}`);
};

export default {
  subirArchivos,
  consultarEstadoArchivo,
  consultarProgresoDetallado,
  consultarEstadoArchivos,
  cancelarProcesamiento
};
