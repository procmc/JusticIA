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
  
  // Normalizar: reemplazar cualquier tipo de guion por guion ASCII normal
  const expedienteNormalizado = expediente
    .trim()
    .replace(/[\u2010-\u2015\u2212\uFE58\uFE63\uFF0D]/g, '-'); // Reemplazar guiones Unicode
  
  // Formato EXACTO: YYYY-NNNNNN-NNNN-XX
  // - 4 dígitos (año)
  // - guion
  // - 6 dígitos
  // - guion  
  // - 4 dígitos
  // - guion
  // - 2 letras mayúsculas
  const regex = /^\d{4}-\d{6}-\d{4}-[A-Z]{2}$/;
  
  const esValido = regex.test(expedienteNormalizado);
    
  return esValido;
};

// Normalizar número de expediente (convertir guiones Unicode a ASCII)
export const normalizarExpediente = (expediente) => {
  if (!expediente || typeof expediente !== 'string') {
    return expediente;
  }
  
  // Reemplazar todos los tipos de guiones Unicode por guion ASCII normal
  return expediente
    .trim()
    .toUpperCase() // Convertir letras a mayúsculas
    .replace(/[\u2010-\u2015\u2212\uFE58\uFE63\uFF0D]/g, '-'); // Normalizar guiones
};

// Obtener todos los tipos de archivos como array (para input accept)
export const getAllowedFileExtensions = () => {
  return [...tiposArchivo.documentos, ...tiposArchivo.audio];
};
