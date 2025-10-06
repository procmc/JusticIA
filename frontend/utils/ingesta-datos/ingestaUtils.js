import { 
  validarExpediente, 
  normalizarExpediente,
  EXPEDIENTE_INPUT_MAX_LENGTH,
  obtenerMensajeError 
} from '@/utils/validation/expedienteValidator';

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

// Obtener todos los tipos de archivos como array (para input accept)
export const getAllowedFileExtensions = () => {
  return [...tiposArchivo.documentos, ...tiposArchivo.audio];
};

export const validarFormatoExpediente = (expediente) => {
  return validarExpediente(expediente);
};

// Re-exportar funciones útiles del validador para compatibilidad
export { 
  validarExpediente,
  normalizarExpediente, 
  EXPEDIENTE_INPUT_MAX_LENGTH, 
  obtenerMensajeError 
};
