/**
 * @deprecated Este hook ha sido reemplazado por useChatContext.js
 * 
 * PROBLEMA IDENTIFICADO:
 * - Usa sessionStorage que persiste en recargas de página
 * - No se limpia automáticamente en navegación/logout
 * - Causa problemas de contexto no deseado
 * 
 * USAR EN SU LUGAR: hooks/conversacion/useChatContext.js
 */

// Este archivo se mantiene solo para evitar errores de importación
// TODO: Eliminar cuando se confirme que no se usa en ningún lugar

console.warn(
  'DEPRECATED: useConversationContext está obsoleto. Usar useChatContext en su lugar.'
);

import { useSession } from 'next-auth/react';
import { useCallback, useEffect, useState } from 'react';

export const useConversationContext = () => {
  console.error('useConversationContext está deprecado. Usar useChatContext de hooks/conversacion/useChatContext.js');
  
  const { data: session } = useSession();
  const [contextHistory, setContextHistory] = useState([]);

  // Clave única para cada usuario
  const getContextKey = useCallback(() => {
    const userId = session?.user?.email || session?.user?.id || 'anonymous';
    return `justicia_context_${userId}`;
  }, [session]);

  // NO cargar contexto automáticamente - este es el problema
  useEffect(() => {
    console.warn('Hook deprecado useConversationContext en uso - migrar a useChatContext');
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