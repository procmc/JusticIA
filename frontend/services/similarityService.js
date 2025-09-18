import httpService from './httpService';

class SimilarityService {
  constructor() {
    this.currentRequest = null;
  }

  async searchSimilarCases({ searchMode, query, limit = 30, threshold = 0.3 }) {
    // Crear nueva request
    const requestId = Date.now();
    
    try {
      // Cancelar request anterior si existe
      if (this.currentRequest) {
        console.log('Cancelando búsqueda anterior...');
        this.currentRequest.cancelled = true;
      }

      // Configurar nueva request
      this.currentRequest = { id: requestId, cancelled: false };
      const currentRequest = this.currentRequest;

      // Validar parámetros de entrada
      this._validateSearchParams({ searchMode, query, limit, threshold });

      // Preparar payload para el backend (mapear a campos en español)
      const payload = this._buildBackendPayload({ searchMode, query, limit, threshold });
      
      console.log('🔍 Enviando búsqueda de similares:', {
        modo_busqueda: payload.modo_busqueda,
        query_length: query?.length || 0,
        limite: payload.limite,
        umbral: payload.umbral_similitud
      });

      // Hacer llamada al backend
      const response = await httpService.post('/similarity/search', payload);

      // Verificar si la request fue cancelada
      if (currentRequest.cancelled) {
        console.log('Request cancelada después de respuesta');
        return null;
      }

      // Adaptar respuesta del backend al formato del frontend
      const adaptedResults = this._adaptBackendResponse(response);
      
      return adaptedResults;

    } catch (error) {
      if (this.currentRequest && !this.currentRequest.cancelled) {
        console.error('Error en búsqueda de similares:', error);
        throw this._handleError(error);
      }
      return null;
    } finally {
      if (this.currentRequest?.id === requestId) {
        this.currentRequest = null;
      }
    }
  }

  cancelSearch() {
    if (this.currentRequest) {
      console.log('Cancelando búsqueda de similares...');
      this.currentRequest.cancelled = true;
      this.currentRequest = null;
    }
  }

  _validateSearchParams({ searchMode, query, limit, threshold }) {
    // Validar modo de búsqueda
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
      // Validar formato básico de expediente
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

  _buildBackendPayload({ searchMode, query, limit, threshold }) {
    const payload = {
      modo_busqueda: searchMode, // 'descripcion' o 'expediente'
      limite: limit,
      umbral_similitud: threshold
    };

    // Agregar campo específico según modo
    if (searchMode === 'descripcion') {
      payload.texto_consulta = query.trim();
      payload.numero_expediente = null;
    } else {
      payload.numero_expediente = query.trim();
      payload.texto_consulta = null;
    }

    return payload;
  }

  _adaptBackendResponse(backendResponse) {
    try {
      return {
        searchCriteria: backendResponse.criterio_busqueda,
        searchMode: backendResponse.modo_busqueda,
        totalResults: backendResponse.total_resultados,
        similarCases: (backendResponse.casos_similares || []).map(caso => ({
          // IDs y básicos
          id: caso.CN_Id_expediente, // ID real de BD
          expedientId: caso.expediente_id, // ID original del expediente
          expedientNumber: caso.CT_Num_expediente, // Número del expediente
          
          // Similitud
          similarity: caso.puntuacion_similitud,
          similarityPercentage: Math.round(caso.puntuacion_similitud * 100),
          
          // Documentos
          documents: (caso.documentos_coincidentes || []).map(doc => ({
            id: doc.CN_Id_documento, // ID real del documento
            name: doc.CT_Nombre_archivo, // Nombre del archivo
            similarity: doc.puntuacion_similitud,
            similarityPercentage: Math.round(doc.puntuacion_similitud * 100),
            downloadUrl: doc.url_descarga,
            filePath: doc.CT_Ruta_archivo
          })),
          
          // Estadísticas
          totalDocuments: caso.total_documentos,
          
          // Metadatos adicionales
          hasDocuments: (caso.documentos_coincidentes || []).length > 0,
          topDocumentSimilarity: Math.max(
            ...(caso.documentos_coincidentes || []).map(d => d.puntuacion_similitud),
            0
          )
        }))
      };
    } catch (error) {
      console.error('Error adaptando respuesta del backend:', error);
      throw new Error('Error procesando resultados de búsqueda');
    }
  }

  _handleError(error) {
    if (error.response) {
      // Error de respuesta HTTP
      const status = error.response.status;
      const message = error.response.data?.detail || error.response.data?.message || 'Error desconocido';
      
      switch (status) {
        case 400:
          return new Error(`Parámetros inválidos: ${message}`);
        case 404:
          return new Error('Servicio de búsqueda no encontrado');
        case 500:
          return new Error(`Error del servidor: ${message}`);
        default:
          return new Error(`Error HTTP ${status}: ${message}`);
      }
    } else if (error.request) {
      // Error de red
      return new Error('Error de conexión. Verifique su conexión a internet.');
    } else {
      // Error de configuración u otro
      return new Error(error.message || 'Error inesperado en búsqueda');
    }
  }

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
      maxQueryLength: 2000
    };
  }
}

export default new SimilarityService();