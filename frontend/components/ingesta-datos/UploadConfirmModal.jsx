/**
 * Modal de confirmación específico para guardar archivos de ingesta
 */
import React from 'react';
import { Chip } from '@heroui/react';
import { FiFile, FiUploadCloud } from 'react-icons/fi';
import ConfirmModal from '@/components/ui/ConfirmModal';
import { formatearTamano } from '@/utils/ingesta-datos/funciones';
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
      description={
        <div className="space-y-4 text-left">
          {/* Warning al inicio */}
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-start space-x-3">
              <FiFile className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-amber-800">
                <p className="font-medium mb-1">Importante:</p>
                <p>Esta acción asociará permanentemente los archivos a sus respectivos expedientes. Verifique cuidadosamente que toda la información sea correcta antes de continuar.</p>
              </div>
            </div>
          </div>

          <div className="text-gray-700">
            <p className="mb-4">
              ¿Está seguro que desea guardar <span className="font-semibold text-blue-600">{pendingFiles} archivo{pendingFiles !== 1 ? 's' : ''}</span> en el sistema?
            </p>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center space-x-2">
                <FiFile className="w-4 h-4 text-blue-600" />
                <span className="font-medium text-blue-800">Expediente Principal:</span>
                <span className="font-mono font-bold text-blue-700">{expedienteNumero}</span>
              </div>
            </div>
          </div>

          <div>
            <h4 className="font-medium text-gray-800 mb-3 flex items-center space-x-2">
              <FiFile className="w-4 h-4" />
              <span>Archivos a procesar:</span>
            </h4>

            <div className="max-h-60 overflow-y-auto space-y-2 border border-gray-200 rounded-lg p-3 bg-gray-50">
              {files
                .filter(f => f.status === 'pending')
                .map((file) => (
                  <div
                    key={file.id}
                    className="flex items-center justify-between p-3 bg-white rounded border border-gray-100 hover:border-gray-200 transition-colors"
                  >
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      {getFileIcon(file.type)}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {file.name}
                        </p>
                        <div className="flex items-center space-x-4 mt-1">
                          <span className="text-xs text-gray-500">
                            {formatearTamano(file.size)}
                          </span>
                          <div className="flex items-center space-x-1">
                            <FiFile className="w-3 h-3 text-gray-400" />
                            <span className="text-xs font-mono font-bold text-gray-600">
                              {file.expediente || expedienteNumero}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <Chip
                      color={file.type === 'document' ? 'primary' : 'secondary'}
                      size="sm"
                      variant="flat"
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
