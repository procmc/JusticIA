import React, { useState } from 'react';
import { Textarea, Button } from '@heroui/react';
import { IoSend } from 'react-icons/io5';

const ChatInput = ({ onSendMessage, isDisabled = false }) => {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = () => {
    if (inputValue.trim() && !isDisabled) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-gray-100 bg-white/80 backdrop-blur-sm">
      <div className="max-w-4xl mx-auto px-4 py-4">
        <div className="relative">
          <Textarea
            placeholder="Envía un mensaje a JusticIA..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            minRows={1}
            maxRows={6}
            disabled={isDisabled}
            variant="flat"
            className="pr-12"
            classNames={{
              input: "resize-none",
              inputWrapper: "bg-gray-50 border border-gray-200 hover:border-gray-300 focus-within:border-blue-500 rounded-xl shadow-sm"
            }}
          />
          <Button
            onClick={handleSubmit}
            isDisabled={!inputValue.trim() || isDisabled}
            color="primary"
            size="sm"
            isIconOnly
            className="absolute right-2 bottom-2 min-w-8 h-8 bg-blue-600 hover:bg-blue-700 disabled:opacity-30"
          >
            <IoSend className="w-4 h-4" />
          </Button>
        </div>
        <div className="flex items-center justify-between mt-2 px-2">
          <p className="text-xs text-gray-400">
            JusticIA puede cometer errores. Considera verificar información importante.
          </p>
          <p className="text-xs text-gray-400">
            {inputValue.length > 0 && `${inputValue.length} caracteres`}
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChatInput;
