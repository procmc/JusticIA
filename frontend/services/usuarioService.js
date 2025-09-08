import httpService from './httpService';

/**
 * Servicio para gestión de usuarios
 */

// Obtener todos los usuarios
export async function obtenerUsuariosService() {
  try {
    const data = await httpService.get('/usuarios');
    return { success: true, usuarios: data };
  } catch (error) {
    console.error('Error al obtener usuarios:', error);
    return { error: true, message: error.message || 'Error al obtener usuarios' };
  }
}

// Obtener usuario por ID
export async function obtenerUsuarioPorIdService(usuarioId) {
  try {
    const data = await httpService.get(`/usuarios/${usuarioId}`);
    return { success: true, usuario: data };
  } catch (error) {
    console.error('Error al obtener usuario:', error);
    return { error: true, message: error.message || 'Usuario no encontrado' };
  }
}

// Crear nuevo usuario
export async function crearUsuarioService(usuarioData) {
  try {
    const data = await httpService.post('/usuarios', usuarioData);
    return { success: true, usuario: data };
  } catch (error) {
    console.error('Error al crear usuario:', error);
    return { error: true, message: error.message || 'Error al crear usuario' };
  }
}

// Editar usuario
export async function editarUsuarioService(usuarioId, usuarioData) {
  try {
    const data = await httpService.put(`/usuarios/${usuarioId}`, usuarioData);
    return { success: true, usuario: data };
  } catch (error) {
    console.error('Error al editar usuario:', error);
    return { error: true, message: error.message || 'Error al editar usuario' };
  }
}

// Resetear contraseña de usuario
export async function resetearContrasenaService(usuarioId) {
  try {
    const data = await httpService.post(`/usuarios/${usuarioId}/resetear-contrasenna`);
    return { success: true, message: data.mensaje };
  } catch (error) {
    console.error('Error al resetear contraseña:', error);
    return { error: true, message: error.message || 'Error al resetear contraseña' };
  }
}

export default {
  obtenerUsuariosService,
  obtenerUsuarioPorIdService,
  crearUsuarioService,
  editarUsuarioService,
  resetearContrasenaService
};
