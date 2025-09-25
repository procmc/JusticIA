/**
 * Servicio HTTP simple para la aplicación
 */
import { getSession } from 'next-auth/react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
 * Wrapper simple para fetch con manejo básico de errores y auth automática
 */
const apiRequest = async (url, options = {}) => {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
  
  try {
    // Obtener headers de autenticación
    const authHeaders = await getAuthHeaders();
    
    const response = await fetch(fullUrl, {
      ...options,
      headers: {
        ...authHeaders,
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = `Error ${response.status}`;
      
      try {
        const errorData = JSON.parse(errorText);
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch {
        errorMessage = errorText || errorMessage;
      }
      
      // Asegurar que sea string
      if (typeof errorMessage !== 'string') {
        errorMessage = String(errorMessage);
      }
      
      throw new Error(errorMessage);
    }

    // Intentar parsear JSON
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }
    
    return await response.text();
  } catch (error) {
    console.error('API Request Error:', error.message || error.toString());
    throw error;
  }
};

/**
 * GET request
 */
const get = (url, params = {}) => {
  const queryString = new URLSearchParams(params).toString();
  const fullUrl = queryString ? `${url}?${queryString}` : url;
  
  return apiRequest(fullUrl, {
    method: 'GET',
  });
};

/**
 * POST request
 */
const post = (url, data = null) => {
  const options = {
    method: 'POST',
  };

  if (data instanceof FormData) {
    options.body = data;
    // No establecer Content-Type para FormData
  } else if (data) {
    options.headers = {
      'Content-Type': 'application/json',
    };
    options.body = JSON.stringify(data);
  }

  return apiRequest(url, options);
};

/**
 * PUT request
 */
const put = (url, data = null) => {
  const options = {
    method: 'PUT',
  };

  if (data instanceof FormData) {
    options.body = data;
    // No establecer Content-Type para FormData
  } else if (data) {
    options.headers = {
      'Content-Type': 'application/json',
    };
    options.body = JSON.stringify(data);
  }

  return apiRequest(url, options);
};

/**
 * POST request para streaming
 */
const postStream = async (url, data = null, timeout = 120000) => { // 2 minutos timeout
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
  
  // Declarar timeoutId fuera del try para que esté disponible en el catch
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

    console.log('🌐 Realizando petición HTTP streaming:', {
      url: fullUrl,
      method: options.method,
      headers: options.headers,
      bodySize: options.body ? options.body.length : 0,
      bodyPreview: options.body ? options.body.substring(0, 500) : 'NO BODY'
    });
    


    const response = await fetch(fullUrl, options);
    clearTimeout(timeoutId);

    if (!response.ok) {
      console.log('❌ Response not ok:', response.status, response.statusText);
      
      let errorMessage = `Error ${response.status}: ${response.statusText}`;
      
      try {
        const errorText = await response.text();
        console.log('📄 Error response text:', errorText);
        
        if (errorText) {
          try {
            const errorData = JSON.parse(errorText);
            // Si el error tiene detalles de validación (array), procesarlos
            if (Array.isArray(errorData.detail)) {
              const validationErrors = errorData.detail.map(err => 
                `${err.loc ? err.loc.join('.') : 'campo'}: ${err.msg}`
              ).join('; ');
              errorMessage = `Errores de validación: ${validationErrors}`;
            } else {
              errorMessage = errorData.detail || errorData.message || errorText || errorMessage;
            }
          } catch (parseError) {
            // Si no es JSON válido, usar el texto tal como viene
            errorMessage = errorText || errorMessage;
          }
        }
      } catch (readError) {
        console.log('⚠️ Error leyendo response:', readError);
      }
      
      console.log('🎯 Final error message:', errorMessage);
      throw new Error(String(errorMessage));
    }

    return response; // Devolver la respuesta completa para streaming
  } catch (error) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    
    if (error.name === 'AbortError') {
      console.log('Request was aborted due to timeout');
      throw new Error('La consulta tardó demasiado tiempo. Por favor, intenta nuevamente.');
    }
    
    // Mejor manejo de errores de conexión
    if (error.message === 'Failed to fetch' || error.name === 'TypeError') {
      console.error('🔌 Error de conexión con el backend:', fullUrl);
      throw new Error(`No se puede conectar con el servidor backend (${API_BASE_URL}). Verifica que el servidor esté ejecutándose.`);
    }
    
    console.error('API Stream Request Error:', {
      message: error.message,
      name: error.name,
      url: fullUrl,
      error: error
    });
    
    // Asegurar que siempre lanzamos un string como mensaje de error
    const errorMessage = typeof error === 'string' ? error : (error.message || error.toString() || 'Error de conexión con el servidor');
    throw new Error(errorMessage);
  }
};

export default {
  get,
  post,
  put,
  apiRequest,
  postStream
};
