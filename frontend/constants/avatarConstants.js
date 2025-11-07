/**
 * Constantes relacionadas con el sistema de avatares de usuarios.
 */

// Tipos de avatar permitidos
export const AVATAR_TYPES = {
  CUSTOM: 'custom',
  INITIALS: 'initials',
  HOMBRE: 'hombre',
  MUJER: 'mujer'
};

// Rutas de avatares predefinidos
export const AVATAR_PATHS = {
  DEFAULT_HOMBRE: '/avatar-male-default.png',
  DEFAULT_MUJER: '/avatar-female-default.png'
};

// Mapeo de tipos a rutas
export const AVATAR_TYPE_MAP = {
  [AVATAR_TYPES.HOMBRE]: AVATAR_PATHS.DEFAULT_HOMBRE,
  [AVATAR_TYPES.MUJER]: AVATAR_PATHS.DEFAULT_MUJER
};

// Configuración de archivos
export const MAX_AVATAR_SIZE_MB = 5;
export const MAX_AVATAR_SIZE_BYTES = MAX_AVATAR_SIZE_MB * 1024 * 1024;
export const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp'];

// Configuración de SVG para iniciales
export const INITIALS_SVG_CONFIG = {
  width: 200,
  height: 200,
  radius: 100,
  backgroundColor: '#1B5E9F',
  textColor: 'white',
  fontSize: 80,
  fontFamily: 'Arial, sans-serif',
  fontWeight: 'bold'
};
