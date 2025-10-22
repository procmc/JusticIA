/**
 * DownloadService - Servicio para descargar archivos
 * 
 * Maneja errores de forma amigable sin causar crashes en el frontend
 */

import { getSession } from 'next-auth/react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class DownloadService {
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
   * Descarga un archivo usando su ruta completa
   * @param {string} rutaArchivo - Ruta completa del archivo
   * @param {string} nombreArchivo - Nombre del archivo para la descarga
   * @returns {Promise<void>}
   */
  async downloadFile(rutaArchivo, nombreArchivo) {
    try {
      // Validar parámetros
      if (!rutaArchivo || rutaArchivo.trim() === '') {
        throw new Error('La ruta del archivo es requerida');
      }

      // Agregar timestamp para evitar cache
      const timestamp = Date.now();
      const url = `${API_BASE_URL}/archivos/download?ruta_archivo=${encodeURIComponent(rutaArchivo)}&_t=${timestamp}`;
      
      // Obtener headers con autenticación
      const authHeaders = await this.getAuthHeaders();
      
      // Hacer petición fetch para obtener el archivo
      const response = await fetch(url, {
        method: 'GET',
        cache: 'no-cache',
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0',
          ...authHeaders
        }
      });

      // Manejo específico por código de error
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Su sesión ha expirado. Por favor, inicie sesión nuevamente.');
        }
        
        if (response.status === 404) {
          throw new Error('El archivo no existe o fue eliminado');
        }
        
        if (response.status === 403) {
          throw new Error('No tiene permisos para descargar este archivo');
        }
        
        if (response.status === 500) {
          throw new Error('Error del servidor al procesar el archivo. Intente nuevamente.');
        }

        if (response.status >= 500) {
          throw new Error('El servidor no está disponible. Intente nuevamente en unos momentos.');
        }

        throw new Error(`No se pudo descargar el archivo (Error ${response.status})`);
      }

      // Convertir la respuesta a blob
      const blob = await response.blob();

      if (blob.size === 0) {
        throw new Error('El archivo está vacío');
      }

      // Crear URL temporal para el blob
      const blobUrl = window.URL.createObjectURL(blob);

      // Crear enlace de descarga
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = nombreArchivo || 'archivo';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);

      // Limpiar URL temporal
      window.URL.revokeObjectURL(blobUrl);
      
    } catch (error) {
      console.error('Error en descarga:', error);
      
      // Mensajes amigables para errores de red
      if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        throw new Error('No se pudo conectar con el servidor. Verifique su conexión a internet.');
      }

      // Propagar el error con mensaje amigable
      throw new Error(error.message || 'Error al descargar el archivo');
    }
  }

  /**
   * Abre un archivo en una nueva pestaña para vista previa
   * NOTA: Este método tiene limitaciones de autenticación ya que window.open
   * no permite enviar headers personalizados con el token JWT.
   * @param {string} rutaArchivo - Ruta completa del archivo
   * @returns {Promise<void>}
   */
  async viewFile(rutaArchivo) {
    try {
      // Validar parámetros
      if (!rutaArchivo || rutaArchivo.trim() === '') {
        throw new Error('La ruta del archivo es requerida');
      }

      // LIMITACIÓN: window.open no puede enviar headers de autenticación
      // Para vista previa autenticada, se necesitaría otra implementación
      const url = `${API_BASE_URL}/archivos/download?ruta_archivo=${encodeURIComponent(rutaArchivo)}`;
      window.open(url, '_blank');
      
    } catch (error) {
      console.error('Error abriendo archivo:', error);
      throw new Error(error.message || 'Error al abrir el archivo');
    }
  }
}

// Exportar instancia singleton
const downloadService = new DownloadService();

export default downloadService;

// Exportar clase para testing o instancias personalizadas
export { DownloadService };