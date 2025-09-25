import { useRouter } from 'next/router';
import { useEffect } from 'react';
import { clearAllChatContext, hasStoredContext } from '../../utils/chatContextUtils';

/**
 * Hook que limpia automáticamente el contexto cuando es necesario
 * Monitorea la navegación y eventos del navegador
 */
export const useChatContextCleanup = () => {
  const router = useRouter();

  useEffect(() => {
    // Limpiar contexto cuando se navega fuera del chat
    const handleRouteChange = (url) => {
      if (!url.includes('/consulta-datos/chat') && hasStoredContext()) {
        console.log('Navegando fuera del chat - limpiando contexto persistente');
        clearAllChatContext();
      }
    };

    // Limpiar contexto cuando se cierra/recarga la página
    const handleBeforeUnload = () => {
      if (hasStoredContext()) {
        console.log('Página cerrándose - limpiando contexto');
        clearAllChatContext();
      }
    };

    // Limpiar contexto cuando la pestaña pierde el foco por mucho tiempo
    let tabHiddenTimeout;
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // Limpiar contexto después de 30 minutos de inactividad
        tabHiddenTimeout = setTimeout(() => {
          if (hasStoredContext()) {
            console.log('Pestaña inactiva por mucho tiempo - limpiando contexto');
            clearAllChatContext();
          }
        }, 30 * 60 * 1000); // 30 minutos
      } else {
        // Cancelar el timeout si la pestaña vuelve a estar activa
        if (tabHiddenTimeout) {
          clearTimeout(tabHiddenTimeout);
        }
      }
    };

    // Agregar event listeners
    router.events.on('routeChangeStart', handleRouteChange);
    window.addEventListener('beforeunload', handleBeforeUnload);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      // Limpiar event listeners
      router.events.off('routeChangeStart', handleRouteChange);
      window.removeEventListener('beforeunload', handleBeforeUnload);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      
      if (tabHiddenTimeout) {
        clearTimeout(tabHiddenTimeout);
      }
    };
  }, [router]);

  // Función manual para limpiar contexto
  const manualCleanup = () => {
    clearAllChatContext();
  };

  return { manualCleanup };
};