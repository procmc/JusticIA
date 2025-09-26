import { useSession } from 'next-auth/react';
import { useCallback, useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/router';
import { autoCleanupIfNeeded } from '../../utils/chatContextUtils';

/**
 * Hook mejorado para manejar contexto de chat con persistencia
 * - Integra NextAuth para identificación de usuario
 * - Persiste contexto en localStorage vinculado al usuario
 * - Mantiene conversaciones separadas por sesión de usuario
 * - Recupera contexto después de recargas de página
 * - Permite múltiples conversaciones por usuario
 */
export const usePersistentChatContext = () => {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [contextHistory, setContextHistory] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Generar clave única para el usuario
  const getUserKey = useCallback(() => {
    if (session?.user?.id) {
      return `chat_user_${session.user.id}`;
    }
    return 'chat_anonymous';
  }, [session?.user?.id]);

  // Generar ID de conversación
  const generateConversationId = useCallback(() => {
    const timestamp = Date.now();
    const userPart = session?.user?.id || 'anon';
    return `conv_${userPart}_${timestamp}`;
  }, [session?.user?.id]);

  // Obtener clave de almacenamiento para el contexto
  const getContextKey = useCallback((convId) => {
    const userKey = getUserKey();
    return `${userKey}_context_${convId}`;
  }, [getUserKey]);

  // Obtener clave para lista de conversaciones del usuario
  const getConversationsKey = useCallback(() => {
    const userKey = getUserKey();
    return `${userKey}_conversations`;
  }, [getUserKey]);

  // Cargar conversaciones del usuario
  const loadUserConversations = useCallback(() => {
    try {
      // Verificar que estamos en el cliente
      if (typeof window === 'undefined') return [];
      
      const conversationsKey = getConversationsKey();
      const saved = localStorage.getItem(conversationsKey);
      return saved ? JSON.parse(saved) : [];
    } catch (error) {
      console.error('Error cargando conversaciones:', error);
      return [];
    }
  }, [getConversationsKey]);

  // Guardar lista de conversaciones
  const saveUserConversations = useCallback((conversations) => {
    try {
      // Verificar que estamos en el cliente
      if (typeof window === 'undefined') return;
      
      const conversationsKey = getConversationsKey();
      localStorage.setItem(conversationsKey, JSON.stringify(conversations));
    } catch (error) {
      console.error('Error guardando conversaciones:', error);
    }
  }, [getConversationsKey]);

  // Cargar contexto de una conversación específica
  const loadConversationContext = useCallback((convId) => {
    try {
      // Verificar que estamos en el cliente
      if (typeof window === 'undefined') return [];
      
      const contextKey = getContextKey(convId);
      const saved = localStorage.getItem(contextKey);
      return saved ? JSON.parse(saved) : [];
    } catch (error) {
      console.error('Error cargando contexto:', error);
      return [];
    }
  }, [getContextKey]);

  // Guardar contexto de conversación
  const saveConversationContext = useCallback((convId, context) => {
    try {
      // Verificar que estamos en el cliente
      if (typeof window === 'undefined') return;
      
      const contextKey = getContextKey(convId);
      localStorage.setItem(contextKey, JSON.stringify(context));
      
      // Actualizar metadata de la conversación
      const conversations = loadUserConversations();
      const existingIndex = conversations.findIndex(c => c.id === convId);
      
      const conversationMeta = {
        id: convId,
        lastMessage: context.length > 0 ? context[context.length - 1] : null,
        lastUpdated: new Date().toISOString(),
        messageCount: context.length
      };

      if (existingIndex >= 0) {
        conversations[existingIndex] = conversationMeta;
      } else {
        conversations.push(conversationMeta);
      }

      // Mantener solo las últimas 10 conversaciones
      const sortedConversations = conversations
        .sort((a, b) => new Date(b.lastUpdated) - new Date(a.lastUpdated))
        .slice(0, 10);

      saveUserConversations(sortedConversations);
    } catch (error) {
      console.error('Error guardando contexto:', error);
    }
  }, [getContextKey, loadUserConversations, saveUserConversations]);

  // Inicializar contexto al cambiar sesión
  useEffect(() => {
    // Solo ejecutar en el cliente cuando la sesión esté lista
    if (typeof window === 'undefined' || status === 'loading') return;

    const initializeContext = async () => {
      setIsLoading(true);
      
      // Ejecutar limpieza automática si es necesario
      autoCleanupIfNeeded();
      
      // Cargar conversaciones del usuario
      const conversations = loadUserConversations();
      
      if (conversations.length > 0) {
        // Cargar la conversación más reciente
        const latestConversation = conversations[0];
        setConversationId(latestConversation.id);
        
        // Cargar el contexto de esa conversación
        const context = loadConversationContext(latestConversation.id);
        setContextHistory(context);
        
        console.log(`Contexto cargado para conversación ${latestConversation.id}:`, context.length, 'mensajes');
      } else {
        // Crear nueva conversación si no hay ninguna
        const newConvId = generateConversationId();
        setConversationId(newConvId);
        setContextHistory([]);
        
        console.log('Nueva conversación creada:', newConvId);
      }
      
      setIsLoading(false);
    };

    initializeContext();
  }, [status, session?.user?.id, loadUserConversations, loadConversationContext, generateConversationId]);

  // Agregar nuevo intercambio al contexto
  const addToContext = useCallback((userMessage, assistantResponse) => {
    if (!userMessage?.trim() || !assistantResponse?.trim() || !conversationId) {
      console.warn('No se puede agregar al contexto: mensaje vacío o sin conversación activa');
      return;
    }

    const newEntry = {
      id: Date.now(),
      userMessage: userMessage.trim(),
      assistantResponse: assistantResponse.trim(),
      timestamp: new Date().toISOString(),
      conversationId
    };

    setContextHistory(prev => {
      // Mantener últimos 15 intercambios para contexto robusto
      const updated = [...prev, newEntry];
      const limited = updated.slice(-15);
      
      // Guardar en localStorage
      saveConversationContext(conversationId, limited);
      
      console.log(`Contexto actualizado para conversación ${conversationId}:`, limited.length, 'intercambios');
      
      return limited;
    });
  }, [conversationId, saveConversationContext]);

  // Obtener contexto formateado para el backend
  const getFormattedContext = useCallback(() => {
    if (contextHistory.length === 0) {
      return '';
    }

    const contextLines = ['HISTORIAL DE CONVERSACIÓN PREVIA:'];
    
    // Usar los últimos 4 intercambios para contexto efectivo pero completo
    const recentHistory = contextHistory.slice(-4);
    
    recentHistory.forEach((entry, index) => {
      contextLines.push(`\n[Intercambio ${index + 1}]`);
      contextLines.push(`Usuario: ${entry.userMessage}`);
      
      // Mantener más contexto del asistente, especialmente listas y detalles importantes
      const response = entry.assistantResponse.length > 2000 
        ? entry.assistantResponse.substring(0, 2000) + '...[respuesta truncada]'
        : entry.assistantResponse;
      
      contextLines.push(`Asistente: ${response}`);
    });

    const formattedContext = contextLines.join('\n');
    console.log('🔄 Contexto formateado para envío:', {
      historyLength: contextHistory.length,
      recentHistoryLength: recentHistory.length,
      contextSize: formattedContext.length,
      preview: formattedContext.substring(0, 200) + '...'
    });
    
    contextLines.push('\n---\nNUEVA CONSULTA:');
    
    return formattedContext;
  }, [contextHistory]);

  // Crear nueva conversación
  const startNewConversation = useCallback(() => {
    const newConvId = generateConversationId();
    setConversationId(newConvId);
    setContextHistory([]);
    
    console.log('Nueva conversación iniciada:', newConvId);
  }, [generateConversationId]);

  // Cambiar a una conversación existente
  const switchToConversation = useCallback((convId) => {
    if (convId === conversationId) return;
    
    const context = loadConversationContext(convId);
    setConversationId(convId);
    setContextHistory(context);
    
    console.log(`Cambiado a conversación ${convId}:`, context.length, 'mensajes');
  }, [conversationId, loadConversationContext]);

  // Eliminar una conversación
  const deleteConversation = useCallback((convId) => {
    try {
      // Verificar que estamos en el cliente
      if (typeof window === 'undefined') return;
      
      // Eliminar contexto
      const contextKey = getContextKey(convId);
      localStorage.removeItem(contextKey);
      
      // Actualizar lista de conversaciones
      const conversations = loadUserConversations();
      const filtered = conversations.filter(c => c.id !== convId);
      saveUserConversations(filtered);
      
      // Si era la conversación activa, crear una nueva
      if (convId === conversationId) {
        startNewConversation();
      }
      
      console.log('Conversación eliminada:', convId);
    } catch (error) {
      console.error('Error eliminando conversación:', error);
    }
  }, [conversationId, getContextKey, loadUserConversations, saveUserConversations, startNewConversation]);

  // Limpiar contexto de conversación actual
  const clearCurrentConversation = useCallback(() => {
    if (!conversationId) return;
    
    setContextHistory([]);
    saveConversationContext(conversationId, []);
    
    console.log('Contexto de conversación actual limpiado');
  }, [conversationId, saveConversationContext]);

  // Obtener estadísticas del contexto
  const getContextStats = useCallback(() => {
    const totalChars = contextHistory.reduce((acc, entry) => 
      acc + entry.userMessage.length + entry.assistantResponse.length, 0
    );

    return {
      conversationId,
      totalInteractions: contextHistory.length,
      hasContext: contextHistory.length > 0,
      totalCharacters: totalChars,
      lastInteraction: contextHistory.length > 0 
        ? new Date(contextHistory[contextHistory.length - 1].timestamp)
        : null,
      isLoading,
      userConversations: loadUserConversations()
    };
  }, [conversationId, contextHistory, isLoading, loadUserConversations]);

  return {
    // Estado
    conversationId,
    contextHistory,
    isLoading,
    hasContext: contextHistory.length > 0,
    
    // Funciones principales
    addToContext,
    getFormattedContext,
    getContextStats,
    
    // Gestión de conversaciones
    startNewConversation,
    switchToConversation,
    deleteConversation,
    clearCurrentConversation,
    
    // Datos adicionales
    userConversations: loadUserConversations(),
    isAuthenticated: !!session?.user
  };
};