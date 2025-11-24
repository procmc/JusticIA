import { useSession } from 'next-auth/react';
import { useCallback, useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/router';

/**
 * Hook corregido para manejar contexto de chat
 * - NO persiste automáticamente en sessionStorage
 * - Solo mantiene contexto en memoria durante la sesión activa
 * - Se limpia automáticamente en navegación y logout
 */
export const useChatContext = () => {
  const { data: session } = useSession();
  const router = useRouter();
  const [contextHistory, setContextHistory] = useState([]);
  const conversationStartRef = useRef(Date.now());

  // Clave única para identificar la sesión de chat actual
  const getSessionKey = useCallback(() => {
    const userId = session?.user?.email || session?.user?.id || 'anonymous';
    return `chat_session_${userId}_${conversationStartRef.current}`;
  }, [session]);

  // Limpiar contexto cuando se navega fuera del chat
  useEffect(() => {
    const handleRouteChange = (url) => {
      // Si navegamos fuera de la página de chat, limpiar contexto
      if (!url.includes('/consulta-datos/chat')) {
        console.log('Navegando fuera del chat - limpiando contexto');
        setContextHistory([]);
        conversationStartRef.current = Date.now(); // Nueva sesión
      }
    };

    router.events.on('routeChangeStart', handleRouteChange);
    return () => {
      router.events.off('routeChangeStart', handleRouteChange);
    };
  }, [router]);

  // Limpiar contexto cuando cambie la sesión (login/logout)
  useEffect(() => {
    console.log('Sesión cambió - reiniciando contexto');
    setContextHistory([]);
    conversationStartRef.current = Date.now();
  }, [session?.user?.id]);

  // Agregar nuevo intercambio al contexto (solo en memoria)
  const addToContext = useCallback((userMessage, assistantResponse) => {
    if (!userMessage?.trim() || !assistantResponse?.trim()) {
      console.warn('Intentando agregar mensajes vacíos al contexto');
      return;
    }

    const newEntry = {
      id: Date.now(),
      userMessage: userMessage.trim(),
      assistantResponse: assistantResponse.trim(),
      timestamp: new Date().toISOString(),
      sessionKey: getSessionKey(),
    };

    setContextHistory(prev => {
      // Mantener solo los últimos 10 intercambios para contexto eficiente
      const updated = [...prev, newEntry];
      const limited = updated.slice(-10);
      
      console.log(`Contexto actualizado: ${limited.length} intercambios`, {
        sessionKey: newEntry.sessionKey,
        totalChars: limited.reduce((acc, entry) => 
          acc + entry.userMessage.length + entry.assistantResponse.length, 0
        )
      });
      
      return limited;
    });
  }, [getSessionKey]);

  // Obtener contexto formateado para enviar al backend
  const getFormattedContext = useCallback(() => {
    console.log('getFormattedContext llamado, contextHistory.length:', contextHistory.length);
    
    if (contextHistory.length === 0) {
      console.log('No hay contexto - devolviendo string vacío');
      return '';
    }

    console.log('Formateando contexto con', contextHistory.length, 'entradas');
    const contextLines = ['HISTORIAL DE CONVERSACIÓN PREVIA:'];
    
    // Usar los últimos 3 intercambios para mantener contexto completo sin sobrecargar
    const recentHistory = contextHistory.slice(-3);
    
    recentHistory.forEach((entry, index) => {
      contextLines.push(`\n[Intercambio ${index + 1}]`);
      contextLines.push(`Usuario: ${entry.userMessage}`);
      
      // Guardar la respuesta completa del asistente para mantener todo el contexto
      // Especialmente importante para respuestas con múltiples expedientes
      contextLines.push(`Asistente: ${entry.assistantResponse}`);
    });
    
    contextLines.push('\n---\nNUEVA CONSULTA:');
    
    const resultado = contextLines.join('\n');
    console.log('Contexto formateado:', resultado.substring(0, 200) + '...');
    
    return resultado;
  }, [contextHistory]);

  // Limpiar contexto manualmente (para botón "Nueva conversación")
  const clearContext = useCallback(() => {
    console.log('Limpiando contexto manualmente');
    setContextHistory([]);
    conversationStartRef.current = Date.now(); // Nueva sesión
  }, []);

  // Iniciar nueva conversación
  const startNewConversation = useCallback(() => {
    console.log('Iniciando nueva conversación');
    clearContext();
  }, [clearContext]);

  // Obtener estadísticas del contexto
  const getContextStats = useCallback(() => {
    const totalChars = contextHistory.reduce((acc, entry) => 
      acc + entry.userMessage.length + entry.assistantResponse.length, 0
    );

    return {
      totalInteractions: contextHistory.length,
      hasContext: contextHistory.length > 0,
      totalCharacters: totalChars,
      sessionKey: getSessionKey(),
      lastInteraction: contextHistory.length > 0 
        ? new Date(contextHistory[contextHistory.length - 1].timestamp)
        : null,
    };
  }, [contextHistory, getSessionKey]);

  return {
    contextHistory,
    addToContext,
    getFormattedContext,
    clearContext,
    startNewConversation,
    getContextStats,
    hasContext: contextHistory.length > 0,
  };
};