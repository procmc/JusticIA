/**
 * Utilidades para manejo de mensajes, expedientes y streaming en el chat
 * Consolida toda la lógica de negocio relacionada con mensajes de Chat.jsx
 */

import { validarFormatoExpediente, normalizarExpediente } from '../ingesta-datos/ingestaUtils';
import { formatearSoloHoraCostaRica } from '../dateUtils';

// ============================================
// CONSTANTES
// ============================================

export const EXPEDIENTE_WELCOME_MESSAGE = `¡Hola! Me alegra que hayas elegido consultar un tema específico. 

Puedo ayudarte a generar resúmenes, responder cualquier consulta y crear borradores sobre el tema que selecciones.

---

### **¿Cómo funciona?**

**1.** Elige un tema de la lista de abajo o escribe su nombre  
**2.** Realiza cualquier consulta específica sobre ese tema  
**3.** Para cambiar de tema, pulsa «Nueva» o vuelve a marcar «Por tema específico»  

---

**¿Sobre qué tema quieres consultar?**`;

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
      ? `Cambiar consulta a tema: ${newExpediente}`
      : `Establecer consulta para tema: ${newExpediente}`,
    isUser: true,
    timestamp: formatearSoloHoraCostaRica(new Date()),
    scope: 'expediente',
    expedienteNumber: newExpediente
  };

  const assistantMessage = {
    text: isChange
      ? `**Tema cambiado:** ${newExpediente}\n\nAhora puedes hacer cualquier consulta sobre este nuevo tema. ¿Qué te gustaría saber?`
      : `**Tema establecido:** ${newExpediente}\n\nAhora puedes hacer cualquier consulta sobre este tema. ¿Qué te gustaría saber?`,
    isUser: false,
    timestamp: formatearSoloHoraCostaRica(new Date())
  };

  return { userMessage, assistantMessage };
};

/**
 * El tema que el usuario quiso decir (RF-06.2): el de la lista de temas disponibles que coincide con lo escrito, sin distinguir
 * mayúsculas ni espacios de más, con su nombre exacto (el servidor filtra por el nombre tal como se registró). Si la lista no se
 * pudo cargar (`temas` vacío), acepta el texto tal cual para no bloquear el chat; el servidor responde sin documentos si no existe.
 * Devuelve null si no hay coincidencia, o si el texto está vacío o supera los 60 caracteres que admite un tema.
 */
export const resolverTema = (texto, temas) => {
  const escrito = (texto || '').trim().replace(/\s+/g, ' ');
  if (!escrito || escrito.length > 60) return null;
  if (!temas || temas.length === 0) return escrito;
  const coincidencia = temas.find((t) => t.nombre.toLowerCase() === escrito.toLowerCase());
  return coincidencia ? coincidencia.nombre : null;
};

/**
 * Crea los mensajes cuando lo escrito no coincide con ningún tema: avisa y recuerda cuáles hay (RF-06.2).
 */
export const createTemaNoEncontradoMessage = (userText, temas) => {
  const lista = (temas || []).slice(0, 8).map((t) => `- ${t.nombre}`).join('\n');
  return {
    userMessage: {
      text: userText,
      isUser: true,
      timestamp: formatearSoloHoraCostaRica(new Date()),
      scope: 'expediente'
    },
    assistantMessage: {
      text: `No encontré un tema con ese nombre. Elige uno de la lista de abajo o escríbelo tal como aparece.${lista ? `\n\nAlgunos temas disponibles:\n${lista}` : ''}`,
      isUser: false,
      timestamp: formatearSoloHoraCostaRica(new Date())
    }
  };
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
    text: `Para realizar consultas sobre un tema específico, **necesito que ingreses el nombre de un tema válido**.\n\nSi deseas hacer una **consulta general** o una búsqueda amplia, puedes cambiar a "Búsqueda general" usando los botones de abajo.\n\n¿Tienes un tema específico que quieras consultar?`,
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

/**
 * Marca mensaje como cortado por pérdida de conexión a mitad de stream
 * (ver createStreamingCallbacks -> temporizador de inactividad). A
 * diferencia de createErrorMessage(), conserva el texto parcial que ya
 * había llegado antes del corte en vez de reemplazarlo.
 */
export const markMessageAsConnectionLost = (message) => (
  markMessageWithNotice(message, 'Se perdió la conexión con el servidor. Intente de nuevo.')
);

/**
 * Agrega un aviso de error al mensaje conservando el texto ya recibido (RF-11.67) y quita
 * la etapa visible. Sirve para el aviso de conexión perdida, el de pregunta larga y el del tope.
 */
export const markMessageWithNotice = (message, notice) => {
  const currentText = message.text || '';
  return {
    ...message,
    etapa: undefined,
    text: currentText.trim()
      ? `${currentText}\n\n---\n\n*${notice}*`
      : `*${notice}*`,
    timestamp: formatearSoloHoraCostaRica(new Date()),
    isError: true
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

// Los errores del motor llegan con este texto del servidor: no se muestran tal cual (RF-11.67 los deja fuera de alcance).
const PREFIJO_ERROR_DEL_MOTOR = 'Error al procesar la consulta';

// Si un stream se queda en silencio (ningún dato del servidor: ni etapa, ni señal de
// vida, ni chunk, ni done, ni error) por más
// de esto, se da por perdida la conexión y se libera el estado solo. Ver
// doc 26 §3.9: un corte abrupto (crash de Docker, wifi) no dispara ni
// onComplete ni onError -- reader.read() del fetch se queda esperando una
// promesa que nunca se resuelve.
const STREAM_INACTIVITY_TIMEOUT_MS = 30000;

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
  let inactivityTimer = null;

  const clearInactivityTimer = () => {
    if (inactivityTimer) {
      clearTimeout(inactivityTimer);
      inactivityTimer = null;
    }
  };

  const onConnectionLost = () => {
    inactivityTimer = null;
    // Verificar que esta request siga siendo la activa
    if (currentRequestRef.current?.active && currentRequestRef.current?.id === requestId) {
      setStreamingMessageIndex(null);
      setIsTyping(false);
      currentRequestRef.current = null;

      setMessages(prevMessages => {
        const updatedMessages = [...prevMessages];
        if (updatedMessages[messageIndex]) {
          updatedMessages[messageIndex] = markMessageAsConnectionLost(updatedMessages[messageIndex]);
        }
        return updatedMessages;
      });
    }
  };

  const resetInactivityTimer = () => {
    clearInactivityTimer();
    inactivityTimer = setTimeout(onConnectionLost, STREAM_INACTIVITY_TIMEOUT_MS);
  };

  // Arranca el reloj desde ya: si no llega ni el primer chunk (silencio
  // total desde el inicio de la consulta), también debe liberarse solo.
  resetInactivityTimer();

  const isActiveRequest = () => (
    currentRequestRef.current?.active && currentRequestRef.current?.id === requestId
  );

  // Cualquier dato del stream (etapa, señal de vida, tipo desconocido) cuenta como actividad (RF-16.60).
  const onActividad = () => {
    if (isActiveRequest()) resetInactivityTimer();
  };

  // La etapa que informa el servidor sustituye a la animación hasta que llega el primer texto (RF-11.64).
  const onEtapa = (etapa) => {
    if (isActiveRequest()) {
      resetInactivityTimer();
      setMessages(prevMessages => {
        const updatedMessages = [...prevMessages];
        if (updatedMessages[messageIndex]) {
          updatedMessages[messageIndex] = { ...updatedMessages[messageIndex], etapa };
        }
        return updatedMessages;
      });
    }
  };

  const onChunk = (chunk) => {
    // Verificar que esta request siga siendo la activa
    if (currentRequestRef.current?.active && currentRequestRef.current?.id === requestId) {
      resetInactivityTimer();
      setMessages(prevMessages => {
        const updatedMessages = [...prevMessages];
        if (updatedMessages[messageIndex]) {
          updatedMessages[messageIndex] = {
            ...updatedMessages[messageIndex],
            etapa: undefined,
            text: (updatedMessages[messageIndex].text || '') + chunk
          };
        }
        return updatedMessages;
      });
    }
  };

  const onComplete = () => {
    clearInactivityTimer();
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
                // Vuelve a armar el reloj para el reintento -- si tampoco
                // llega nada esta vez, debe liberarse solo igual que la
                // primera vez.
                resetInactivityTimer();

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
          updatedMessages[messageIndex] = assignTimestamp({ ...updatedMessages[messageIndex], etapa: undefined });
        }
        return updatedMessages;
      });
    }
  };

  const onError = (error) => {
    clearInactivityTimer();
    // Verificar que esta request siga siendo la activa
    if (currentRequestRef.current?.active && currentRequestRef.current?.id === requestId) {
      setStreamingMessageIndex(null);
      setIsTyping(false);
      currentRequestRef.current = null;

      setMessages(prevMessages => {
        const updatedMessages = [...prevMessages];
        const actual = updatedMessages[messageIndex];
        if (actual) {
          // RF-11.67: se conserva el texto recibido. El aviso del servidor (pregunta larga, tope) se muestra tal cual;
          // el error del motor y los fallos locales, con el texto genérico de siempre.
          const avisoDelServidor = error?.deServidor && !String(error.message).startsWith(PREFIJO_ERROR_DEL_MOTOR);
          const generico = createErrorMessage(error);
          if (avisoDelServidor) {
            updatedMessages[messageIndex] = markMessageWithNotice(actual, error.message);
          } else if ((actual.text || '').trim()) {
            updatedMessages[messageIndex] = markMessageWithNotice(actual, generico.text);
          } else {
            updatedMessages[messageIndex] = generico;
          }
        }
        return updatedMessages;
      });
    }
  };

  return { onChunk, onComplete, onError, onEtapa, onActividad, alRecibir: { onEtapa, onActividad } };
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

/**
 * Guarda el chat de un notebook en sessionStorage, con clave propia por
 * notebook. A diferencia del chat general (una sola conversación activa
 * a la vez), en NotebookServIA conviven varias conversaciones -- una por
 * notebook -- así que no alcanza con una clave global como
 * 'current_chat_session'.
 */
export const saveNotebookChatToSessionStorage = (notebookId, sessionId, messages) => {
  if (!notebookId || !sessionId || !messages || messages.length === 0) return;
  try {
    sessionStorage.setItem(`notebook_chat_session_${notebookId}`, sessionId);
    sessionStorage.setItem(`notebook_chat_messages_${notebookId}`, JSON.stringify(messages));
  } catch (error) {
    // sessionStorage lleno o inaccesible (navegación privada): no es crítico
  }
};

/**
 * Restaura el chat de un notebook desde sessionStorage, si existe.
 * Devuelve null si no hay nada guardado para ese notebook.
 */
export const restoreNotebookChatFromSessionStorage = (notebookId) => {
  if (!notebookId) return null;
  try {
    const savedSessionId = sessionStorage.getItem(`notebook_chat_session_${notebookId}`);
    const savedMessages = sessionStorage.getItem(`notebook_chat_messages_${notebookId}`);

    if (savedSessionId && savedMessages) {
      const parsedMessages = JSON.parse(savedMessages);
      if (parsedMessages.length > 0) {
        return { sessionId: savedSessionId, messages: parsedMessages };
      }
    }
  } catch (error) {
    sessionStorage.removeItem(`notebook_chat_messages_${notebookId}`);
  }
  return null;
};
