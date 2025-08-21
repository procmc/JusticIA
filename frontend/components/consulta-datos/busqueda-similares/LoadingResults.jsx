import React from 'react';
import { Card, CardBody } from '@heroui/react';

const LoadingResults = () => {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-800">Analizando casos similares...</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[...Array(6)].map((_, index) => (
          <Card key={index} className="animate-pulse">
            <CardBody className="p-6">
              <div className="space-y-3">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                <div className="h-12 bg-gray-200 rounded"></div>
                <div className="h-3 bg-gray-200 rounded w-2/3"></div>
              </div>
            </CardBody>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default LoadingResults;
