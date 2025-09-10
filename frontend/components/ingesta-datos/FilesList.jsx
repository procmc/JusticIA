/**
 * Componente para la lista de archivos seleccionados
 * Versión simplificada con spinner y botón de cancelar
 */
import React from 'react';
import { Card, CardHeader, CardBody, Divider, Chip, Input, Spinner, Button, Tooltip } from '@heroui/react';
import { motion, AnimatePresence } from 'framer-motion';
import { FiX, FiFolder, FiXCircle } from 'react-icons/fi';
import { formatearTamano } from '@/utils/ingesta-datos/ingestaUtils';
import { getFileIcon, getStatusColor } from '@/utils/ingesta-datos/iconos';

const FilesList = ({
  files,
  updateFileExpediente,
  removeFile,
  cancelFileProcessing,
  expedienteNumero
}) => {
  if (files.length === 0) {
    return null;
  }

  return (
    <div className="mb-6" data-files-list>
      <Card className="shadow-lg border border-gray-200">
        <CardHeader className="flex justify-between items-center p-6 bg-gray-50">
          <h3 className="text-lg font-semibold text-gray-800">Archivos Seleccionados</h3>
        </CardHeader>
        <Divider />
        <CardBody className="p-0">
          <div className="space-y-0">
            <AnimatePresence>
              {files.map((file) => (
                <motion.div
                  key={file.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="flex items-center justify-between p-4 hover:bg-gray-50 border-b border-gray-100 last:border-b-0 transition-colors"
                >
                  {/* Información del archivo */}
                  <div className="flex items-center space-x-4 flex-1 min-w-0">
                    {getFileIcon(file.type)}
                    <div className="flex-1 min-w-0">
                      {/* Nombre y estado */}
                      <div className="flex items-center space-x-3 mb-2">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {file.name}
                        </p>
                        <Chip
                          color={getStatusColor(file.status)}
                          size="sm"
                          variant="flat"
                        >
                          {file.status === 'pending' && 'Pendiente'}
                          {file.status === 'uploading' && 'Procesando'}
                          {file.status === 'success' && 'Completado'}
                          {file.status === 'error' && 'Error'}
                        </Chip>
                      </div>

                      {/* Información adicional */}
                      <div className="flex items-center space-x-3 text-xs text-gray-500">
                        <span>{formatearTamano(file.size)}</span>

                        {/* Input de expediente (solo si es necesario) */}
                        {file.status === 'pending' && !expedienteNumero?.trim() && !file.expediente?.trim() && (
                          <Input
                            size="sm"
                            placeholder="Núm. expediente"
                            value={file.expediente || ''}
                            onChange={(e) => updateFileExpediente(file.id, e.target.value)}
                            className="w-48"
                            startContent={<FiFolder className="text-gray-400 w-3 h-3" />}
                            classNames={{
                              input: "text-xs",
                              inputWrapper: "h-8 min-h-8"
                            }}
                          />
                        )}

                        {/* Chip de expediente */}
                        {(expedienteNumero?.trim() || file.expediente?.trim()) && (
                          <Chip color="primary" size="sm" variant="flat">
                            {file.expediente || expedienteNumero}
                          </Chip>
                        )}
                      </div>

                      {/* Spinner para archivos en procesamiento */}
                      {file.status === 'uploading' && (
                        <div className="flex items-center space-x-2 mt-2">
                          <Spinner size="sm" color="primary" />
                          <span className="text-sm text-gray-600">
                            {file.message || 'Procesando archivo...'}
                          </span>
                        </div>
                      )}

                      {/* Mensaje de error */}
                      {file.status === 'error' && file.message && (
                        <div className="text-xs text-red-600 mt-2">
                          {file.message}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Acciones */}
                  <div className="flex items-center space-x-2 flex-shrink-0 ml-4">
                    {/* Botón de eliminar para archivos pendientes, completados, con error o cancelados */}
                    {(file.status === 'pending' || file.status === 'success' || file.status === 'error' || file.status === 'cancelado') && (
                      <Tooltip content="Quitar archivo" placement="top">
                        <Button
                          size="sm"
                          variant="light"
                          color="danger"
                          isIconOnly
                          onClick={() => removeFile(file.id)}
                        >
                          <FiX className="w-4 h-4" />
                        </Button>
                      </Tooltip>
                    )}
                    
                    {/* Botón de cancelar para archivos en procesamiento */}
                    {file.status === 'uploading' && cancelFileProcessing && (
                      <Tooltip content="Cancelar procesamiento" placement="top">
                        <Button
                          size="sm"
                          variant="light"
                          color="danger"
                          isIconOnly
                          onClick={() => cancelFileProcessing(file.id, file.fileProcessId)}
                          className="hover:bg-red-50"
                        >
                          <FiXCircle className="w-4 h-4" />
                        </Button>
                      </Tooltip>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </CardBody>
      </Card>
    </div>
  );
};

export default FilesList;
