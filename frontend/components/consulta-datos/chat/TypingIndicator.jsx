import React from 'react';
import { Avatar } from '@heroui/react';

const TypingIndicator = () => {
  return (
    <div className="flex gap-4 mb-6 max-w-4xl mx-auto px-4">
      <Avatar
        size="sm"
        name="J"
        className="flex-shrink-0 bg-gradient-to-br from-emerald-500 to-emerald-600 text-white"
        showFallback
      />
      
      <div className="flex-1 min-w-0">
        <div className="inline-flex items-center gap-1 text-gray-500">
          <div className="flex gap-1">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TypingIndicator;
