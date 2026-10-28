/**
 * Utilidades centralizadas para iconos de archivos y estados
 * Elimina la duplicación de getFileIcon, getStatusIcon, getStatusColor
 */
import { FiFile, FiMusic, FiImage, FiCheck, FiAlertCircle, FiLoader } from 'react-icons/fi';

// Iconos por tipo de archivo
export const getFileIcon = (type) => {
  switch (type) {
    case 'document':
      return <FiFile className="w-6 h-6 text-blue-500" />;
    case 'audio':
      return <FiMusic className="w-6 h-6 text-purple-500" />;
    case 'image':
      return <FiImage className="w-6 h-6 text-emerald-500" />;
    default:
      return <FiFile className="w-6 h-6 text-gray-500" />;
  }
};

// Iconos por estado (estados en español)
export const getStatusIcon = (status) => {
  switch (status) {
    case 'completado':
      return <FiCheck className="w-5 h-5 text-green-500" />;
    case 'fallido':
    case 'cancelado':
    case 'rechazado':
      return <FiAlertCircle className="w-5 h-5 text-red-500" />;
    case 'procesando':
    case 'pendiente':
      return <FiLoader className="w-5 h-5 text-blue-500 animate-spin" />;
    default:
      return null;
  }
};

// Colores por estado (estados en español)
export const getStatusColor = (status) => {
  switch (status) {
    case 'completado':
      return 'success';
    case 'fallido':
    case 'cancelado':
    case 'rechazado':
      return 'danger';
    case 'procesando':
      return 'primary';
    case 'pendiente':
      return 'warning';
    default:
      return 'default';
  }
};

// Aviso de una respuesta de carga (RF-05.23): el mensaje y los motivos se muestran tal como los entrega el sistema.
// Solo se une cada motivo con el nombre local del archivo (el sistema no lo devuelve, RNF-07.24); posiciones desde 1.
// Éxito si se aceptó al menos un archivo; si no, advertencia (sin confirmación de envío).
export const armarAvisoCarga = (respuesta, nombres) => {
  const rechazados = respuesta?.rechazados?.archivos || [];
  return {
    tipo: (respuesta?.aceptados?.cantidad || 0) > 0 ? 'success' : 'warning',
    mensaje: respuesta?.message || '',
    motivos: rechazados.map((r) => `${nombres[r.posicion - 1] ?? 'Archivo'}: ${r.motivo}`),
  };
};
