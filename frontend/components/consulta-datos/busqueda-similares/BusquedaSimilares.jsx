import React from 'react';

const BusquedaSimilares = () => {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-gray-800 mb-6">
        Búsqueda de Casos Similares
      </h1>
      <div className="bg-white rounded-lg shadow-md p-6">
        <p className="text-gray-600">
          Buscar expedientes similares mediante análisis semántico del contenido.
        </p>
      </div>
    </div>
  );
};

export default BusquedaSimilares;
