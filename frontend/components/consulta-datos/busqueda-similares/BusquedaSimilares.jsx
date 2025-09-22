import React, { useState, useRef } from 'react';
import { useDisclosure } from '@heroui/react';
import HeaderBusquedaSimilares from './HeaderBusquedaSimilares';
import SearchFilters from './search-filters/SearchFilters';
import LoadingResults from './LoadingResults';
import ResultsHeader from './ResultsHeader';
import NoResults from './results-grid/NoResults';
import ResultsGrid from './results-grid/ResultsGrid';
import CaseDetailsModal from './results-grid/details-drawer/CaseDetailsDrawer';
import useSimilarityUtils from '@/hooks/busqueda-similares/useSimilarityUtils';
import similarityService from '@/services/similarityService';
import Toast from '@/components/ui/CustomAlert';  

const BusquedaSimilares = () => {
  // Estados
  const [searchMode, setSearchMode] = useState('description');
  const [searchText, setSearchText] = useState('');
  const [expedientNumber, setExpedientNumber] = useState('');
  const [similarityThreshold, setSimilarityThreshold] = useState([30]); // Cambiar a 30% por defecto
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [searchStats, setSearchStats] = useState(null); // Estadísticas de búsqueda
  const [selectedCase, setSelectedCase] = useState(null);
  const [searchError, setSearchError] = useState(null);
  
  // Ref para hacer scroll a los resultados
  const resultsRef = useRef(null);
  
  // Modal
  const { isOpen, onOpen, onClose } = useDisclosure();
  
  // Hook personalizado para utilidades
  const { parseExpedientNumber, getMatterDescription, getSimilarityColor } = useSimilarityUtils();

  // Filtrar resultados por umbral de similitud (convertir de porcentaje a decimal)
  const filteredResults = searchResults.filter(
    result => (result.similarityPercentage || 0) >= similarityThreshold[0]
  );

  // Función de búsqueda real con el servicio
  const handleSearch = async () => {
    try {
      setIsSearching(true);
      setHasSearched(true);
      setSearchError(null);
      setSearchResults([]);
      
      // Hacer scroll inmediatamente cuando comience la búsqueda
      setTimeout(() => {
        if (resultsRef.current) {
          resultsRef.current.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start',
            inline: 'nearest'
          });
        }
      }, 100);

      // Determinar query según modo
      const query = searchMode === 'description' ? searchText : expedientNumber;
      const searchModeSpanish = searchMode === 'description' ? 'descripcion' : 'expediente';
      
      // Validar query
      if (!query || query.trim().length === 0) {
        throw new Error(
          searchMode === 'description' 
            ? 'Por favor ingrese una descripción para buscar'
            : 'Por favor ingrese un número de expediente para buscar'
        );
      }

      // Llamar al servicio
      const results = await similarityService.searchSimilarCases({
        searchMode: searchModeSpanish,
        query: query,
        limit: 30,
        threshold: similarityThreshold[0] / 100 // Convertir de porcentaje a decimal
      });

      if (results) {
        setSearchResults(results.similarCases || []);
        setSearchStats(results.searchStats || null); // Guardar estadísticas
        
        // Mostrar notificación de éxito
        Toast.success(
          'Búsqueda completada',
          `Se encontraron ${results.totalResults} casos similares`,
          {
            timeout: 4000
          }
        );
      } else {
        setSearchResults([]);
        setSearchStats(null);
      }

    } catch (error) {
      console.error('❌ Error en búsqueda:', error);
      setSearchError(error.message);
      setSearchResults([]);
      setSearchStats(null); // Limpiar estadísticas en caso de error
      
      // Mostrar notificación de error
      Toast.error(
        'Error en búsqueda',
        error.message || 'Error al realizar búsqueda',
        {
          timeout: 5000
        }
      );
    } finally {
      setIsSearching(false);
    }
  };

  // Función para ver detalles
  const handleViewDetails = (caseData) => {
    setSelectedCase(caseData);
    onOpen();
  };

  // Función para reducir similitud cuando no hay resultados
  const handleReduceSimilarity = () => {
    setSimilarityThreshold([20]); // Reducir a 20%
  };

  // Función para limpiar inputs y cancelar búsqueda
  const clearInputs = () => {
    // Cancelar búsqueda en progreso si existe
    similarityService.cancelSearch();
    
    setSearchText('');
    setExpedientNumber('');
    setHasSearched(false);
    setSearchResults([]);
    setSearchError(null);
    setIsSearching(false);
  };

  // Verificar si hay contenido para limpiar
  const hasContent = () => {
    return searchText.trim().length > 0 || expedientNumber.trim().length > 0;
  };

  return (
    <div 
      className="p-6 space-y-6"
      style={{
        transform: 'none',
        transition: 'none',
        position: 'static',
        willChange: 'auto'
      }}
    >
      <div className="space-y-6">

        {/* Header estandarizado */}
        <HeaderBusquedaSimilares 
          searchMode={searchMode}
          setSearchMode={setSearchMode}
          onClearInputs={clearInputs}
          hasContent={hasContent()}
          hasSearched={hasSearched}
          searchResults={searchResults}
          similarityThreshold={similarityThreshold}
          isSearching={isSearching}
        />

        {/* Filtros de Búsqueda */}
        <SearchFilters
          searchMode={searchMode}
          setSearchMode={setSearchMode}
          searchText={searchText}
          setSearchText={setSearchText}
          expedientNumber={expedientNumber}
          setExpedientNumber={setExpedientNumber}
          onSearch={handleSearch}
          isSearching={isSearching}
          hasSearched={hasSearched}
          onClearResults={clearInputs}
        />

        {/* Estado de Carga y Resultados */}
        {(isSearching || (hasSearched && !isSearching)) && (
          <div ref={resultsRef} className="space-y-6">
            {/* Estado de Carga */}
            {isSearching && <LoadingResults />}

            {/* Resultados */}
            {hasSearched && !isSearching && (
              <>
                {/* Header de Resultados con Filtro */}
                <ResultsHeader
                  resultsCount={filteredResults.length}
                  similarityThreshold={similarityThreshold}
                  setSimilarityThreshold={setSimilarityThreshold}
                  searchStats={searchStats}
                />

                {/* Contenido de Resultados */}
                {filteredResults.length === 0 ? (
                  <NoResults onReduceSimilarity={handleReduceSimilarity} />
                ) : (
                  <ResultsGrid
                    results={filteredResults}
                    parseExpedientNumber={parseExpedientNumber}
                    getMatterDescription={getMatterDescription}
                    getSimilarityColor={getSimilarityColor}
                    onViewDetails={handleViewDetails}
                  />
                )}
              </>
            )}
          </div>
        )}

        <CaseDetailsModal
          isOpen={isOpen}
          onClose={onClose}
          selectedCase={selectedCase}
          parseExpedientNumber={parseExpedientNumber}
          getMatterDescription={getMatterDescription}
          getSimilarityColor={getSimilarityColor}
        />
      </div>
    </div>
  );
};

export default BusquedaSimilares;
