import React, { useState } from 'react';
import { useDisclosure } from '@heroui/react';
import HeaderBusquedaSimilares from './HeaderBusquedaSimilares';
import SearchFilters from './search-filters/SearchFilters';
import LoadingResults from './LoadingResults';
import ResultsHeader from './ResultsHeader';
import NoResults from './results-grid/NoResults';
import ResultsGrid from './results-grid/ResultsGrid';
import CaseDetailsModal from './results-grid/details-drawer/CaseDetailsDrawer';
import useSimilarityUtils from '@/hooks/busqueda-similares/useSimilarityUtils';

const BusquedaSimilares = () => {
  // Estados
  const [searchMode, setSearchMode] = useState('description');
  const [searchText, setSearchText] = useState('');
  const [expedientNumber, setExpedientNumber] = useState('');
  const [similarityThreshold, setSimilarityThreshold] = useState([75]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  
  // Modal
  const { isOpen, onOpen, onClose } = useDisclosure();
  
  // Hook personalizado para utilidades
  const { parseExpedientNumber, getMatterDescription, getSimilarityColor, mockResults } = useSimilarityUtils();

  // Filtrar resultados por umbral de similitud
  const filteredResults = searchResults.filter(
    result => result.similarity >= similarityThreshold[0]
  );

  // Función de búsqueda
  const handleSearch = async () => {
    setIsSearching(true);
    setHasSearched(true);
    
    // Simular delay de búsqueda
    setTimeout(() => {
      setSearchResults(mockResults);
      setIsSearching(false);
    }, 2000);
  };

  // Función para ver detalles
  const handleViewDetails = (caseData) => {
    setSelectedCase(caseData);
    onOpen();
  };

  // Función para reducir similitud cuando no hay resultados
  const handleReduceSimilarity = () => {
    setSimilarityThreshold([60]);
  };

  // Función para limpiar inputs
  const clearInputs = () => {
    setSearchText('');
    setExpedientNumber('');
    setHasSearched(false);
    setSearchResults([]);
  };

  // Verificar si hay contenido para limpiar
  const hasContent = () => {
    return searchText.trim().length > 0 || expedientNumber.trim().length > 0;
  };

  return (
    <div className="w-full py-9">
      <div className="max-w-7xl mx-auto space-y-12 px-8">

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
        />

        {/* Estado de Carga */}
        {isSearching && <LoadingResults />}

        {/* Resultados */}
        {hasSearched && !isSearching && (
          <div className="space-y-10">
            {/* Header de Resultados con Filtro */}
            <ResultsHeader
              resultsCount={filteredResults.length}
              similarityThreshold={similarityThreshold}
              setSimilarityThreshold={setSimilarityThreshold}
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
