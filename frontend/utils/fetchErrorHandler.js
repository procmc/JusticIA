/**
 * Utilidades para manejo robusto de errores en fetch/HTTP
 */

/**
 * Tipos de errores clasificados
 */
export const ErrorTypes = {
  NETWORK: 'network',
  TIMEOUT: 'timeout',
  CANCELLED: 'cancelled', // Nueva categoría para cancelaciones manuales
  SERVER: 'server',
  CLIENT: 'client',
  VALIDATION: 'validation',
  AUTH: 'auth',
  NOT_FOUND: 'not_found',
  UNKNOWN: 'unknown'
};

/**
 * Configuración de reintentos por tipo de error
 */
const RETRY_CONFIG = {
  [ErrorTypes.NETWORK]: { max: 3, delay: 1000, backoff: 2 },
  [ErrorTypes.TIMEOUT]: { max: 2, delay: 2000, backoff: 1.5 },
  [ErrorTypes.CANCELLED]: { max: 0, delay: 0, backoff: 1 }, // NO reintentar cancelaciones
  [ErrorTypes.SERVER]: { max: 2, delay: 1500, backoff: 2 },
  [ErrorTypes.CLIENT]: { max: 0, delay: 0, backoff: 1 },
  [ErrorTypes.AUTH]: { max: 0, delay: 0, backoff: 1 },
  [ErrorTypes.NOT_FOUND]: { max: 0, delay: 0, backoff: 1 },
};

/**
 * Patrones de mensajes técnicos que no deben mostrarse
 */
const TECHNICAL_PATTERNS = [
  /failed to fetch/i,
  /fetch.*failed/i,
  /typeerror/i,
  /traceback/i,
  /\[errno \d+\]/i,
  /valueerror:/i,
  /exception:/i,
  /permission denied/i,
  /tika falló/i,
  /después de \d+ intentos/i,
  /connectionerror/i,
  /extract_text/i,
  /network.*error/i,
  /cannot read property/i,
];

/**
 * Mensajes amigables por tipo de error
 */
const USER_FRIENDLY_MESSAGES = {
  [ErrorTypes.NETWORK]: 'No se puede conectar con el servidor. Verifica tu conexión a internet.',
  [ErrorTypes.TIMEOUT]: 'La solicitud está tardando demasiado. Por favor, intenta nuevamente.',
  [ErrorTypes.CANCELLED]: 'Operación cancelada por el usuario.',
  [ErrorTypes.SERVER]: 'Error en el servidor. Por favor, intenta nuevamente más tarde.',
  [ErrorTypes.CLIENT]: 'Error en la solicitud. Verifica los datos e intenta nuevamente.',
  [ErrorTypes.VALIDATION]: 'Los datos proporcionados no son válidos.',
  [ErrorTypes.AUTH]: 'No tienes permisos para realizar esta acción.',
  [ErrorTypes.NOT_FOUND]: 'El recurso solicitado no existe.',
  [ErrorTypes.UNKNOWN]: 'Ha ocurrido un error inesperado. Por favor, intenta nuevamente.',
};

export function classifyError(error, status = null) {
  if (error.message === 'Failed to fetch' || error.name === 'TypeError') {
    return ErrorTypes.NETWORK;
  }
  
  // Diferenciar entre AbortError real (cancelación manual) y timeout
  if (error.name === 'AbortError') {
    // Si el mensaje menciona timeout, es un timeout real
    if (error.message && error.message.toLowerCase().includes('timeout')) {
      return ErrorTypes.TIMEOUT;
    }
    // Si no, es una cancelación manual
    return ErrorTypes.CANCELLED;
  }
  
  if (error.message && error.message.includes('timeout')) {
    return ErrorTypes.TIMEOUT;
  }
  
  if (status) {
    if (status === 401 || status === 403) return ErrorTypes.AUTH;
    if (status === 404) return ErrorTypes.NOT_FOUND;
    if (status === 422) return ErrorTypes.VALIDATION;
    if (status >= 400 && status < 500) return ErrorTypes.CLIENT;
    if (status >= 500) return ErrorTypes.SERVER;
  }
  
  return ErrorTypes.UNKNOWN;
}

export function sanitizeErrorMessage(message, errorType = ErrorTypes.UNKNOWN) {
  if (!message || typeof message !== 'string') {
    return USER_FRIENDLY_MESSAGES[errorType] || USER_FRIENDLY_MESSAGES[ErrorTypes.UNKNOWN];
  }
  
  if (message.length > 200) {
    return USER_FRIENDLY_MESSAGES[errorType] || USER_FRIENDLY_MESSAGES[ErrorTypes.UNKNOWN];
  }
  
  const hasTechnicalInfo = TECHNICAL_PATTERNS.some(pattern => pattern.test(message));
  if (hasTechnicalInfo) {
    return USER_FRIENDLY_MESSAGES[errorType] || USER_FRIENDLY_MESSAGES[ErrorTypes.UNKNOWN];
  }
  
  return message;
}

export function shouldRetry(errorType, attemptCount = 0) {
  const config = RETRY_CONFIG[errorType];
  if (!config) return false;
  
  return attemptCount < config.max;
}

export function getRetryDelay(errorType, attemptCount = 0) {
  const config = RETRY_CONFIG[errorType];
  if (!config) return 0;
  
  return config.delay * Math.pow(config.backoff, attemptCount);
}

export async function parseErrorResponse(response) {
  let errorMessage = `Error ${response.status}`;
  
  try {
    const contentType = response.headers.get('content-type');
    
    if (contentType && contentType.includes('application/json')) {
      const errorData = await response.json();
      
      if (response.status === 422 && Array.isArray(errorData.detail)) {
        const validationErrors = errorData.detail
          .map(err => {
            const field = err.loc ? err.loc.slice(1).join('.') : 'campo';
            return `${field}: ${err.msg}`;
          })
          .join('; ');
        return `Errores de validación: ${validationErrors}`;
      }
      
      if (errorData.message) return errorData.message;
      if (errorData.detail) return errorData.detail;
      if (errorData.error) return errorData.error;
    } else {
      const errorText = await response.text();
      if (errorText && errorText.length < 200) {
        return errorText;
      }
    }
  } catch (parseError) {
    console.warn('Error parseando respuesta de error:', parseError);
  }
  
  return errorMessage;
}

export function createStructuredError(error, errorType, userMessage, context = {}) {
  return {
    type: errorType,
    message: userMessage,
    originalError: error.message || error.toString(),
    timestamp: new Date().toISOString(),
    context,
    ...(process.env.NODE_ENV === 'development' && {
      stack: error.stack,
      details: error
    })
  };
}

export function logError(context, error, extra = {}) {
  const errorType = classifyError(error);
  
  if (process.env.NODE_ENV === 'development') {
    console.group(`Error en ${context}`);
    console.error('Tipo:', errorType);
    console.error('Mensaje:', error.message);
    console.error('Extra:', extra);
    console.error('Stack:', error.stack);
    console.groupEnd();
  } else {
    console.error(`[${context}] ${errorType}:`, error.message, extra);
  }
}

export const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export async function fetchWithRetry(
  fetchFn,
  options = { maxRetries: 3, context: 'API' }
) {
  let lastError;
  let attemptCount = 0;
  
  while (attemptCount <= (options.maxRetries || 3)) {
    try {
      return await fetchFn();
    } catch (error) {
      lastError = error;
      const errorType = classifyError(error);
      
      logError(options.context || 'API', error, {
        attempt: attemptCount + 1,
        errorType
      });
      
      if (!shouldRetry(errorType, attemptCount)) {
        throw error;
      }
      
      const delay = getRetryDelay(errorType, attemptCount);
      console.log(`Reintentando en ${delay}ms... (intento ${attemptCount + 1})`);
      await sleep(delay);
      
      attemptCount++;
    }
  }
  
  throw lastError;
}

export default {
  ErrorTypes,
  classifyError,
  sanitizeErrorMessage,
  shouldRetry,
  getRetryDelay,
  parseErrorResponse,
  createStructuredError,
  logError,
  sleep,
  fetchWithRetry
};
