/**
 * httpService.js - Servicio HTTP
 * 
 * Filosofía: Este servicio solo maneja lo BÁSICO:
 * - Autenticación (JWT)
 * - Timeout (30s default, configurable)
 * - Propagación de errores del backend SIN sanitizar
 * 
 * Cada servicio específico maneja:
 * - Sus propios reintentos (si los necesita)
 * - Sus propios AbortControllers
 * - Sus propios mensajes de error amigables
 * - Sus propias validaciones
 */

import { getSession } from 'next-auth/react';

class HttpService {
  constructor(config = {}) {
    this.baseURL = config.baseURL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    this.defaultTimeout = config.timeout || 30000; // 30 segundos
  }

  /**
   * Obtener headers con autenticación
   */
  async getAuthHeaders() {
    const session = await getSession();
    const headers = {};
    
    if (session?.accessToken) {
      headers.Authorization = `Bearer ${session.accessToken}`;
    }
    
    return headers;
  }

  /**
   * Crear signal de timeout que se puede fusionar con signal externo
   * Devuelve tanto el signal como la función cleanup
   */
  createTimeoutSignal(timeout, externalSignal = null) {
    const controller = new AbortController();
    
    // Configurar timeout automático
    const timeoutId = setTimeout(() => {
      controller.abort('Request timeout');
    }, timeout);

    // Si hay un signal externo, propagarlo al controller interno
    if (externalSignal) {
      const onExternalAbort = () => {
        clearTimeout(timeoutId);
        controller.abort(externalSignal.reason || 'Request cancelled');
      };
      
      if (externalSignal.aborted) {
        onExternalAbort();
      } else {
        externalSignal.addEventListener('abort', onExternalAbort, { once: true });
      }
    }

    // Cleanup del timeout cuando termine el request
    controller.signal.addEventListener('abort', () => {
      clearTimeout(timeoutId);
    }, { once: true });

    // Devolver tanto el signal como función para cancelar timeout manualmente
    return {
      signal: controller.signal,
      clearTimeout: () => clearTimeout(timeoutId)
    };
  }

  /**
   * Request HTTP básico sin reintentos ni sanitización
   * Propaga errores del backend tal cual para que cada servicio los maneje
   */
  async request(url, options = {}) {
    const { 
      timeout = this.defaultTimeout,
      signal: externalSignal,
      headers = {},
      ...fetchOptions 
    } = options;

    // Obtener token de autenticación
    const authHeaders = await this.getAuthHeaders();

    // Combinar headers
    const finalHeaders = {
      ...headers,
      ...authHeaders
    };

    // Crear signal con timeout (fusionado con signal externo si existe)
    const { signal, clearTimeout: clearTimeoutFn } = this.createTimeoutSignal(timeout, externalSignal);

    // Construir URL completa
    const fullUrl = url.startsWith('http') ? url : `${this.baseURL}${url}`;

    try {
      const response = await fetch(fullUrl, {
        ...fetchOptions,
        headers: finalHeaders,
        signal
      });

      // El fetch ya completó, ahora solo falta parsear el JSON
      clearTimeoutFn();

      // Si no es OK, parsear error del backend
      if (!response.ok) {
        let errorMessage = `Error ${response.status}`;
        let errorData = null;
        
        try {
          const contentType = response.headers.get('content-type');
          if (contentType?.includes('application/json')) {
            errorData = await response.json();
            // Extraer mensaje del backend (puede estar en message, detail, error, etc.)
            errorMessage = errorData.message || errorData.detail || errorData.error || errorMessage;
          } else {
            const text = await response.text();
            errorMessage = text || errorMessage;
          }
        } catch (parseError) {
          console.warn('No se pudo parsear error del backend:', parseError);
        }

        // Manejar sesión expirada (401 Unauthorized)
        if (response.status === 401) {
          // Emitir evento global para que _app.js lo maneje
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new Event('unauthorized'));
          }
        }

        // Crear error con información del backend (SIN SANITIZAR)
        const error = new Error(errorMessage);
        error.status = response.status;
        error.data = errorData;
        
        throw error;
      }

      // Parsear respuesta exitosa
      const contentType = response.headers.get('content-type');
      if (contentType?.includes('application/json')) {
        return await response.json();
      }
      
      // Para streaming o archivos, devolver response raw
      return response;

    } catch (error) {
      // AbortError (timeout o cancelación manual)
      if (error.name === 'AbortError') {
        const abortError = new Error(signal.reason || 'Request aborted');
        abortError.name = 'AbortError';
        abortError.isTimeout = signal.reason === 'Request timeout';
        abortError.isCancelled = !abortError.isTimeout;
        throw abortError;
      }
      
      // Errores de red (TypeError: Failed to fetch)
      if (error instanceof TypeError && error.message.includes('fetch')) {
        const networkError = new Error('No se pudo conectar con el servidor');
        networkError.name = 'NetworkError';
        networkError.isNetworkError = true;
        networkError.originalError = error;
        throw networkError;
      }
      
      // Propagar otros errores sin modificar
      throw error;
    }
  }

  /**
   * GET request
   */
  async get(url, options = {}) {
    return this.request(url, { ...options, method: 'GET' });
  }

  /**
   * POST request
   */
  async post(url, data, options = {}) {
    const isFormData = data instanceof FormData;
    
    return this.request(url, {
      ...options,
      method: 'POST',
      headers: isFormData ? options.headers : { 'Content-Type': 'application/json', ...options.headers },
      body: isFormData ? data : JSON.stringify(data)
    });
  }

  /**
   * PUT request
   */
  async put(url, data, options = {}) {
    return this.request(url, {
      ...options,
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...options.headers },
      body: JSON.stringify(data)
    });
  }

  /**
   * DELETE request
   */
  async delete(url, options = {}) {
    return this.request(url, { ...options, method: 'DELETE' });
  }

  /**
   * POST con streaming (para chat RAG)
   * Devuelve el response raw para que el caller pueda leer el stream
   */
  async postStream(url, data, timeout = 300000, options = {}) {
    const { signal: externalSignal, ...otherOptions } = options;

    // Obtener headers de autenticación
    const authHeaders = await this.getAuthHeaders();

    // Crear signal con timeout largo para streaming
    const { signal, clearTimeout: clearTimeoutFn } = this.createTimeoutSignal(timeout, externalSignal);

    // Construir URL completa
    const fullUrl = url.startsWith('http') ? url : `${this.baseURL}${url}`;

    try {
      const response = await fetch(fullUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
          ...otherOptions.headers
        },
        body: JSON.stringify(data),
        signal
      });

      // No cancelar timeout aquí porque el stream seguirá leyendo datos
      // El caller debe manejar el cleanup

      if (!response.ok) {
        clearTimeoutFn();
        
        let errorMessage = `Error ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.message || errorData.detail || errorMessage;
        } catch (e) {
          // Ignorar error de parsing
        }

        const error = new Error(errorMessage);
        error.status = response.status;
        throw error;
      }

      // Devolver response raw para streaming
      // El caller es responsable de:
      // 1. Leer el stream
      // 2. Llamar clearTimeoutFn() cuando termine
      response._clearTimeout = clearTimeoutFn;
      return response;

    } catch (error) {
      clearTimeoutFn();

      // Manejar errores de abort/timeout
      if (error.name === 'AbortError') {
        const abortError = new Error(signal.reason || 'Request aborted');
        abortError.name = 'AbortError';
        abortError.isTimeout = signal.reason === 'Request timeout';
        abortError.isCancelled = !abortError.isTimeout;
        throw abortError;
      }

      // Errores de red
      if (error instanceof TypeError && error.message.includes('fetch')) {
        const networkError = new Error('No se pudo conectar con el servidor');
        networkError.name = 'NetworkError';
        networkError.isNetworkError = true;
        throw networkError;
      }

      throw error;
    }
  }
}

// Exportar instancia singleton por defecto (para compatibilidad)
const httpService = new HttpService();

export default httpService;

// Exportar clase para casos donde se necesite instancia personalizada
export { HttpService };
