// Tipos de archivos permitidos
export const tiposArchivo = {
  documentos: ['.pdf', '.doc', '.docx', '.rtf', '.txt'],
  audio: ['.mp3', '.wav', '.m4a', '.ogg']
};

// Obtener tipo de archivo basado en la extensión
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
  // Formato: 98-003287-0166-LA (año 2 dígitos, -, 6 dígitos consecutivo, -, 4 dígitos oficina, -, 2 caracteres materia)
  const regex = /^\d{2}-\d{6}-\d{4}-[A-Za-z]{2}$/;
  return regex.test(expediente.trim());
};
