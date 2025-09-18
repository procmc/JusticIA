import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { v4 as uuidv4 } from 'uuid';

/**
 * Hook para manejar el contexto de conversación usando NextAuth + localStorage
 * Sin necesidad de cambios en la base de datos
 */
export const useConversationContext = () => {
  const { data: session } = useSession();
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);

  // Generar o recuperar ID de conversación
  useEffect(() => {
    if (session?.user?.id) {
      // Si hay usuario autenticado, usar su ID + timestamp
      const storageKey = `conversation_${session.user.id}`;
      let savedConversationId = localStorage.getItem(storageKey);
      
      if (!savedConversationId) {
        // Crear nueva conversación
        savedConversationId = `${session.user.id}_${Date.now()}`;
        localStorage.setItem(storageKey, savedConversationId);
      }
      
      setConversationId(savedConversationId);
    } else {
      // Usuario anónimo - usar localStorage temporal
      let anonId = localStorage.getItem('anon_conversation_id');
      if (!anonId) {
        anonId = `anon_${uuidv4()}`;
        localStorage.setItem('anon_conversation_id', anonId);
      }
      setConversationId(anonId);
    }
  }, [session]);

  // Cargar mensajes guardados
  useEffect(() => {
    if (conversationId) {
      const savedMessages = localStorage.getItem(`messages_${conversationId}`);
      if (savedMessages) {
        try {
          setMessages(JSON.parse(savedMessages));
        } catch (error) {
          console.error('Error cargando mensajes guardados:', error);
          setMessages([]);
        }
      }
    }
  }, [conversationId]);

  // Guardar mensajes cuando cambien
  useEffect(() => {
    if (conversationId && messages.length > 0) {
      try {
        localStorage.setItem(`messages_${conversationId}`, JSON.stringify(messages));
      } catch (error) {
        console.error('Error guardando mensajes:', error);
      }
    }
  }, [conversationId, messages]);

  /**
   * Agrega un nuevo mensaje a la conversación
   */
  const addMessage = (message) => {
    const newMessage = {
      ...message,
      id: uuidv4(),
      timestamp: new Date().toISOString(),
      conversationId
    };
    
    setMessages(prev => [...prev, newMessage]);
    return newMessage;
  };

  /**
   * Actualiza un mensaje existente (útil para streaming)
   */
  const updateMessage = (messageId, updates) => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageId ? { ...msg, ...updates } : msg
    ));
  };

  /**
   * Obtiene el contexto de conversación para enviar al backend
   * Solo incluye los últimos N mensajes para no sobrecargar
   */
  const getConversationContext = (maxMessages = 6) => {
    const recentMessages = messages.slice(-maxMessages);
    
    if (recentMessages.length === 0) return null;
    
    return {
      conversationId,
      messages: recentMessages.map(msg => ({
        type: msg.isUser ? 'user' : 'assistant',
        content: msg.text,
        timestamp: msg.timestamp
      }))
    };
  };

  /**
   * Formatea el contexto para incluir en el prompt
   */
  const formatContextForPrompt = (maxMessages = 6) => {
    const recentMessages = messages.slice(-maxMessages);
    
    if (recentMessages.length === 0) return '';
    
    const contextLines = ['HISTORIAL DE CONVERSACIÓN PREVIA:'];
    
    recentMessages.forEach(msg => {
      if (msg.isUser) {
        contextLines.push(`Usuario: ${msg.text}`);
      } else {
        // Limitar respuestas largas del asistente
        const content = msg.text.length > 300 ? 
          msg.text.substring(0, 300) + '...' : msg.text;
        contextLines.push(`Asistente: ${content}`);
      }
    });
    
    contextLines.push('---');
    contextLines.push('NUEVA CONSULTA:');
    
    return contextLines.join('\n');
  };

  /**
   * Inicia una nueva conversación
   */
  const startNewConversation = () => {
    const newId = session?.user?.id ? 
      `${session.user.id}_${Date.now()}` : 
      `anon_${uuidv4()}`;
    
    setConversationId(newId);
    setMessages([]);
    
    // Actualizar localStorage
    const storageKey = session?.user?.id ? 
      `conversation_${session.user.id}` : 
      'anon_conversation_id';
    localStorage.setItem(storageKey, newId);
  };

  /**
   * Limpia el historial actual
   */
  const clearConversation = () => {
    if (conversationId) {
      localStorage.removeItem(`messages_${conversationId}`);
      setMessages([]);
    }
  };

  return {
    conversationId,
    messages,
    addMessage,
    updateMessage,
    getConversationContext,
    formatContextForPrompt,
    startNewConversation,
    clearConversation,
    hasContext: messages.length > 0
  };
};