import React, { useState, useRef } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import ConversationHistory from './ConversationHistory';
import consultaService from '../../../services/consultaService';
import { useChatContext } from '../../../hooks/conversacion/useChatContext';

const ConsultaChat = () => {
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [streamingMessageIndex, setStreamingMessageIndex] = useState(null);
  const stopStreamingRef = useRef(false);
  const currentRequestRef = useRef(null);

  // Estados para el alcance de búsqueda
  const [searchScope, setSearchScope] = useState('general');
  const [consultedExpediente, setConsultedExpediente] = useState(null); // Para rastrear el expediente consultado

  // Función personalizada para cambiar el scope y limpiar cuando sea necesario
  const handleSearchScopeChange = (newScope) => {
    if (newScope !== searchScope) {
      // Si cambiamos de modo, limpiar la conversación
      setMessages([]);
      setConsultedExpediente(null);
      clearContext();
      
      setSearchScope(newScope);
      
      // Mostrar mensaje de bienvenida específico para el modo expediente
      if (newScope === 'expediente') {
        const welcomeMessage = {
          text: `**🔍 Modo: Consulta por Expediente Específico**\n\nPara comenzar, necesito que ingreses un número de expediente válido.\n\n**Formato:** YYYY-NNNNNN-NNNN-XX\n**Ejemplo:** 2022-097794-3873-PN\n\nUna vez que ingreses el número, podrás hacer cualquier consulta específica sobre ese expediente.\n\n💡 **Tip:** Si quieres hacer consultas generales sobre temas legales, cambia a "Búsqueda general".`,
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
  const isExpedienteNumber = (text) => {
    // Patrón típico de expedientes: YYYY-NNNNNN-NNNN-XX
    const expedientePattern = /^\d{4}-\d{6}-\d{4}-[A-Z]{2}$/;
    return expedientePattern.test(text.trim());
  };
  
  // Estado para el modal de historial
  const [showHistory, setShowHistory] = useState(false);

  // Hook para manejar el contexto de conversación (versión corregida sin persistencia problemática)
  const { 
    addToContext, 
    getFormattedContext, 
    clearContext, 
    hasContext,
    getContextStats,
    startNewConversation
  } = useChatContext();

  // DEBUG: Log del estado del contexto (comentado para reducir ruido)
  // console.log('🔍 Estado del contexto en Chat.jsx:', { hasContext, contextStats: getContextStats() });

  const handleStopGeneration = () => {
    stopStreamingRef.current = true;
    setIsTyping(false);
    setStreamingMessageIndex(null);
    
    // Cancelar la request actual si existe
    if (currentRequestRef.current) {
      currentRequestRef.current = null;
    }
  };

  const handleSendMessage = async (text) => {
    // Si estamos en modo expediente específico
    if (searchScope === 'expediente') {
      // Si no tenemos expediente consultado, verificar si el texto es un número de expediente
      if (!consultedExpediente) {
        if (isExpedienteNumber(text)) {
          // El usuario ingresó un número de expediente
          setConsultedExpediente(text.trim());
          
          // Crear mensaje del usuario indicando que se estableció el expediente
          const userMessage = {
            text: `Establecer consulta para expediente: ${text.trim()}`,
            isUser: true,
            timestamp: new Date().toLocaleTimeString('es-ES', {
              hour: '2-digit',
              minute: '2-digit'
            }),
            scope: searchScope,
            expedienteNumber: text.trim()
          };
          
          // Crear mensaje del asistente confirmando
          const assistantMessage = {
            text: `✅ **Expediente establecido:** ${text.trim()}\n\nAhora puedes hacer cualquier consulta sobre este expediente. ¿Qué te gustaría saber?`,
            isUser: false,
            timestamp: new Date().toLocaleTimeString('es-ES', {
              hour: '2-digit',
              minute: '2-digit'
            })
          };
          
          setMessages(prev => [...prev, userMessage, assistantMessage]);
          
          // Guardar también en el contexto para mantener la historia
          addToContext(
            `Establecer consulta para expediente: ${text.trim()}`,
            `Expediente ${text.trim()} establecido correctamente. Ahora puedes hacer cualquier consulta sobre este expediente.`
          );
          
          return;
        } else {
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
            text: `Para realizar consultas sobre un expediente específico, necesito que ingreses un número de expediente válido.\n\n**Formato esperado:** YYYY-NNNNNN-NNNN-XX\n**Ejemplo:** 2022-097794-3873-PN\n\nSi deseas hacer una **consulta general** sobre temas legales o búsquedas amplias, puedes cambiar a "Búsqueda general" usando los botones de arriba.\n\n¿Tienes un número de expediente específico que quieras consultar?`,
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
      // Si ya tenemos expediente consultado, continuar con la consulta normal
    }
    
    // Cancelar cualquier request anterior
    if (currentRequestRef.current) {
      stopStreamingRef.current = true;
    }
    
    // Resetear flag de parada
    stopStreamingRef.current = false;
    currentRequestRef.current = { active: true };

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

    // Obtener el contexto de conversación formateado SOLO si realmente hay contexto
    const contextStats = getContextStats();
    const conversationContext = hasContext ? getFormattedContext() : '';
    console.log('📤 DEBUG CONTEXTO - Enviando al backend:', { 
      hasContext, 
      contextLength: conversationContext.length,
      contextStats: contextStats,
      contextPreview: conversationContext.substring(0, 200) + '...'
    });
    
    // ======= MODO STREAMING MEJORADO =======
    try {
      // Definir callbacks comunes para ambos tipos de consulta
      const onChunk = (chunk) => {
        // Callback para cada chunk recibido
        if (currentRequestRef.current?.active) {
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
        if (currentRequestRef.current?.active) {
          setStreamingMessageIndex(null);
          setIsTyping(false);
          currentRequestRef.current = null;
          
          // Primero asignar timestamp
          setMessages(prevMessages => {
            const updatedMessages = [...prevMessages];
            if (updatedMessages[messageIndex]) {
              updatedMessages[messageIndex] = {
                ...updatedMessages[messageIndex],
                timestamp: new Date().toLocaleTimeString('es-ES', {
                  hour: '2-digit',
                  minute: '2-digit'
                })
              };
              
              // Guardar en el contexto DESPUÉS de actualizar los mensajes
              const finalMessage = updatedMessages[messageIndex];
              if (finalMessage?.text?.trim()) {
                console.log('💾 Guardando en contexto:', {
                  userMessage: text,
                  assistantResponse: finalMessage.text.trim().substring(0, 100) + '...',
                  length: finalMessage.text.trim().length
                });
                
                // Usar setTimeout para asegurar que se ejecute después del render
                setTimeout(() => {
                  console.log('🔧 Llamando addToContext con:', { text, responseLength: finalMessage.text.trim().length });
                  addToContext(text, finalMessage.text.trim());
                  console.log('✅ addToContext ejecutado, nuevo estado:', getContextStats());
                }, 50);
              }
            }
            return updatedMessages;
          });
        }
      };

      const onError = (error) => {
        // Callback para errores
        console.error('Error en streaming RAG:', error);
        if (currentRequestRef.current?.active) {
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

      // Usar siempre el endpoint general, pero pasar el expediente como parámetro separado
      await consultaService.consultaGeneralStreaming(
        text,
        onChunk,
        onComplete,
        onError,
        5, // topK
        conversationContext,
        searchScope === 'expediente' ? consultedExpediente : null // pasar expediente como parámetro
      );

    } catch (error) {
      console.error('❌ Error en handleSendMessage:', error);
      console.error('❌ Error tipo:', typeof error);
      console.error('❌ Error nombre:', error.name);
      console.error('❌ Error mensaje:', error.message);
      
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
      {/* Indicador de contexto mejorado */}
      {hasContext && (
        <div className="absolute top-3 left-3 z-20 flex items-center gap-2 px-3 py-1.5 text-xs text-green-600 bg-green-50/80 border border-green-200/50 rounded-full shadow-sm backdrop-blur-sm">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          <span className="font-medium">
            Contexto activo ({getContextStats().totalInteractions} intercambios)
          </span>
        </div>
      )}

      {/* El hook useChatContext no requiere indicador de carga ya que es instantáneo */}

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
              startNewConversation();
              setMessages([]);
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
        onConversationSelect={() => setMessages([])} // Limpiar mensajes UI al cambiar conversación
      />
    </div>
  );
};

export default ConsultaChat;
