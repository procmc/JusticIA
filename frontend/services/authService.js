import httpService from './httpService';

/**
 * AuthService - Servicio para autenticación y gestión de contraseñas
 * 
 * Maneja login, cambio de contraseña y recuperación de contraseña
 */

class AuthService {

  /**
   * Iniciar sesión
   */
  async login(email, password) {
    try {
      // Validar parámetros
      if (!email || !password) {
        return { error: true, message: 'Email y contraseña son requeridos' };
      }

      const data = await httpService.post('/auth/login', { email, password });

      // Validar respuesta
      if (data?.error) {
        return { error: true, message: data.message || 'Credenciales incorrectas' };
      }

      if (!data?.success || !data?.user) {
        return { error: true, message: data?.message || 'Credenciales incorrectas' };
      }
      
      // Retornar user y access_token
      return { 
        user: data.user,
        access_token: data.access_token 
      };
      
    } catch (error) {
      console.error('Error en login:', error);
      
      if (error.status === 401) {
        return { error: true, message: 'Credenciales incorrectas' };
      }
      
      if (error.status === 403) {
        return { error: true, message: 'Cuenta desactivada o sin permisos' };
      }
      
      if (error.isNetworkError) {
        return { error: true, message: 'Error de conexión. Verifique su red.' };
      }
      
      return { error: true, message: error.message || 'Error al iniciar sesión' };
    }
  }

  /**
   * Cambiar contraseña del usuario autenticado
   */
  async cambiarContrasena(contraseñaActual, nuevaContraseña, cedulaUsuario) {
    try {
      // Validar parámetros
      if (!contraseñaActual || !nuevaContraseña || !cedulaUsuario) {
        return { error: true, message: 'Todos los campos son requeridos' };
      }

      const payload = {
        cedula_usuario: String(cedulaUsuario),
        contrasenna_actual: String(contraseñaActual),
        nueva_contrasenna: String(nuevaContraseña)
      };
      
      // Usar PUT en lugar de apiRequest (que ya no existe)
      const data = await httpService.put('/auth/cambiar-contrasenna', payload);
      
      if (data?.error) {
        return { error: true, message: data.message || 'Error al cambiar contraseña' };
      }
      
      if (!data?.success) {
        return { error: true, message: data?.message || 'Error al cambiar contraseña' };
      }
      
      return { success: true, message: data.message || 'Contraseña cambiada exitosamente' };
      
    } catch (error) {
      console.error('Error al cambiar contraseña:', error);
      
      if (error.status === 401) {
        return { error: true, message: 'Contraseña actual incorrecta' };
      }
      
      if (error.status === 400) {
        return { error: true, message: error.message || 'Contraseña no cumple los requisitos' };
      }
      
      if (error.isNetworkError) {
        return { error: true, message: 'Error de conexión. Verifique su red.' };
      }
      
      return { error: true, message: error.message || 'Error al cambiar contraseña' };
    }
  }

  /**
   * Solicitar recuperación de contraseña (envía código por email)
   */
  async solicitarRecuperacion(email) {
    try {
      // Validar parámetro
      if (!email) {
        return { error: true, message: 'Email es requerido' };
      }

      const data = await httpService.post('/auth/solicitar-recuperacion', { email });
      
      if (data?.error) {
        return { error: true, message: data.message || 'Error al solicitar recuperación' };
      }
      
      if (!data?.success) {
        return { error: true, message: data?.message || 'Error al solicitar recuperación' };
      }
      
      return { 
        success: true, 
        message: data.message || 'Código enviado exitosamente', 
        token: data.token 
      };
      
    } catch (error) {
      console.error('Error en solicitar recuperación:', error);
      
      if (error.status === 404) {
        return { error: true, message: 'Email no registrado' };
      }
      
      if (error.status === 429) {
        return { error: true, message: 'Demasiados intentos. Intente más tarde.' };
      }
      
      if (error.isNetworkError) {
        return { error: true, message: 'Error de conexión. Verifique su red.' };
      }
      
      return { error: true, message: error.message || 'Error al solicitar recuperación' };
    }
  }

  /**
   * Verificar código de recuperación
   */
  async verificarCodigoRecuperacion(token, codigo) {
    try {
      // Validar parámetros
      if (!token || !codigo) {
        return { error: true, message: 'Token y código son requeridos' };
      }

      const data = await httpService.post('/auth/verificar-codigo', { token, codigo });
      
      if (data?.error) {
        return { error: true, message: data.message || 'Código inválido' };
      }
      
      if (!data?.success) {
        return { error: true, message: data?.message || 'Código inválido' };
      }
      
      return { 
        success: true, 
        message: data.message || 'Código verificado exitosamente', 
        verificationToken: data.verificationToken 
      };
      
    } catch (error) {
      console.error('Error al verificar código:', error);
      
      if (error.status === 400) {
        return { error: true, message: 'Código inválido o expirado' };
      }
      
      if (error.status === 404) {
        return { error: true, message: 'Token de recuperación no válido' };
      }
      
      if (error.isNetworkError) {
        return { error: true, message: 'Error de conexión. Verifique su red.' };
      }
      
      return { error: true, message: error.message || 'Error al verificar código' };
    }
  }

  /**
   * Cambiar contraseña con token de verificación (recuperación)
   */
  async cambiarContrasenaRecuperacion(verificationToken, nuevaContraseña) {
    try {
      // Validar parámetros
      if (!verificationToken || !nuevaContraseña) {
        return { error: true, message: 'Token y nueva contraseña son requeridos' };
      }

      const payload = { 
        verificationToken, 
        nuevaContrasenna: nuevaContraseña
      };
      
      const data = await httpService.post('/auth/cambiar-contrasenna-recuperacion', payload);
      
      if (data?.error) {
        return { error: true, message: data.message || 'Error al cambiar contraseña' };
      }
      
      if (!data?.success) {
        return { error: true, message: data?.message || 'Error al cambiar contraseña' };
      }
      
      return { 
        success: true, 
        message: data.message || 'Contraseña cambiada exitosamente' 
      };
      
    } catch (error) {
      console.error('Error al cambiar contraseña (recuperación):', error);
      
      if (error.status === 400) {
        return { error: true, message: error.message || 'Token inválido o contraseña no válida' };
      }
      
      if (error.status === 404) {
        return { error: true, message: 'Token de verificación no válido o expirado' };
      }
      
      if (error.isNetworkError) {
        return { error: true, message: 'Error de conexión. Verifique su red.' };
      }
      
      return { error: true, message: error.message || 'Error al cambiar contraseña' };
    }
  }
}

// Exportar instancia singleton
const authService = new AuthService();

export default authService;

// Exportar clase para testing
export { AuthService };

// Exportar funciones legacy para compatibilidad con código existente
export const loginService = (email, password) => authService.login(email, password);
export const cambiarContraseñaService = (actual, nueva, cedula) => authService.cambiarContrasena(actual, nueva, cedula);
export const solicitarRecuperacionService = (email) => authService.solicitarRecuperacion(email);
export const verificarCodigoRecuperacionService = (token, codigo) => authService.verificarCodigoRecuperacion(token, codigo);
export const cambiarContraseñaRecuperacionService = (token, nueva) => authService.cambiarContrasenaRecuperacion(token, nueva);
