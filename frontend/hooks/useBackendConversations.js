import { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import conversationService from '../services/conversationService';

/**
 * Hook para gestionar el historial de conversaciones desde el backend.
 * 
 * Este hook obtiene las conversaciones persistidas en el servidor,
 * permitiendo que el historial se mantenga incluso después de cerrar sesión.
 */
export const useBackendConversations = () => {
  const { data: session, status } = useSession();
  const [conversations, setConversations] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastFetch, setLastFetch] = useState(null);

  /**
   * Carga las conversaciones del usuario desde el backend
   */
  const fetchConversations = useCallback(async (forceRefresh = false) => {
    // Solo cargar si hay sesión activa
    if (status !== 'authenticated' || !session?.user) {
      setConversations([]);
      return;
    }

    // Evitar múltiples llamadas seguidas (cache de 30 segundos)
    const now = Date.now();
    if (!forceRefresh && lastFetch && (now - lastFetch < 30000)) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await conversationService.getUserConversations();

      if (result.success) {
        setConversations(result.conversations);
        setLastFetch(now);
        console.log(`✅ ${result.total} conversaciones cargadas desde backend`);
      } else {
        setError(result.error);
        console.error('Error obteniendo conversaciones:', result.error);
      }
    } catch (err) {
      setError(err.message);
      console.error('Error en fetchConversations:', err);
    } finally {
      setIsLoading(false);
    }
  }, [session, status]); // ✅ Removed lastFetch from dependencies

  /**
   * Obtiene los detalles completos de una conversación específica
   */
  const getConversationDetail = useCallback(async (sessionId) => {
    try {
      const result = await conversationService.getConversationDetail(sessionId);
      
      if (result.success) {
        return result.conversation;
      } else {
        console.error('Error obteniendo detalles:', result.error);
        return null;
      }
    } catch (err) {
      console.error('Error en getConversationDetail:', err);
      return null;
    }
  }, []);

  /**
   * Elimina una conversación
   */
  const deleteConversation = useCallback(async (sessionId) => {
    try {
      const result = await conversationService.deleteConversation(sessionId);

      if (result.success) {
        // Actualizar lista local removiendo la conversación eliminada
        setConversations(prev => prev.filter(conv => conv.session_id !== sessionId));
        console.log(`✅ Conversación ${sessionId} eliminada`);
        return true;
      } else {
        console.error('Error eliminando conversación:', result.error);
        return false;
      }
    } catch (err) {
      console.error('Error en deleteConversation:', err);
      return false;
    }
  }, []);

  /**
   * Restaura una conversación desde el archivo
   */
  const restoreConversation = useCallback(async (sessionId) => {
    try {
      const result = await conversationService.restoreConversation(sessionId);

      if (result.success) {
        // Recargar lista de conversaciones
        await fetchConversations(true);
        console.log(`✅ Conversación ${sessionId} restaurada`);
        return result.conversation;
      } else {
        console.error('Error restaurando conversación:', result.error);
        return null;
      }
    } catch (err) {
      console.error('Error en restoreConversation:', err);
      return null;
    }
  }, [fetchConversations]);

  /**
   * Refresca manualmente la lista de conversaciones
   */
  const refreshConversations = useCallback(() => {
    return fetchConversations(true);
  }, [fetchConversations]);

  // Cargar conversaciones al montar o cuando cambie la sesión
  useEffect(() => {
    if (status === 'authenticated') {
      // Llamar directamente sin depender de fetchConversations
      const loadConversations = async () => {
        setIsLoading(true);
        setError(null);

        try {
          const result = await conversationService.getUserConversations();

          if (result.success) {
            setConversations(result.conversations);
            setLastFetch(Date.now());
            console.log(`✅ ${result.total} conversaciones cargadas desde backend`);
          } else {
            setError(result.error);
            console.error('Error obteniendo conversaciones:', result.error);
          }
        } catch (err) {
          setError(err.message);
          console.error('Error en loadConversations:', err);
        } finally {
          setIsLoading(false);
        }
      };

      loadConversations();
    } else if (status === 'unauthenticated') {
      setConversations([]);
      setError(null);
    }
  }, [status]); // Solo depende de status

  return {
    // Estado
    conversations,
    isLoading,
    error,
    hasConversations: conversations.length > 0,

    // Acciones
    fetchConversations: refreshConversations,
    getConversationDetail,
    deleteConversation,
    restoreConversation,
    
    // Utilidades
    totalConversations: conversations.length
  };
};

export default useBackendConversations;
