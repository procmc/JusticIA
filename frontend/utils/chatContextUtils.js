/**
 * Utilidades para contexto de chat
 */

export const autoCleanupIfNeeded = () => {
  try {
    // Verificar que estamos en el cliente
    if (typeof window === 'undefined') return;
    
    const lastCleanup = localStorage.getItem('last_context_cleanup');
    const now = Date.now();
    
    const cleanupInterval = 7 * 24 * 60 * 60 * 1000; // 7 días
    
    if (!lastCleanup || (now - parseInt(lastCleanup)) > cleanupInterval) {
      console.log('Limpieza automática iniciada');
      localStorage.setItem('last_context_cleanup', now.toString());
    }
  } catch (error) {
    console.error('Error en limpieza automática:', error);
  }
};

/**
 * Limpia todo el contexto de chat almacenado
 */
export const clearAllChatContext = () => {
  try {
    // Verificar que estamos en el cliente
    if (typeof window === 'undefined') return false;
    
    // Limpiar sessionStorage (hooks antiguos)
    const sessionKeys = Object.keys(sessionStorage);
    sessionKeys.forEach(key => {
      if (key.startsWith('justicia_context_') || key.startsWith('chat_session_')) {
        sessionStorage.removeItem(key);
      }
    });
    
    // Limpiar localStorage (hooks antiguos y nuevos)
    const localKeys = Object.keys(localStorage);
    localKeys.forEach(key => {
      if (key.startsWith('conversation_') || 
          key.startsWith('messages_') || 
          key.startsWith('anon_conversation_id') ||
          key.includes('chat_user_') ||
          key.includes('_conversations') ||
          key.includes('_context_')) {
        localStorage.removeItem(key);
      }
    });
    
    console.log('Todo el contexto de chat ha sido limpiado');
    return true;
  } catch (error) {
    console.error('Error limpiando contexto de chat:', error);
    return false;
  }
};

/**
 * Verifica si hay contexto almacenado en localStorage
 */
export const hasStoredContext = () => {
  try {
    // Verificar que estamos en el cliente
    if (typeof window === 'undefined') return false;
    
    const allKeys = Object.keys(localStorage);
    return allKeys.some(key => 
      key.includes('chat_user_') ||
      key.includes('_conversations') ||
      key.includes('_context_') ||
      key.startsWith('conversation_') ||
      key.startsWith('messages_') ||
      key.startsWith('justicia_context_')
    );
  } catch (error) {
    console.error('Error verificando contexto almacenado:', error);
    return false;
  }
};

/**
 * Limpia el contexto de un usuario específico
 */
export const clearUserChatContext = (userId) => {
  try {
    // Verificar que estamos en el cliente
    if (typeof window === 'undefined' || !userId) return false;
    
    const userKey = `chat_user_${userId}`;
    
    // Limpiar sessionStorage para el usuario específico (legacy)
    const sessionKeys = Object.keys(sessionStorage);
    sessionKeys.forEach(key => {
      if (key.includes(userId)) {
        sessionStorage.removeItem(key);
      }
    });
    
    // Limpiar localStorage para el usuario específico
    const localKeys = Object.keys(localStorage);
    localKeys.forEach(key => {
      if (key.startsWith(userKey) || key.includes(`_${userId}`)) {
        localStorage.removeItem(key);
      }
    });
    
    console.log(`Contexto de chat limpiado para usuario: ${userId}`);
    return true;
  } catch (error) {
    console.error(`Error limpiando contexto para usuario ${userId}:`, error);
    return false;
  }
};
