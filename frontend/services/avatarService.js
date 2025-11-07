/**
 * Servicio para gestión de avatares.
 * Centraliza la lógica de generación y validación de avatares.
 */

import {
  AVATAR_TYPES,
  AVATAR_TYPE_MAP,
  AVATAR_PATHS,
  INITIALS_SVG_CONFIG,
  MAX_AVATAR_SIZE_BYTES,
  ALLOWED_IMAGE_TYPES
} from '@/constants/avatarConstants';

/**
 * Genera un avatar SVG con las iniciales del usuario
 * @param {string} fullName - Nombre completo del usuario
 * @returns {string} URL del SVG generado
 */
export const generateInitialsAvatar = (fullName) => {
  if (!fullName || fullName.trim() === '') {
    return AVATAR_PATHS.DEFAULT_HOMBRE;
  }
  
  const partes = fullName.trim().split(' ');
  const firstName = partes[0] || '';
  const lastName = partes.length >= 3 ? partes[2] : (partes[1] || '');
  const initials = `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase() || 'U';
  
  const { width, height, radius, backgroundColor, textColor, fontSize, fontFamily, fontWeight } = INITIALS_SVG_CONFIG;
  
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">
      <circle cx="${radius}" cy="${radius}" r="${radius}" fill="${backgroundColor}"/>
      <text x="${radius}" y="${radius}" font-family="${fontFamily}" font-size="${fontSize}" font-weight="${fontWeight}" 
            fill="${textColor}" text-anchor="middle" dominant-baseline="central">${initials}</text>
    </svg>
  `;
  
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
};

/**
 * Mapea un tipo de avatar a su ruta correspondiente
 * @param {string} tipo - Tipo de avatar
 * @param {string} fullName - Nombre completo (requerido para tipo 'initials')
 * @returns {string} URL del avatar
 */
export const mapAvatarTypeToPath = (tipo, fullName = '') => {
  if (tipo === AVATAR_TYPES.INITIALS) {
    return generateInitialsAvatar(fullName);
  }
  
  return AVATAR_TYPE_MAP[tipo] || AVATAR_PATHS.DEFAULT_HOMBRE;
};

/**
 * Construye la URL completa del avatar desde la ruta del backend
 * @param {string} avatarRuta - Ruta del avatar en el backend
 * @param {string} apiUrl - URL base del API
 * @returns {string} URL completa del avatar
 */
export const buildAvatarUrl = (avatarRuta, apiUrl) => {
  if (!avatarRuta) return AVATAR_PATHS.DEFAULT_HOMBRE;
  
  // Si ya es una URL completa o data URL
  if (avatarRuta.startsWith('http') || avatarRuta.startsWith('data:')) {
    return avatarRuta;
  }
  
  // Construir URL sin timestamp - la sesión ya maneja la actualización
  return `${apiUrl}/${avatarRuta}`;
};

/**
 * Valida un archivo de imagen para avatar
 * @param {File} file - Archivo a validar
 * @returns {Object} Resultado de validación { valid: boolean, error?: string }
 */
export const validateAvatarFile = (file) => {
  if (!file) {
    return { valid: false, error: 'No se proporcionó un archivo' };
  }
  
  // Validar tipo
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
    return { 
      valid: false, 
      error: `Tipo de archivo no permitido. Use: ${ALLOWED_IMAGE_TYPES.join(', ')}` 
    };
  }
  
  // Validar tamaño
  if (file.size > MAX_AVATAR_SIZE_BYTES) {
    const maxSizeMB = MAX_AVATAR_SIZE_BYTES / (1024 * 1024);
    return { 
      valid: false, 
      error: `El archivo excede el tamaño máximo de ${maxSizeMB}MB` 
    };
  }
  
  return { valid: true };
};

/**
 * Emite un evento de actualización de avatar
 * @param {string} avatar - Nueva URL del avatar
 * @param {string} tipo - Nuevo tipo de avatar
 */
export const emitAvatarUpdateEvent = (avatar, tipo) => {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('avatarUpdated', { 
      detail: { avatar, tipo } 
    }));
  }
};

/**
 * Verifica si un avatar es personalizado (no predefinido)
 * @param {string} avatarUrl - URL del avatar
 * @returns {boolean} true si es personalizado
 */
export const isCustomAvatar = (avatarUrl) => {
  if (!avatarUrl) return false;
  
  const predefinedPaths = Object.values(AVATAR_PATHS);
  return !predefinedPaths.some(path => avatarUrl.includes(path)) && 
         !avatarUrl.startsWith('data:image/svg+xml');
};

export default {
  generateInitialsAvatar,
  mapAvatarTypeToPath,
  buildAvatarUrl,
  validateAvatarFile,
  emitAvatarUpdateEvent,
  isCustomAvatar
};
