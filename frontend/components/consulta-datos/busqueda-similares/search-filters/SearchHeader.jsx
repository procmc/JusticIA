import React from 'react';
import { Card, CardBody, Tab, Tabs, Button, Chip, Input } from '@heroui/react';
import { IoSparkles, IoText, IoDocument, IoSearch } from 'react-icons/io5';
import { PiBroomLight } from 'react-icons/pi';
import { Textarea } from '@/components/ui/Textarea';

const SearchHeader = ({
  searchMode,
  setSearchMode,
  searchText,
  setSearchText,
  expedientNumber,
  setExpedientNumber,
  onSearch,
  isSearching
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

  // Función para limpiar los inputs
  const clearInputs = () => {
    setSearchText('');
    setExpedientNumber('');
  };

  // Verificar si hay contenido para limpiar
  const hasContent = () => {
    return searchText.trim().length > 0 || expedientNumber.trim().length > 0;
  };

  return (
    <div className="relative">
      {/* Gradiente de fondo sutil */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary-50/30 via-white to-secondary-50/20 rounded-2xl -z-10"></div>

      <Card className="mb-6 border border-gray-200 shadow-lg bg-white/80 backdrop-blur-sm">
        <CardBody className="p-10">
          {/* Header con título elegante */}
          <div className="flex items-center gap-2 mb-8">
            <div className="p-2 bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg shadow-lg">
              <IoSparkles className="w-4 h-4 text-white" />
            </div>
            <div >
              <h2 className="text-lg font-bold bg-gradient-to-r from-primary-600 to-primary-800 bg-clip-text text-transparent">
                Búsqueda Inteligente
              </h2>
              <p className="text-gray-500 text-xs">
                Encuentra casos similares usando IA
              </p>
            </div>
          </div>

          {/* Layout responsive - vertical en móvil, horizontal en desktop */}
          <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-3">
            {/* Tabs compactos */}
            <div className="w-full sm:w-auto">
              <Tabs
                selectedKey={searchMode}
                onSelectionChange={setSearchMode}
                color="primary"
                variant="solid"
                size="sm"
                classNames={{
                  tabList: "grid grid-cols-2 gap-1 p-0.5 bg-gray-100 rounded-lg w-full sm:w-48",
                  cursor: "w-full rounded-md shadow-sm",
                  tab: "w-full h-7 rounded-md",
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

            {/* Botones de acción */}
            <div className="flex gap-2 w-full sm:w-auto">
              <Button
                onPress={onSearch}
                color="primary"
                size="sm"
                startContent={<IoSearch className="w-3 h-3" />}
                isLoading={isSearching}
                isDisabled={isButtonDisabled}
                className={`flex-1 sm:flex-none px-4 font-semibold shadow-lg hover:shadow-xl transform transition-all duration-200 text-sm ${isButtonDisabled
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 hover:scale-105'
                  }`}
                radius="full"
                spinner={
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                }
              >
                {isSearching ? 'Analizando...' : 'Buscar Casos'}
              </Button>

              <Button
                onPress={clearInputs}
                color="default"
                variant="flat"
                size="sm"
                startContent={<PiBroomLight className="w-3 h-3" />}
                isDisabled={!hasContent() || isSearching}
                className="px-3 font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-100 transition-all duration-200 text-sm"
                radius="full"
              >
                Limpiar
              </Button>
            </div>
          </div>

          {/* Contenido de los tabs */}
          <div className="mt-2">
            {searchMode === 'description' && (
              <div className="space-y-2">
                <div className="relative mb-4">
                  <Textarea
                    placeholder="Describe tu caso legal... Ej: 'Despido injustificado de trabajador...'"
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
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
                    placeholder="2024-001-01-CI"
                    value={expedientNumber}
                    onChange={(e) => setExpedientNumber(e.target.value)}
                    variant="bordered"
                    color='primary'
                    size="md"
                    startContent={
                      <IoDocument className="w-4 h-4 text-gray-400" />
                    }
                    className="w-full"
                  />
                  <p className="text-gray-500 text-xs mt-3">
                    Formato: AAAA-NNN-NN-XX
                  </p>
                </div>
              </div>
            )}
          </div>
        </CardBody>
      </Card>
    </div>
  );
};

export default SearchHeader;
