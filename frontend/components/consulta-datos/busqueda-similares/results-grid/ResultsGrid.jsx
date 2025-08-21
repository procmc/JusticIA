import React from 'react';
import CaseCard from './CaseCard';

const ResultsGrid = ({ 
  results, 
  parseExpedientNumber, 
  getMatterDescription, 
  getSimilarityColor,
  onViewDetails 
}) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {results.map((result) => (
        <CaseCard
          key={result.id}
          caseData={result}
          parseExpedientNumber={parseExpedientNumber}
          getMatterDescription={getMatterDescription}
          getSimilarityColor={getSimilarityColor}
          onViewDetails={onViewDetails}
        />
      ))}
    </div>
  );
};

export default ResultsGrid;
