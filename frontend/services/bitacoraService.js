/**
 * bitacoraService.js - Servicio de Bitácora
 * 
 * Maneja operaciones relacionadas con la auditoría y bitácora del sistema:
 * - Consulta de registros con filtros
 * - Estadísticas agregadas
 * - Historial de usuario
 * - Historial por expediente
 */

import httpService from './httpService';

class BitacoraService {
  constructor() {
    this.baseURL = '/bitacora';
  }

  /**
   * Obtener registros de bitácora con filtros múltiples y paginación server-side
   * Solo accesible para administradores
   * 
   * @param {Object} filtros - Filtros de búsqueda
   * @param {string} filtros.usuario - Nombre o correo de usuario
   * @param {number} filtros.tipoAccion - ID del tipo de acción (1-15)
   * @param {string} filtros.expediente - Número de expediente
   * @param {string} filtros.fechaInicio - Fecha inicio ISO
   * @param {string} filtros.fechaFin - Fecha fin ISO
   * @param {number} filtros.page - Número de página (default: 1)
   * @param {number} filtros.limit - Registros por página (default: 10, max: 100)
   * @returns {Promise<Object>} { items: Array, total: number, page: number, pages: number }
   */
  async obtenerRegistros(filtros = {}) {
    try {
      // Construir query params (solo incluir los que tienen valor)
      const params = new URLSearchParams();
      
      if (filtros.usuario) params.append('usuario', filtros.usuario);
      if (filtros.tipoAccion) params.append('tipoAccion', filtros.tipoAccion);
      if (filtros.expediente) params.append('expediente', filtros.expediente);
      
      // Convertir fechas a formato ISO completo (con hora) para FastAPI
      if (filtros.fechaInicio) {
        // Agregar 00:00:00 al inicio del día
        params.append('fechaInicio', `${filtros.fechaInicio}T00:00:00`);
      }
      if (filtros.fechaFin) {
        // Agregar 23:59:59 al final del día
        params.append('fechaFin', `${filtros.fechaFin}T23:59:59`);
      }
      
      // Paginación
      const page = filtros.page || 1;
      const limit = filtros.limit || 10;
      const offset = (page - 1) * limit;
      
      params.append('limite', limit);
      params.append('offset', offset);

      const queryString = params.toString();
      const url = `${this.baseURL}/registros${queryString ? `?${queryString}` : ''}`;

      const data = await httpService.get(url);
    
      // Mapear campos del backend al formato del frontend
      return {
        registros: this._mapearRegistros(data.items || []),
        total: data.total || 0,
        page: data.page || 1,
        pages: data.pages || 1,
        limit: data.limit || limit
      };
      
    } catch (error) {
      console.error('Error obteniendo registros de bitácora:', error);
      
      // Extraer mensaje de error detallado
      let mensajeError = 'Error al obtener registros de bitácora';
      
      if (error.data?.detail) {
        // FastAPI 422 devuelve detail como array o string
        if (Array.isArray(error.data.detail)) {
          mensajeError = error.data.detail.map(e => e.msg || e.message).join(', ');
        } else {
          mensajeError = error.data.detail;
        }
      } else if (error.message) {
        mensajeError = error.message;
      }
      
      throw new Error(mensajeError);
    }
  }

  /**
   * Obtener estadísticas agregadas de la bitácora
   * Solo accesible para administradores
   */
  async obtenerEstadisticas(dias = 30) {
    try {
      const data = await httpService.get(
        `${this.baseURL}/estadisticas?dias=${dias}`
      );
      
      return {
        registrosHoy: data.registrosHoy || 0,
        registros7Dias: data.registros7Dias || 0,
        registros30Dias: data.registros30Dias || 0,
        totalRegistros: data.totalRegistros || 0,
        usuariosUnicos: data.usuariosUnicos || 0,
        expedientesUnicos: data.expedientesUnicos || 0,
        accionesPorTipo: data.accionesPorTipo || [],
        usuariosMasActivos: data.usuariosMasActivos || [],
        expedientesMasConsultados: data.expedientesMasConsultados || [],
        actividadPorDia: data.actividadPorDia || []
      };
      
    } catch (error) {
      console.error('Error obteniendo estadísticas de bitácora:', error);
      throw new Error(
        error.message || 'Error al obtener estadísticas'
      );
    }
  }

  /**
   * Obtener historial del usuario autenticado
   * Accesible para usuarios judiciales y administradores
   */
  async obtenerMiHistorial(limite = 100, tipoAccion = null) {
    try {
      const params = new URLSearchParams({ limite: limite.toString() });
      if (tipoAccion) params.append('tipoAccion', tipoAccion);

      const data = await httpService.get(
        `${this.baseURL}/mi-historial?${params.toString()}`
      );
      
      return this._mapearRegistros(data);
      
    } catch (error) {
      console.error('Error obteniendo mi historial:', error);
      throw new Error(
        error.message || 'Error al obtener tu historial'
      );
    }
  }

  /**
   * Registrar exportación de bitácora
   * Llama al backend para registrar la acción de exportación
   */
  async registrarExportacion() {
    try {
      await httpService.post(`${this.baseURL}/registrar-exportacion`);
    } catch (error) {
      // No lanzamos error para no bloquear la exportación
      console.error('Error registrando exportación en bitácora:', error);
    }
  }

  /**
   * Obtener historial de un expediente específico
   * Muestra todas las acciones realizadas sobre ese expediente
   */
  async obtenerHistorialExpediente(expedienteNumero, limite = 100) {
    try {
      if (!expedienteNumero) {
        throw new Error('Número de expediente es requerido');
      }

      const data = await httpService.get(
        `${this.baseURL}/expediente/${encodeURIComponent(expedienteNumero)}?limite=${limite}`
      );
      
      return this._mapearRegistros(data);
      
    } catch (error) {
      console.error(`Error obteniendo historial del expediente ${expedienteNumero}:`, error);
      throw new Error(
        error.message || 'Error al obtener historial del expediente'
      );
    }
  }

  /**
   * Mapear registros del formato backend al formato frontend
   * Backend usa nomenclatura CN_*, CT_*, CF_*
   * Frontend usa camelCase
   */
  _mapearRegistros(registros) {
    if (!Array.isArray(registros)) return [];

    return registros.map(registro => {
      const mapeado = {
        id: registro.CN_Id_bitacora || registro.id_bitacora || registro.id,
        fechaHora: registro.CF_Fecha_hora || registro.fecha_hora || registro.fechaHora,
        texto: registro.CT_Texto || registro.texto,
        informacionAdicional: this._parseJSON(
          registro.CT_Informacion_adicional || registro.info_adicional || registro.informacionAdicional
        ),
        
        // IDs relacionados
        idUsuario: registro.CN_Id_usuario || registro.id_usuario || registro.idUsuario,
        idTipoAccion: registro.CN_Id_tipo_accion || registro.id_tipo_accion || registro.idTipoAccion,
        idExpediente: registro.CN_Id_expediente || registro.id_expediente || registro.idExpediente,
        
        // Datos relacionados (si están expandidos)
        usuario: registro.usuario || registro.nombre_usuario || 'Usuario desconocido',
        correoUsuario: registro.correoUsuario || registro.correo_usuario || null,
        tipoAccion: registro.tipoAccion || registro.tipo_accion || registro.nombre_tipo_accion || this._mapearTipoAccion(registro.idTipoAccion || registro.CN_Id_tipo_accion || registro.id_tipo_accion),
        expediente: registro.expediente || registro.numero_expediente || null,
        
        // Campos adicionales útiles para UI
        rolUsuario: registro.rol_usuario || registro.rolUsuario || null,
        estado: registro.estado || 'Procesado',
        ip: registro.ip || null,
        navegador: registro.navegador || null,
        duracion: registro.duracion || null
      };

      return mapeado;
    });
  }

  /**
   * Parsear JSON de forma segura
   */
  _parseJSON(jsonString) {
    if (!jsonString) return null;
    if (typeof jsonString === 'object') return jsonString;
    
    try {
      return JSON.parse(jsonString);
    } catch (e) {
      return jsonString;
    }
  }

  /**
   * Mapear ID de tipo de acción a nombre legible
   */
  _mapearTipoAccion(idTipo) {
    const tipos = {
      1: 'Búsqueda de Casos Similares',
      2: 'Carga de Documentos',
      3: 'Login',
      4: 'Logout',
      5: 'Cambio de Contraseña',
      6: 'Recuperación de Contraseña',
      7: 'Crear Usuario',
      8: 'Editar Usuario',
      9: 'Consultar Usuarios',
      10: 'Descargar Archivo',
      11: 'Listar Archivos',
      12: 'Consulta RAG',
      13: 'Generar Resumen',
      14: 'Consultar Bitácora',
      15: 'Exportar Bitácora'
    };
    
    return tipos[idTipo] || `Acción ${idTipo}`;
  }

  /**
   * Exportar registros a CSV (funcionalidad futura)
   */
  async exportarRegistros(filtros = {}) {
    // TODO: Implementar cuando el backend tenga el endpoint de exportación
    throw new Error('Funcionalidad de exportación pendiente de implementación');
  }
}

// Exportar instancia singleton
const bitacoraService = new BitacoraService();
export default bitacoraService;

// Exportar métodos individuales para imports selectivos
export const obtenerRegistros = (filtros) => bitacoraService.obtenerRegistros(filtros);
export const obtenerEstadisticas = (dias) => bitacoraService.obtenerEstadisticas(dias);
export const obtenerMiHistorial = (limite, tipoAccion) => bitacoraService.obtenerMiHistorial(limite, tipoAccion);
export const obtenerHistorialExpediente = (expediente, limite) => bitacoraService.obtenerHistorialExpediente(expediente, limite);
