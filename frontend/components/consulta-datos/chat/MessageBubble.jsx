import React from 'react';
import { Avatar } from '@heroui/react';

const MessageBubble = ({ message, isUser, isStreaming = false }) => {
  return (
    <div className={`flex gap-4 mb-6 ${isUser ? 'flex-row-reverse' : 'flex-row'} max-w-4xl mx-auto px-4`}>
      <Avatar
        size="sm"
        src={isUser ? "/usuario.png" : null}
        name={isUser ? "U" : "J"}
        className={`flex-shrink-0 ${
          isUser 
            ? 'bg-blue-600 text-white' 
            : 'bg-gradient-to-br from-emerald-500 to-emerald-600 text-white'
        }`}
        showFallback
      />
      
      <div className={`flex-1 min-w-0 ${isUser ? 'text-right' : 'text-left'}`}>
        <div className={`inline-block max-w-full ${
          isUser 
            ? 'bg-blue-600 text-white rounded-2xl rounded-tr-md px-4 py-3' 
            : 'bg-transparent text-gray-800'
        }`}>
          <div className={`text-sm leading-relaxed whitespace-pre-wrap ${
            isUser ? 'text-white' : 'text-gray-800'
          }`}>
            {message.text}
            {isStreaming && (
              <span className="inline-block w-2 h-5 bg-gray-400 ml-1 animate-pulse">|</span>
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
