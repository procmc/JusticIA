/**
 * Tipos de acción para bitácora
 * Sincronizados con backend/app/constants/tipos_accion.py
 */

export const TIPOS_ACCION = [
  { key: '1', label: 'Búsqueda de Casos Similares' },
  { key: '2', label: 'Carga de Documentos' },
  { key: '3', label: 'Login' },
  { key: '4', label: 'Logout' },
  { key: '5', label: 'Cambio de Contraseña' },
  { key: '6', label: 'Recuperación de Contraseña' },
  { key: '7', label: 'Crear Usuario' },
  { key: '8', label: 'Editar Usuario' },
  { key: '9', label: 'Consultar Usuarios' },
  { key: '10', label: 'Descargar Archivo' },
  { key: '11', label: 'Listar Archivos' },
  { key: '12', label: 'Consulta RAG' },
  { key: '13', label: 'Generar Resumen' },
  { key: '14', label: 'Consultar Bitácora' },
  { key: '15', label: 'Exportar Bitácora' }
];

export default TIPOS_ACCION;
