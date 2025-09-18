import { useSession } from 'next-auth/react';
import { useCallback, useEffect, useState } from 'react';

/**
 * Hook personalizado para manejar el contexto de conversación
 * Almacena el historial de mensajes en sessionStorage vinculado al usuario
 */
export const useConversationContext = () => {
  const { data: session } = useSession();
  const [contextHistory, setContextHistory] = useState([]);

  // Clave única para cada usuario
  const getContextKey = useCallback(() => {
    const userId = session?.user?.email || session?.user?.id || 'anonymous';
    return `justicia_context_${userId}`;
  }, [session]);

  // Cargar contexto al inicializar
  useEffect(() => {
    const loadContext = () => {
      try {
        const stored = sessionStorage.getItem(getContextKey());
        if (stored) {
          const parsed = JSON.parse(stored);
          setContextHistory(parsed);
        }
      } catch (error) {
        console.error('Error cargando contexto:', error);
        setContextHistory([]);
      }
    };

    loadContext();
  }, [getContextKey]);

  // Agregar nuevo intercambio al contexto
  const addToContext = useCallback((userMessage, assistantResponse) => {
    const newEntry = {
      id: Date.now(),
      userMessage: userMessage.trim(),
      assistantResponse: assistantResponse.trim(),
      timestamp: new Date().toISOString(),
    };

    setContextHistory(prev => {
      // Mantener solo los últimos 10 intercambios para no sobrecargar el contexto
      const updated = [...prev, newEntry];
      const limited = updated.slice(-10);
      
      try {
        sessionStorage.setItem(getContextKey(), JSON.stringify(limited));
      } catch (error) {
        console.error('Error guardando contexto:', error);
      }
      
      return limited;
    });
  }, [getContextKey]);

  // Obtener contexto formateado para enviar al backend
  const getFormattedContext = useCallback(() => {
    if (contextHistory.length === 0) {
      return '';
    }

    const contextLines = ['HISTORIAL DE CONVERSACIÓN PREVIA:'];
    
    // Agregar los últimos 6 intercambios para no sobrecargar
    const recentHistory = contextHistory.slice(-6);
    
    recentHistory.forEach((entry, index) => {
      contextLines.push(`\n[Intercambio ${index + 1}]`);
      contextLines.push(`Usuario: ${entry.userMessage}`);
      
      // Limitar la respuesta del asistente si es muy larga
      const response = entry.assistantResponse.length > 400 
        ? entry.assistantResponse.substring(0, 400) + '...'
        : entry.assistantResponse;
      
      contextLines.push(`Asistente: ${response}`);
    });
    
    contextLines.push('\n---\nNUEVA CONSULTA:');
    
    return contextLines.join('\n');
  }, [contextHistory]);

  // Limpiar contexto
  const clearContext = useCallback(() => {
    try {
      sessionStorage.removeItem(getContextKey());
      setContextHistory([]);
    } catch (error) {
      console.error('Error limpiando contexto:', error);
    }
  }, [getContextKey]);

  // Obtener estadísticas del contexto
  const getContextStats = useCallback(() => {
    return {
      totalInteractions: contextHistory.length,
      hasContext: contextHistory.length > 0,
      lastInteraction: contextHistory.length > 0 
        ? new Date(contextHistory[contextHistory.length - 1].timestamp)
        : null,
    };
  }, [contextHistory]);

  return {
    contextHistory,
    addToContext,
    getFormattedContext,
    clearContext,
    getContextStats,
    hasContext: contextHistory.length > 0,
  };
};