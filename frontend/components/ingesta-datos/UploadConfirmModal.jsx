/**
 * Modal de confirmación específico para guardar archivos de ingesta
 */
import React from 'react';
import { Chip } from '@heroui/react';
import { FiFile, FiUploadCloud } from 'react-icons/fi';
import ConfirmModal from '@/components/ui/ConfirmModal';
import { formatearTamano } from '@/utils/ingesta-datos/ingestaUtils';
import { getFileIcon } from '@/utils/ingesta-datos/iconos';

const UploadConfirmModal = ({
  isOpen,
  onClose,
  onConfirm,
  files,
  pendingFiles,
  expedienteNumero
}) => {
  
  const handleConfirm = () => {
    onConfirm();
  };

  return (
    <ConfirmModal
      isOpen={isOpen}
      onClose={onClose}
      title="Confirmar Guardado de Archivos"
      customContent={
        <div className="space-y-3 text-left">
          {/* Warning al inicio - más compacto */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-start space-x-2">
              <FiFile className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-amber-800">
                <p className="font-semibold mb-0.5">Importante:</p>
                <p className="leading-relaxed">Esta acción asociará permanentemente los archivos a sus respectivos expedientes. Verifique cuidadosamente que toda la información sea correcta antes de continuar.</p>
              </div>
            </div>
          </div>

          <div className="text-gray-700">
            <p className="mb-3 text-sm">
              ¿Está seguro que desea guardar <span className="font-semibold text-blue-600">{pendingFiles} archivo{pendingFiles !== 1 ? 's' : ''}</span> en el sistema?
            </p>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="flex items-center space-x-2">
                <FiFile className="w-3.5 h-3.5 text-blue-600" />
                <span className="text-xs font-medium text-blue-800">Expediente:</span>
                <span className="text-xs font-mono font-bold text-blue-700">{expedienteNumero}</span>
              </div>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium text-gray-800 mb-2 flex items-center space-x-1.5">
              <FiFile className="w-3.5 h-3.5" />
              <span>Archivos a procesar:</span>
            </h4>

            <div className="max-h-60 overflow-y-auto space-y-1.5 border border-gray-200 rounded-lg p-2.5 bg-gray-50">
              {files
                .filter(f => f.status === 'pendiente')
                .map((file) => (
                  <div
                    key={file.id}
                    className="flex items-center justify-between p-2 bg-white rounded border border-gray-100 hover:border-blue-100 hover:bg-blue-50/30 transition-all"
                  >
                    <div className="flex items-center space-x-2 flex-1 min-w-0">
                      <div className="scale-75">
                        {getFileIcon(file.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-900 truncate leading-tight">
                          {file.name}
                        </p>
                        <div className="flex items-center space-x-3 mt-0.5">
                          <span className="text-[10px] text-gray-500">
                            {formatearTamano(file.size)}
                          </span>
                          <div className="flex items-center space-x-1">
                            <FiFile className="w-2.5 h-2.5 text-gray-400" />
                            <span className="text-[10px] font-mono font-semibold text-gray-600">
                              {file.expediente && file.expediente.trim() 
                                ? file.expediente.trim() 
                                : expedienteNumero || 'SIN EXPEDIENTE'
                              }
                            </span>
                            {!file.expediente?.trim() && !expedienteNumero?.trim() && (
                              <span className="text-[10px] text-red-500 font-semibold">⚠️</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                    <Chip
                      color={file.type === 'document' ? 'primary' : 'secondary'}
                      size="sm"
                      variant="flat"
                      className="text-[10px] h-5 px-2"
                    >
                      {file.type === 'document' ? 'DOC' : 'AUDIO'}
                    </Chip>
                  </div>
                ))
              }
            </div>
          </div>
        </div>
      }
      confirmText="Sí, Guardar Archivos"
      cancelText="Cancelar"
      confirmColor="primary"
      onConfirm={handleConfirm}
      icon={<FiUploadCloud className="w-6 h-6" />}
      size="lg"
      showIcon={true}
      centered={true}
    />
  );
};

export default UploadConfirmModal;
