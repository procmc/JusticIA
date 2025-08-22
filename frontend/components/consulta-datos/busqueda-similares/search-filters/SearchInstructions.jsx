import React from 'react';
import { Card, CardBody } from '@heroui/react';
import { IoSparkles, IoText, IoDocument } from 'react-icons/io5';

const SearchInstructions = ({ hasSearched = false }) => {
  // Solo mostrar cuando no se ha buscado nada
  if (hasSearched) {
    return null;
  }

  return (
    <Card className="border-0 shadow-sm bg-gradient-to-br from-blue-50/50 to-indigo-50/50 backdrop-blur-sm">
      <CardBody className="p-6">
        <div className="text-center space-y-4">
          <div className="flex justify-center">
            <div className="p-3 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full shadow-lg">
              <IoSparkles className="w-6 h-6 text-white" />
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-2">
              ¿Cómo usar la Búsqueda Inteligente?
            </h3>
            <p className="text-gray-600 text-sm mb-4">
              Nuestra IA utiliza análisis semántico para encontrar casos similares al tuyo
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-4 text-left">
            <div className="bg-white/60 rounded-lg p-4 border border-blue-100">
              <div className="flex items-start gap-3">
                <div className="p-1 bg-blue-100 rounded-lg mt-0.5">
                  <IoText className="w-4 h-4 text-blue-600" />
                </div>
                <div>
                  <h4 className="font-medium text-gray-800 text-sm mb-1">
                    Búsqueda por Descripción
                  </h4>
                  <p className="text-gray-600 text-xs leading-relaxed">
                    Describe tu caso en lenguaje natural. Ej: "Despido injustificado de trabajador con contrato indefinido"
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white/60 rounded-lg p-4 border border-blue-100">
              <div className="flex items-start gap-3">
                <div className="p-1 bg-blue-100 rounded-lg mt-0.5">
                  <IoDocument className="w-4 h-4 text-blue-600" />
                </div>
                <div>
                  <h4 className="font-medium text-gray-800 text-sm mb-1">
                    Búsqueda por Expediente
                  </h4>
                  <p className="text-gray-600 text-xs leading-relaxed">
                    Ingresa el número de expediente específico para encontrar casos relacionados o similares
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
            <div className="flex items-center gap-2 text-amber-800">
              <div className="w-4 h-4 rounded-full bg-amber-400 flex items-center justify-center">
                <span className="text-white text-xs font-bold">!</span>
              </div>
              <span className="font-medium text-xs">Consejo:</span>
            </div>
            <p className="text-amber-700 text-xs mt-1">
              Sé específico en tu descripción. Incluye detalles como el tipo de caso, las circunstancias y los elementos legales relevantes.
            </p>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

export default SearchInstructions;
