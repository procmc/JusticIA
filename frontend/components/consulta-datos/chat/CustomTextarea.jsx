import React, { useRef, useEffect, useCallback } from 'react';
import { Button, Input, Checkbox } from '@heroui/react';
import { IoSend, IoDocument, IoGlobe, IoStop } from 'react-icons/io5';

const CustomTextarea = ({ 
  value, 
  onChange, 
  onSubmit, 
  onStop,
  placeholder = "Escribe tu mensaje...", 
  disabled = false,
  isLoading = false,
  maxRows = 10,
  // Props para alcance de búsqueda
  searchScope = 'general',
  setSearchScope,
  consultedExpediente = null
}) => {
  const textareaRef = useRef(null);

  // Auto-resize function like multimodal-input
  const adjustHeight = useCallback(() => {
    if (textareaRef.current) {
      // Resetear altura primero para obtener el scrollHeight correcto
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = "20px"; // Altura mínima
      
      // Calcular nueva altura basada en contenido
      const scrollHeight = textareaRef.current.scrollHeight;
      const newHeight = Math.max(20, scrollHeight); // Mínimo 20px
      textareaRef.current.style.height = `${newHeight}px`;
    }
  }, []);

  useEffect(() => {
    if (textareaRef.current) {
      adjustHeight();
    }
  }, [adjustHeight, value]); // Agregar 'value' como dependencia

  const handleInput = (event) => {
    onChange(event);
    adjustHeight();
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (isLoading && onStop) {
        onStop();
      } else if (value.trim() && !disabled) {
        onSubmit();
      }
    }
  };

  const handleSubmit = () => {
    if (isLoading && onStop) {
      onStop();
    } else if (value.trim() && !disabled) {
      onSubmit();
    }
  };

  // Calcular altura dinámica basada en contenido
  const getContainerHeight = () => {
    if (!value.trim()) return '52px'; // Altura fija cuando está vacío (incluye padding)
    
    if (textareaRef.current) {
      // Forzar recálculo del scrollHeight
      textareaRef.current.style.height = "auto";
      const scrollHeight = textareaRef.current.scrollHeight;
      const maxHeight = 20 * maxRows; // Usando lineHeight de 20px
      const calculatedHeight = Math.min(Math.max(scrollHeight, 20) + 32, maxHeight + 32);
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
    <div className="space-y-2">
      {/* Card para el textarea */}
      <div className="flex items-end gap-3">
        <div className="flex-1 bg-white rounded-2xl border border-gray-200 shadow-lg hover:shadow-xl transition-all duration-300 overflow-hidden">
          {/* Efecto de gradiente sutil en el borde superior */}
          <div className="h-1 bg-primary"></div>
          
          {/* Contenedor del textarea con scroll */}
        <div className="relative">
          <div
            className={`p-4 transition-all duration-300 flex items-center ${value.trim() && shouldShowScroll() ? 'overflow-y-auto custom-blue-scroll' : 'overflow-hidden'}`}
            style={{ height: getContainerHeight() }}
          >
            <textarea
              ref={textareaRef}
              placeholder={
                searchScope === 'expediente' && !consultedExpediente 
                  ? "Ingresa número de expediente (ej: 2022-097794-3873-PN)..."
                  : searchScope === 'expediente' && consultedExpediente
                  ? `Pregunta sobre el expediente ${consultedExpediente}...`
                  : "¿En qué puedo ayudarte hoy?..."
              }
              value={value}
              onChange={handleInput}
              rows={1}
              disabled={disabled} // Solo disabled por la prop, no por isLoading
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
          isDisabled={(!value.trim() && !isLoading) || disabled}
          size="lg"
          isIconOnly
          className={`w-12 h-12 rounded-xl transition-all duration-300 ${
            isLoading
              ? 'bg-gradient-to-r from-primario to-azulOscuro hover:from-primario/90 hover:to-azulOscuro/90 text-white shadow-lg hover:shadow-xl hover:scale-105'
              : value.trim() && !disabled
              ? 'bg-gradient-to-r from-primario to-azulOscuro hover:from-primario/90 hover:to-azulOscuro/90 text-white shadow-lg hover:shadow-xl hover:scale-105'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed shadow-sm'
          }`}
        >
          {isLoading ? (
            <IoStop className="w-5 h-5" />
          ) : (
            <IoSend className={`w-5 h-5 transition-transform duration-200 ${
              value.trim() && !disabled ? 'translate-x-0.5' : ''
            }`} />
          )}
        </Button>
      </div>
      </div>

      {/* Barra de alcance debajo del textarea - estilo equilibrado */}
      <div className="px-2 py-2">
        <div className="flex items-center justify-between min-h-[32px]">
          <div className="flex items-center gap-5">
            <Checkbox
              isSelected={searchScope === 'general'}
              onValueChange={(checked) => checked && setSearchScope && setSearchScope('general')}
              size="md"
              classNames={{
                wrapper: "group-data-[selected=true]:border-primario group-data-[selected=true]:bg-primario",
                icon: "text-white",
                label: "text-sm font-medium text-gray-700"
              }}
            >
              <div className="flex items-center gap-2">
                <IoGlobe className="w-4 h-4 text-primario" />
                <span>Búsqueda general</span>
              </div>
            </Checkbox>

            <Checkbox
              isSelected={searchScope === 'expediente'}
              onValueChange={(checked) => checked && setSearchScope && setSearchScope('expediente')}
              size="md"
              classNames={{
                wrapper: "group-data-[selected=true]:border-primario group-data-[selected=true]:bg-primario",
                icon: "text-white",
                label: "text-sm font-medium text-gray-700"
              }}
            >
              <div className="flex items-center gap-2">
                <IoDocument className="w-4 h-4 text-primario" />
                <span>Por expediente específico</span>
                {/* Indicador discreto del expediente consultado */}
                {searchScope === 'expediente' && consultedExpediente && (
                  <span className="ml-2 px-2 py-0.5 text-xs font-medium text-blue-700 bg-blue-100 border border-blue-200 rounded-md whitespace-nowrap">
                    {consultedExpediente}
                  </span>
                )}
              </div>
            </Checkbox>
          </div>
          
          {/* Contador de caracteres en el lado derecho */}
          {value.length > 0 && (
            <span className="text-xs text-gray-500">
              {value.length} caracteres
            </span>
          )}
        </div>


      </div>
    </div>
  );
};

export default CustomTextarea;
