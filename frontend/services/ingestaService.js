/**
 * Servicio para subida de archivos
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
 * Consultar estado de un archivo individual
 */
const consultarEstadoArchivo = async (fileProcessId) => {
  return httpService.get(`/ingesta/status/${fileProcessId}`);
};

/**
 * Consultar estado de múltiples archivos
 */
const consultarEstadoArchivos = async (fileProcessIds) => {
  const promesas = fileProcessIds.map(id => consultarEstadoArchivo(id));
  const resultados = await Promise.allSettled(promesas);
  
  return resultados.map((resultado, index) => ({
    fileProcessId: fileProcessIds[index],
    success: resultado.status === 'fulfilled',
    data: resultado.status === 'fulfilled' ? resultado.value : null,
    error: resultado.status === 'rejected' ? resultado.reason : null
  }));
};

export default {
  subirArchivos,
  consultarEstadoArchivo,
  consultarEstadoArchivos
};
