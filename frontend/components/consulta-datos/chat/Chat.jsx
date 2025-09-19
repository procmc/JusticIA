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
    
    // ======= MODO SIN STREAMING PARA PRUEBAS =======
    try {
      const resultado = await consultaService.consultaGeneralNoStreaming(
        text,
        5, // topK
        conversationContext
      );

      if (currentRequestRef.current?.active) {
        setStreamingMessageIndex(null);
        setIsTyping(false);
        currentRequestRef.current = null;
        
        // Forzar un pequeño delay para evitar problemas de renderizado inconsistente
        setTimeout(() => {
          // Actualizar el mensaje del asistente con la respuesta completa
          setMessages(prevMessages => {
            const updatedMessages = [...prevMessages];
            if (updatedMessages[messageIndex]) {
              updatedMessages[messageIndex] = {
                ...updatedMessages[messageIndex],
                text: resultado.respuesta || 'No se recibió respuesta del servidor.',
                timestamp: new Date().toLocaleTimeString('es-ES', {
                  hour: '2-digit',
                  minute: '2-digit'
                }),
                // Agregar una key única para forzar re-renderizado
                renderKey: Date.now()
              };
            }
            return updatedMessages;
          });
        }, 100); // Delay de 100ms para asegurar renderizado correcto
        
        // Guardar la conversación en el contexto
        if (resultado.respuesta?.trim()) {
          addToContext(text, resultado.respuesta.trim());
        }
      }
    } catch (error) {
      console.error('Error en la consulta sin streaming:', error);
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
    }
    // ======= FIN MODO SIN STREAMING =======
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Botón sutil de nuevo chat - solo mostrar si hay contexto */}
      {hasContext && (
        <div className="px-4 py-3 flex justify-end">
          <button
            onClick={() => {
              clearContext();
              setMessages([]); // También limpiar mensajes visuales
            }}
            className="flex items-center gap-2 px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-lg transition-colors duration-200 border border-gray-200 hover:border-gray-300"
            title="Iniciar nueva conversación"
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
