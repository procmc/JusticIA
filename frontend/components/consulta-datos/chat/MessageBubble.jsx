import React from 'react';
import { Avatar } from '@heroui/react';

const MessageBubble = ({ message, isUser, isStreaming = false }) => {
  const isError = message.isError || false;
  const isWarning = message.isWarning || false;

  // Función para formatear el texto del mensaje
  const formatText = (text) => {
    if (!text) return '';
    
    return text
      // Agregar espacios después de puntos seguidos de letras mayúsculas
      .replace(/\.([A-Z])/g, '. $1')
      // Agregar espacios después de comas seguidas de letras mayúsculas
      .replace(/,([A-Z])/g, ', $1')
      // Agregar espacios después de dos puntos seguidos de letras mayúsculas
      .replace(/:([A-Z])/g, ': $1')
      // Separar cédulas mal formateadas (ej: cédula1-0555-0099 -> cédula 1-0555-0099)
      .replace(/([a-záéíóúñ])(\d+-\d+-\d+)/gi, '$1 $2')
      // Separar expedientes mal formateados (ej: expediente2025-CR-000567 -> expediente 2025-CR-000567)
      .replace(/([a-záéíóúñ])(\d{4}-[A-Z]{2}-\d+)/gi, '$1 $2')
      // Separar números de expediente mal formateados
      .replace(/([a-záéíóúñ])(\d{4}-[A-Z]{2,3}-\d+)/gi, '$1 $2')
      // Agregar espacios después de números seguidos de letras (pero no en códigos)
      .replace(/(\d)([A-Za-záéíóúñ])/g, (match, num, letter, offset, string) => {
        // No separar si es parte de un código como "2025-CR" o cédula
        const before = string.substring(Math.max(0, offset - 10), offset);
        if (before.includes('-') || before.toLowerCase().includes('cédula') || before.toLowerCase().includes('expediente')) {
          return match;
        }
        return `${num} ${letter}`;
      })
      // Agregar espacios antes de números después de letras (excepto en códigos)
      .replace(/([A-Za-záéíóúñ])(\d)/g, (match, letter, num, offset, string) => {
        // No separar si es parte de un código
        const after = string.substring(offset + match.length, offset + match.length + 10);
        if (after.includes('-') || match.toLowerCase().includes('artículo') || match.toLowerCase().includes('ley')) {
          return match;
        }
        return `${letter} ${num}`;
      })
      // Agregar espacios después de paréntesis de cierre seguidos de letras mayúsculas
      .replace(/\)([A-Z])/g, ') $1')
      // Separar múltiples espacios en uno solo
      .replace(/\s+/g, ' ')
      // Limpiar espacios al inicio y final
      .trim();
  };

  // Función para renderizar texto con markdown y estructura mejorada
  const renderFormattedText = (text) => {
    if (!text) return '';
    
    const formattedText = formatText(text);
    
    // Dividir por líneas de separación (---)
    const sections = formattedText.split(/\n*---+\n*/);
    
    return (
      <div className="space-y-4">
        {sections.map((section, sectionIndex) => {
          if (!section.trim()) return null;
          
          // Dividir en párrafos dentro de cada sección
          const paragraphs = section
            .split(/\n\n+/)
            .map(p => p.trim())
            .filter(p => p.length > 0);
          
          return (
            <div key={sectionIndex} className="space-y-3">
              {sectionIndex > 0 && (
                <div className="border-t border-gray-200 pt-4"></div>
              )}
              {paragraphs.map((paragraph, paragraphIndex) => {
                // Procesar markdown simple
                const processedParagraph = paragraph
                  // Convertir **texto** a <strong>texto</strong>
                  .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                  // Convertir saltos de línea simples a <br>
                  .replace(/\n/g, '<br>');
                
                // Identificar si es la fuente (última línea)
                const isFuente = paragraph.toLowerCase().startsWith('fuente:');
                
                return (
                  <div 
                    key={paragraphIndex}
                    className={`leading-relaxed text-justify ${
                      isFuente 
                        ? 'text-xs text-gray-500 italic mt-6 pt-2 border-t border-gray-200' 
                        : 'text-sm'
                    }`}
                    dangerouslySetInnerHTML={{ __html: processedParagraph }}
                  />
                );
              })}
            </div>
          );
        })}
      </div>
    );
  };
  
  return (
    <div className={`flex gap-2 sm:gap-4 mb-6 ${isUser ? 'flex-row-reverse' : 'flex-row'} w-full max-w-full sm:max-w-4xl mx-auto px-2 sm:px-4`}>
      <Avatar
        size="sm"
        className="sm:w-10 sm:h-10"
        src={isUser ? "/usuario.png" : "/bot.png"}
        name={isUser ? "U" : "J"}
        classNames={{
          base: `flex-shrink-0 border-0 ring-0 outline-0 ${
            isUser 
              ? 'bg-white text-white' 
              : isError 
                ? 'bg-red-100 text-red-600' 
                : isWarning
                  ? 'bg-yellow-100 text-yellow-600'
                  : 'bg-blue-900 text-white'
          }`
        }}
        showFallback
      />
      
      <div className={`flex-1 min-w-0 ${isUser ? 'text-right' : 'text-left'}`}>
        <div className={`inline-block max-w-[calc(100%-5rem)] sm:max-w-[calc(100%-10rem)] break-words ${
          isUser 
            ? 'bg-gray-100 text-gray-800 rounded-2xl rounded-tr-md px-4 py-3 text-left' 
            : isError
              ? 'bg-red-50 border border-red-200 text-red-800 rounded-2xl rounded-tl-md px-4 py-3'
              : isWarning
                ? 'bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-2xl rounded-tl-md px-4 py-3'
                : 'bg-transparent text-gray-800'
        }`}>
          <div className={`text-sm leading-relaxed break-words word-wrap ${
            isUser 
              ? 'text-gray-800' 
              : isError 
                ? 'text-red-800' 
                : isWarning
                  ? 'text-yellow-800'
                  : 'text-gray-800'
          }`}>
            {isError && (
              <span className="text-red-600 mr-2">⚠️</span>
            )}
            {isWarning && (
              <span className="text-yellow-600 mr-2">ℹ️</span>
            )}
            {isUser ? (
              <span>{message.text}</span>
            ) : (
              renderFormattedText(message.text)
            )}
            {isStreaming && !isUser && !message.text && (
              <div className="inline-flex items-center space-x-1 align-baseline">
                <div className="flex space-x-1 items-center">
                  <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                  <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                  <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                </div>
                <span className="text-gray-500 text-sm ml-2">Escribiendo...</span>
              </div>
            )}
          </div>
        </div>
        <div className={`text-xs text-gray-400 mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
          {message.timestamp && message.timestamp}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
