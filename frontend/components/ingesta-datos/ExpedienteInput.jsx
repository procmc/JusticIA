/**
 * Componente para el input de expediente y botones de acción
 * Extraído del componente principal sin modificaciones
 */
import React from 'react';
import { Button, Input, Tooltip } from '@heroui/react';
import { FiAlertCircle, FiFolder, FiSave } from 'react-icons/fi';
import { PiBroomLight } from 'react-icons/pi';
import { EXPEDIENTE_INPUT_MAX_LENGTH } from '@/utils/validation/expedienteValidator';

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
    <div className="space-y-4 mb-6">
      {/* Sección Input + Botones */}
      <div className="flex flex-col gap-4">
        {/* Fila: Input + Botones */}
        <div className="flex flex-col sm:flex-row sm:items-end gap-3">
          {/* Input (crece en desktop con límite) */}
          <div className="flex-1 sm:max-w-md">
            <Input
              label="Número de Expediente"
              labelPlacement="outside"
              placeholder="02-000744-0164-CI"
              value={expedienteNumero}
              onChange={(e) => {
                const value = e.target.value;
                // Usar límite del validador unificado (25 chars con margen)
                if (value.length <= EXPEDIENTE_INPUT_MAX_LENGTH) {
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
          
          {/* Botones (fijos en desktop, stack en mobile) */}
          <div className="flex gap-2 sm:flex-shrink-0">
            <Button
              color="primary"
              onPress={handleSaveClick}
              disabled={isButtonDisabled}
              isLoading={uploading}
              size="md"
              radius="md"
              className={`flex-1 sm:flex-none px-4 sm:px-6 font-medium shadow-lg hover:shadow-xl transform transition-all duration-200 text-sm ${isButtonDisabled
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
                  className="flex-1 sm:flex-none px-4 font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-50 border-slate-300 hover:border-slate-400 transition-all duration-200 text-sm shadow-sm hover:shadow-md"
                  radius="md"
                >
                  Limpiar
                </Button>
              </Tooltip>
            )}
          </div>
        </div>
      </div>

      {/* Explicación del formato (ABAJO) */}
      <div className="bg-primary-50 border-l-4 border-primary-400 p-3 sm:p-4 rounded-r-lg">
        <div className="flex items-start gap-2">
          <FiAlertCircle className="w-4 h-4 text-primary-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2 text-sm text-gray-700">
              <span className="font-medium">Formato requerido:</span>
              <code className="text-xs bg-gray-100 px-2 py-1 rounded border border-gray-200">
                YY-NNNNNN-NNNN-XX
              </code>
            </div>
            <p className="text-xs text-gray-600 italic mt-1">
              * Use el formato oficial del Poder Judicial de Costa Rica
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExpedienteInput;
