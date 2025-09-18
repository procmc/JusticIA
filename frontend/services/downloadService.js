/**
 * Servicio para descargar archivos usando las rutas centralizadas en /archivos
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class DownloadService {
  /**
   * Descarga un archivo usando su ruta completa
   * @param {string} rutaArchivo - Ruta completa del archivo
   * @param {string} nombreArchivo - Nombre del archivo para la descarga
   * @returns {Promise<void>}
   */
   async downloadFile(rutaArchivo, nombreArchivo) {
     try {
       // Agregar timestamp para evitar cache
       const timestamp = Date.now();
       const url = `${API_BASE_URL}/archivos/download?ruta_archivo=${encodeURIComponent(rutaArchivo)}&_t=${timestamp}`;
       
       // Hacer petición fetch para obtener el archivo
       const response = await fetch(url, {
         method: 'GET',
         cache: 'no-cache',
         headers: {
           'Cache-Control': 'no-cache, no-store, must-revalidate',
           'Pragma': 'no-cache',
           'Expires': '0'
         }
       });

       if (!response.ok) {
         throw new Error(`Error HTTP: ${response.status} - ${response.statusText}`);
       }

       // Convertir la respuesta a blob
       const blob = await response.blob();

       if (blob.size === 0) {
         throw new Error('El archivo descargado está vacío');
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
       throw error;
     }
   }

  /**
   * Abre un archivo en una nueva pestaña para vista previa
   * @param {string} rutaArchivo - Ruta completa del archivo
   * @returns {Promise<void>}
   */
  async viewFile(rutaArchivo) {
    try {
      const url = `${API_BASE_URL}/archivos/download?ruta_archivo=${encodeURIComponent(rutaArchivo)}`;
      window.open(url, '_blank');
    } catch (error) {
      console.error('Error abriendo archivo:', error);
      throw error;
    }
  }
}

const downloadService = new DownloadService();
export default downloadService;