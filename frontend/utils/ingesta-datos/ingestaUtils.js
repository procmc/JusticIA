/**
 * Utilidades para el módulo de ingesta de datos
 * Funciones de validación, formato y procesamiento de archivos
 */

// Tipos de archivos permitidos (centralizados)
export const tiposArchivo = {
  documentos: ['.pdf', '.doc', '.docx', '.rtf', '.txt'],
  audio: ['.mp3', '.wav', '.m4a', '.ogg']
};

// Obtener tipo de archivo basado en la extensión (unificado)
export const obtenerTipoArchivo = (nombreArchivo) => {
  const extension = '.' + nombreArchivo.split('.').pop().toLowerCase();
  if (tiposArchivo.documentos.includes(extension)) return 'document';
  if (tiposArchivo.audio.includes(extension)) return 'audio';
  return 'unknown';
};

// Formatear tamaño de archivo
export const formatearTamano = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const tamanos = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + tamanos[i];
};

// Validación del formato de expediente
export const validarFormatoExpediente = (expediente) => {
  // Verificar que expediente no sea null, undefined o vacío
  if (!expediente || typeof expediente !== 'string') {
    return false;
  }
  
  // Formato: entre 17 y 20 caracteres alfanuméricos (incluyendo guiones)
  const regex = /^[A-Za-z0-9\-]{17,20}$/;
  return regex.test(expediente.trim());
};

// Obtener todos los tipos de archivos como array (para input accept)
export const getAllowedFileExtensions = () => {
  return [...tiposArchivo.documentos, ...tiposArchivo.audio];
};
