import React from 'react';
import { IoText, IoDocument } from 'react-icons/io5';

const SearchInstructions = () => {
  return (
    <div className="mt-6 p-4 bg-gradient-to-r from-slate-100 to-gray-50 rounded-lg border border-gray-100 w-full">
      <div className="grid md:grid-cols-2 gap-4">
        {/* Búsqueda por Descripción */}
        <div className="flex items-start gap-3">
          <div className="p-2 bg-slate-100 rounded-lg mt-0.5 flex-shrink-0">
            <IoText className="w-4 h-4 text-slate-600" />
          </div>
          <div className="min-w-0">
            <h4 className="font-medium text-slate-700 text-sm mb-1">
              Búsqueda por Descripción
            </h4>
            <p className="text-slate-600 text-xs leading-relaxed">
              Describe tu caso en lenguaje natural con detalles específicos sobre el tipo de caso y circunstancias relevantes.
            </p>
          </div>
        </div>

        {/* Búsqueda por Expediente */}
        <div className="flex items-start gap-3">
          <div className="p-2 bg-slate-100 rounded-lg mt-0.5 flex-shrink-0">
            <IoDocument className="w-4 h-4 text-slate-600" />
          </div>
          <div className="min-w-0">
            <h4 className="font-medium text-slate-700 text-sm mb-1">
              Búsqueda por Expediente
            </h4>
            <p className="text-slate-600 text-xs leading-relaxed">
              Ingresa el número de expediente específico para encontrar casos relacionados o con características similares.
            </p>
          </div>
        </div>
      </div>

      {/* Consejo en la parte inferior */}
      <div className="mt-4 pt-3 border-t border-gray-150">
        <div className="flex items-start gap-2">
          <div className="w-4 h-4 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0 mt-0.5">
            <span className="text-amber-600 text-xs font-bold">!</span>
          </div>
          <div>
            <span className="font-medium text-slate-700 text-xs">Consejo: </span>
            <span className="text-slate-600 text-xs">
              Nuestra IA utiliza análisis semántico avanzado. Sé específico e incluye elementos legales relevantes para obtener mejores resultados.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SearchInstructions;
