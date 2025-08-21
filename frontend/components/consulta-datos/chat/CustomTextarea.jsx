import React, { useRef, useEffect, useCallback } from 'react';
import { Button } from '@heroui/react';
import { IoSend } from 'react-icons/io5';
import { Textarea } from '../../ui/Textarea';

const CustomTextarea = ({ 
  value, 
  onChange, 
  onSubmit, 
  placeholder = "Send a message...", 
  disabled = false,
  maxRows = 6 
}) => {
  const textareaRef = useRef(null);

  // Auto-resize function like multimodal-input
  const adjustHeight = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, []);

  useEffect(() => {
    if (textareaRef.current) {
      adjustHeight();
    }
  }, [adjustHeight]);

  const handleInput = (event) => {
    onChange(event);
    adjustHeight();
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (value.trim() && !disabled) {
        onSubmit();
      }
    }
  };

  const handleSubmit = () => {
    if (value.trim() && !disabled) {
      onSubmit();
    }
  };

  return (
    <div className="relative">
      <Textarea
        ref={textareaRef}
        placeholder={placeholder}
        value={value}
        onChange={handleInput}
        className="min-h-[50px] overflow-y-auto resize-none rounded-3xl text-base bg-white hover:border-gray-300 focus:border-gray-400 pr-12"
        rows={1}
        disabled={disabled}
        onKeyDown={handleKeyDown}
        style={{
          maxHeight: `${24 * maxRows}px`
        }}
      />
      
      <Button
        onPress={handleSubmit}
        isDisabled={!value.trim() || disabled}
        size="sm"
        isIconOnly
        className={`absolute bottom-2 right-2 min-w-8 h-8 rounded-full transition-all duration-200 ${
          value.trim() && !disabled
            ? 'bg-gray-900 hover:bg-gray-800 text-white'
            : 'bg-gray-100 text-gray-400 cursor-not-allowed'
        }`}
      >
        <IoSend className="w-4 h-4" />
      </Button>
    </div>
  );
};

export default CustomTextarea;
