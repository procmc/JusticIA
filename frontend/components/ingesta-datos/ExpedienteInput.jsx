/**
 * Componente para el input de expediente y botones de acción
 * Extraído del componente principal sin modificaciones
 */
import React from 'react';
import { Button, Input, Tooltip } from '@heroui/react';
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
      <div className="mb-4">
        <div className="bg-primary-50 border-l-4 border-primary-400 p-3 sm:p-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-0">
            <div className="flex items-center">
              <FiAlertCircle className="w-4 h-4 text-primary-600 mr-2 flex-shrink-0" />
              <span className="text-sm text-gray-700">Formato requerido:</span>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center sm:ml-1 gap-1 sm:gap-2">
              <div className="text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2 border">
                <span className="font-medium">Ejemplo:</span> 98-003287-0166-LA
              </div>
            </div>
          </div>
          <div className="mt-2 text-xs text-gray-600 italic">
            * Use el formato oficial del Poder Judicial
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
            onChange={(e) => {
              const value = e.target.value;
              // Limitar a 20 caracteres máximo
              if (value.length <= 20) {
                setExpedienteNumero(value);
              }
            }}
            startContent={<FiFolder className="w-4 h-4 text-gray-400" />}
            endContent={
              <div className="relative group">
                {expedienteNumero.length < 17 && expedienteNumero.length > 0 && (
                  <div className="absolute bottom-full right-0 mb-3 px-3 py-2 bg-gray-800 text-white text-xs rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-all duration-300 whitespace-nowrap z-50 border border-gray-700">
                    <div className="flex items-center gap-1">
                      <FiAlertCircle className="w-3 h-3 text-orange-400" />
                      <span>Formato no válido</span>
                    </div>
                    <div className="absolute top-full right-3 w-0 h-0 border-l-[6px] border-r-[6px] border-t-[6px] border-transparent border-t-gray-800"></div>
                  </div>
                )}
              </div>
            }
            size="md"
            variant="bordered"
            radius="md"
            color={expedienteNumero.length < 17 && expedienteNumero.length > 0 ? 'danger' : 'primary'}
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
            <Tooltip 
              content="Limpiar lista de archivos" 
              placement="top"
              delay={300}
            >
              <Button
                onPress={() => setFiles([])}
                color="default"
                variant="bordered"
                size="md"
                startContent={<PiBroomLight className="w-4 h-4" />}
                disabled={uploading}
                className="px-4 font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-50 border-slate-300 hover:border-slate-400 transition-all duration-200 text-sm shadow-sm hover:shadow-md"
                radius="md"
              >
                Limpiar
              </Button>
            </Tooltip>
          )}
        </div>
      </div>
    </>
  );
};

export default ExpedienteInput;
