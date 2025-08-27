import React from 'react';
import { Button, Card, CardBody, Tabs, Tab } from '@heroui/react';
import { 
  IoSparkles, 
  IoText, 
  IoDocument, 
  IoSearch,
  IoFunnel
} from 'react-icons/io5';
import { PiBroomLight } from 'react-icons/pi';

const HeaderBusquedaSimilares = ({ 
  searchMode, 
  setSearchMode,
  onClearInputs,
  hasContent = false,
  hasSearched = false,
  searchResults = [],
  similarityThreshold = [75],
  isSearching = false
}) => {
  
  // Calcular estadísticas de búsqueda
  const totalResults = searchResults.length;
  const filteredResults = searchResults.filter(result => result.similarity >= similarityThreshold[0]);
  const highSimilarity = searchResults.filter(result => result.similarity >= 90).length;
  const mediumSimilarity = searchResults.filter(result => result.similarity >= 70 && result.similarity < 90).length;
  const lowSimilarity = searchResults.filter(result => result.similarity < 70).length;

  return (
    <Card className="bg-primary text-white shadow-lg border-none">
      <CardBody className="p-4 sm:p-6 lg:p-8">
        <div className="space-y-6">
          {/* Fila superior: Título y controles */}
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 lg:gap-6">
            {/* Título y descripción */}
            <div className="flex items-center gap-3 sm:gap-4 flex-1">
              <div className="p-2 sm:p-3 bg-white/15 rounded-xl border border-white/20 flex-shrink-0">
                <IoSparkles className="text-2xl sm:text-3xl lg:text-4xl text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-white mb-1 sm:mb-2 truncate">
                  Búsqueda de Casos Similares
                </h1>
                <p className="text-white/80 text-sm sm:text-base">
                  Encuentra casos relacionados usando inteligencia artificial
                </p>
              </div>
            </div>

            {/* Controles: Modo de búsqueda y botón limpiar */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 sm:gap-4">
              {/* Selector de modo de búsqueda */}
              <Tabs
                selectedKey={searchMode}
                onSelectionChange={setSearchMode}
                variant="underlined"
                classNames={{
                  tabList: "bg-white/10 p-1 rounded-lg border border-white/20",
                  tab: "text-white/70 data-[selected=true]:text-white px-3 sm:px-4 py-2",
                  cursor: "bg-white/20 rounded-md",
                  panel: "p-0"
                }}
              >
                <Tab
                  key="description"
                  title={
                    <div className="flex items-center gap-2">
                      <IoText className="text-base sm:text-lg" />
                      <span className="hidden sm:inline">Por Descripción</span>
                      <span className="sm:hidden">Descripción</span>
                    </div>
                  }
                />
                <Tab
                  key="expedient"
                  title={
                    <div className="flex items-center gap-2">
                      <IoDocument className="text-base sm:text-lg" />
                      <span className="hidden sm:inline">Por Expediente</span>
                      <span className="sm:hidden">Expediente</span>
                    </div>
                  }
                />
              </Tabs>

              {/* Botón limpiar */}
              {hasContent && (
                <Button
                  color="secondary"
                  size="lg"
                  startContent={<PiBroomLight className="text-lg sm:text-xl" />}
                  className="bg-white/20 text-white font-bold hover:bg-white/30 border border-white/30 px-3 sm:px-4 lg:px-6 py-2 sm:py-3 rounded-xl text-sm sm:text-base whitespace-nowrap"
                  onPress={onClearInputs}
                >
                  <span className="hidden sm:inline">Limpiar</span>
                  <span className="sm:hidden">Limpiar</span>
                </Button>
              )}
            </div>
          </div>

          {/* Estadísticas de resultados - Solo mostrar si hay búsqueda realizada */}
          {hasSearched && !isSearching && (
            <div className="pt-2">
              <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                {/* Total de resultados */}
                <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                  <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-blue-400 flex-shrink-0"></div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-white/90 font-semibold text-sm">{totalResults}</span>
                    <span className="text-white/70 text-xs font-medium uppercase">Encontrados</span>
                  </div>
                </div>

                {/* Resultados filtrados */}
                <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                  <IoFunnel className="text-white/90 text-sm" />
                  <div className="flex items-center gap-1.5">
                    <span className="text-white/90 font-semibold text-sm">{filteredResults.length}</span>
                    <span className="text-white/70 text-xs font-medium uppercase">Filtrados ≥{similarityThreshold[0]}%</span>
                  </div>
                </div>

                {/* Alta similitud */}
                {highSimilarity > 0 && (
                  <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                    <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-emerald-400 flex-shrink-0"></div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-white/90 font-semibold text-sm">{highSimilarity}</span>
                      <span className="text-white/70 text-xs font-medium uppercase">Alta ≥90%</span>
                    </div>
                  </div>
                )}

                {/* Media similitud */}
                {mediumSimilarity > 0 && (
                  <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                    <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-yellow-400 flex-shrink-0"></div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-white/90 font-semibold text-sm">{mediumSimilarity}</span>
                      <span className="text-white/70 text-xs font-medium uppercase">Media 70-89%</span>
                    </div>
                  </div>
                )}

                {/* Baja similitud */}
                {lowSimilarity > 0 && (
                  <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                    <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-red-400 flex-shrink-0"></div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-white/90 font-semibold text-sm">{lowSimilarity}</span>
                      <span className="text-white/70 text-xs font-medium uppercase">Baja &lt;70%</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Indicador de búsqueda en progreso */}
          {isSearching && (
            <div className="pt-2">
              <div className="flex items-center gap-2 bg-white/15 px-3 py-2 rounded-lg border border-white/30 h-10 sm:h-12">
                <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-blue-400 animate-pulse flex-shrink-0"></div>
                <span className="text-white/90 text-sm font-medium">Buscando casos similares...</span>
              </div>
            </div>
          )}
        </div>
      </CardBody>
    </Card>
  );
};

export default HeaderBusquedaSimilares;
