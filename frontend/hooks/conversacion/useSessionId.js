import { useSession } from 'next-auth/react';
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';

/**
 * Hook para gestión de session_id conversacional.
 * 
 * Reemplaza a useChatContext con un enfoque más simple:
 * - Backend gestiona el historial automáticamente
 * - Frontend solo mantiene el session_id
 * - Genera nuevo ID al iniciar o al cambiar de conversación
 * 
 * @returns {Object} { sessionId, newSession, isReady }
 */
export const useSessionId = () => {
  const { data: session } = useSession();
  const router = useRouter();
  const [sessionId, setSessionId] = useState(null);
  const [isReady, setIsReady] = useState(false);

  // Generar session_id cuando el usuario esté disponible
  useEffect(() => {
    // Primero verificar si hay un sessionId guardado (reload)
    const savedSessionId = sessionStorage.getItem('current_chat_session');
    
    if (savedSessionId) {
      // Es un reload, reutilizar el sessionId existente
      setSessionId(savedSessionId);
      setIsReady(true);
      return;
    }
    
    // No hay sessionId guardado, generar uno nuevo
    if (session?.user?.email) {
      const userId = session.user.email;
      const timestamp = Date.now();
      const newId = `session_${userId}_${timestamp}`;
      
      setSessionId(newId);
      setIsReady(true);
    } else if (!session) {
      // Usuario no autenticado, usar ID anónimo
      const timestamp = Date.now();
      const newId = `session_anonymous_${timestamp}`;
      
      setSessionId(newId);
      setIsReady(true);
    }
  }, [session?.user?.email]);

  // Limpiar session al navegar fuera del chat
  useEffect(() => {
    const handleRouteChange = (url) => {
      if (!url.includes('/consulta-datos/chat')) {
        setIsReady(false);
      }
    };

    router.events.on('routeChangeStart', handleRouteChange);
    return () => {
      router.events.off('routeChangeStart', handleRouteChange);
    };
  }, [router]);

  // Función para iniciar nueva conversación
  const newSession = useCallback(() => {
    // Limpiar el sessionId guardado para forzar uno nuevo
    sessionStorage.removeItem('current_chat_session');
    sessionStorage.removeItem('current_chat_messages');
    sessionStorage.removeItem('current_chat_scope');
    sessionStorage.removeItem('current_chat_expediente');
    
    const userId = session?.user?.email || 'anonymous';
    const timestamp = Date.now();
    const newId = `session_${userId}_${timestamp}`;
    
    setSessionId(newId);
    
    return newId;
  }, [session?.user?.email]);

  // Función para restaurar una conversación existente con su session_id original
  const restoreSession = useCallback((existingSessionId) => {
    if (!existingSessionId) {
      console.error('restoreSession: sessionId no válido');
      return false;
    }
    
    // Actualizar el sessionId a la sesión existente
    setSessionId(existingSessionId);
    
    // Guardar en sessionStorage para persistir en reloads
    sessionStorage.setItem('current_chat_session', existingSessionId);
    
    return true;
  }, []);

  return {
    sessionId,
    newSession,
    restoreSession,
    isReady
  };
};
