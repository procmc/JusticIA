import React, { useRef, useEffect, useCallback } from 'react';
import { Button } from '@heroui/react';
import { IoSend } from 'react-icons/io5';

const CustomTextarea = ({ 
  value, 
  onChange, 
  onSubmit, 
  placeholder = "Escribe tu mensaje...", 
  disabled = false,
  maxRows = 10 
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

  // Calcular altura dinámica basada en contenido
  const getContainerHeight = () => {
    if (!value.trim()) return '52px'; // Altura fija cuando está vacío (incluye padding)
    
    if (textareaRef.current) {
      const scrollHeight = textareaRef.current.scrollHeight;
      const maxHeight = 20 * maxRows; // Usando lineHeight de 20px
      const calculatedHeight = Math.min(scrollHeight + 32, maxHeight + 32);
      return `${calculatedHeight}px`;
    }
    return '52px';
  };

  // Determinar si debe mostrar scroll
  const shouldShowScroll = () => {
    if (!value.trim()) return false;
    if (textareaRef.current) {
      const scrollHeight = textareaRef.current.scrollHeight;
      const maxHeight = 20 * maxRows; // Usando lineHeight de 20px
      return scrollHeight > maxHeight;
    }
    return false;
  };

  return (
    <div className="flex items-end gap-3">
      {/* Card para el textarea */}
      <div className="flex-1 bg-white rounded-2xl border border-gray-200 shadow-lg hover:shadow-xl transition-all duration-300 overflow-hidden">
        {/* Efecto de gradiente sutil en el borde superior */}
        <div className="h-1 bg-gradient-to-r from-blue-700/60 via-blue-600 via-blue-700 to-blue-700/60"></div>
        
        {/* Contenedor del textarea con scroll */}
        <div className="relative">
          <div
            className={`p-4 transition-all duration-300 flex items-center ${value.trim() && shouldShowScroll() ? 'overflow-y-auto custom-blue-scroll' : 'overflow-hidden'}`}
            style={{ height: getContainerHeight() }}
          >
            <textarea
              ref={textareaRef}
              placeholder="Escribe tu mensaje..."
              value={value}
              onChange={handleInput}
              rows={1}
              disabled={disabled}
              onKeyDown={handleKeyDown}
              className="w-full resize-none border-none bg-transparent text-base text-gray-800 placeholder:text-gray-400 focus:outline-none flex items-center"
              style={{
                height: value.trim() ? (textareaRef.current ? textareaRef.current.style.height : '20px') : '20px',
                lineHeight: '20px',
                minHeight: '20px',
                paddingTop: '0px',
                paddingBottom: '0px',
                display: 'flex',
                alignItems: 'center'
              }}
            />
          </div>
          
          {/* Efecto de desvanecimiento solo cuando hay scroll */}
          {shouldShowScroll() && (
            <>
              <div className="absolute top-0 left-0 right-0 h-6 bg-gradient-to-b from-white to-transparent pointer-events-none z-10"></div>
              <div className="absolute bottom-0 left-0 right-0 h-6 bg-gradient-to-t from-white to-transparent pointer-events-none z-10"></div>
            </>
          )}
        </div>
      </div>

      {/* Botón de envío separado - alineado al fondo */}
      <div className="flex-shrink-0 mb-2">
        <Button
          onPress={handleSubmit}
          isDisabled={!value.trim() || disabled}
          size="lg"
          isIconOnly
          className={`w-12 h-12 rounded-xl transition-all duration-300 ${
            value.trim() && !disabled
              ? 'bg-gradient-to-r from-primario to-azulOscuro hover:from-primario/90 hover:to-azulOscuro/90 text-white shadow-lg hover:shadow-xl hover:scale-105'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed shadow-sm'
          }`}
        >
          <IoSend className={`w-5 h-5 transition-transform duration-200 ${
            value.trim() && !disabled ? 'translate-x-0.5' : ''
          }`} />
        </Button>
      </div>
    </div>
  );
};

export default CustomTextarea;
