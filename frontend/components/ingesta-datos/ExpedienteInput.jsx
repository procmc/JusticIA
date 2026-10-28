/**
 * Campo del tema y botones de acción de Ingesta de Datos.
 * El tema es de nombre libre: la pantalla solo exige que no esté vacío; las reglas (longitud, caracteres) las aplica el servidor
 * (RF-06.52). Enter o perder el foco confirma el texto para los archivos que siguen sin tema (RF-06.50).
 */
import React from 'react';
import { Button, Input, Tooltip } from '@heroui/react';
import { FiAlertCircle, FiFolder, FiSave } from 'react-icons/fi';
import { PiBroomLight } from 'react-icons/pi';

const ExpedienteInput = ({
  expedienteNumero,
  setExpedienteNumero,
  confirmarTema,
  handleSaveClick,
  isButtonDisabled,
  uploading,
  pendingFiles,
  filesWithoutExpediente,
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
              label="Tema"
              labelPlacement="outside"
              value={expedienteNumero}
              onChange={(e) => setExpedienteNumero(e.target.value)}
              onBlur={confirmarTema}
              onKeyDown={(e) => {
                if (e.key === 'Enter') confirmarTema();
              }}
              startContent={<FiFolder className="w-4 h-4 text-gray-400" />}
              size="md"
              variant="bordered"
              radius="md"
              color="primary"
              isRequired
              className="w-full"
            />
          </div>

          {/* Botones (fijos en desktop, stack en mobile) */}
          <div className="flex gap-2 sm:flex-shrink-0">
            <Button
              color="primary"
              onPress={handleSaveClick}
              isDisabled={isButtonDisabled}
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
                content="Limpiar lista de archivos y tema"
                placement="top"
                delay={300}
              >
                <Button
                  onPress={() => {
                    setFiles([]);
                    setExpedienteNumero('');
                  }}
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

      {/* Mientras algún pendiente siga sin tema, se dice por qué Guardar está deshabilitado (RF-06.50) */}
      {filesWithoutExpediente > 0 && (
        <div className="bg-warning-50 border-l-4 border-warning-400 p-3 sm:p-4 rounded-r-lg" role="status">
          <div className="flex items-start gap-2">
            <FiAlertCircle className="w-4 h-4 text-warning-600 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-gray-700">Indique el tema antes de guardar los archivos.</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExpedienteInput;
