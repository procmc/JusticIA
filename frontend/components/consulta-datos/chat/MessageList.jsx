import React, { useEffect, useRef } from 'react';
import Image from 'next/image';
import MessageBubble from './MessageBubble';
import { ScrollShadow } from '@heroui/react';

const MessageList = ({ messages, streamingMessageIndex }) => {
  const messagesEndRef = useRef(null);
  const prevMessagesLengthRef = useRef(0);
  const lastMessageContentRef = useRef('');

  const scrollToBottom = (behavior = "smooth") => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  // Auto-scroll cuando se agregan nuevos mensajes
  useEffect(() => {
    if (messages.length > prevMessagesLengthRef.current) {
      prevMessagesLengthRef.current = messages.length;
      scrollToBottom();
    }
  }, [messages.length]);

  // Auto-scroll durante el streaming del mensaje
  useEffect(() => {
    if (streamingMessageIndex !== null && streamingMessageIndex >= 0) {
      const streamingMessage = messages[streamingMessageIndex];
      if (streamingMessage && !streamingMessage.isUser) {
        // Solo hacer scroll si el contenido del mensaje ha cambiado
        if (streamingMessage.text !== lastMessageContentRef.current) {
          lastMessageContentRef.current = streamingMessage.text;
          
          // Usar un pequeño delay para asegurar que el DOM se actualice
          setTimeout(() => {
            scrollToBottom("auto");
          }, 10);
        }
      }
    }
  }, [messages, streamingMessageIndex]);

  return (
    <ScrollShadow 
      hideScrollBar 
      className="flex-1 h-full" 
      size={60}
    >
      <div className="mx-2 sm:mx-12 md:mr-28">
        <div className="min-h-full py-8 sm:py-20">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-full sm:max-w-lg mx-auto px-2 sm:px-4">
                {/* Imagen del bot de inicio */}
                <div className="mb-6 flex justify-center">
                  <Image
                    src="/botInicio.png"
                    alt="JusticIA Bot"
                    width={192}
                    height={192}
                    className="w-32 h-32 sm:w-48 sm:h-48 object-contain"
                    priority
                  />
                </div>

                {/* Título */}
                <h1 className="text-2xl sm:text-3xl font-bold text-primary mb-3">
                  ¡Hola! Soy JusticBot
                </h1>

                {/* Descripción simple */}
                <p className="text-gray-600 text-base sm:text-lg leading-relaxed mb-4">
                  Tu asistente inteligente especializado en el marco jurídico costarricense.
                </p>

                {/* Capacidades */}
                <p className="text-gray-500 text-sm sm:text-base leading-relaxed mb-6">
                  Puedo ayudarte a generar resúmenes de documentos legales y crear borradores para tus casos.
                </p>

                {/* Mensaje de advertencia discreto */}
                <p className="text-xs text-gray-400 mt-4 italic">
                  JusticBot puede cometer errores. Considera verificar información importante.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message, index) => (
                <MessageBubble
                  key={`message-${index}-${message.renderKey || message.timestamp || index}`}
                  message={message}
                  isUser={message.isUser}
                  isStreaming={index === streamingMessageIndex}
                />
              ))}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
    </ScrollShadow>
  );
};

export default MessageList;
