import React, { useState, useEffect } from 'react';
import { Avatar } from '@heroui/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import TypingIndicator from './TypingIndicator';
import { CopyIcon, CheckIcon } from '../../icons';

const MessageBubble = ({ message, isUser, isStreaming = false }) => {
  const isError = message.isError || false;
  const isWarning = message.isWarning || false;
  
  // Estado para forzar re-renderizado cuando sea necesario
  const [forceRender, setForceRender] = useState(0);
  
  // Estado para el botón de copiar
  const [copied, setCopied] = useState(false);

  // Efecto para manejar renderizado inconsistente - forzar actualización cuando el texto cambia
  useEffect(() => {
    if (!isUser && message.text && message.renderKey) {
      setForceRender(prev => prev + 1);
    }
  }, [message.text, message.renderKey, isUser]);

  // Función para copiar al portapapeles
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000); // Volver al estado normal después de 2 segundos
    } catch (err) {
      console.error('Error al copiar:', err);
    }
  };

  // Componente personalizado para renderizar Markdown con estilos
  const MarkdownRenderer = ({ content, forceKey }) => {
    if (!content) return null;

    // Preprocesar contenido para limpiar tags HTML del LLM
    const preprocessContent = (text) => {
      return text
        // Reemplazar <br> y <br/> y <br /> con saltos de línea Markdown
        .replace(/<br\s*\/?>/gi, '  \n')
        // Reemplazar múltiples <br> consecutivos con doble salto (nuevo párrafo)
        .replace(/(<br\s*\/?>\s*){2,}/gi, '\n\n')
        // Eliminar otros tags HTML comunes que el LLM pueda generar
        .replace(/<\/?strong>/gi, '**')
        .replace(/<\/?b>/gi, '**')
        .replace(/<\/?em>/gi, '*')
        .replace(/<\/?i>/gi, '*')
        // Limpiar cualquier otro tag HTML residual
        .replace(/<[^>]+>/g, '');
    };

    const cleanContent = preprocessContent(content);

    // Componentes personalizados para elementos Markdown
    const components = {
      // Párrafos con justificación
      p: ({ children }) => (
        <p className="mb-4 leading-relaxed text-gray-800 last:mb-0 text-justify">
          {children}
        </p>
      ),
      
      // Encabezados con mejor espaciado
      h1: ({ children }) => (
        <h1 className="text-lg font-bold text-gray-900 mb-3 mt-4 first:mt-0 text-left">
          {children}
        </h1>
      ),
      h2: ({ children }) => (
        <h2 className="text-base font-semibold text-gray-900 mb-2 mt-3 first:mt-0 text-left">
          {children}
        </h2>
      ),
      h3: ({ children }) => (
        <h3 className="text-sm font-semibold text-gray-900 mb-2 mt-3 first:mt-0 text-left">
          {children}
        </h3>
      ),
      
      // Listas con bullets justificadas
      ul: ({ children }) => (
        <ul className="list-disc list-outside mb-4 space-y-2 ml-6">
          {children}
        </ul>
      ),
      ol: ({ children }) => (
        <ol className="list-decimal list-outside mb-4 space-y-2 ml-6">
          {children}
        </ol>
      ),
      li: ({ children }) => (
        <li className="text-gray-800 leading-relaxed text-justify">
          {children}
        </li>
      ),
      
      // Texto en negrita
      strong: ({ children }) => (
        <strong className="font-semibold text-gray-900">
          {children}
        </strong>
      ),
      
      // Texto en cursiva
      em: ({ children }) => (
        <em className="italic text-gray-800">
          {children}
        </em>
      ),
      
      // Código inline
      code: ({ children, className, ...props }) => {
        // Si no tiene className, es código inline
        if (!className) {
          return (
            <code className="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-sm font-mono">
              {children}
            </code>
          );
        }
        // Si tiene className, es un bloque de código
        return (
          <code className={className} {...props}>
            {children}
          </code>
        );
      },
      
      // Bloques de código
      pre: ({ children }) => (
        <pre className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-4 overflow-x-auto">
          {children}
        </pre>
      ),
      
      // Enlaces
      a: ({ href, children }) => (
        <a 
          href={href} 
          className="text-blue-600 hover:text-blue-800 underline"
          target="_blank"
          rel="noopener noreferrer"
        >
          {children}
        </a>
      ),
      
      // Citas/blockquotes
      blockquote: ({ children }) => (
        <blockquote className="border-l-4 border-blue-200 pl-4 italic text-gray-700 mb-4 text-justify">
          {children}
        </blockquote>
      ),
      
      // Líneas horizontales con mejor espaciado
      hr: () => (
        <hr className="border-t-2 border-gray-300 my-6" />
      ),
      
      // Tablas
      table: ({ children }) => (
        <div className="overflow-x-auto mb-4">
          <table className="min-w-full border border-gray-200 rounded-lg">
            {children}
          </table>
        </div>
      ),
      thead: ({ children }) => (
        <thead className="bg-gray-50">
          {children}
        </thead>
      ),
      th: ({ children }) => (
        <th className="border border-gray-200 px-3 py-2 text-left font-semibold text-gray-900">
          {children}
        </th>
      ),
      td: ({ children }) => (
        <td className="border border-gray-200 px-3 py-2 text-gray-800">
          {children}
        </td>
      ),
    };

    return (
      <div className="markdown-content">
        <ReactMarkdown 
          key={`markdown-${forceKey}-${content.length}`} // Key única para forzar re-renderizado
          remarkPlugins={[remarkGfm]}
          components={components}
        >
          {cleanContent}
        </ReactMarkdown>
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
              <MarkdownRenderer 
                content={message.text} 
                forceKey={forceRender}
              />
            )}
            {isStreaming && !isUser && !message.text && (
              <div className="w-full">
                <TypingIndicator compact={true} />
              </div>
            )}
          </div>
        </div>
        
        <div className={`flex items-center gap-2 mt-1 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          <div className={`text-xs text-gray-400`}>
            {message.timestamp && message.timestamp}
          </div>
          
          {/* Botón de copiar - debajo del mensaje */}
          {!isUser && message.text && !isStreaming && (
            <div className="relative group">
              <button
                onClick={handleCopy}
                className="p-1.5 rounded-lg hover:bg-gray-100 transition-all duration-200 focus:outline-none text-gray-400 hover:text-gray-700 hover:scale-110"
                aria-label="Copiar respuesta"
              >
                {copied ? (
                  <CheckIcon size={14} className="text-gray-600" />
                ) : (
                  <CopyIcon size={14} className="text-gray-500" />
                )}
              </button>
              
              {/* Tooltip personalizado */}
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-md opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap shadow-md border border-gray-200">
                {copied ? "¡Copiado!" : "Copiar"}
                <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1 border-4 border-transparent border-t-gray-100"></div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
