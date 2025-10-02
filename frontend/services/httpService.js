/**
 * Servicio HTTP robusto con manejo avanzado de errores
 */
import { getSession } from 'next-auth/react';
import {
  classifyError,
  sanitizeErrorMessage,
  parseErrorResponse,
  createStructuredError,
  logError,
  fetchWithRetry,
  ErrorTypes
} from '@/utils/fetchErrorHandler';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Configuración global
const DEFAULT_TIMEOUT = 30000; // 30 segundos

/**
 * Obtener headers con autenticación automática
 */
const getAuthHeaders = async () => {
  const session = await getSession();
  const headers = {};
  
  // Agregar token si hay sesión
  if (session?.accessToken) {
    headers.Authorization = `Bearer ${session.accessToken}`;
  }
  
  return headers;
};

/**
 * Crear controller para timeout
 */
const createTimeoutController = (timeout = DEFAULT_TIMEOUT) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  return { controller, timeoutId };
};

/**
 * Wrapper robusto para fetch con manejo avanzado de errores
 */
const apiRequest = async (url, options = {}) => {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
  const timeout = options.timeout || DEFAULT_TIMEOUT;
  const enableRetry = options.retry !== false; // Por defecto true
  const context = options.context || 'API';
  
  // Función fetch principal
  const executeFetch = async () => {
    const { controller, timeoutId } = createTimeoutController(timeout);
    
    try {
      // Obtener headers de autenticación
      const authHeaders = await getAuthHeaders();
      
      const fetchOptions = {
        ...options,
        headers: {
          ...authHeaders,
          ...options.headers,
        },
        signal: controller.signal
      };
      
      // Eliminar opciones personalizadas que no son parte de fetch
      delete fetchOptions.timeout;
      delete fetchOptions.retry;
      delete fetchOptions.context;
      
      const response = await fetch(fullUrl, fetchOptions);
      clearTimeout(timeoutId);

      if (!response.ok) {
        // Parsear mensaje de error del backend
        const errorMessage = await parseErrorResponse(response);
        const errorType = classifyError(null, response.status);
        
        // Sanitizar mensaje para el usuario
        const userMessage = sanitizeErrorMessage(errorMessage, errorType);
        
        // Crear error estructurado
        const structuredError = createStructuredError(
          new Error(errorMessage),
          errorType,
          userMessage,
          { url: fullUrl, status: response.status }
        );
        
        // Log del error
        logError(context, new Error(userMessage), {
          url: fullUrl,
          status: response.status,
          originalMessage: errorMessage
        });
        
        // Lanzar error con mensaje sanitizado
        const error = new Error(userMessage);
        error.status = response.status;
        error.type = errorType;
        error.details = structuredError;
        throw error;
      }

      // Intentar parsear JSON
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      
      return await response.text();
      
    } catch (error) {
      clearTimeout(timeoutId);
      
      // Si es un error que ya procesamos (response.ok = false), re-lanzarlo
      if (error.status) {
        throw error;
      }
      
      // Errores de red o timeout
      const errorType = classifyError(error);
      const userMessage = sanitizeErrorMessage(error.message, errorType);
      
      // Log del error
      logError(context, error, { url: fullUrl });
      
      // Crear error estructurado
      const structuredError = createStructuredError(
        error,
        errorType,
        userMessage,
        { url: fullUrl }
      );
      
      const finalError = new Error(userMessage);
      finalError.type = errorType;
      finalError.details = structuredError;
      throw finalError;
    }
  };
  
  // Ejecutar con o sin reintentos
  if (enableRetry) {
    return await fetchWithRetry(executeFetch, {
      maxRetries: 2,
      context
    });
  } else {
    return await executeFetch();
  }
};

/**
 * GET request
 */
const get = (url, params = {}, options = {}) => {
  const queryString = new URLSearchParams(params).toString();
  const fullUrl = queryString ? `${url}?${queryString}` : url;
  
  return apiRequest(fullUrl, {
    method: 'GET',
    context: 'GET ' + url,
    ...options
  });
};

/**
 * POST request
 */
const post = (url, data = null, options = {}) => {
  const requestOptions = {
    method: 'POST',
    context: 'POST ' + url,
    ...options
  };

  if (data instanceof FormData) {
    requestOptions.body = data;
    // No establecer Content-Type para FormData (el browser lo hace automáticamente)
  } else if (data) {
    requestOptions.headers = {
      'Content-Type': 'application/json',
      ...requestOptions.headers
    };
    requestOptions.body = JSON.stringify(data);
  }

  return apiRequest(url, requestOptions);
};

/**
 * PUT request
 */
const put = (url, data = null, options = {}) => {
  const requestOptions = {
    method: 'PUT',
    context: 'PUT ' + url,
    ...options
  };

  if (data instanceof FormData) {
    requestOptions.body = data;
  } else if (data) {
    requestOptions.headers = {
      'Content-Type': 'application/json',
      ...requestOptions.headers
    };
    requestOptions.body = JSON.stringify(data);
  }

  return apiRequest(url, requestOptions);
};

/**
 * POST request para streaming (SSE - Server Sent Events)
 */
const postStream = async (url, data = null, timeout = 120000) => {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
  
  let timeoutId;
  
  try {
    // Obtener headers de autenticación
    const authHeaders = await getAuthHeaders();
    
    const controller = new AbortController();
    timeoutId = setTimeout(() => controller.abort(), timeout);
    
    const options = {
      method: 'POST',
      headers: {
        ...authHeaders,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
      signal: controller.signal
    };

    console.log('Realizando petición HTTP streaming:', {
      url: fullUrl,
      method: options.method,
      timeout: `${timeout}ms`
    });

    const response = await fetch(fullUrl, options);
    clearTimeout(timeoutId);

    if (!response.ok) {
      console.log('Response not ok:', response.status, response.statusText);
      
      // Parsear error del backend
      const errorMessage = await parseErrorResponse(response);
      const errorType = classifyError(null, response.status);
      const userMessage = sanitizeErrorMessage(errorMessage, errorType);
      
      // Log del error
      logError('POST STREAM ' + url, new Error(userMessage), {
        url: fullUrl,
        status: response.status,
        originalMessage: errorMessage
      });
      
      throw new Error(userMessage);
    }

    return response; // Devolver la respuesta completa para streaming
    
  } catch (error) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    
    // Clasificar y sanitizar error
    const errorType = classifyError(error);
    const userMessage = sanitizeErrorMessage(error.message, errorType);
    
    // Log del error
    logError('POST STREAM ' + url, error, { url: fullUrl });
    
    throw new Error(userMessage);
  }
};

export default {
  get,
  post,
  put,
  apiRequest,
  postStream
};
