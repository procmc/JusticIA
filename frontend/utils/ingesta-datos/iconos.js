/**
 * Utilidades centralizadas para iconos de archivos y estados
 * Elimina la duplicación de getFileIcon, getStatusIcon, getStatusColor
 */
import { FiFile, FiMusic, FiCheck, FiAlertCircle, FiLoader } from 'react-icons/fi';

// Iconos por tipo de archivo
export const getFileIcon = (type) => {
  switch (type) {
    case 'document':
      return <FiFile className="w-6 h-6 text-blue-500" />;
    case 'audio':
      return <FiMusic className="w-6 h-6 text-purple-500" />;
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
      return 'danger';
    case 'procesando':
      return 'primary';
    case 'pendiente':
      return 'warning';
    default:
      return 'default';
  }
};
