import React from 'react';
import { motion } from 'framer-motion';
import { Chip } from '@heroui/react';
import { FiUploadCloud, FiAlertCircle } from 'react-icons/fi';
import { tiposArchivo } from './funciones';

const ZonaArrastre = ({ 
  expedienteValido, 
  arrastreActivo, 
  alEntrarArrastre, 
  alSalirArrastre, 
  alSobreArrastre, 
  alSoltar,
  alSeleccionarArchivo,
  referenciaInput 
}) => {
  return (
    <div
      className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 ${
        !expedienteValido
          ? 'border-gray-200 bg-gray-50 opacity-50 cursor-not-allowed'
          : arrastreActivo 
            ? 'border-blue-500 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
      }`}
      onDragEnter={expedienteValido ? alEntrarArrastre : undefined}
      onDragLeave={expedienteValido ? alSalirArrastre : undefined}
      onDragOver={expedienteValido ? alSobreArrastre : undefined}
      onDrop={expedienteValido ? alSoltar : undefined}
    >
      {!expedienteValido && (
        <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-90 rounded-xl z-10">
          <div className="text-center">
            <FiAlertCircle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
            <p className="text-sm font-medium text-gray-700 mb-1">
              Área bloqueada
            </p>
            <p className="text-xs text-gray-500">
              Ingrese un número de expediente válido para continuar
            </p>
          </div>
        </div>
      )}
      
      <motion.div
        animate={{ scale: arrastreActivo ? 1.04 : 1 }}
        transition={{ duration: 0.2 }}
        className="flex flex-col items-center space-y-3"
      >
        <div className={`p-3 rounded-full ${arrastreActivo ? 'bg-blue-100' : 'bg-gray-100'}`}>
          <FiUploadCloud className={`w-10 h-10 ${arrastreActivo ? 'text-blue-600' : 'text-gray-400'}`} />
        </div>
        
        <div className="space-y-1">
          <h3 className="text-lg font-semibold text-gray-700">
            {arrastreActivo ? '¡Suelta los archivos aquí!' : 'Arrastra archivos aquí'}
          </h3>
          <p className="text-sm text-gray-500">
            o{' '}
            <button
              onClick={() => expedienteValido && referenciaInput.current?.click()}
              className={`font-medium underline ${
                expedienteValido 
                  ? 'text-blue-600 hover:text-blue-700 cursor-pointer' 
                  : 'text-gray-400 cursor-not-allowed'
              }`}
              disabled={!expedienteValido}
            >
              examina tu dispositivo
            </button>
          </p>
        </div>

        <div className="flex flex-wrap gap-2 justify-center">
          <Chip color="primary" variant="flat" size="sm">PDF</Chip>
          <Chip color="primary" variant="flat" size="sm">DOC/DOCX</Chip>
          <Chip color="primary" variant="flat" size="sm">RTF</Chip>
          <Chip color="primary" variant="flat" size="sm">TXT</Chip>
          <Chip color="secondary" variant="flat" size="sm">MP3</Chip>
          <Chip color="secondary" variant="flat" size="sm">WAV</Chip>
          <Chip color="secondary" variant="flat" size="sm">M4A</Chip>
          <Chip color="secondary" variant="flat" size="sm">OGG</Chip>
        </div>
      </motion.div>

      <input
        ref={referenciaInput}
        type="file"
        multiple
        onChange={alSeleccionarArchivo}
        accept={[...tiposArchivo.documentos, ...tiposArchivo.audio].join(',')}
        className="hidden"
      />
    </div>
  );
};

export default ZonaArrastre;
