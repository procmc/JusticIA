import React from 'react';
import { Card, CardBody, Button } from '@heroui/react';

const NoResults = ({ onReduceSimilarity }) => {
  return (
    <Card>
      <CardBody className="p-12 text-center">
        <div className="text-6xl mb-4">🔍</div>
        <h3 className="text-xl font-semibold text-gray-700 mb-2">
          No se encontraron casos similares
        </h3>
        <p className="text-gray-500 mb-4">
          Prueba reduciendo el porcentaje de similitud o ajustando tu búsqueda
        </p>
        <Button
          color="primary"
          variant="flat"
          onPress={onReduceSimilarity}
        >
          Reducir a 60% de similitud
        </Button>
      </CardBody>
    </Card>
  );
};

export default NoResults;
