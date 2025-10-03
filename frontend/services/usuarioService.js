import httpService from './httpService';

/**
 * UsuarioService - Servicio para gestión de usuarios
 * 
 * Maneja operaciones CRUD de usuarios con manejo de errores robusto
 */

class UsuarioService {
  
  /**
   * Obtener todos los usuarios
   */
  async obtenerUsuarios() {
    try {
      const data = await httpService.get('/usuarios');
      return { success: true, usuarios: data };
      
    } catch (error) {
      console.error('Error al obtener usuarios:', error);
      
      // Mensajes específicos por tipo de error
      if (error.status === 403) {
        return { error: true, message: 'No tiene permisos para ver usuarios' };
      }
      
      if (error.isNetworkError) {
        return { error: true, message: 'Error de conexión. Verifique su red.' };
      }
      
      return { error: true, message: error.message || 'Error al obtener usuarios' };
    }
  }

  /**
   * Obtener usuario por ID
   */
  async obtenerUsuarioPorId(usuarioId) {
    try {
      // Validar parámetro
      if (!usuarioId) {
        throw new Error('ID de usuario es requerido');
      }

      const data = await httpService.get(`/usuarios/${usuarioId}`);
      return { success: true, usuario: data };
      
    } catch (error) {
      console.error('Error al obtener usuario:', error);
      
      if (error.status === 404) {
        return { error: true, message: 'Usuario no encontrado' };
      }
      
      if (error.status === 403) {
        return { error: true, message: 'No tiene permisos para ver este usuario' };
      }
      
      return { error: true, message: error.message || 'Error al obtener usuario' };
    }
  }

  /**
   * Crear nuevo usuario
   */
  async crearUsuario(usuarioData) {
    try {
      // Validar datos básicos
      if (!usuarioData || !usuarioData.email) {
        throw new Error('Datos de usuario incompletos');
      }

      const data = await httpService.post('/usuarios', usuarioData);
      return { success: true, usuario: data };
      
    } catch (error) {
      console.error('Error al crear usuario:', error);
      
      if (error.status === 400) {
        return { error: true, message: error.message || 'Datos de usuario inválidos' };
      }
      
      if (error.status === 409) {
        return { error: true, message: 'El usuario ya existe' };
      }
      
      if (error.status === 403) {
        return { error: true, message: 'No tiene permisos para crear usuarios' };
      }
      
      return { error: true, message: error.message || 'Error al crear usuario' };
    }
  }

  /**
   * Editar usuario existente
   */
  async editarUsuario(usuarioId, usuarioData) {
    try {
      // Validar parámetros
      if (!usuarioId) {
        throw new Error('ID de usuario es requerido');
      }
      
      if (!usuarioData) {
        throw new Error('Datos de usuario son requeridos');
      }

      const data = await httpService.put(`/usuarios/${usuarioId}`, usuarioData);
      return { success: true, usuario: data };
      
    } catch (error) {
      console.error('Error al editar usuario:', error);
      
      if (error.status === 404) {
        return { error: true, message: 'Usuario no encontrado' };
      }
      
      if (error.status === 400) {
        return { error: true, message: error.message || 'Datos de usuario inválidos' };
      }
      
      if (error.status === 403) {
        return { error: true, message: 'No tiene permisos para editar este usuario' };
      }
      
      return { error: true, message: error.message || 'Error al editar usuario' };
    }
  }

  /**
   * Resetear contraseña de usuario
   */
  async resetearContrasena(usuarioId) {
    try {
      // Validar parámetro
      if (!usuarioId) {
        throw new Error('ID de usuario es requerido');
      }

      const data = await httpService.post(`/usuarios/${usuarioId}/resetear-contrasenna`);
      return { success: true, message: data.mensaje || 'Contraseña reseteada exitosamente' };
      
    } catch (error) {
      console.error('Error al resetear contraseña:', error);
      
      if (error.status === 404) {
        return { error: true, message: 'Usuario no encontrado' };
      }
      
      if (error.status === 403) {
        return { error: true, message: 'No tiene permisos para resetear contraseñas' };
      }
      
      return { error: true, message: error.message || 'Error al resetear contraseña' };
    }
  }
}

// Exportar instancia singleton
const usuarioService = new UsuarioService();

export default usuarioService;

// Exportar clase para testing
export { UsuarioService };

// Exportar funciones legacy para compatibilidad con código existente
export const obtenerUsuariosService = () => usuarioService.obtenerUsuarios();
export const obtenerUsuarioPorIdService = (id) => usuarioService.obtenerUsuarioPorId(id);
export const crearUsuarioService = (data) => usuarioService.crearUsuario(data);
export const editarUsuarioService = (id, data) => usuarioService.editarUsuario(id, data);
export const resetearContrasenaService = (id) => usuarioService.resetearContrasena(id);
