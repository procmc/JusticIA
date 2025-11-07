/**
 * Utilidades para manejo de mensajes, expedientes y streaming en el chat
 * Consolida toda la lógica de negocio relacionada con mensajes de Chat.jsx
 */

import { validarFormatoExpediente, normalizarExpediente } from '../ingesta-datos/ingestaUtils';
import { formatearSoloHoraCostaRica } from '../dateUtils';

// ============================================
// CONSTANTES
// ============================================

export const EXPEDIENTE_WELCOME_MESSAGE = `¡Hola! Me alegra que hayas elegido consultar un expediente específico. 

Puedo ayudarte a generar resúmenes, responder cualquier consulta y crear borradores sobre el expediente que selecciones.

---

### **¿Cómo funciona?**

**1.** Proporciona el número del expediente que deseas analizar  
**2.** Realiza cualquier consulta específica sobre el caso  
**3.** Cambia a otro expediente escribiendo un nuevo número  

---

**¿Tienes el número de expediente que quieres consultar?**`;

// ============================================
// VALIDACIÓN Y MANEJO DE EXPEDIENTES
// ============================================

/**
 * Valida si el texto es un número de expediente válido
 */
export const isValidExpediente = (text) => {
  return validarFormatoExpediente(text);
};

/**
 * Normaliza un número de expediente (mayúsculas y guiones ASCII)
 */
export const normalizeExpediente = (text) => {
  return normalizarExpediente(text.trim());
};

/**
 * Verifica si se debe cambiar de expediente
 */
export const shouldChangeExpediente = (text, currentExpediente) => {
  if (!isValidExpediente(text)) return false;
  const newExpediente = normalizeExpediente(text);
  return newExpediente !== currentExpediente;
};

/**
 * Crea mensajes para cambio/establecimiento de expediente
 */
export const createExpedienteMessages = (newExpediente, isChange) => {
  const userMessage = {
    text: isChange
      ? `Cambiar consulta a expediente: ${newExpediente}`
      : `Establecer consulta para expediente: ${newExpediente}`,
    isUser: true,
    timestamp: formatearSoloHoraCostaRica(new Date()),
    scope: 'expediente',
    expedienteNumber: newExpediente
  };

  const assistantMessage = {
    text: isChange
      ? `**Expediente cambiado:** ${newExpediente}\n\nAhora puedes hacer cualquier consulta sobre este nuevo expediente. ¿Qué te gustaría saber?`
      : `**Expediente establecido:** ${newExpediente}\n\nAhora puedes hacer cualquier consulta sobre este expediente. ¿Qué te gustaría saber?`,
    isUser: false,
    timestamp: formatearSoloHoraCostaRica(new Date())
  };

  return { userMessage, assistantMessage };
};

/**
 * Crea mensaje cuando no hay expediente en modo expediente
 */
export const createNoExpedienteMessage = (userText) => {
  const userMessage = {
    text: userText,
    isUser: true,
    timestamp: formatearSoloHoraCostaRica(new Date()),
    scope: 'expediente'
  };

  const assistantMessage = {
    text: `Para realizar consultas sobre un expediente específico, **necesito que ingreses un número de expediente válido**.\n\nSi deseas hacer una **consulta general** sobre temas legales o búsquedas amplias, puedes cambiar a "Búsqueda general" usando los botones de abajo.\n\n¿Tienes un número de expediente específico que quieras consultar?`,
    isUser: false,
    timestamp: formatearSoloHoraCostaRica(new Date())
  };

  return { userMessage, assistantMessage };
};

// ============================================
// CREACIÓN DE MENSAJES
// ============================================

/**
 * Crea un mensaje de usuario
 */
export const createUserMessage = (text, searchScope, expedienteNumber = null) => {
  return {
    text,
    isUser: true,
    timestamp: formatearSoloHoraCostaRica(new Date()),
    scope: searchScope,
    expedienteNumber: searchScope === 'expediente' ? expedienteNumber : null
  };
};

/**
 * Crea un mensaje vacío del asistente (para streaming)
 */
export const createEmptyAssistantMessage = () => {
  return {
    text: '',
    isUser: false,
    timestamp: '' // Se asignará cuando termine la respuesta
  };
};

/**
 * Crea mensaje de bienvenida para modo expediente
 */
export const createWelcomeMessage = () => {
  return {
    text: EXPEDIENTE_WELCOME_MESSAGE,
    isUser: false,
    timestamp: formatearSoloHoraCostaRica(new Date())
  };
};

/**
 * Asigna timestamp a mensaje completado
 */
export const assignTimestamp = (message) => {
  return {
    ...message,
    timestamp: formatearSoloHoraCostaRica(new Date())
  };
};

/**
 * Marca mensaje como cancelado
 */
export const markMessageAsCanceled = (message) => {
  const currentText = message.text || '';
  return {
    ...message,
    text: currentText.trim() 
      ? currentText + '\n\n---\n\n*Consulta cancelada por el usuario*'
      : '*Consulta cancelada por el usuario*',
    timestamp: formatearSoloHoraCostaRica(new Date()),
    isCanceled: true
  };
};

// ============================================
// MANEJO DE ERRORES
// ============================================

/**
 * Crea mensaje de error específico según tipo
 */
export const createErrorMessage = (error) => {
  let errorMessage = 'Lo siento, ocurrió un error al procesar tu consulta.';

  const errorText = typeof error === 'string' 
    ? error 
    : (error.message || error.toString() || 'Error desconocido');

  if (errorText.includes('No se puede conectar con el servidor backend')) {
    errorMessage = '**Error de Conexión**\n\nNo se puede conectar con el servidor backend. Por favor verifica que:\n\n• El servidor backend esté ejecutándose en el puerto 8000\n• Ollama esté activo en el puerto 11434\n• No haya problemas de red\n\nIntenta nuevamente en unos momentos.';
  } else if (errorText.includes('Failed to fetch')) {
    errorMessage = '**Error de Red**\n\nNo se puede conectar con el servidor. Verifica tu conexión y que los servicios estén activos.';
  }

  return {
    text: errorMessage,
    isError: true,
    timestamp: formatearSoloHoraCostaRica(new Date())
  };
};

// ============================================
// CALLBACKS DE STREAMING
// ============================================

/**
 * Crea callbacks para streaming de mensajes
 */
export const createStreamingCallbacks = (
  messageIndex,
  currentRequestRef,
  requestId,
  setMessages,
  setStreamingMessageIndex,
  setIsTyping,
  retryCountRef,
  retryFunction
) => {
  const onChunk = (chunk) => {
    // Verificar que esta request siga siendo la activa
    if (currentRequestRef.current?.active && currentRequestRef.current?.id === requestId) {
      setMessages(prevMessages => {
        const updatedMessages = [...prevMessages];
        if (updatedMessages[messageIndex]) {
          updatedMessages[messageIndex] = {
            ...updatedMessages[messageIndex],
            text: (updatedMessages[messageIndex].text || '') + chunk
          };
        }
        return updatedMessages;
      });
    }
  };

  const onComplete = () => {
    // Verificar que esta request siga siendo la activa
    if (currentRequestRef.current?.active && currentRequestRef.current?.id === requestId) {
      setStreamingMessageIndex(null);
      setIsTyping(false);
      currentRequestRef.current = null;

      // Asignar timestamp al mensaje completado
      setMessages(prevMessages => {
        const updatedMessages = [...prevMessages];
        if (updatedMessages[messageIndex]) {
          const responseText = updatedMessages[messageIndex].text || '';
          
          // Solo reintentar si la respuesta está completamente vacía Y no hemos reintentado antes
          if (!responseText.trim() && retryCountRef.current === 0) {
            retryCountRef.current = 1;
            
            // Mantener el mensaje y agregar indicador de reintento
            updatedMessages[messageIndex] = {
              ...updatedMessages[messageIndex],
              text: 'Reintentando obtener respuesta...',
              timestamp: '',
              isRetrying: true
            };
            
            // Reintentar después de una pausa
            setTimeout(() => {
              // Verificar que no se haya iniciado otra consulta mientras tanto
              if (currentRequestRef.current === null || currentRequestRef.current.id === requestId) {
                setIsTyping(true);
                setStreamingMessageIndex(messageIndex);
                
                const retryRequestId = requestId + 0.1;
                currentRequestRef.current = { active: true, id: retryRequestId };
                
                // Limpiar el mensaje antes de reintentar
                setMessages(prev => {
                  const updated = [...prev];
                  if (updated[messageIndex]) {
                    updated[messageIndex] = {
                      ...updated[messageIndex],
                      text: '',
                      isRetrying: false
                    };
                  }
                  return updated;
                });
                
                // Ejecutar función de reintento
                if (retryFunction) {
                  retryFunction().catch((error) => {
                    // Error en reintento
                    if (currentRequestRef.current?.active && currentRequestRef.current?.id === retryRequestId) {
                      setStreamingMessageIndex(null);
                      setIsTyping(false);
                      currentRequestRef.current = null;
                      
                      setMessages(prevMsgs => {
                        const updated = [...prevMsgs];
                        if (updated[messageIndex]) {
                          updated[messageIndex] = createErrorMessage(error);
                        }
                        return updated;
                      });
                    }
                  });
                }
              }
            }, 1500);
            
            return updatedMessages;
          }
          
          // Respuesta exitosa o ya reintentamos
          updatedMessages[messageIndex] = assignTimestamp(updatedMessages[messageIndex]);
        }
        return updatedMessages;
      });
    }
  };

  const onError = (error) => {
    // Verificar que esta request siga siendo la activa
    if (currentRequestRef.current?.active && currentRequestRef.current?.id === requestId) {
      setStreamingMessageIndex(null);
      setIsTyping(false);
      currentRequestRef.current = null;

      setMessages(prevMessages => {
        const updatedMessages = [...prevMessages];
        if (updatedMessages[messageIndex]) {
          updatedMessages[messageIndex] = createErrorMessage(error);
        }
        return updatedMessages;
      });
    }
  };

  return { onChunk, onComplete, onError };
};

// ============================================
// GESTIÓN DE SESSIONSTORAGE
// ============================================

/**
 * Guarda el estado actual en sessionStorage
 */
export const saveToSessionStorage = (sessionId, messages, searchScope, consultedExpediente) => {
  if (messages.length > 0 && sessionId) {
    sessionStorage.setItem('current_chat_session', sessionId);
    sessionStorage.setItem('current_chat_messages', JSON.stringify(messages));
    sessionStorage.setItem('current_chat_scope', searchScope);
    if (consultedExpediente) {
      sessionStorage.setItem('current_chat_expediente', consultedExpediente);
    }
  }
};

/**
 * Restaura el estado desde sessionStorage
 */
export const restoreFromSessionStorage = (sessionId) => {
  const savedSessionId = sessionStorage.getItem('current_chat_session');
  const savedMessages = sessionStorage.getItem('current_chat_messages');
  const savedScope = sessionStorage.getItem('current_chat_scope');
  const savedExpediente = sessionStorage.getItem('current_chat_expediente');

  // Si hay datos guardados Y el sessionId coincide, restaurar
  if (savedSessionId === sessionId && savedMessages) {
    try {
      const parsedMessages = JSON.parse(savedMessages);
      if (parsedMessages.length > 0) {
        return {
          messages: parsedMessages,
          scope: savedScope || 'general',
          expediente: savedExpediente || null
        };
      }
    } catch (error) {
      // Error al parsear, limpiar datos corruptos
      sessionStorage.removeItem('current_chat_messages');
    }
  }

  return null;
};
