import React, { useState } from 'react';
import CustomTextarea from './CustomTextarea';

const ChatInput = ({ onSendMessage, isDisabled = false }) => {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = () => {
    if (inputValue.trim() && !isDisabled) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  const handleChange = (e) => {
    setInputValue(e.target.value);
  };

  return (
    <div className="bg-white/80 backdrop-blur-sm border-t border-gray-100">
      <div className="max-w-4xl mx-auto px-4 py-4">
        <CustomTextarea
          value={inputValue}
          onChange={handleChange}
          onSubmit={handleSubmit}
          placeholder="Send a message..."
          disabled={isDisabled}
          maxRows={6}
        />
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