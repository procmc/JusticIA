import React, { useState, useRef } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import consultaService from '../../../services/consultaService';

const ConsultaChat = () => {
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [streamingMessageIndex, setStreamingMessageIndex] = useState(null);
  const stopStreamingRef = useRef(false);

  // Estados para el alcance de búsqueda
  const [searchScope, setSearchScope] = useState('general');

  const handleStopGeneration = () => {
    stopStreamingRef.current = true;
    setIsTyping(false);
    setStreamingMessageIndex(null);
  };

  const handleSendMessage = async (text) => {
    // Resetear flag de parada
    stopStreamingRef.current = false;

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

    // Crear mensaje del asistente vacío
    const assistantMessage = {
      text: '',
      isUser: false,
      timestamp: new Date().toLocaleTimeString('es-ES', {
        hour: '2-digit',
        minute: '2-digit'
      })
    };

    // Agregar mensaje vacío del asistente
    setMessages(prev => {
      const newMessages = [...prev, assistantMessage];
      const messageIndex = newMessages.length - 1;
      setStreamingMessageIndex(messageIndex);
      setIsTyping(false);

      // Iniciar consulta con streaming
      consultaService.consultaGeneralStreaming(
        text,
        // onChunk: Cada fragmento de texto que llega
        (chunk) => {
          if (stopStreamingRef.current) return;
          
          setMessages(prevMessages => {
            const updatedMessages = [...prevMessages];
            updatedMessages[messageIndex] = {
              ...updatedMessages[messageIndex],
              text: updatedMessages[messageIndex].text + chunk
            };
            return updatedMessages;
          });
        },
        // onComplete: Cuando termina el streaming
        () => {
          setStreamingMessageIndex(null);
          setIsTyping(false);
        },
        // onError: Si hay un error
        (error) => {
          console.error('Error en la consulta:', error);
          setStreamingMessageIndex(null);
          setIsTyping(false);
          
          // Mostrar mensaje de error
          setMessages(prevMessages => {
            const updatedMessages = [...prevMessages];
            updatedMessages[messageIndex] = {
              ...updatedMessages[messageIndex],
              text: 'Lo siento, ocurrió un error al procesar tu consulta. Por favor, intenta nuevamente o consulta con un profesional legal.',
              isError: true
            };
            return updatedMessages;
          });
        },
        30 // top_k: número de documentos a buscar
      );

      return newMessages;
    });
  };

  return (
    <div className="h-full flex flex-col bg-white">
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
