import React from 'react';
import { Card, CardBody } from '@heroui/react';
import { IoSearchOutline } from 'react-icons/io5';

const NoResults = () => {
  return (
    <div className="relative">
      {/* Gradiente de fondo sutil */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-50/30 via-white to-blue-50/20 rounded-2xl -z-10"></div>

      <Card className="border-0 shadow-lg bg-white/80 backdrop-blur-sm">
        <CardBody className="p-8 sm:p-12 text-center">
          {/* Ícono principal con gradiente */}
          <div className="flex justify-center mb-6">
            <div className="relative">
              <div className="p-6 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-full">
                <IoSearchOutline className="w-12 h-12 text-blue-600" />
              </div>
              {/* Decoración circular */}
              <div className="absolute -top-1 -right-1 w-6 h-6 bg-gradient-to-br from-orange-400 to-red-400 rounded-full opacity-80"></div>
            </div>
          </div>
          {/* Descripción */}
          <div className="space-y-3 mb-6">
            <p className="text-lg font-medium text-gray-700 max-w-lg mx-auto">
              ¡Ups! No encontramos casos similares
            </p>
            <p className="text-sm text-gray-500 max-w-md mx-auto leading-relaxed">
              Intenta ajustar tus criterios de búsqueda para obtener mejores resultados
            </p>
          </div>
        </CardBody>
      </Card>
    </div>
  );
};

export default NoResults;
