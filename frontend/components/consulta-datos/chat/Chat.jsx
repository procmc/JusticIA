import React, { useState } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';

const ConsultaChat = () => {
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [streamingMessageIndex, setStreamingMessageIndex] = useState(null);

  const simulateStreamingResponse = (fullText, messageIndex) => {
    let currentText = '';
    const words = fullText.split(' ');
    
    const streamWords = (index) => {
      if (index < words.length) {
        currentText += (index > 0 ? ' ' : '') + words[index];
        
        setMessages(prev => {
          const newMessages = [...prev];
          newMessages[messageIndex] = {
            ...newMessages[messageIndex],
            text: currentText
          };
          return newMessages;
        });

        setTimeout(() => streamWords(index + 1), 50 + Math.random() * 100);
      } else {
        setStreamingMessageIndex(null);
      }
    };

    streamWords(0);
  };

  const handleSendMessage = async (text) => {
    // Crear mensaje del usuario
    const userMessage = {
      text,
      isUser: true,
      timestamp: new Date().toLocaleTimeString('es-ES', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    };

    // Agregar mensaje del usuario
    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);

    // Simular delay de respuesta
    setTimeout(() => {
      setIsTyping(false);
      
      // Crear mensaje del asistente vacío
      const assistantMessage = {
        text: '',
        isUser: false,
        timestamp: new Date().toLocaleTimeString('es-ES', { 
          hour: '2-digit', 
          minute: '2-digit' 
        })
      };

      // Agregar mensaje vacío y comenzar streaming
      setMessages(prev => {
        const newMessages = [...prev, assistantMessage];
        const messageIndex = newMessages.length - 1;
        setStreamingMessageIndex(messageIndex);
        
        // Texto completo de respuesta
        const fullResponse = `Entiendo tu consulta sobre "${text}". Como asistente legal de JusticIA, he analizado tu pregunta y puedo ayudarte con información relevante basada en el marco jurídico colombiano.

Según mi análisis de los expedientes y la jurisprudencia disponible, puedo proporcionarte los siguientes puntos clave:

• Marco legal aplicable
• Precedentes jurisprudenciales relevantes  
• Procedimientos recomendados
• Posibles alternativas de solución

¿Te gustaría que profundice en algún aspecto específico de tu consulta?`;

        // Comenzar streaming después de un breve delay
        setTimeout(() => {
          simulateStreamingResponse(fullResponse, messageIndex);
        }, 500);
        
        return newMessages;
      });
    }, 1000);
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
          isDisabled={isTyping || streamingMessageIndex !== null}
        />
      </div>
    </div>
  );
};

export default ConsultaChat;
