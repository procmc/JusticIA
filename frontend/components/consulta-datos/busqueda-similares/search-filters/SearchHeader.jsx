import React from 'react';
import { Card, CardBody, Tab, Tabs, Button, Chip, Input, CardHeader, CardFooter } from '@heroui/react';
import { IoSparkles, IoText, IoDocument, IoSearch } from 'react-icons/io5';
import { FiAlertCircle, FiFolder } from 'react-icons/fi';
import { PiBroomLight } from 'react-icons/pi';
import { Textarea } from '@/components/ui/Textarea';
import SearchInstructions from './SearchInstructions';

const SearchHeader = ({
  searchMode,
  setSearchMode,
  searchText,
  setSearchText,
  expedientNumber,
  setExpedientNumber,
  onSearch,
  isSearching,
  onClearResults
}) => {

  // Validación: verificar si hay contenido para buscar
  const canSearch = () => {
    if (searchMode === 'description') {
      return searchText.trim().length > 0;
    } else if (searchMode === 'expedient') {
      return expedientNumber.trim().length > 0;
    }
    return false;
  };

  const isButtonDisabled = !canSearch() || isSearching;

  // Función para limpiar los inputs y resultados
  const clearInputs = () => {
    setSearchText('');
    setExpedientNumber('');
    // Limpiar también los resultados de búsqueda si existe la función
    if (onClearResults) {
      onClearResults();
    }
  };

  // Verificar si hay contenido para limpiar
  const hasContent = () => {
    return searchText.trim().length > 0 || expedientNumber.trim().length > 0;
  };

  // Manejar tecla Enter para enviar búsqueda
  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey && canSearch() && !isSearching) {
      event.preventDefault();
      onSearch();
    }
  };

  return (
    <div className="relative">
      {/* Gradiente de fondo sutil */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary-50/30 via-white to-secondary-50/20 rounded-2xl -z-10"></div>

      <Card className="mb-6 border border-gray-200 shadow-lg bg-white/80 backdrop-blur-sm">
        <CardBody className="p-6">
          {/* Layout responsive - tabs izquierda, acciones derecha */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-3">
            {/* Tabs compactos - izquierda */}
            <div className="w-full sm:w-auto">
              <Tabs
                selectedKey={searchMode}
                onSelectionChange={setSearchMode}
                color="primary"
                variant="solid"
                size="md"
                classNames={{
                  tabList: "grid grid-cols-2 gap-1 p-0.5 bg-gray-100 rounded-lg w-full sm:w-48",
                  cursor: "w-full rounded-md shadow-sm",
                  tab: "w-full h-9 rounded-md",
                  tabContent: "group-data-[selected=true]:text-white text-gray-600 font-medium text-xs"
                }}
              >
                <Tab
                  key="description"
                  title={
                    <div className="flex items-center justify-center space-x-1">
                      <IoText className="w-3 h-3" />
                      <span>Descripción</span>
                    </div>
                  }
                />
                <Tab
                  key="expedient"
                  title={
                    <div className="flex items-center justify-center space-x-1">
                      <IoDocument className="w-3 h-3" />
                      <span>Expediente</span>
                    </div>
                  }
                />
              </Tabs>
            </div>

            {/* Botones de acción - derecha */}
            <div className="flex gap-2 w-full sm:w-auto sm:flex-shrink-0">
              <Button
                onPress={onSearch}
                color="primary"
                size="md"
                startContent={<IoSearch className="w-4 h-4" />}
                isLoading={isSearching}
                isDisabled={isButtonDisabled}
                className={`flex-1 sm:flex-none px-4 font-medium shadow-lg hover:shadow-xl transform transition-all duration-200 text-sm ${isButtonDisabled
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 hover:scale-105'
                  }`}
                radius="md"
                spinner={
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                }
              >
                {isSearching ? 'Analizando...' : 'Buscar Casos'}
              </Button>

              <Button
                onPress={clearInputs}
                color="default"
                variant="flat"
                size="sm"
                startContent={<PiBroomLight className="w-4 h-4" />}
                isDisabled={!hasContent() || isSearching}
                className="px-4 font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-100 transition-all duration-200 text-sm h-10.5"
                radius="lg"
              >
              </Button>
            </div>
          </div>

          {/* Contenido de los tabs */}
          <div className="mt-2">
            {searchMode === 'description' && (
              <div className="space-y-2">
                <div className="relative mb-4">
                  <label className="block text-sm font-medium text-primary pb-1.5">
                    Descripción del caso<span className="text-danger">*</span>
                  </label>
                  <Textarea
                    placeholder="Describe tu caso legal... Ej: 'Despido injustificado de trabajador...'"
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    rows={6}
                    className="w-full resize-none text-gray-700 text-sm custom-scrollbar"
                  />
                </div>

                {/* Contador y ejemplos alineados */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  {/* Ejemplos */}
                  <div className="flex flex-wrap gap-1 items-center">
                    <span className="text-xs text-gray-500">Ejemplos:</span>
                    {[
                      "Despido laboral",
                      "Accidente tránsito",
                      "Divorcio",
                      "Resp. civil"
                    ].map((suggestion) => (
                      <Chip
                        key={suggestion}
                        size="sm"
                        variant="flat"
                        color="primary"
                        className="cursor-pointer hover:bg-primary-100 transition-colors text-xs px-2 py-0"
                        onClick={() => setSearchText(suggestion)}
                      >
                        {suggestion}
                      </Chip>
                    ))}
                  </div>

                  {/* Contador */}
                  <div className="text-xs text-gray-400 bg-gray-50 px-2 py-1 rounded flex-shrink-0">
                    {searchText.length}/2000
                  </div>
                </div>
              </div>
            )}

            {searchMode === 'expedient' && (
              <div className="space-y-3">

                <div className="w-full sm:max-w-sm">
                  <Input
                    label="Número de expediente"
                    labelPlacement='outside'
                    placeholder="98-003287-0166-LA"
                    value={expedientNumber}
                    onChange={(e) => setExpedientNumber(e.target.value)}
                    onKeyDown={handleKeyDown}
                    variant="bordered"
                    color='primary'
                    size="md"
                    isRequired
                    startContent={
                      <IoDocument className="w-4 h-4 text-gray-400" />
                    }
                    className="w-full"
                  />
                </div>
                
                {/* Instrucción simple y elegante - Responsive */}
                <div className="mb-10">
                  <div className="bg-primary-50 border-l-4 border-primary-400 p-3 sm:p-4">
                    <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-0">
                      <div className="flex items-center">
                        <FiAlertCircle className="w-4 h-4 text-primary-600 mr-2 flex-shrink-0" />
                        <span className="text-sm text-gray-700">Formato requerido:</span>
                      </div>
                      <div className="flex flex-col sm:flex-row sm:items-center sm:ml-1 gap-1 sm:gap-2">
                        <code className="px-2 py-1 bg-white rounded text-primary-600 font-mono text-xs border inline-block">
                          AA-NNNNNN-OOOO-MM
                        </code>
                        <span className="text-xs text-gray-600 sm:text-sm">
                          (Año-Consecutivo-Oficina-Materia)
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
          <SearchInstructions />
        </CardBody>
      </Card>
    </div>
  );
};

export default SearchHeader;
