import React, { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';

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
    <div className="flex-1 overflow-y-auto">
      <div className="min-h-full py-8">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md mx-auto px-4">
              <div className="text-6xl mb-6 opacity-20">⚖️</div>
              <h3 className="text-2xl font-semibold text-gray-700 mb-3">
                JusticIA
              </h3>
              <p className="text-gray-500 text-lg leading-relaxed">
                Tu asistente legal inteligente. Pregúntame sobre cualquier tema legal o consulta específica sobre expedientes.
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
  );
};

export default MessageList;
