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
  
  // Calcular estadísticas de búsqueda basadas en similarityPercentage
  // PRIMERO filtrar por umbral
  const filteredResults = searchResults.filter(result => 
    (result.similarityPercentage || 0) >= similarityThreshold[0]
  );
  
  // Calcular categorías SOLO sobre resultados filtrados
  const highSimilarity = filteredResults.filter(result => 
    (result.similarityPercentage || 0) >= 90
  ).length;
  const mediumSimilarity = filteredResults.filter(result => 
    (result.similarityPercentage || 0) >= 70 && (result.similarityPercentage || 0) < 90
  ).length;
  const lowSimilarity = filteredResults.filter(result => 
    (result.similarityPercentage || 0) < 70
  ).length;

  // Mostrar SOLO los casos que pasan el umbral
  const currentStats = {
    total: filteredResults.length,  // Solo casos que cumplen umbral
    filtered: filteredResults.length,
    high: highSimilarity,
    medium: mediumSimilarity,
    low: lowSimilarity
  };

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
          </div>

          {/* Estadísticas de resultados - Siempre visible */}
          <div className="pt-2">
            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              {/* Total de resultados */}
              <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-blue-400 flex-shrink-0"></div>
                <div className="flex items-center gap-1.5">
                  <span className="text-white/90 font-semibold text-sm">{currentStats.total}</span>
                  <span className="text-white/70 text-xs font-medium uppercase">
                    {hasSearched ? 'Encontrados' : 'Sistema listo'}
                  </span>
                </div>
              </div>

              {/* Resultados filtrados */}
              <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                <IoFunnel className="text-white/90 text-sm" />
                <div className="flex items-center gap-1.5">
                  <span className="text-white/90 font-semibold text-sm">{currentStats.filtered}</span>
                  <span className="text-white/70 text-xs font-medium uppercase">
                    {hasSearched ? `Filtrados ≥${similarityThreshold[0]}%` : 'Pendientes'}
                  </span>
                </div>
              </div>

              {/* Alta similitud */}
              <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-emerald-400 flex-shrink-0"></div>
                <div className="flex items-center gap-1.5">
                  <span className="text-white/90 font-semibold text-sm">{currentStats.high}</span>
                  <span className="text-white/70 text-xs font-medium uppercase">
                    {hasSearched ? 'Alta ≥90%' : 'Alta similitud'}
                  </span>
                </div>
              </div>

              {/* Media similitud */}
              <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-yellow-400 flex-shrink-0"></div>
                <div className="flex items-center gap-1.5">
                  <span className="text-white/90 font-semibold text-sm">{currentStats.medium}</span>
                  <span className="text-white/70 text-xs font-medium uppercase">
                    {hasSearched ? 'Media 70-89%' : 'Media similitud'}
                  </span>
                </div>
              </div>

              {/* Baja similitud */}
              <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-red-400 flex-shrink-0"></div>
                <div className="flex items-center gap-1.5">
                  <span className="text-white/90 font-semibold text-sm">{currentStats.low}</span>
                  <span className="text-white/70 text-xs font-medium uppercase">
                    {hasSearched ? 'Baja <70%' : 'Baja similitud'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

export default HeaderBusquedaSimilares;
