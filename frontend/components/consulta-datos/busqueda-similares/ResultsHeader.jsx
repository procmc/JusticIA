import React from 'react';
import { Slider, Chip, Card, CardBody } from '@heroui/react';
import { IoDocuments, IoCheckmarkCircle } from 'react-icons/io5';

const ResultsHeader = ({
  resultsCount,
  similarityThreshold,
  setSimilarityThreshold
}) => {
  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Card principal con información de resultados */}
        <Card className="lg:col-span-2 border-l-4 border-l-primary-400">
          <CardBody className="p-6">
            <div className="flex items-start gap-3">
              <div className="p-2.5 bg-primary-100 rounded-xl">
                <IoDocuments className="w-5 h-5 text-primary-600" />
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-bold text-gray-900 leading-tight">
                  {resultsCount} casos encontrados
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  Filtrados por relevancia semántica
                </p>
                <div className="flex items-center gap-2 mt-2">
                  <IoCheckmarkCircle className="w-4 h-4 text-success-500" />
                  <span className="text-sm text-gray-600">
                    Análisis completado
                  </span>
                </div>
                
                {/* Estadísticas integradas */}
                <div className="flex items-center gap-6 mt-3 pt-3 border-t border-gray-100">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <span className="text-xs text-gray-500">Tiempo:</span>
                    <span className="text-xs font-medium text-gray-700">1.2s</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-xs text-gray-500">Precisión:</span>
                    <span className="text-xs font-medium text-gray-700">92%</span>
                  </div>
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Card de filtro de similitud */}
        <Card className="border-l-4 border-l-primary-400">
          <CardBody className="p-6">
            <div className="flex items-center justify-between mb-4">
              <label className="text-sm font-medium text-gray-700">
                Filtrar por similitud
              </label>
              <Chip 
                size="sm" 
                color="primary" 
                variant="flat"
                className="font-semibold"
              >
                {similarityThreshold[0]}%
              </Chip>
            </div>
            <div className="space-y-3">
              <Slider
                value={similarityThreshold}
                onChange={setSimilarityThreshold}
                minValue={50}
                maxValue={100}
                step={5}
                size='sm'
                color="primary"
                className="w-full"
                marks={[
                  { value: 50, label: "50%" },
                  { value: 75, label: "75%" },
                  { value: 100, label: "100%" }
                ]}
              />
              <div className="relative mt-4 pt-2 -mx-3">
                <div className="absolute left-0 text-xs text-gray-500">
                  <span>Menos similar</span>
                </div>
                <div className="absolute right-0 text-xs text-gray-500">
                  <span>Muy similar</span>
                </div>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>
      
      {/* Divider sutil */}
      <div className="relative mb-8">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-200"></div>
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="bg-gray-50 px-4 text-gray-500 font-medium">Resultados de búsqueda</span>
        </div>
      </div>
    </>
  );
};

export default ResultsHeader;
