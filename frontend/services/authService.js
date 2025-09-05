import httpService from './httpService';

export async function loginService(email, password) {
  try {
    const data = await httpService.post('/auth/login', { email, password });

    if (data && data.error) {
      return { error: true, message: data.message || "Credenciales incorrectas" };
    }
    if (!data.success || !data.user) {
      return { error: true, message: data.message || "Credenciales incorrectas" };
    }
    
    return { user: data.user };
  } catch (error) {
    return { error: true, message: 'Error de red al iniciar sesión' };
  }
}

export async function cambiarContraseñaService(contraseñaActual, nuevaContraseña, cedulaUsuario) {
  try {
    const payload = {
      cedula_usuario: String(cedulaUsuario),
      contrasenna_actual: String(contraseñaActual),
      nueva_contrasenna: String(nuevaContraseña)
    };
    
    const data = await httpService.apiRequest('/auth/cambiar-contrasenna', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload)
    });
    
    if (data && data.error) {
      return { error: data.error, message: data.message };
    }
    
    if (!data.success) {
      return { error: data.error || "Error al cambiar contraseña", message: data.message };
    }
    
    return { success: true, message: data.message || "Contraseña cambiada exitosamente" };
  } catch (error) {
    const errorMessage = error.message || error.toString() || 'Error de red al cambiar contraseña';
    return { error: true, message: errorMessage };
  }
}

// Función para solicitar recuperación de contraseña
export async function solicitarRecuperacionService(email) {
  try {
    const data = await httpService.post('/auth/solicitar-recuperacion', { email });
    
    if (data && data.error) {
      return { error: data.error, message: data.message };
    }
    
    if (!data.success) {
      return { error: true, message: data.message || "Error al solicitar recuperación" };
    }
    
    return { 
      success: true, 
      message: data.message || "Código enviado exitosamente", 
      token: data.token 
    };
  } catch (error) {
    console.error('Error en solicitarRecuperacionService:', error);
    return { error: true, message: 'Error de red al solicitar recuperación' };
  }
}

// Función para verificar código de recuperación
export async function verificarCodigoRecuperacionService(token, codigo) {
  try {
    console.log('Verificando código:', { token: token?.substring(0, 20) + '...', codigo });
    
    const data = await httpService.post('/auth/verificar-codigo', { token, codigo });
    
    if (data && data.error) {
      return { error: data.error, message: data.message };
    }
    
    if (!data.success) {
      return { error: true, message: data.message || "Error al verificar código" };
    }
    
    return { 
      success: true, 
      message: data.message || "Código verificado exitosamente", 
      verificationToken: data.verificationToken 
    };
  } catch (error) {
    console.error('Error en verificarCodigoRecuperacionService:', error);
    const errorMessage = error.message || error.toString() || 'Error de red al verificar código';
    return { error: true, message: errorMessage };
  }
}

// Función para cambiar contraseña con token de verificación
export async function cambiarContraseñaRecuperacionService(verificationToken, nuevaContraseña) {
  try {
    const payload = { 
      verificationToken, 
      nuevaContrasenna: nuevaContraseña
    };
    
    const data = await httpService.post('/auth/cambiar-contrasenna-recuperacion', payload);
    
    if (data && data.error) {
      return { error: data.error, message: data.message };
    }
    
    if (!data.success) {
      return { error: true, message: data.message || "Error al cambiar contraseña" };
    }
    
    return { 
      success: true, 
      message: data.message || "Contraseña cambiada exitosamente" 
    };
  } catch (error) {
    const errorMessage = error.message || error.toString() || 'Error de red al cambiar contraseña';
    return { error: true, message: errorMessage };
  }
}
