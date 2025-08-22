import React from 'react';
import SearchHeader from './SearchHeader';
import SearchInstructions from './SearchInstructions';

const SearchFilters = ({
  searchMode,
  setSearchMode,
  searchText,
  setSearchText,
  expedientNumber,
  setExpedientNumber,
  onSearch,
  isSearching,
  hasSearched = false
}) => {
  return (
    <div>
      <SearchHeader
        searchMode={searchMode}
        setSearchMode={setSearchMode}
        searchText={searchText}
        setSearchText={setSearchText}
        expedientNumber={expedientNumber}
        setExpedientNumber={setExpedientNumber}
        onSearch={onSearch}
        isSearching={isSearching}
      />
      
      <SearchInstructions
        hasSearched={hasSearched}
      />
    </div>
  );
};

export default SearchFilters;
