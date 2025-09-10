import React from 'react';
import { Avatar } from '@heroui/react';

const MessageBubble = ({ message, isUser, isStreaming = false }) => {
  const isError = message.isError || false;
  const isWarning = message.isWarning || false;
  
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
          <div className={`text-sm leading-relaxed whitespace-pre-wrap break-words word-wrap ${
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
            {message.text}
            {isStreaming && (
              <span 
                className="inline-block w-0.5 h-4 bg-primario ml-1" 
                style={{
                  animation: 'blink 1.2s ease-in-out infinite'
                }}
              >
                |
              </span>
            )}
          </div>
        </div>
        <div className={`text-xs text-gray-400 mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
          {message.timestamp}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
