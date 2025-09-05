/**
 * Servicio HTTP simple para la aplicación
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Wrapper simple para fetch con manejo básico de errores
 */
const apiRequest = async (url, options = {}) => {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
  
  try {
    const response = await fetch(fullUrl, {
      ...options,
      headers: {
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

export default {
  get,
  post,
  apiRequest
};
