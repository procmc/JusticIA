import React, { useState, useRef } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import consultaService from '../../../services/consultaService';
import { useConversationContext } from '../../../hooks/conversacion/useConversationContext';

const ConsultaChat = () => {
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [streamingMessageIndex, setStreamingMessageIndex] = useState(null);
  const stopStreamingRef = useRef(false);
  const currentRequestRef = useRef(null);

  // Estados para el alcance de búsqueda
  const [searchScope, setSearchScope] = useState('general');

  // Hook para manejar el contexto de conversación
  const { 
    addToContext, 
    getFormattedContext, 
    clearContext, 
    hasContext,
    getContextStats 
  } = useConversationContext();

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

    // Obtener el contexto de conversación formateado
    const conversationContext = getFormattedContext();
    
    // Variable para almacenar la respuesta completa
    let fullResponse = '';

    // Iniciar consulta con streaming FUERA del setMessages
    consultaService.consultaGeneralStreaming(
      text,
      // onChunk: Cada fragmento de texto que llega
      (chunk) => {
        if (stopStreamingRef.current || !currentRequestRef.current?.active) return;
        
        // Acumular la respuesta completa
        fullResponse += chunk;
        
        setMessages(prevMessages => {
          const updatedMessages = [...prevMessages];
          if (updatedMessages[messageIndex]) {
            updatedMessages[messageIndex] = {
              ...updatedMessages[messageIndex],
              text: updatedMessages[messageIndex].text + chunk
            };
          }
          return updatedMessages;
        });
      },
      // onComplete: Cuando termina el streaming
      () => {
        if (currentRequestRef.current?.active) {
          setStreamingMessageIndex(null);
          setIsTyping(false);
          currentRequestRef.current = null;
          
          // Actualizar el timestamp del mensaje del asistente AHORA que terminó
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
          if (fullResponse.trim()) {
            addToContext(text, fullResponse.trim());
          }
        }
      },
      // onError: Si hay un error
      (error) => {
        console.error('Error en la consulta:', error);
        if (currentRequestRef.current?.active) {
          setStreamingMessageIndex(null);
          setIsTyping(false);
          currentRequestRef.current = null;
          
          // Mostrar mensaje de error
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
      10, // topK
      conversationContext // contexto de conversación
    );
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Información del contexto - solo mostrar si hay contexto */}
      {hasContext && (
        <div className="px-4 py-2 bg-blue-50 border-b border-blue-200 text-sm text-blue-700 flex items-center justify-between">
          <span>
            💬 Conversación activa ({getContextStats().totalInteractions} intercambios)
          </span>
          <button
            onClick={() => {
              clearContext();
              setMessages([]); // También limpiar mensajes visuales
            }}
            className="text-blue-600 hover:text-blue-800 underline text-xs"
            title="Limpiar historial de conversación"
          >
            Nuevo chat
          </button>
        </div>
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
