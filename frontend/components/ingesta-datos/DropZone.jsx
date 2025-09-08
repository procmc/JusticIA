/**
 * Componente para la zona de arrastre y selección de archivos
 * Actualizado para usar getAllowedFileExtensions de utils
 */
import React from 'react';
import { motion } from 'framer-motion';
import { FiUploadCloud, FiAlertCircle } from 'react-icons/fi';
import { IoCheckmarkCircle } from 'react-icons/io5';
import { getAllowedFileExtensions } from '@/utils/ingesta-datos/ingestaUtils';

const DropZone = ({
  dragZoneRef,
  fileInputRef,
  isExpedienteValid,
  dragActive,
  handleDrag,
  handleDrop,
  handleChange,
  files,
  pendingFiles
}) => {
  const allowedExtensions = getAllowedFileExtensions();
  return (
    <div
      ref={dragZoneRef}
      className={`relative border-2 border-dashed rounded-2xl p-12 min-h-[300px] text-center transition-all duration-300 ${
        !isExpedienteValid
          ? 'border-gray-200 bg-gray-50 opacity-50 cursor-not-allowed'
          : dragActive 
            ? 'border-blue-500 bg-blue-50 shadow-lg' 
            : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50/50'
      }`}
      onDragEnter={isExpedienteValid ? handleDrag : undefined}
      onDragLeave={isExpedienteValid ? handleDrag : undefined}
      onDragOver={isExpedienteValid ? handleDrag : undefined}
      onDrop={isExpedienteValid ? handleDrop : undefined}
    >

      {!isExpedienteValid && (
        <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-95 rounded-2xl z-10">
          <div className="text-center">
            <FiAlertCircle className="w-10 h-10 text-amber-500 mx-auto mb-3" />
            <p className="text-base font-medium text-gray-700 mb-2">
              Área bloqueada
            </p>
            <p className="text-sm text-gray-500">
              Ingrese un número de expediente válido para continuar
            </p>
          </div>
        </div>
      )}

      <motion.div
        animate={{ scale: dragActive ? 1.02 : 1 }}
        transition={{ duration: 0.2 }}
        className="flex flex-col items-center space-y-4"
      >
        <div className={`p-4 rounded-full ${dragActive ? 'bg-blue-100' : 'bg-gray-100'}`}>
          <FiUploadCloud className={`w-12 h-12 ${dragActive ? 'text-blue-600' : 'text-gray-400'}`} />
        </div>

        <div className="space-y-2">
          <h3 className="text-xl font-semibold text-gray-700">
            {dragActive ? '¡Suelta los archivos aquí!' : 'Selecciona tus archivos'}
          </h3>
          <p className="text-gray-500">
            Arrastra y suelta archivos aquí o{' '}
            <button
              onClick={() => isExpedienteValid && fileInputRef.current?.click()}
              className={`font-medium underline ${isExpedienteValid
                ? 'text-blue-600 hover:text-blue-700 cursor-pointer'
                : 'text-gray-400 cursor-not-allowed'
                }`}
              disabled={!isExpedienteValid}
            >
              examina tu dispositivo
            </button>
          </p>
          {files.length > 0 && (
            <div className="mt-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
              <div className="flex items-center justify-center gap-2">
                <IoCheckmarkCircle className="w-5 h-5 text-emerald-600" />
                <span className="text-emerald-800 font-medium">
                  ¡{files.length} archivo{files.length !== 1 ? 's' : ''} {files.length !== 1 ? 'agregados' : 'agregado'}!
                  {pendingFiles > 0 && ` ${pendingFiles} listo${pendingFiles !== 1 ? 's' : ''} para guardar`}
                </span>
              </div>
              {files.length >= 8 && (
                <div className="mt-2 text-xs text-amber-700">
                  Cerca del límite: {files.length}/10 archivos
                </div>
              )}
            </div>
          )}
        </div>

        {/* Formatos soportados y límites */}
        <div className="mt-6 space-y-1 text-xs text-gray-500 text-center">
          <div>Formatos soportados: PDF, DOC, DOCX, RTF, TXT, MP3, WAV, M4A, OGG</div>
          <div>Máximo 10 archivos por expediente</div>
        </div>
      </motion.div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        onChange={handleChange}
        accept={allowedExtensions.join(',')}
        className="hidden"
      />
    </div>
  );
};

export default DropZone;
