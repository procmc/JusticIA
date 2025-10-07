/**
 * SimilarityService - Servicio para búsqueda de casos similares
 * 
 * Maneja:
 * - Cancelación de búsquedas con AbortController propio
 * - Timeout de 60s para primera búsqueda (warm-up)
 * - Reintentos SOLO para 503 (servidor ocupado/warm-up)
 * - Validaciones de parámetros antes de enviar
 * - Mensajes de error específicos del contexto
 */

import httpService from './httpService';

class SimilarityService {
  constructor() {
    this.abortController = null;
    this.maxRetries503 = 2; // Solo para 503 (servidor ocupado)
    this.retryDelay503 = 5000; // 5 segundos entre reintentos 503
    this.searchTimeout = 120000; // 2 minutos para primera búsqueda (warm-up puede tardar)
  }

  /**
   * Sleep helper
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Buscar casos similares con manejo robusto de errores
   */
  async searchSimilarCases({ searchMode, query, limit = 30, threshold = 0.3 }) {
    try {
      // Cancelar búsqueda anterior si existe
      if (this.abortController) {
        console.log('Cancelando búsqueda anterior...');
        this.abortController.abort('Nueva búsqueda iniciada');
      }

      // Crear nuevo AbortController
      this.abortController = new AbortController();

      // Validar parámetros
      this._validateSearchParams({ searchMode, query, limit, threshold });

      // Preparar payload
      const payload = this._buildBackendPayload({ searchMode, query, limit, threshold });

      // Intentar búsqueda con reintentos SOLO para 503
      for (let attempt = 0; attempt <= this.maxRetries503; attempt++) {
        try {
          const response = await httpService.post('/similarity/search', payload, {
            signal: this.abortController.signal,
            timeout: this.searchTimeout // 2 minutos para primera búsqueda (warm-up puede tardar mucho en CPU)
          });

          // Adaptar respuesta
          return this._adaptBackendResponse(response);

        } catch (error) {
          const isLastAttempt = attempt === this.maxRetries503;

          // Si fue cancelado, salir inmediatamente
          if (error.name === 'AbortError') {
            console.log('Búsqueda cancelada:', error.message);
            return null;
          }

          // Reintentar SOLO si es 503 y no es el último intento
          if (error.status === 503 && !isLastAttempt) {
            console.log(`Servidor ocupado (intento ${attempt + 1}/${this.maxRetries503 + 1}), reintentando en ${this.retryDelay503/1000}s...`);
            await this.sleep(this.retryDelay503);
            continue;
          }

          // Para otros errores o último intento, lanzar con mensaje apropiado
          throw this._handleError(error);
        }
      }

    } catch (error) {
      console.error('Error en búsqueda de similares:', error);
      throw error;
    } finally {
      this.abortController = null;
    }
  }

  /**
   * Generar resumen de caso con IA
   */
  async generateCaseSummary(numeroExpediente) {
    try {
      // Validar entrada
      if (!numeroExpediente || typeof numeroExpediente !== 'string') {
        throw new Error('Número de expediente es requerido');
      }

      const expedienteTrimmed = numeroExpediente.trim();
      if (!expedienteTrimmed) {
        throw new Error('Número de expediente no puede estar vacío');
      }

      // Validar formato
      const expedientPattern = /^[0-9]{2,4}-[A-Z0-9]{6,8}-[0-9]{4,6}(-[A-Z]{1,2})?$/;
      if (!expedientPattern.test(expedienteTrimmed)) {
        throw new Error('Formato de número de expediente inválido');
      }

      // Llamada al backend con timeout largo (puede tardar)
      const response = await httpService.post('/similarity/generate-summary', {
        numero_expediente: expedienteTrimmed
      }, {
        timeout: 120000 // 2 minutos para generación con IA
      });

      // Validar respuesta del backend
      if (!response) {
        throw new Error('El servidor no devolvió ninguna respuesta');
      }

      if (!response.resumen_ia) {
        throw new Error('La respuesta del servidor no contiene resumen de IA');
      }

      // Devolver estructura válida siempre
      return {
        numeroExpediente: response.numero_expediente || expedienteTrimmed,
        totalDocumentosAnalizados: response.total_documentos_analizados || 0,
        tiempoGeneracionSegundos: response.tiempo_generacion_segundos || 0,
        resumen: response.resumen_ia.resumen || 'No se pudo generar el resumen',
        palabrasClave: Array.isArray(response.resumen_ia.palabras_clave) ? response.resumen_ia.palabras_clave : [],
        factoresSimilitud: Array.isArray(response.resumen_ia.factores_similitud) ? response.resumen_ia.factores_similitud : [],
        conclusion: response.resumen_ia.conclusion || 'No se pudo generar la conclusión'
      };

    } catch (error) {
      console.error('Error generando resumen de IA:', error);
      throw this._handleError(error);
    }
  }

  /**
   * Cancelar búsqueda en progreso
   */
  cancelSearch() {
    if (this.abortController) {
      console.log('Cancelando búsqueda de similares...');
      this.abortController.abort('Cancelado por el usuario');
      this.abortController = null;
    }
  }

  /**
   * Validar parámetros de búsqueda
   */
  _validateSearchParams({ searchMode, query, limit, threshold }) {
    // Validar modo
    if (!['descripcion', 'expediente'].includes(searchMode)) {
      throw new Error('Modo de búsqueda debe ser "descripcion" o "expediente"');
    }

    // Validar query según modo
    if (searchMode === 'descripcion') {
      if (!query || query.trim().length === 0) {
        throw new Error('Texto de consulta es requerido para búsqueda por descripción');
      }
      if (query.length > 2000) {
        throw new Error('Texto de consulta no puede exceder 2000 caracteres');
      }
    } else if (searchMode === 'expediente') {
      if (!query || query.trim().length === 0) {
        throw new Error('Número de expediente es requerido para búsqueda por expediente');
      }
      const expedientPattern = /^[0-9]{2,4}-[A-Z0-9]{6,8}-[0-9]{4,6}(-[A-Z]{1,2})?$/;
      if (!expedientPattern.test(query.trim())) {
        throw new Error('Formato de número de expediente inválido');
      }
    }

    // Validar límite
    if (limit < 1 || limit > 100) {
      throw new Error('Límite debe estar entre 1 y 100');
    }

    // Validar umbral
    if (threshold < 0.0 || threshold > 1.0) {
      throw new Error('Umbral de similitud debe estar entre 0.0 y 1.0');
    }
  }

  /**
   * Construir payload para backend
   */
  _buildBackendPayload({ searchMode, query, limit, threshold }) {
    const payload = {
      modo_busqueda: searchMode,
      limite: limit,
      umbral_similitud: threshold
    };

    if (searchMode === 'descripcion') {
      payload.texto_consulta = query.trim();
      payload.numero_expediente = null;
    } else {
      payload.numero_expediente = query.trim();
      payload.texto_consulta = null;
    }

    return payload;
  }

  /**
   * Adaptar respuesta del backend al formato del frontend
   */
  _adaptBackendResponse(backendResponse) {
    try {
      // Validar que existe respuesta
      if (!backendResponse) {
        throw new Error('Respuesta del backend vacía');
      }

      return {
        searchCriteria: backendResponse.criterio_busqueda || '',
        searchMode: backendResponse.modo_busqueda || '',
        totalResults: backendResponse.total_resultados || 0,
        searchStats: {
          searchTime: backendResponse.tiempo_busqueda_segundos || 0,
          averagePrecision: backendResponse.precision_promedio || 0
        },
        similarCases: (backendResponse.casos_similares || []).map(caso => {
          // Validación defensiva por caso
          if (!caso) return null;
          
          return {
            id: caso.CN_Id_expediente || '',
            expedientId: caso.expediente_id || '',
            expedientNumber: caso.CT_Num_expediente || '',
            date: caso.fecha_creacion || '',  // Fecha de creación del expediente
            similarity: caso.puntuacion_similitud || 0,
            similarityPercentage: Math.round((caso.puntuacion_similitud || 0) * 100),
            documents: (caso.documentos_coincidentes || []).map(doc => {
              if (!doc) return null;
              return {
                id: doc.CN_Id_documento || '',
                name: doc.CT_Nombre_archivo || 'Sin nombre',
                similarity: doc.puntuacion_similitud || 0,
                similarityPercentage: Math.round((doc.puntuacion_similitud || 0) * 100),
                filePath: doc.CT_Ruta_archivo || ''
              };
            }).filter(Boolean), // Eliminar nulls
            totalDocuments: caso.total_documentos || 0,
            hasDocuments: (caso.documentos_coincidentes || []).length > 0,
            topDocumentSimilarity: Math.max(
              ...(caso.documentos_coincidentes || []).map(d => d?.puntuacion_similitud || 0),
              0
            )
          };
        }).filter(Boolean) // Eliminar nulls
      };
    } catch (error) {
      console.error('Error adaptando respuesta del backend:', error);
      throw new Error('Error procesando resultados de búsqueda');
    }
  }

  /**
   * Manejar errores con mensajes específicos
   */
  _handleError(error) {
    // Errores de cancelación
    if (error.name === 'AbortError') {
      if (error.isTimeout) {
        return new Error('La búsqueda tardó demasiado tiempo. Intente con criterios más específicos.');
      }
      return new Error('Búsqueda cancelada');
    }

    // Errores de red
    if (error.isNetworkError) {
      return new Error('No se pudo conectar con el servidor. Verifique su conexión a internet.');
    }

    // Errores HTTP específicos
    if (error.status) {
      switch (error.status) {
        case 400:
          return new Error(`Parámetros inválidos: ${error.message}`);
        
        case 404:
          if (error.message.includes('expediente')) {
            return new Error('No se encontró el expediente especificado');
          }
          return new Error('Servicio de búsqueda no encontrado');
        
        case 500:
          return new Error('Error interno del servidor. Intente nuevamente en unos momentos.');
        
        case 503:
          return new Error('El servidor está ocupado o iniciándose. Por favor, espere unos segundos e intente de nuevo.');
        
        case 504:
          return new Error('El servidor tardó demasiado en responder. Intente con criterios más específicos.');
        
        default:
          return new Error(error.message || `Error del servidor (${error.status})`);
      }
    }

    // Error genérico
    return new Error(error.message || 'Error inesperado en búsqueda');
  }

  /**
   * Obtener configuración del servicio
   */
  getServiceConfig() {
    return {
      supportedModes: ['descripcion', 'expediente'],
      limits: {
        min: 1,
        max: 100,
        default: 30
      },
      threshold: {
        min: 0.0,
        max: 1.0,
        default: 0.3
      },
      maxQueryLength: 2000,
      timeouts: {
        search: 120000, // 2min (primera búsqueda con warm-up)
        summary: 120000 // 2min
      },
      retries: {
        status503: this.maxRetries503,
        delay503: this.retryDelay503
      }
    };
  }
}

// Exportar instancia singleton
const similarityService = new SimilarityService();

export default similarityService;

// Exportar clase para testing
export { SimilarityService };
