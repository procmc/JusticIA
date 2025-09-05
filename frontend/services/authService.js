import httpService from './httpService';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

// Función auxiliar para manejar respuestas HTTP
const handleResponse = async (response) => {
  const contentType = response.headers.get("content-type");
  if (!response.ok) {
    let errorMessage = `HTTP error! status: ${response.status}`;
    let errorCode = response.status;
    try {
      if (contentType && contentType.includes("application/json")) {
        const error = await response.json();
        errorMessage = error.error || error.message || errorMessage;
      } else {
        const text = await response.text();
        errorMessage = text || errorMessage;
      }
    } catch (parseError) {
      // No hacer nada extra
    }
    return { error: true, message: errorMessage, code: errorCode };
  }
  if (contentType && contentType.includes("application/json")) {
    return await response.json();
  }
  return await response.text();
};

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
    console.error('🔍 [DEBUG] Error en catch:', error);
    return { error: true, message: 'Error de red al iniciar sesión' };
  }
}

export async function cambiarContraseñaService(contraseñaActual, nuevaContraseña, cedulaUsuario) {
  try {
    const res = await fetch(`${API_URL}/auth/cambiar-contrasenna`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        contraseñaActual, 
        nuevaContraseña, 
        cedulaUsuario 
      })
    });
    
    const data = await handleResponse(res);
    
    if (data && data.error) {
      return { error: data.error, message: data.message };
    }
    
    if (!data.success) {
      return { error: data.error || "Error al cambiar contraseña", message: data.message };
    }
    
    return { success: true, message: data.message || "Contraseña cambiada exitosamente" };
  } catch (error) {
    console.error('Error en cambiarContraseñaService:', error);
    return { error: true, message: 'Error de red al cambiar contraseña' };
  }
}

// Función para solicitar recuperación de contraseña
export async function solicitarRecuperacionService(email) {
  try {
    const res = await fetch(`${API_URL}/auth/solicitar-recuperacion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    });
    
    const data = await handleResponse(res);
    
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
    if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
      return { error: true, message: 'No se pudo conectar con el servidor. Verifique su conexión a internet.' };
    }
    return { error: true, message: 'Error de red al solicitar recuperación' };
  }
}

// Función para verificar código de recuperación
export async function verificarCodigoRecuperacionService(token, codigo) {
  try {
    const res = await fetch(`${API_URL}/auth/verificar-codigo-recuperacion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, codigo })
    });
    
    const data = await handleResponse(res);
    
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
    if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
      return { error: true, message: 'No se pudo conectar con el servidor. Verifique su conexión a internet.' };
    }
    return { error: true, message: 'Error de red al verificar código' };
  }
}

// Función para cambiar contraseña con token de verificación
export async function cambiarContraseñaRecuperacionService(verificationToken, nuevaContraseña) {
  try {
    const res = await fetch(`${API_URL}/auth/cambiar-contrasenna-recuperacion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ verificationToken, nuevaContraseña })
    });
    
    const data = await handleResponse(res);
    
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
    console.error('Error en cambiarContraseñaRecuperacionService:', error);
    if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
      return { error: true, message: 'No se pudo conectar con el servidor. Verifique su conexión a internet.' };
    }
    return { error: true, message: 'Error de red al cambiar contraseña' };
  }
}
