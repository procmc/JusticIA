/**
 * Roles del sistema JusticIA
 * Archivo centralizado para mantener consistencia entre frontend y backend
 */

export const ROLES = {
  ADMIN: "Administrador",
  USER: "Usuario Judicial",
};

/**
 * Utilidad para verificar si un usuario tiene un rol específico
 * @param {string} userRole - Rol del usuario
 * @param {string|Array<string>} allowedRoles - Rol(es) permitido(s)
 * @returns {boolean}
 */
export const hasRole = (userRole, allowedRoles) => {
  if (!userRole) return false;
  
  if (Array.isArray(allowedRoles)) {
    return allowedRoles.includes(userRole);
  }
  
  return userRole === allowedRoles;
};

/**
 * Lista de todos los roles disponibles
 */
export const ALL_ROLES = Object.values(ROLES);

/**
 * Descripción de cada rol
 */
export const ROLE_DESCRIPTIONS = {
  [ROLES.ADMIN]: "Gestiona usuarios del sistema y revisa el historial de actividades. Solo acceso administrativo.",
  [ROLES.USER]: "Puede realizar consultas y búsquedas en la base de datos de expedientes, e ingresar nuevos documentos.",
};

/**
 * Permisos por módulo
 */
export const PERMISSIONS = {
  // Administración - SOLO Administrador
  MANAGE_USERS: [ROLES.ADMIN],
  VIEW_AUDIT_LOG: [ROLES.ADMIN],
  
  // Ingesta de datos - SOLO Usuario Judicial
  INGEST_DATA: [ROLES.USER],
  
  // Consultas - SOLO Usuario Judicial
  QUERY_DATA: [ROLES.USER],
  SEARCH_SIMILAR: [ROLES.USER],
};

/**
 * Verificar si un usuario tiene un permiso específico
 * @param {string} userRole - Rol del usuario
 * @param {string} permission - Nombre del permiso (ej: 'MANAGE_USERS')
 * @returns {boolean}
 */
export const hasPermission = (userRole, permission) => {
  const allowedRoles = PERMISSIONS[permission];
  if (!allowedRoles) return false;
  
  return allowedRoles.includes(userRole);
};
