import React, { useState } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';

const ConsultaChat = () => {
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [streamingMessageIndex, setStreamingMessageIndex] = useState(null);

  const simulateStreamingResponse = (fullText, messageIndex) => {
    let currentText = '';
    let currentIndex = 0;
    
    const addNextCharacter = () => {
      if (currentIndex < fullText.length) {
        currentText += fullText[currentIndex];
        
        setMessages(prev => {
          const newMessages = [...prev];
          newMessages[messageIndex] = {
            ...newMessages[messageIndex],
            text: currentText
          };
          return newMessages;
        });

        currentIndex++;
        
        // Velocidad más lenta y variada para efecto más natural
        let delay = 80; // Velocidad base más lenta
        const char = fullText[currentIndex - 1];
        
        if (char === ' ') {
          delay = 60; // Espacios moderadamente rápidos
        } else if (char === '.' || char === '\n') {
          delay = 400; // Pausa larga en puntos y saltos de línea
        } else if (char === ',') {
          delay = 250; // Pausa media en comas
        } else if (char === '?' || char === '!') {
          delay = 500; // Pausa muy larga en signos
        } else if (char === ':' || char === ';') {
          delay = 300; // Pausa en dos puntos
        }
        
        // Variación aleatoria más amplia para mayor naturalidad
        delay += Math.random() * 40 - 20; // ±20ms de variación
        
        // Asegurar que el delay no sea negativo
        delay = Math.max(delay, 30);
        
        setTimeout(addNextCharacter, delay);
      } else {
        setStreamingMessageIndex(null);
      }
    };

    addNextCharacter();
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
        const fullResponse = `Entiendo tu consulta sobre "${text}". Como asistente jurídico de JusticIA, he analizado tu pregunta y puedo ayudarte con información relevante basada en el marco jurídico costarricense.

Según mi análisis de los expedientes y la jurisprudencia disponible, puedo proporcionarte los siguientes puntos clave:

• Marco jurídico aplicable
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
    <div className="h-full flex flex-col bg-white overflow-y-auto custom-page-scroll">
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
