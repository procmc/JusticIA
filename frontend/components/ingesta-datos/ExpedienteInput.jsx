/**
 * Componente para el input de expediente y botones de acción
 * Extraído del componente principal sin modificaciones
 */
import React from 'react';
import { Button, Input } from '@heroui/react';
import { FiAlertCircle, FiFolder, FiSave } from 'react-icons/fi';
import { PiBroomLight } from 'react-icons/pi';

const ExpedienteInput = ({
  expedienteNumero,
  setExpedienteNumero,
  handleSaveClick,
  isButtonDisabled,
  uploading,
  pendingFiles,
  files,
  setFiles
}) => {
  return (
    <>
      {/* Instrucción simple y elegante - Responsive */}
      <div className="mb-4">
        <div className="bg-primary-50 border-l-4 border-primary-400 p-3 sm:p-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-0">
            <div className="flex items-center">
              <FiAlertCircle className="w-4 h-4 text-primary-600 mr-2 flex-shrink-0" />
              <span className="text-sm text-gray-700">Formato requerido:</span>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center sm:ml-1 gap-1 sm:gap-2">
              <code className="px-2 py-1 bg-white rounded text-primary-600 font-mono text-xs border inline-block">
                AA-NNNNNN-OOOO-MM
              </code>
              <span className="text-xs text-gray-600 sm:text-sm">
                (Año-Consecutivo-Oficina-Materia)
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-[320px_1fr] gap-4 sm:gap-3 mb-6 sm:items-end">
        <div>
          <Input
            label="Número de Expediente"
            labelPlacement='outside'
            placeholder="98-003287-0166-LA"
            value={expedienteNumero}
            onChange={(e) => setExpedienteNumero(e.target.value)}
            startContent={<FiFolder className="w-4 h-4 text-gray-400" />}
            size="md"
            variant="bordered"
            radius="md"
            color='primary'
            isRequired
            className="w-full"
          />
        </div>
        
        <div className="flex gap-2">
          <Button
            color="primary"
            onPress={handleSaveClick}
            disabled={isButtonDisabled}
            isLoading={uploading}
            size="md"
            radius="md"
            className={`px-4 sm:px-6 font-medium shadow-lg hover:shadow-xl transform transition-all duration-200 text-sm ${isButtonDisabled
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 hover:scale-105'
              }`}
            startContent={!uploading && <FiSave className="w-4 h-4" />}
            spinner={
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            }
          >
            {uploading
              ? 'Guardando...'
              : pendingFiles > 0
                ? `Guardar ${pendingFiles}`
                : 'Guardar'
            }
          </Button>

          {files.length > 0 && (
            <Button
              onPress={() => setFiles([])}
              color="default"
              variant="flat"
              size="sn"
              startContent={<PiBroomLight className="w-4 h-4" />}
              disabled={uploading}
              className="px-4 font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-100 transition-all duration-200 text-sm"
              radius="md"
            >
            </Button>
          )}
        </div>
      </div>
    </>
  );
};

export default ExpedienteInput;
