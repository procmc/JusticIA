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
   * Obtener registros de bitácora con filtros múltiples
   * Solo accesible para administradores
   * 
   * @param {Object} filtros - Filtros de búsqueda
   * @param {string} filtros.usuario - Nombre o correo de usuario
   * @param {number} filtros.tipoAccion - ID del tipo de acción (1-8)
   * @param {string} filtros.expediente - Número de expediente
   * @param {string} filtros.fechaInicio - Fecha inicio ISO
   * @param {string} filtros.fechaFin - Fecha fin ISO
   * @param {number} filtros.limite - Número máximo de registros (default: 200)
   * @returns {Promise<Array>} Array de registros
   */
  async obtenerRegistros(filtros = {}) {
    try {
      // Construir query params (solo incluir los que tienen valor)
      const params = new URLSearchParams();
      
      if (filtros.usuario) params.append('usuario', filtros.usuario);
      if (filtros.tipoAccion) params.append('tipoAccion', filtros.tipoAccion);
      if (filtros.expediente) params.append('expediente', filtros.expediente);
      if (filtros.fechaInicio) params.append('fechaInicio', filtros.fechaInicio);
      if (filtros.fechaFin) params.append('fechaFin', filtros.fechaFin);
      if (filtros.limite) params.append('limite', filtros.limite);

      const queryString = params.toString();
      const url = `${this.baseURL}/registros${queryString ? `?${queryString}` : ''}`;

      const data = await httpService.get(url);
    
      // Mapear campos del backend al formato del frontend
      return this._mapearRegistros(data);
      
    } catch (error) {
      console.error('Error obteniendo registros de bitácora:', error);
      throw new Error(
        error.message || 'Error al obtener registros de bitácora'
      );
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
        accionesPorTipo: data.accionesPorTipo || []
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
        usuario: registro.nombre_usuario || registro.usuario || 'Usuario desconocido',
        correoUsuario: registro.correo_usuario || registro.correoUsuario || null,
        tipoAccion: registro.nombre_tipo_accion || registro.tipo_accion || registro.tipoAccion || this._mapearTipoAccion(registro.CN_Id_tipo_accion || registro.id_tipo_accion || registro.idTipoAccion),
        expediente: registro.numero_expediente || registro.expediente || null,
        
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
      1: 'Consulta',
      2: 'Carga de Documentos',
      3: 'Búsqueda de Casos Similares',
      4: 'Inicio de Sesión',
      5: 'Creación de Usuario',
      6: 'Edición de Usuario',
      7: 'Consulta de Bitácora',
      8: 'Exportación de Bitácora'
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
