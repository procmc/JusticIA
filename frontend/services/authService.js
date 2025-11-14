/**
 * Servicio de Autenticación y Gestión de Contraseñas - Frontend.
 * 
 * @module services/authService
 * 
 * Este servicio maneja toda la lógica de autenticación del lado del cliente,
 * incluyendo login, logout, cambio de contraseña, recuperación de acceso
 * mediante email, y renovación de tokens (sliding sessions).
 * 
 * Funciones principales:
 *   - login: Autenticación con email/contraseña
 *   - logout: Cierre de sesión con registro en bitácora
 *   - cambiarContrasena: Cambio de contraseña por usuario autenticado
 *   - solicitarRecuperacion: Envío de código de recuperación por email
 *   - verificarCodigoRecuperacion: Validación de código de 6 dígitos
 *   - cambiarContrasenaRecuperacion: Cambio con token verificado
 *   - refreshToken: Renovación de token JWT
 * 
 * Manejo de errores:
 *   - Errores HTTP específicos (401, 403, 404, 429)
 *   - Errores de red con mensajes amigables
 *   - Validación de parámetros antes de llamadas API
 * 
 * @example
 * ```javascript
 * import authService from '@/services/authService';
 * 
 * // Login
 * const result = await authService.login('user@example.com', 'password123');
 * if (result.error) {
 *   console.error(result.message);
 * } else {
 *   console.log('Token:', result.access_token);
 *   console.log('Usuario:', result.user);
 * }
 * 
 * // Cambiar contraseña
 * const change = await authService.cambiarContrasena(
 *   'oldPass', 'newPass', '123456789'
 * );
 * ```
 * 
 * @see {@link httpService} Para llamadas HTTP configuradas
 */

import httpService from './httpService';

/**
 * Servicio de autenticación y gestión de contraseñas.
 * 
 * @class AuthService
 * @category Services
 */
class AuthService {

  /**
   * Iniciar sesión con email y contraseña.
   * 
   * @async
   * @param {string} email - Correo electrónico del usuario
   * @param {string} password - Contraseña en texto plano
   * 
   * @returns {Promise<Object>} Resultado del login:
   *   - Si éxito: { user: Object, access_token: string }
   *   - Si error: { error: true, message: string }
   * 
   * @example
   * ```javascript
   * const result = await authService.login('usuario@ejemplo.com', 'miPassword');
   * 
   * if (result.error) {
   *   alert(result.message); // "Credenciales incorrectas"
   * } else {
   *   localStorage.setItem('token', result.access_token);
   *   // Navegar al dashboard
   * }
   * ```
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
   * Registrar cierre de sesión en el backend
   */
  async logout(usuarioId, email) {
    try {
      // Validar parámetros
      if (!usuarioId || !email) {
        console.warn('Logout sin datos de usuario - se omite registro en bitácora');
        return { success: true };
      }

      const payload = {
        usuario_id: String(usuarioId),
        email: String(email)
      };
      
      const data = await httpService.post('/auth/logout', payload);
      
      return { 
        success: true, 
        message: data?.message || 'Sesión cerrada correctamente' 
      };
      
    } catch (error) {
      console.warn('Error al registrar logout en bitácora:', error);
      // No lanzamos error para no bloquear el cierre de sesión
      return { success: true };
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

  /**
   * Renovar token (para sliding sessions)
   */
  async refreshToken() {
    try {
      const data = await httpService.post('/auth/refresh-token', {});
      
      if (data?.access_token && data?.user) {
        return {
          success: true,
          access_token: data.access_token,
          user: data.user
        };
      }
      
      return { error: true, message: 'Error al renovar token' };
      
    } catch (error) {
      console.error('Error renovando token:', error);
      
      if (error.status === 401) {
        return { error: true, message: 'Sesión expirada', expired: true };
      }
      
      return { error: true, message: 'Error al renovar token' };
    }
  }

  /**
   * Renovar token con token específico (para uso en NextAuth callbacks)
   * No usa httpService porque causaría loop infinito con getSession()
   */
  async refreshTokenWithToken(currentToken) {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/refresh-token`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${currentToken}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        return { error: true, message: `Error ${response.status}` };
      }
      
      const data = await response.json();
      
      if (data?.access_token && data?.user) {
        return {
          success: true,
          access_token: data.access_token,
          user: data.user
        };
      }
      
      return { error: true, message: 'Error al renovar token' };
      
    } catch (error) {
      console.error('Error renovando token:', error);
      return { error: true, message: 'Error al renovar token' };
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
export const logoutService = (usuarioId, email) => authService.logout(usuarioId, email);
export const cambiarContraseñaService = (actual, nueva, cedula) => authService.cambiarContrasena(actual, nueva, cedula);
export const solicitarRecuperacionService = (email) => authService.solicitarRecuperacion(email);
export const verificarCodigoRecuperacionService = (token, codigo) => authService.verificarCodigoRecuperacion(token, codigo);
export const cambiarContraseñaRecuperacionService = (token, nueva) => authService.cambiarContrasenaRecuperacion(token, nueva);
export const refreshTokenService = () => authService.refreshToken();
export const refreshTokenWithTokenService = (token) => authService.refreshTokenWithToken(token);
