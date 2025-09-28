import React, { useState } from 'react';
import CustomTextarea from './CustomTextarea';

const ChatInput = ({ 
  onSendMessage, 
  onStopGeneration,
  isDisabled = false,
  isLoading = false,
  searchScope = 'general',
  setSearchScope,
  consultedExpediente = null
}) => {
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
      <div className="w-full max-w-full sm:max-w-4xl mx-auto px-2 sm:px-4 py-1">
        <CustomTextarea
          value={inputValue}
          onChange={handleChange}
          onSubmit={handleSubmit}
          onStop={onStopGeneration}
          placeholder="Send a message..."
          disabled={isDisabled}
          isLoading={isLoading}
          maxRows={6}
          searchScope={searchScope}
          setSearchScope={setSearchScope}
          consultedExpediente={consultedExpediente}
        />
      </div>
    </div>
  );
};

export default ChatInput;