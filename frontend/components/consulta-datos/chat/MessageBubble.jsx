import React, { useState, useEffect } from 'react';
import { Avatar } from '@heroui/react';
import Image from 'next/image';
import TypingIndicator from './TypingIndicator';
import MarkdownRenderer from './MarkdownRenderer';
import { CopyIcon, CheckIcon } from '../../icons';
import downloadService from '../../../services/downloadService';
import Toast from '@/components/ui/CustomAlert';
import { useAvatar } from '@/contexts/AvatarContext';
import { generateInitialsAvatar } from '@/services/avatarService';
import { useSession } from 'next-auth/react';
import { copyToClipboard, processFilePath } from '../../../utils/chat/markdownUtils';

const MessageBubble = ({ message, isUser, isStreaming = false, showRetry = false, onRetry }) => {
  const { data: session } = useSession();
  const { avatar } = useAvatar();
  const isError = message.isError || false;
  const isWarning = message.isWarning || false;
  
  // Estado para forzar re-renderizado cuando sea necesario
  const [forceRender, setForceRender] = useState(0);
  const [avatarError, setAvatarError] = useState(false);
  
  // Avatar a mostrar (con fallback a iniciales si hay error)
  const displayAvatar = avatarError ? generateInitialsAvatar(session?.user?.name) : avatar;
  
  // Resetear error cuando cambie el avatar
  useEffect(() => {
    setAvatarError(false);
  }, [avatar]);
  
  // Estado para el botón de copiar
  const [copied, setCopied] = useState(false);

  // Función para manejar descarga de archivos con autenticación
  const handleFileDownload = async (e, rutaArchivo) => {
    e.preventDefault();
    e.stopPropagation();
    
    try {
      const fileName = rutaArchivo.split('/').pop() || 'archivo';
      await downloadService.downloadFile(rutaArchivo, fileName);
    } catch (error) {
      Toast.error('Error', error.message || 'Error al descargar el archivo');
    }
  };

  // Interceptar clics en enlaces de descarga
  const handleMessageClick = (e) => {
    const target = e.target;
    
    // Verificar si es un enlace o está dentro de un enlace
    const link = target.closest('a');
    if (!link) return;
    
    const href = link.getAttribute('href');
    if (href && href.startsWith('#download-')) {
      e.preventDefault();
      e.stopPropagation();
      
      // Decodificar la ruta del base64
      try {
        const base64Path = href.replace('#download-', '');
        const rutaArchivo = Buffer.from(base64Path, 'base64').toString('utf-8');
        handleFileDownload(e, rutaArchivo);
      } catch (error) {
        Toast.error('Error', 'No se pudo procesar el enlace de descarga');
      }
    }
  };

  // Efecto para manejar renderizado inconsistente - forzar actualización cuando el texto cambia
  useEffect(() => {
    if (!isUser && message.text && message.renderKey) {
      setForceRender(prev => prev + 1);
    }
  }, [message.text, message.renderKey, isUser]);

  // Función para copiar al portapapeles con formato
  const handleCopy = async () => {
    const success = await copyToClipboard(message.text);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };
  
  return (
    <div className={`flex gap-2 sm:gap-4 ${isUser ? 'flex-row-reverse' : 'flex-row'} w-full max-w-full sm:max-w-4xl mx-auto px-2 sm:px-4`}>
      {displayAvatar?.startsWith('data:') && isUser ? (
        <div key={displayAvatar} className="w-8 h-8 sm:w-10 sm:h-10 rounded-full overflow-hidden flex-shrink-0 bg-white border-2 border-gray-100">
          <Image
            src={displayAvatar}
            alt="User Avatar"
            className="w-full h-full object-cover"
            width={40}
            height={40}
            unoptimized
            onError={() => setAvatarError(true)}
          />
        </div>
      ) : (
        <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full overflow-hidden flex-shrink-0 border-2 border-gray-100">
          <Avatar
            key={displayAvatar}
            size="sm"
            className="w-full h-full"
            src={isUser ? displayAvatar : "/bot.png"}
            name={isUser ? "U" : "J"}
            classNames={{
              base: `flex-shrink-0 border-0 ring-0 outline-0 w-full h-full ${
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
        </div>
      )}
      
      <div className={`flex-1 min-w-0 ${isUser ? 'text-right' : 'text-left'} group`}>
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
              <span className="whitespace-pre-wrap">{message.text}</span>
            ) : (
              <MarkdownRenderer 
                content={message.text} 
                forceKey={forceRender}
                onMessageClick={handleMessageClick}
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
          
          {/* Botón de copiar - para mensajes del bot (siempre visible) */}
          {!isUser && message.text && !isStreaming && (
            <div className="relative group/button">
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
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-md opacity-0 group-hover/button:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap shadow-md border border-gray-200">
                {copied ? "¡Copiado!" : "Copiar"}
                <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1 border-4 border-transparent border-t-gray-100"></div>
              </div>
            </div>
          )}
          
          {/* Botón de copiar - para mensajes del usuario (solo visible en hover) */}
          {isUser && message.text && (
            <div className="relative group/button">
              <button
                onClick={handleCopy}
                className="p-1.5 rounded-lg hover:bg-gray-100 transition-all duration-200 focus:outline-none text-gray-400 hover:text-gray-700 hover:scale-110 opacity-0 group-hover:opacity-100"
                aria-label="Copiar mensaje"
              >
                {copied ? (
                  <CheckIcon size={14} className="text-gray-600" />
                ) : (
                  <CopyIcon size={14} className="text-gray-500" />
                )}
              </button>
              
              {/* Tooltip personalizado */}
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-md opacity-0 group-hover/button:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap shadow-md border border-gray-200">
                {copied ? "¡Copiado!" : "Copiar"}
                <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1 border-4 border-transparent border-t-gray-100"></div>
              </div>
            </div>
          )}
          
          {/* Botón de reintentar - solo para el último mensaje del usuario */}
          {isUser && showRetry && onRetry && (
            <div className="relative group/button">
              <button
                onClick={onRetry}
                className="p-1.5 rounded-lg hover:bg-blue-100 transition-all duration-200 focus:outline-none text-gray-400 hover:text-blue-600 hover:scale-110 opacity-0 group-hover:opacity-100"
                aria-label="Reintentar consulta"
              >
                <svg 
                  className="w-3.5 h-3.5" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" 
                  />
                </svg>
              </button>
              
              {/* Tooltip personalizado */}
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-md opacity-0 group-hover/button:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap shadow-md border border-gray-200">
                Reintentar
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
