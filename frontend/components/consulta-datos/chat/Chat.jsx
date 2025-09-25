import React, { useState, useRef } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
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

  // Hook para manejar el contexto de conversación (corregido)
  const { 
    addToContext, 
    getFormattedContext, 
    clearContext, 
    hasContext,
    getContextStats,
    startNewConversation 
  } = useChatContext();

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
      scope: searchScope
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
    const conversationContext = hasContext ? getFormattedContext() : '';
    
    // ======= MODO STREAMING MEJORADO =======
    try {
      await consultaService.consultaGeneralStreaming(
        text,
        (chunk) => {
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
        },
        () => {
          // Callback cuando termina el streaming
          if (currentRequestRef.current?.active) {
            setStreamingMessageIndex(null);
            setIsTyping(false);
            currentRequestRef.current = null;
            
            // Asignar timestamp al finalizar
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
              }
              return updatedMessages;
            });
            
            // Guardar la conversación en el contexto
            const finalMessage = messages[messageIndex];
            if (finalMessage?.text?.trim()) {
              addToContext(text, finalMessage.text.trim());
            }
          }
        },
        (error) => {
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
        },
        5, // topK
        conversationContext
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
      {/* Botón elegante y discreto de nuevo chat */}
      {messages.length > 0 && (
        <button
          onClick={() => {
            startNewConversation();
            setMessages([]);
          }}
          className="absolute top-3 right-3 z-20 group flex items-center gap-2 px-3 py-1.5 text-xs text-gray-400 hover:text-gray-700 bg-white/80 hover:bg-white border border-gray-200/50 hover:border-gray-300 rounded-full shadow-sm hover:shadow transition-all duration-300 backdrop-blur-sm"
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
          setSearchScope={setSearchScope}
        />
      </div>
    </div>
  );
};

export default ConsultaChat;
