import React from 'react';

const Bitacora = () => {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-gray-800 mb-6">
        Bitácora del Sistema
      </h1>
      <div className="bg-white rounded-lg shadow-md p-6">
        <p className="text-gray-600">
          Aquí se mostrarán todos los registros de actividad del sistema para auditoría.
        </p>
      </div>
    </div>
  );
};

export default Bitacora;
