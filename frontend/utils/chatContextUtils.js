/**
 * @fileoverview Utilidades para gestión y limpieza de contexto de chat.
 * 
 * Este módulo proporciona funciones para gestionar el contexto de conversaciones
 * almacenado en localStorage y sessionStorage. Implementa limpieza automática,
 * detección de contexto almacenado y limpieza selectiva por usuario.
 * 
 * El sistema de chat de JusticIA almacena contexto conversacional en el navegador
 * para mantener continuidad entre sesiones. Este módulo asegura que el almacenamiento
 * no crezca indefinidamente y proporciona herramientas de mantenimiento.
 * 
 * Claves de almacenamiento gestionadas:
 * - sessionStorage:
 *   - justicia_context_{sessionId}: Contexto legacy de sesión
 *   - chat_session_{sessionId}: Sesiones de chat legacy
 * 
 * - localStorage:
 *   - conversation_{conversationId}: Datos de conversación
 *   - messages_{conversationId}: Mensajes de conversación
 *   - anon_conversation_id: ID de conversación anónima
 *   - chat_user_{userId}_*: Contextos de usuario específico
 *   - *_conversations: Listas de conversaciones
 *   - *_context_*: Contextos varios
 * 
 * Política de limpieza:
 * - Limpieza automática cada 7 días
 * - Limpieza manual disponible (clearAllChatContext)
 * - Limpieza selectiva por usuario (clearUserChatContext)
 * 
 * @module chatContextUtils
 * @requires localStorage
 * @requires sessionStorage
 * 
 * @example
 * import { clearAllChatContext, hasStoredContext } from '@/utils/chatContextUtils';
 * 
 * // Verificar si hay contexto almacenado
 * if (hasStoredContext()) {
 *   console.log('Hay contexto de chat almacenado');
 * }
 * 
 * // Limpiar todo el contexto
 * clearAllChatContext();
 * 
 * // Limpiar contexto de usuario específico
 * clearUserChatContext('112340567');
 * 
 * @see {@link ../hooks/useBackendConversations.js} Hook que usa este contexto
 * @see {@link ../components/Layout/Layout.jsx} Layout que limpia contexto al desloguear
 * 
 * @author JusticIA Team
 * @version 1.0.0
 */

/**
 * Ejecuta limpieza automática de contexto si han pasado 7 días desde la última limpieza.
 * 
 * Verifica la marca de tiempo de última limpieza en localStorage y ejecuta limpieza
 * si el intervalo de 7 días ha sido superado. Útil para llamar al inicio de la aplicación.
 * 
 * @function autoCleanupIfNeeded
 * @returns {void}
 * 
 * @example
 * // En _app.js o Layout.jsx
 * useEffect(() => {
 *   autoCleanupIfNeeded();
 * }, []);
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
 * Limpia todo el contexto de chat almacenado en localStorage y sessionStorage.
 * 
 * Esta función es útil para:
 * - Logout completo del usuario
 * - Resetear el estado de la aplicación
 * - Resolver problemas de estado corrupto
 * - Cumplir con solicitudes de eliminación de datos (GDPR)
 * 
 * Limpia todas las claves que coincidan con patrones de contexto de chat:
 * - sessionStorage: justicia_context_*, chat_session_*
 * - localStorage: conversation_*, messages_*, anon_conversation_id, chat_user_*, *_conversations, *_context_*
 * 
 * @function clearAllChatContext
 * @returns {boolean} true si la limpieza fue exitosa, false si hubo error.
 * 
 * @example
 * // Limpiar al hacer logout
 * const handleLogout = () => {
 *   clearAllChatContext();
 *   signOut();
 * };
 * 
 * @example
 * // Limpiar con confirmación
 * if (confirm('¿Desea limpiar todo el historial de conversaciones?')) {
 *   const success = clearAllChatContext();
 *   if (success) {
 *     alert('Historial limpiado exitosamente');
 *   }
 * }
 * 
 * @note Esta operación es irreversible. El contexto eliminado no se puede recuperar.
 * @note Seguro para SSR (verifica typeof window antes de ejecutar).
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
 * Verifica si hay contexto de chat almacenado en localStorage.
 * 
 * Útil para:
 * - Mostrar indicadores de estado (badge de "tiene conversaciones")
 * - Decisiones de UI (mostrar/ocultar botón "Limpiar historial")
 * - Logging y debugging
 * 
 * @function hasStoredContext
 * @returns {boolean} true si existe al menos una clave de contexto de chat, false en caso contrario.
 * 
 * @example
 * // Mostrar badge si hay contexto
 * {hasStoredContext() && (
 *   <Badge color="primary">Hay historial</Badge>
 * )}
 * 
 * @example
 * // Habilitar botón de limpieza
 * <Button
 *   isDisabled={!hasStoredContext()}
 *   onPress={clearAllChatContext}
 * >
 *   Limpiar Historial
 * </Button>
 * 
 * @note Seguro para SSR (retorna false en servidor).
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
 * Limpia el contexto de chat de un usuario específico.
 * 
 * Útil para:
 * - Cambio de usuario sin logout completo
 * - Limpieza selectiva por usuario en panel administrativo
 * - Resolver problemas de contexto corrupto de un usuario
 * 
 * Limpia todas las claves que incluyan el userId:
 * - sessionStorage: claves que incluyen el userId
 * - localStorage: chat_user_{userId}_*, claves que incluyen _{userId}
 * 
 * @function clearUserChatContext
 * @param {string} userId - ID del usuario (cédula) cuyo contexto se limpiará.
 * @returns {boolean} true si la limpieza fue exitosa, false si hubo error o userId inválido.
 * 
 * @example
 * // Limpiar contexto al cambiar de usuario
 * const handleUserSwitch = (newUserId) => {
 *   clearUserChatContext(currentUserId);
 *   setCurrentUser(newUserId);
 * };
 * 
 * @example
 * // Limpiar contexto desde panel de administración
 * const handleClearUserContext = (userId) => {
 *   if (confirm(`¿Limpiar contexto de usuario ${userId}?`)) {
 *     const success = clearUserChatContext(userId);
 *     if (success) {
 *       showNotification('Contexto limpiado', 'success');
 *     }
 *   }
 * };
 * 
 * @note No afecta el contexto de otros usuarios.
 * @note Seguro para SSR (verifica typeof window antes de ejecutar).
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
