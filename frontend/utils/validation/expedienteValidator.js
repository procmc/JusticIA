/**
 * Validador Unificado de Expedientes del Poder Judicial de Costa Rica
 * 
 * FUENTE ÚNICA DE VERDAD para validación de números de expediente.
 * Usado por:
 * - Módulo de Ingesta (ingestaUtils.js)
 * - Módulo de Búsqueda Similares (SearchHeader.jsx)
 * - Cualquier otro módulo que necesite validar expedientes
 * 
 * @module expedienteValidator
 */

/**
 * Patrón OFICIAL del Poder Judicial de Costa Rica
 * 
 * Formato aceptado:
 * - YY-NNNNNN-NNNN-XX   (año corto: 2 dígitos)
 * - YYYY-NNNNNN-NNNN-XX (año largo: 4 dígitos)
 * 
 * Donde:
 * - YY/YYYY: Año (2 o 4 dígitos)
 * - NNNNNN: 6 dígitos
 * - NNNN: 4 dígitos
 * - XX: 2 letras mayúsculas (código de materia)
 * 
 * Ejemplos válidos:
 * - 02-000744-0164-CI
 * - 2022-003287-0166-LA
 * - 2023-123456-7890-FA
 */
export const EXPEDIENTE_PATTERN = /^\d{2,4}-\d{6}-\d{4}-[A-Z]{2}$/;

/**
 * Longitudes válidas de expediente
 * - Formato corto (YY): 17 caracteres (02-000744-0164-CI)
 * - Formato largo (YYYY): 19 caracteres (2022-063557-6597-LA)
 */
export const EXPEDIENTE_LENGTH_MIN = 17;
export const EXPEDIENTE_LENGTH_MAX = 19;

/**
 * Límite de caracteres del input (con margen para errores de tipeo)
 */
export const EXPEDIENTE_INPUT_MAX_LENGTH = 25;

/**
 * Ejemplos de expedientes válidos para mostrar al usuario
 */
export const EXPEDIENTE_EXAMPLES = [
  '02-000744-0164-CI',
  '2022-003287-0166-LA',
  '2023-123456-7890-FA'
];

/**
 * Códigos de materia válidos del Poder Judicial
 * Lista completa actualizada según normativa del Poder Judicial de Costa Rica
 */
export const CODIGOS_MATERIA = {
  AG: 'Agrario',
  AT: 'Atención a la Víctima',
  CA: 'Contencioso Administrativo',
  CC: 'Centro de Conciliación',
  CI: 'Civil',
  CJ: 'Cobro Judicial',
  CO: 'Constitucional',
  DI: 'Inspección Judicial',
  FA: 'Familia',
  FC: 'Faltas y Contravenciones',
  LA: 'Laboral',
  NA: 'Niñez y Adolescencia',
  NO: 'Notariado',
  PA: 'Pensiones Alimentarias',
  PE: 'Penal',
  PJ: 'Penal Juvenil',
  PT: 'Protección a la Víctima',
  S1: 'Sala Primera',
  S2: 'Sala Segunda',
  TR: 'Tránsito',
  TS: 'Trabajo Social y Psicología',
  VD: 'Violencia Doméstica'
};

/**
 * Normaliza un número de expediente reemplazando guiones Unicode por guiones ASCII
 * 
 * Algunos sistemas copian expedientes con guiones Unicode (–, —, etc.)
 * Esta función los normaliza a guiones ASCII estándar (-)
 * 
 * @param {string} expediente - Número de expediente a normalizar
 * @returns {string} Expediente normalizado
 * 
 * @example
 * normalizarExpediente('2022–003287–0166‐LA') // '2022-003287-0166-LA'
 */
export const normalizarExpediente = (expediente) => {
  if (!expediente || typeof expediente !== 'string') {
    return '';
  }
  
  return expediente
    .trim()
    .toUpperCase() // Asegurar que las letras sean mayúsculas
    .replace(/[\u2010-\u2015\u2212\uFE58\uFE63\uFF0D]/g, '-'); // Normalizar guiones Unicode
};

/**
 * Valida el formato de un número de expediente
 * 
 * @param {string} expediente - Número de expediente a validar
 * @returns {boolean} true si el formato es válido, false en caso contrario
 * 
 * @example
 * validarExpediente('02-000744-0164-CI')        // true
 * validarExpediente('2022-003287-0166-LA')      // true
 * validarExpediente('2022-003287-0166')         // false (falta código materia)
 * validarExpediente('22-003287-0166-LA')        // true (año corto válido)
 * validarExpediente('2022-03287-0166-LA')       // false (solo 5 dígitos en segundo grupo)
 */
export const validarExpediente = (expediente) => {
  // Verificar que expediente no sea null, undefined o vacío
  if (!expediente || typeof expediente !== 'string') {
    return false;
  }
  
  // Normalizar antes de validar
  const expedienteNormalizado = normalizarExpediente(expediente);
  
  // Verificar longitud (performance check antes de regex)
  if (expedienteNormalizado.length < EXPEDIENTE_LENGTH_MIN || 
      expedienteNormalizado.length > EXPEDIENTE_LENGTH_MAX) {
    return false;
  }
  
  // Validar con regex
  return EXPEDIENTE_PATTERN.test(expedienteNormalizado);
};

/**
 * Valida si la longitud del expediente es válida (para feedback en tiempo real)
 * 
 * @param {string} expediente - Número de expediente a validar
 * @returns {boolean} true si la longitud está en rango válido
 */
export const validarLongitudExpediente = (expediente) => {
  if (!expediente || typeof expediente !== 'string') {
    return false;
  }
  
  const length = expediente.trim().length;
  return length >= EXPEDIENTE_LENGTH_MIN && length <= EXPEDIENTE_LENGTH_MAX;
};

/**
 * Extrae el código de materia de un expediente válido
 * 
 * @param {string} expediente - Número de expediente
 * @returns {string|null} Código de materia (ej: 'CI', 'LA') o null si inválido
 * 
 * @example
 * extraerCodigoMateria('02-000744-0164-CI') // 'CI'
 * extraerCodigoMateria('2022-003287-0166-LA') // 'LA'
 */
export const extraerCodigoMateria = (expediente) => {
  if (!validarExpediente(expediente)) {
    return null;
  }
  
  const partes = expediente.split('-');
  return partes[partes.length - 1]; // Último elemento
};

/**
 * Obtiene el nombre completo de la materia
 * 
 * @param {string} expediente - Número de expediente
 * @returns {string|null} Nombre de la materia o null si no se encuentra
 * 
 * @example
 * obtenerNombreMateria('02-000744-0164-CI') // 'Civil'
 * obtenerNombreMateria('2022-003287-0166-LA') // 'Laboral'
 */
export const obtenerNombreMateria = (expediente) => {
  const codigo = extraerCodigoMateria(expediente);
  return codigo ? (CODIGOS_MATERIA[codigo] || 'Desconocida') : null;
};

/**
 * Formatea un expediente para visualización (agrega espacios si se desea)
 * 
 * @param {string} expediente - Número de expediente
 * @param {Object} options - Opciones de formateo
 * @param {boolean} options.separador - Usar espacios en lugar de guiones (default: false)
 * @returns {string} Expediente formateado
 * 
 * @example
 * formatearExpediente('02-000744-0164-CI') // '02-000744-0164-CI'
 * formatearExpediente('02-000744-0164-CI', { separador: true }) // '02 000744 0164 CI'
 */
export const formatearExpediente = (expediente, options = {}) => {
  if (!validarExpediente(expediente)) {
    return expediente; // Retornar sin cambios si es inválido
  }
  
  const normalizado = normalizarExpediente(expediente);
  
  if (options.separador) {
    return normalizado.replace(/-/g, ' ');
  }
  
  return normalizado;
};

/**
 * Genera un mensaje de error descriptivo para un expediente inválido
 * 
 * @param {string} expediente - Número de expediente a validar
 * @returns {string|null} Mensaje de error o null si es válido
 * 
 * @example
 * obtenerMensajeError('2022-03287-0166-LA') 
 * // 'Formato inválido. Debe tener 6 dígitos después del primer guion.'
 */
export const obtenerMensajeError = (expediente) => {
  if (!expediente || typeof expediente !== 'string') {
    return 'El número de expediente es requerido';
  }
  
  const trimmed = expediente.trim();
  
  if (trimmed.length === 0) {
    return 'El número de expediente es requerido';
  }
  
  if (trimmed.length < EXPEDIENTE_LENGTH_MIN) {
    return `El expediente debe tener al menos ${EXPEDIENTE_LENGTH_MIN} caracteres (formato: YY-NNNNNN-NNNN-XX)`;
  }
  
  if (trimmed.length > EXPEDIENTE_LENGTH_MAX) {
    return `El expediente no debe exceder ${EXPEDIENTE_LENGTH_MAX} caracteres`;
  }
  
  const normalizado = normalizarExpediente(trimmed);
  const partes = normalizado.split('-');
  
  if (partes.length !== 4) {
    return 'Formato inválido. Debe tener exactamente 3 guiones (-)';
  }
  
  const [año, grupo1, grupo2, materia] = partes;
  
  if (!/^\d{2,4}$/.test(año)) {
    return 'El año debe tener 2 o 4 dígitos (ej: 02 o 2022)';
  }
  
  if (!/^\d{6}$/.test(grupo1)) {
    return 'El segundo grupo debe tener exactamente 6 dígitos';
  }
  
  if (!/^\d{4}$/.test(grupo2)) {
    return 'El tercer grupo debe tener exactamente 4 dígitos';
  }
  
  if (!/^[A-Z]{2}$/.test(materia)) {
    return 'El código de materia debe ser 2 letras mayúsculas (ej: CI, LA, FA)';
  }
  
  return null; // Válido
};

/**
 * Hook helper para React (opcional, pero útil)
 * Retorna estado de validación y mensaje de error
 * 
 * @param {string} expediente - Número de expediente
 * @returns {Object} { isValid, error, materia }
 */
export const useExpedienteValidation = (expediente) => {
  const isValid = validarExpediente(expediente);
  const error = isValid ? null : obtenerMensajeError(expediente);
  const materia = isValid ? obtenerNombreMateria(expediente) : null;
  
  return {
    isValid,
    error,
    materia
  };
};

// Export default con todas las funciones (para import * as)
export default {
  EXPEDIENTE_PATTERN,
  EXPEDIENTE_LENGTH_MIN,
  EXPEDIENTE_LENGTH_MAX,
  EXPEDIENTE_INPUT_MAX_LENGTH,
  EXPEDIENTE_EXAMPLES,
  CODIGOS_MATERIA,
  normalizarExpediente,
  validarExpediente,
  validarLongitudExpediente,
  extraerCodigoMateria,
  obtenerNombreMateria,
  formatearExpediente,
  obtenerMensajeError,
  useExpedienteValidation
};
