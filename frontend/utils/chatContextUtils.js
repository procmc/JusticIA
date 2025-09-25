/**
 * Utilidades para limpieza de contexto de chat
 * Centraliza la lógica de limpieza para evitar duplicación
 */

/**
 * Limpia todo el contexto de chat almacenado en localStorage y sessionStorage
 */
export const clearAllChatContext = () => {
  try {
    // Limpiar sessionStorage
    const sessionKeys = Object.keys(sessionStorage);
    sessionKeys.forEach(key => {
      if (key.startsWith('justicia_context_') || key.startsWith('chat_session_')) {
        sessionStorage.removeItem(key);
      }
    });
    
    // Limpiar localStorage
    const localKeys = Object.keys(localStorage);
    localKeys.forEach(key => {
      if (key.startsWith('conversation_') || key.startsWith('messages_') || key.startsWith('anon_conversation_id')) {
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
 * Limpia el contexto de un usuario específico
 */
export const clearUserChatContext = (userId) => {
  try {
    if (!userId) return false;
    
    // Limpiar sessionStorage para el usuario específico
    const sessionKeys = Object.keys(sessionStorage);
    sessionKeys.forEach(key => {
      if (key.includes(userId)) {
        sessionStorage.removeItem(key);
      }
    });
    
    // Limpiar localStorage para el usuario específico
    const localKeys = Object.keys(localStorage);
    localKeys.forEach(key => {
      if (key.includes(userId)) {
        localStorage.removeItem(key);
      }
    });
    
    console.log(`Contexto de chat limpiado para usuario: ${userId}`);
    return true;
  } catch (error) {
    console.error('Error limpiando contexto de usuario:', error);
    return false;
  }
};

/**
 * Verifica si existe contexto almacenado
 */
export const hasStoredContext = () => {
  try {
    const allKeys = [...Object.keys(sessionStorage), ...Object.keys(localStorage)];
    return allKeys.some(key => 
      key.startsWith('justicia_context_') || 
      key.startsWith('chat_session_') || 
      key.startsWith('conversation_') || 
      key.startsWith('messages_')
    );
  } catch (error) {
    console.error('Error verificando contexto almacenado:', error);
    return false;
  }
};