/**
 * Servicio HTTP Cliente con Autenticación y Gestión de Timeouts.
 * 
 * @module services/httpService
 * 
 * Cliente HTTP minimalista que maneja las operaciones básicas de comunicación
 * con el backend, delegando lógica compleja a servicios específicos.
 * 
 * Filosofía de diseño:
 *   - BÁSICO: Solo autenticación, timeouts, y propagación de errores
 *   - DELEGACIÓN: Cada servicio maneja sus propios reintentos y validaciones
 *   - TRANSPARENCIA: Errores del backend se propagan sin sanitizar
 * 
 * Responsabilidades del httpService:
 *   - Autenticación: Inyección automática de JWT desde NextAuth
 *   - Timeout: 30s por defecto, configurable por petición
 *   - Propagación de errores: Sin transformación ni ocultamiento
 * 
 * Responsabilidades delegadas a servicios específicos:
 *   - Reintentos: Cada servicio decide si y cómo reintentar
 *   - AbortControllers: Control granular de cancelación
 *   - Mensajes amigables: Traducción de errores técnicos
 *   - Validaciones: Validación de datos antes de enviar
 * 
 * Configuración de timeouts:
 *   - Por defecto: 30 segundos
 *   - Configurable: Pasar `timeout` en options
 *   - Sin timeout: Pasar `timeout: null` o usar fetchStream
 * 
 * @example
 * ```javascript
 * import httpService from '@/services/httpService';
 * 
 * // GET con timeout por defecto (30s)
 * const data = await httpService.get('/usuarios');
 * 
 * // POST con timeout personalizado
 * const result = await httpService.post('/auth/login', 
 *   { username: 'admin', password: 'secret' },
 *   { timeout: 10000 } // 10 segundos
 * );
 * 
 * // Streaming sin timeout
 * const response = await httpService.fetchStream(
 *   '/rag/consulta-stream',
 *   { pregunta: '¿Qué es esto?' }
 * );
 * 
 * // Control manual de cancelación
 * const controller = new AbortController();
 * httpService.get('/data', { signal: controller.signal });
 * setTimeout(() => controller.abort(), 5000);
 * ```
 * 
 * @see {@link getSession} NextAuth session management
 */

import { getSession } from 'next-auth/react';

/**
 * Cliente HTTP básico con autenticación automática y timeouts.
 * 
 * Maneja operaciones HTTP fundamentales delegando lógica compleja
 * a servicios específicos del dominio.
 * 
 * @class HttpService
 * @category Services
 */
class HttpService {
  /**
   * Construye el servicio HTTP con configuración personalizable.
   * 
   * @constructor
   * @param {Object} [config={}] - Configuración del servicio
   * @param {string} [config.baseURL] - URL base del backend (default: NEXT_PUBLIC_API_URL o localhost:8000)
   * @param {number} [config.timeout=30000] - Timeout por defecto en milisegundos
   * 
   * @example
   * ```javascript
   * // Con configuración por defecto
   * const httpService = new HttpService();
   * 
   * // Con configuración personalizada
   * const httpService = new HttpService({
   *   baseURL: 'https://api.example.com',
   *   timeout: 60000
   * });
   * ```
   */
  constructor(config = {}) {
    this.baseURL = config.baseURL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    this.defaultTimeout = config.timeout || 30000; // 30 segundos
  }

  /**
   * Obtiene headers HTTP con token de autenticación inyectado.
   * 
   * Recupera el JWT del contexto de NextAuth y lo agrega al header
   * Authorization con formato Bearer. Si no hay sesión activa,
   * retorna headers vacíos.
   * 
   * @async
   * @returns {Promise<Object>} Headers con Authorization si hay token
   * 
   * @example
   * ```javascript
   * const headers = await httpService.getAuthHeaders();
   * // { Authorization: 'Bearer eyJhbGc...' }
   * ```
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
   * Crea un signal de timeout que se puede fusionar con un signal externo.
   * 
   * Utiliza AbortController para cancelar peticiones que excedan el tiempo
   * límite. Soporta fusión con signals externos para control manual de cancelación.
   * Incluye limpieza automática del timeout cuando la petición finaliza.
   * 
   * @param {number} timeout - Tiempo límite en milisegundos
   * @param {AbortSignal} [externalSignal=null] - Signal externo para fusionar
   * @returns {Object} Objeto con:
   *   - signal {AbortSignal}: Signal para pasar a fetch
   *   - clearTimeout {Function}: Función para cancelar timeout manualmente
   * 
   * @example
   * ```javascript
   * // Timeout simple
   * const { signal, clearTimeout } = httpService.createTimeoutSignal(5000);
   * try {
   *   const response = await fetch(url, { signal });
   *   clearTimeout(); // Cancelar timeout al completar
   * } catch (error) {
   *   if (error.name === 'AbortError') {
   *     console.log('Request timeout o cancelado');
   *   }
   * }
   * 
   * // Con signal externo (control manual)
   * const externalController = new AbortController();
   * const { signal } = httpService.createTimeoutSignal(
   *   30000,
   *   externalController.signal
   * );
   * // Cancelar manualmente antes del timeout
   * externalController.abort();
   * ```
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
   * Ejecuta una petición HTTP básica sin reintentos ni sanitización de errores.
   * 
   * Método de bajo nivel que propaga errores del backend sin modificación,
   * permitiendo que servicios específicos manejen errores según su contexto.
   * Agrega autenticación automática y timeout configurable.
   * 
   * @async
   * @param {string} url - URL relativa o absoluta del endpoint
   * @param {Object} [options={}] - Opciones de la petición
   * @param {string} [options.method='GET'] - Método HTTP
   * @param {Object|FormData} [options.body] - Cuerpo de la petición
   * @param {Object} [options.headers={}] - Headers adicionales
   * @param {number} [options.timeout] - Timeout personalizado en ms
   * @param {AbortSignal} [options.signal] - Signal externo para cancelación
   * @returns {Promise<Object>} Respuesta parseada del backend
   * @throws {Error} Error con código de estado HTTP o mensaje de red
   * 
   * @example
   * ```javascript
   * // GET simple
   * const data = await httpService.request('/api/usuarios');
   * 
   * // POST con body y timeout personalizado
   * const result = await httpService.request('/api/login', {
   *   method: 'POST',
   *   body: { username: 'admin', password: 'secret' },
   *   timeout: 10000
   * });
   * 
   * // Con FormData (upload)
   * const formData = new FormData();
   * formData.append('file', file);
   * await httpService.request('/api/upload', {
   *   method: 'POST',
   *   body: formData
   * });
   * ```
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
   * Ejecuta una petición HTTP GET.
   * 
   * @async
   * @param {string} url - URL del endpoint
   * @param {Object} [options={}] - Opciones adicionales (headers, timeout, signal)
   * @returns {Promise<Object>} Respuesta parseada del servidor
   * 
   * @example
   * ```javascript
   * // GET simple
   * const usuarios = await httpService.get('/usuarios');
   * 
   * // GET con timeout personalizado
   * const data = await httpService.get('/data', { timeout: 5000 });
   * ```
   */
  async get(url, options = {}) {
    return this.request(url, { ...options, method: 'GET' });
  }

  /**
   * Ejecuta una petición HTTP POST.
   * 
   * Soporta automáticamente FormData (para uploads) y JSON.
   * 
   * @async
   * @param {string} url - URL del endpoint
   * @param {Object|FormData} data - Datos a enviar
   * @param {Object} [options={}] - Opciones adicionales
   * @returns {Promise<Object>} Respuesta parseada del servidor
   * 
   * @example
   * ```javascript
   * // POST con JSON
   * const result = await httpService.post('/auth/login', {
   *   username: 'admin',
   *   password: 'secret'
   * });
   * 
   * // POST con FormData (upload)
   * const formData = new FormData();
   * formData.append('file', file);
   * await httpService.post('/upload', formData);
   * ```
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
   * Ejecuta una petición HTTP PUT.
   * 
   * @async
   * @param {string} url - URL del endpoint
   * @param {Object} data - Datos a enviar (se serializa a JSON)
   * @param {Object} [options={}] - Opciones adicionales
   * @returns {Promise<Object>} Respuesta parseada del servidor
   * 
   * @example
   * ```javascript
   * await httpService.put('/usuarios/123', {
   *   nombre: 'Juan Actualizado',
   *   email: 'juan@example.com'
   * });
   * ```
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
   * Ejecuta una petición HTTP DELETE.
   * 
   * @async
   * @param {string} url - URL del endpoint
   * @param {Object} [options={}] - Opciones adicionales
   * @returns {Promise<Object>} Respuesta parseada del servidor
   * 
   * @example
   * ```javascript
   * await httpService.delete('/usuarios/123');
   * ```
   */
  async delete(url, options = {}) {
    return this.request(url, { ...options, method: 'DELETE' });
  }

  /**
   * Ejecuta una petición HTTP POST con soporte para streaming (SSE).
   * 
   * Utilizado principalmente para el chat RAG donde las respuestas del LLM
   * se envían progresivamente mediante Server-Sent Events. Retorna el
   * response raw para que el llamador pueda leer el stream chunk por chunk.
   * 
   * @async
   * @param {string} url - URL del endpoint
   * @param {Object} data - Datos a enviar (se serializa a JSON)
   * @param {number} [timeout=300000] - Timeout largo (5 min) para streaming
   * @param {Object} [options={}] - Opciones adicionales
   * @returns {Promise<Response>} Response raw de fetch para leer stream
   * 
   * @example
   * ```javascript
   * const response = await httpService.postStream(
   *   '/rag/consulta-stream',
   *   { pregunta: '¿Qué es esto?', historial: [] }
   * );
   * 
   * const reader = response.body.getReader();
   * const decoder = new TextDecoder();
   * 
   * while (true) {
   *   const { done, value } = await reader.read();
   *   if (done) break;
   *   const chunk = decoder.decode(value);
   *   console.log(chunk);
   * }
   * ```
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
