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
  
  try {
    // Obtener headers de autenticación
    const authHeaders = await getAuthHeaders();
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    const options = {
      method: 'POST',
      headers: {
        ...authHeaders,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
      signal: controller.signal
    };

    const response = await fetch(fullUrl, options);
    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = `Error ${response.status}`;
      
      try {
        const errorData = JSON.parse(errorText);
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch {
        errorMessage = errorText || errorMessage;
      }
      
      throw new Error(errorMessage);
    }

    return response; // Devolver la respuesta completa para streaming
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('Request was aborted due to timeout');
      throw new Error('La consulta tardó demasiado tiempo. Por favor, intenta nuevamente.');
    }
    console.error('API Stream Request Error:', error.message || error.toString());
    throw error;
  }
};

export default {
  get,
  post,
  put,
  apiRequest,
  postStream
};
