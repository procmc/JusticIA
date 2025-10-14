import React, { useState, useRef } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import ConversationHistory from './ConversationHistory';
import consultaService from '../../../services/consultaService';
import RAG_CONFIG from '../../../config/ragConfig';
import { useSessionId } from '../../../hooks/conversacion/useSessionId';
import { validarFormatoExpediente, normalizarExpediente } from '../../../utils/ingesta-datos/ingestaUtils';

const ConsultaChat = () => {
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [streamingMessageIndex, setStreamingMessageIndex] = useState(null);
  const stopStreamingRef = useRef(false);
  const currentRequestRef = useRef(null);
  const retryCountRef = useRef(0);

  // Estados para el alcance de búsqueda
  const [searchScope, setSearchScope] = useState('general');
  const [consultedExpediente, setConsultedExpediente] = useState(null); // Para rastrear el expediente consultado

  // Función personalizada para cambiar el scope y limpiar cuando sea necesario
  const handleSearchScopeChange = (newScope) => {
    // Solo cambiar si realmente es diferente al modo actual
    if (newScope !== searchScope) {
      // Limpiar conversación e iniciar nueva sesión al cambiar de modo
      setMessages([]);
      setConsultedExpediente(null);
      newSession();  // Generar nuevo session_id
      setSearchScope(newScope);

      // Mostrar mensaje de bienvenida específico para el modo expediente
      if (newScope === 'expediente') {
        const welcomeMessage = {
          text: `¡Hola! Me alegra que hayas elegido consultar un expediente específico. 

---

### 🎯 **¿Cómo funciona?**

**1.** Proporciona el número del expediente que deseas analizar  
**2.** Realiza cualquier consulta específica sobre el caso  
**3.** Cambia a otro expediente escribiendo un nuevo número  

---

**¿Tienes el número de expediente que quieres consultar?**`,
          isUser: false,
          timestamp: new Date().toLocaleTimeString('es-ES', {
            hour: '2-digit',
            minute: '2-digit'
          })
        };
        setMessages([welcomeMessage]);
      }
    }
  };

  // Función para detectar si un texto es un número de expediente
  const isExpedienteNumber = validarFormatoExpediente;

  // Estado para el modal de historial
  const [showHistory, setShowHistory] = useState(false);

  // Hook para gestión de session_id (backend gestiona el historial automáticamente)
  const { sessionId, newSession, isReady } = useSessionId();

  const handleStopGeneration = () => {
    stopStreamingRef.current = true;
    setIsTyping(false);
    setStreamingMessageIndex(null);

    // Cancelar la request actual si existe
    if (currentRequestRef.current) {
      currentRequestRef.current.active = false;
      currentRequestRef.current = null;
    }

    // Cancelar en el servicio también
    consultaService.cancelConsulta();
  };

  const handleSendMessage = async (text) => {
    // IMPORTANTE: Cancelar cualquier consulta en progreso PRIMERO
    if (currentRequestRef.current?.active) {
      stopStreamingRef.current = true;
      currentRequestRef.current.active = false;
      consultaService.cancelConsulta();
      // Esperar un poco para asegurar que la cancelación se complete
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    // Si estamos en modo expediente específico
    if (searchScope === 'expediente') {
      // Verificar si el texto es un número de expediente (nuevo o cambio de expediente)
      if (isExpedienteNumber(text)) {
        // Normalizar el expediente (convertir guiones Unicode a ASCII y mayúsculas)
        const newExpediente = normalizarExpediente(text.trim());

        // Si es un expediente diferente al actual, cambiarlo
        if (newExpediente !== consultedExpediente) {
          setConsultedExpediente(newExpediente);

          // Crear mensaje del usuario indicando que se estableció/cambió el expediente
          const userMessage = {
            text: consultedExpediente
              ? `Cambiar consulta a expediente: ${newExpediente}`
              : `Establecer consulta para expediente: ${newExpediente}`,
            isUser: true,
            timestamp: new Date().toLocaleTimeString('es-ES', {
              hour: '2-digit',
              minute: '2-digit'
            }),
            scope: searchScope,
            expedienteNumber: newExpediente
          };

          // Crear mensaje del asistente confirmando
          const assistantMessage = {
            text: consultedExpediente
              ? ` **Expediente cambiado:** ${newExpediente}\n\nAhora puedes hacer cualquier consulta sobre este nuevo expediente. ¿Qué te gustaría saber?`
              : ` **Expediente establecido:** ${newExpediente}\n\nAhora puedes hacer cualquier consulta sobre este expediente. ¿Qué te gustaría saber?`,
            isUser: false,
            timestamp: new Date().toLocaleTimeString('es-ES', {
              hour: '2-digit',
              minute: '2-digit'
            })
          };

          setMessages(prev => [...prev, userMessage, assistantMessage]);

          // NUEVO: Actualizar inmediatamente el contexto en el backend
          const action = consultedExpediente ? 'change' : 'set';
          consultaService.updateExpedienteContext(sessionId, newExpediente, action)
            .catch(error => {
              console.error('Error sincronizando contexto:', error);
            });
          return;
        }
      }
      // Si no tenemos expediente consultado y el texto no es un número válido
      else if (!consultedExpediente) {
        // No es un número de expediente válido - responder como asistente
        const userMessage = {
          text: text,
          isUser: true,
          timestamp: new Date().toLocaleTimeString('es-ES', {
            hour: '2-digit',
            minute: '2-digit'
          }),
          scope: searchScope
        };

        const assistantMessage = {
          text: `Para realizar consultas sobre un expediente específico, **necesito que ingreses un número de expediente válido**.\n\nSi deseas hacer una **consulta general** sobre temas legales o búsquedas amplias, puedes cambiar a "Búsqueda general" usando los botones de abajo.\n\n¿Tienes un número de expediente específico que quieras consultar?`,
          isUser: false,
          timestamp: new Date().toLocaleTimeString('es-ES', {
            hour: '2-digit',
            minute: '2-digit'
          })
        };

        setMessages(prev => [...prev, userMessage, assistantMessage]);
        return;
      }
    }

    // Resetear flag de parada y contador de reintentos
    stopStreamingRef.current = false;
    retryCountRef.current = 0;

    // Crear nueva referencia de request con ID único para rastreo
    const requestId = Date.now();
    currentRequestRef.current = { active: true, id: requestId };

    // Crear mensaje del usuario
    const userMessage = {
      text,
      isUser: true,
      timestamp: new Date().toLocaleTimeString('es-ES', {
        hour: '2-digit',
        minute: '2-digit'
      }),
      scope: searchScope,
      expedienteNumber: searchScope === 'expediente' ? consultedExpediente : null
    };

    // Agregar mensaje del usuario
    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);

    // Crear mensaje del asistente vacío SIN timestamp
    const assistantMessage = {
      text: '',
      isUser: false,
      timestamp: '' // Se asignará cuando termine la respuesta
    };

    // Agregar mensaje vacío del asistente
    setMessages(prev => [...prev, assistantMessage]);

    // Obtener el índice del mensaje que vamos a actualizar
    const messageIndex = messages.length + 1; // +1 porque ya agregamos el mensaje del usuario
    setStreamingMessageIndex(messageIndex);
    setIsTyping(false);

    // Validar que tengamos session_id antes de continuar
    if (!sessionId) {
      console.error('No hay session_id disponible');
      setIsTyping(false);
      setStreamingMessageIndex(null);
      return;
    }

    // ======= MODO STREAMING MEJORADO =======
    try {
      // Definir callbacks comunes para ambos tipos de consulta
      const onChunk = (chunk) => {
        // Callback para cada chunk recibido
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
        // Callback cuando termina el streaming
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
                
                // NO vaciar el texto, mantener el mensaje y agregar indicador de reintento
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
                    
                    const retryRequestId = requestId + 0.1; // ID ligeramente diferente para el reintento
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
                    
                    consultaService.consultaGeneralStreaming(
                      text,
                      onChunk,
                      onComplete,
                      onError,
                      null,
                      sessionId,
                      searchScope === 'expediente' ? consultedExpediente : null
                    ).catch(onError);
                  }
                }, 1500);
                
                return updatedMessages;
              }
              
              // Respuesta exitosa o ya reintentamos
              updatedMessages[messageIndex] = {
                ...updatedMessages[messageIndex],
                timestamp: new Date().toLocaleTimeString('es-ES', {
                  hour: '2-digit',
                  minute: '2-digit'
                }),
                isRetrying: false
              };
            }
            return updatedMessages;
          });
        }
      };

      const onError = (error) => {
        // Callback para errores
        // Verificar que esta request siga siendo la activa
        if (currentRequestRef.current?.active && currentRequestRef.current?.id === requestId) {
          console.error('Error en consulta:', error);
          setStreamingMessageIndex(null);
          setIsTyping(false);
          currentRequestRef.current = null;

          setMessages(prevMessages => {
            const updatedMessages = [...prevMessages];
            if (updatedMessages[messageIndex]) {
              updatedMessages[messageIndex] = {
                ...updatedMessages[messageIndex],
                text: 'Lo siento, ocurrió un error al procesar tu consulta. Por favor, intenta nuevamente o consulta con un profesional legal.',
                isError: true,
                timestamp: new Date().toLocaleTimeString('es-ES', {
                  hour: '2-digit',
                  minute: '2-digit'
                })
              };
            }
            return updatedMessages;
          });
        }
      };

      // Llamar al servicio con gestión automática de historial
      await consultaService.consultaGeneralStreaming(
        text,
        onChunk,
        onComplete,
        onError,
        null, // topK null = usar config según tipo de búsqueda
        sessionId,  // Backend gestiona historial con este ID
        searchScope === 'expediente' ? consultedExpediente : null // pasar expediente como parámetro
      );

    } catch (error) {
      console.error('Error en handleSendMessage:', error);

      // Limpiar estado
      setStreamingMessageIndex(null);
      setIsTyping(false);
      currentRequestRef.current = null;

      // Mostrar mensaje de error específico
      setMessages(prevMessages => {
        const updatedMessages = [...prevMessages];
        if (updatedMessages[messageIndex]) {
          let errorMessage = 'Lo siento, ocurrió un error al procesar tu consulta.';

          // Manejar diferentes tipos de error
          const errorText = typeof error === 'string' ? error : (error.message || error.toString() || 'Error desconocido');

          if (errorText.includes('No se puede conectar con el servidor backend')) {
            errorMessage = '🔌 **Error de Conexión**\n\nNo se puede conectar con el servidor backend. Por favor verifica que:\n\n• El servidor backend esté ejecutándose en el puerto 8000\n• Ollama esté activo en el puerto 11434\n• No haya problemas de red\n\nIntenta nuevamente en unos momentos.';
          } else if (errorText.includes('Failed to fetch')) {
            errorMessage = '🔌 **Error de Red**\n\nNo se puede conectar con el servidor. Verifica tu conexión y que los servicios estén activos.';
          }

          updatedMessages[messageIndex] = {
            ...updatedMessages[messageIndex],
            text: errorMessage,
            isError: true,
            timestamp: new Date().toLocaleTimeString('es-ES', {
              hour: '2-digit',
              minute: '2-digit'
            })
          };
        }
        return updatedMessages;
      });
    }
    // ======= FIN MODO STREAMING =======
  };

  return (
    <div className="h-full flex flex-col bg-white relative">
      {/* Indicador de sesión activa */}
      {sessionId && messages.length > 0 && (
        <div className="absolute top-3 left-3 z-20 flex items-center gap-2 px-3 py-1.5 text-xs text-blue-600 bg-blue-50/80 border border-blue-200/50 rounded-full shadow-sm backdrop-blur-sm">
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
          <span className="font-medium">
            Conversación activa ({messages.filter(m => m.isUser).length} mensajes)
          </span>
        </div>
      )}

      {/* Controles de chat */}
      <div className="absolute top-3 right-3 z-20 flex items-center gap-2">
        {/* Botón de historial */}
        <button
          onClick={() => setShowHistory(true)}
          className="group flex items-center gap-2 px-3 py-1.5 text-xs text-gray-400 hover:text-gray-700 bg-white/80 hover:bg-white border border-gray-200/50 hover:border-gray-300 rounded-full shadow-sm hover:shadow transition-all duration-300 backdrop-blur-sm"
          title="Ver historial de conversaciones"
        >
          <svg
            className="w-3.5 h-3.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="font-medium hidden sm:block">Historial</span>
        </button>

        {/* Botón elegante y discreto de nuevo chat */}
        {messages.length > 0 && (
          <button
            onClick={() => {

              // Mantener el modo actual (general o expediente) y solo limpiar la conversación
              newSession();  // Generar nuevo session_id
              setMessages([]);
              
              // Solo limpiar expediente si estamos en modo expediente
              if (searchScope === 'expediente') {
                setConsultedExpediente(null);
                
                // Mostrar mensaje de bienvenida para modo expediente
                const welcomeMessage = {
                  text: `¡Hola! Me alegra que hayas elegido consultar un expediente específico. 

---

### 🎯 **¿Cómo funciona?**

**1.** Proporciona el número del expediente que deseas analizar  
**2.** Realiza cualquier consulta específica sobre el caso  
**3.** Cambia a otro expediente escribiendo un nuevo número  

---

**¿Tienes el número de expediente que quieres consultar?**`,
                  isUser: false,
                  timestamp: new Date().toLocaleTimeString('es-ES', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })
                };
                // Usar setTimeout para asegurar que se ejecute después del setMessages([])
                setTimeout(() => setMessages([welcomeMessage]), 0);
              }
              // Para modo general, simplemente se queda con mensajes vacíos (estado inicial limpio)
            }}
            className="group flex items-center gap-2 px-3 py-1.5 text-xs text-gray-400 hover:text-gray-700 bg-white/80 hover:bg-white border border-gray-200/50 hover:border-gray-300 rounded-full shadow-sm hover:shadow transition-all duration-300 backdrop-blur-sm"
            title="Nueva conversación"
          >
            <svg
              className="w-3.5 h-3.5 transition-transform group-hover:rotate-90"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 4v16m8-8H4"
              />
            </svg>
            <span className="font-medium hidden sm:block">Nueva</span>
          </button>
        )}
      </div>

      {/* Chat Area - Sin header para más espacio */}
      <div className="flex-1 flex flex-col min-h-0">
        <MessageList
          messages={messages}
          isTyping={isTyping}
          streamingMessageIndex={streamingMessageIndex}
        />

        <ChatInput
          onSendMessage={handleSendMessage}
          onStopGeneration={handleStopGeneration}
          isDisabled={false} // El chat siempre está disponible
          isLoading={isTyping || streamingMessageIndex !== null}
          searchScope={searchScope}
          setSearchScope={handleSearchScopeChange}
          consultedExpediente={consultedExpediente}
        />
      </div>

      {/* Modal de historial de conversaciones */}
      <ConversationHistory
        isOpen={showHistory}
        onClose={() => setShowHistory(false)}
        onConversationSelect={(sessionId, conversation) => {
          // Restaurar conversación seleccionada
          if (conversation && conversation.messages) {
            // Convertir mensajes del backend al formato del frontend
            const restoredMessages = conversation.messages.map(msg => ({
              text: msg.content,
              isUser: msg.role === 'user',
              timestamp: new Date().toLocaleTimeString('es-ES', {
                hour: '2-digit',
                minute: '2-digit'
              })
            }));
            
            setMessages(restoredMessages);
            
            // Si la conversación tiene un expediente asociado, restaurar el contexto
            if (conversation.expediente_number) {
              setConsultedExpediente(conversation.expediente_number);
              setSearchScope('expediente');
            } else {
              setSearchScope('general');
              setConsultedExpediente(null);
            }
            
            console.log(`✅ Conversación ${sessionId} restaurada con ${restoredMessages.length} mensajes`);
          }
        }}
        onNewConversation={() => {
          // Crear nueva conversación
          newSession();
          setMessages([]);
          setConsultedExpediente(null);
          
          // Si estamos en modo expediente, mostrar mensaje de bienvenida
          if (searchScope === 'expediente') {
            const welcomeMessage = {
              text: `¡Hola! Me alegra que hayas elegido consultar un expediente específico. 

---

### 🎯 **¿Cómo funciona?**

**1.** Proporciona el número del expediente que deseas analizar  
**2.** Realiza cualquier consulta específica sobre el caso  
**3.** Cambia a otro expediente escribiendo un nuevo número  

---

**¿Tienes el número de expediente que quieres consultar?**`,
              isUser: false,
              timestamp: new Date().toLocaleTimeString('es-ES', {
                hour: '2-digit',
                minute: '2-digit'
              })
            };
            setMessages([welcomeMessage]);
          }
        }}
      />
    </div>
  );
};

export default ConsultaChat;
