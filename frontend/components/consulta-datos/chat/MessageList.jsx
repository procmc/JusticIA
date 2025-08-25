import React, { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';
import { ScrollShadow } from '@heroui/react';

const MessageList = ({ messages, isTyping, streamingMessageIndex }) => {
  const messagesEndRef = useRef(null);
  const prevMessagesLengthRef = useRef(0);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    // Solo hacer scroll cuando se agregue un nuevo mensaje, no durante el streaming
    if (messages.length > prevMessagesLengthRef.current) {
      prevMessagesLengthRef.current = messages.length;
      scrollToBottom();
    }
  }, [messages.length]); // Solo observa el cambio en la cantidad de mensajes

  useEffect(() => {
    // Scroll cuando cambie el estado de typing
    if (isTyping) {
      scrollToBottom();
    }
  }, [isTyping]);

  return (
    <ScrollShadow hideScrollBar className="flex-1 h-full" size={60}>
      <div className="mx-2 sm:mx-12 md:mr-28">
        <div className="min-h-full py-8 sm:py-20">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-full sm:max-w-lg mx-auto px-2 sm:px-4">
                {/* Imagen del bot de inicio */}
                <div className="mb-6 flex justify-center">
                  <img
                    src="/botInicio.png"
                    alt="JusticIA Bot"
                    className="w-32 h-32 sm:w-48 sm:h-48 object-contain"
                  />
                </div>

                {/* Título */}
                <h1 className="text-2xl sm:text-3xl font-bold text-tituloSeccion mb-3">
                  ¡Hola! Soy JusticBot
                </h1>

                {/* Descripción simple */}
                <p className="text-gray-600 text-base sm:text-lg leading-relaxed mb-6">
                  Tu asistente jurídico inteligente especializado en el marco jurídico costarricense.
                </p>

                {/* Call to action simple */}
                <div className="bg-gray-50 p-4 rounded-xl border">
                  <p className="text-gray-700 text-sm">
                    💬 Escribe tu consulta jurídica para comenzar
                  </p>
                </div>

                {/* Mensaje de advertencia discreto */}
                <p className="text-xs text-gray-400 mt-4 italic">
                  JusticBot puede cometer errores. Considera verificar información importante.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-0">
              {messages.map((message, index) => (
                <MessageBubble
                  key={index}
                  message={message}
                  isUser={message.isUser}
                  isStreaming={index === streamingMessageIndex}
                />
              ))}
              {isTyping && <TypingIndicator />}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
    </ScrollShadow>
  );
};

export default MessageList;
