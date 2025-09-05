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

// Iconos por estado
export const getStatusIcon = (status) => {
  switch (status) {
    case 'success':
      return <FiCheck className="w-5 h-5 text-green-500" />;
    case 'error':
      return <FiAlertCircle className="w-5 h-5 text-red-500" />;
    case 'uploading':
      return <FiLoader className="w-5 h-5 text-blue-500 animate-spin" />;
    default:
      return null;
  }
};

// Colores por estado
export const getStatusColor = (status) => {
  switch (status) {
    case 'success':
      return 'success';
    case 'error':
      return 'danger';
    case 'uploading':
      return 'primary';
    default:
      return 'default';
  }
};
