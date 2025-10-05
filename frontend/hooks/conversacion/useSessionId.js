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
    if (session?.user?.email) {
      const userId = session.user.email;
      const timestamp = Date.now();
      const newId = `session_${userId}_${timestamp}`;
      
      setSessionId(newId);
      setIsReady(true);
      
      console.log('✅ Session ID generado:', newId);
    } else if (!session) {
      // Usuario no autenticado, usar ID anónimo
      const timestamp = Date.now();
      const newId = `session_anonymous_${timestamp}`;
      
      setSessionId(newId);
      setIsReady(true);
      
      console.log('✅ Session ID anónimo generado:', newId);
    }
  }, [session?.user?.email]);

  // Limpiar session al navegar fuera del chat
  useEffect(() => {
    const handleRouteChange = (url) => {
      if (!url.includes('/consulta-datos/chat')) {
        console.log('🔄 Navegando fuera del chat - nueva sesión al volver');
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
    const userId = session?.user?.email || 'anonymous';
    const timestamp = Date.now();
    const newId = `session_${userId}_${timestamp}`;
    
    setSessionId(newId);
    console.log('🆕 Nueva sesión iniciada:', newId);
    
    return newId;
  }, [session?.user?.email]);

  return {
    sessionId,
    newSession,
    isReady
  };
};
