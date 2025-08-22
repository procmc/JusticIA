import React from 'react';
import { Avatar } from '@heroui/react';

const MessageBubble = ({ message, isUser, isStreaming = false }) => {
  return (
    <div className={`flex gap-4 mb-6 ${isUser ? 'flex-row-reverse' : 'flex-row'} max-w-4xl mx-auto px-4`}>
      <Avatar
        size="md"
        src={isUser ? "/usuario.png" : "/bot.png"}
        name={isUser ? "U" : "J"}
        className={`flex-shrink-0 ${
          isUser 
            ? 'bg-blue-600 text-white' 
            : ''
        }`}
        showFallback
      />
      
      <div className={`flex-1 min-w-0 ${isUser ? 'text-right' : 'text-left'}`}>
        <div className={`inline-block max-w-[calc(100%-10rem)] break-words ${
          isUser 
            ? 'bg-blue-600 text-white rounded-2xl rounded-tr-md px-4 py-3' 
            : 'bg-transparent text-gray-800'
        }`}>
          <div className={`text-sm leading-relaxed whitespace-pre-wrap break-words word-wrap ${
            isUser ? 'text-white' : 'text-gray-800'
          }`}>
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
