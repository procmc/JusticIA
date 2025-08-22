import React from 'react';
import { Card, CardBody, Progress } from '@heroui/react';
import { IoSparkles } from 'react-icons/io5';

const LoadingResults = () => {
  return (
    <div className="space-y-6">
      {/* Header simple */}
      <div className="text-center space-y-3">
        <div className="flex justify-center">
          <div className="p-3 bg-gradient-to-br from-primary-500 to-primary-600 rounded-full">
            <IoSparkles className="w-6 h-6 pt-1 pl-0.5 text-white animate-pulse" />
          </div>
        </div>

        <div>
          <h2 className="text-xl font-semibold text-gray-800">
            Analizando casos similares
          </h2>
          <p className="text-gray-500 text-sm">
            Procesando su consulta...
          </p>
        </div>

        {/* Barra de progreso simple */}
        <div className="max-w-xs mx-auto">
          <Progress isIndeterminate aria-label="Loading..." className="max-w-md" size="sm" />
        </div>
      </div>

      {/* Cards de loading simplificadas */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, index) => (
          <Card key={index} className="animate-pulse">
            <CardBody className="p-4">
              <div className="space-y-3">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                <div className="h-16 bg-gray-200 rounded"></div>
                <div className="flex justify-between">
                  <div className="h-3 bg-gray-200 rounded w-1/3"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/4"></div>
                </div>
              </div>
            </CardBody>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default LoadingResults;
