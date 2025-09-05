/**
 * Componente para la lista de archivos seleccionados
 * Actualizado para usar utils centralizadas
 */
import React from 'react';
import { Card, CardHeader, CardBody, Divider, Chip, Input, Progress } from '@heroui/react';
import { motion, AnimatePresence } from 'framer-motion';
import { FiX, FiFolder } from 'react-icons/fi';
import { formatearTamano } from '@/utils/ingesta-datos/funciones';
import { getFileIcon, getStatusIcon, getStatusColor } from '@/utils/ingesta-datos/iconos';

const FilesList = ({
  files,
  updateFileExpediente,
  removeFile,
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
                  className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 hover:bg-gray-50 border-b border-gray-100 last:border-b-0 transition-colors space-y-3 sm:space-y-0"
                >
                  {/* Parte principal del archivo */}
                  <div className="flex items-start space-x-4 flex-1 min-w-0">
                    {getFileIcon(file.type)}
                    <div className="flex-1 min-w-0 space-y-2">
                      {/* Nombre y estado */}
                      <div className="flex flex-col sm:flex-row sm:items-center space-y-1 sm:space-y-0 sm:space-x-2">
                        <p className="text-sm font-medium text-gray-900 truncate pr-2">
                          {file.name}
                        </p>
                        <Chip
                          color={getStatusColor(file.status)}
                          size="sm"
                          variant="flat"
                        >
                          {file.status === 'pending' && 'Pendiente'}
                          {file.status === 'uploading' && 'Guardando...'}
                          {file.status === 'success' && 'Completado'}
                          {file.status === 'error' && 'Error'}
                        </Chip>
                      </div>

                      {/* Información adicional */}
                      <div className="flex flex-col space-y-2">
                        <div className="flex items-center space-x-4">
                          <p className="text-xs text-gray-500">
                            {formatearTamano(file.size)}
                          </p>

                          {/* Solo mostrar input si NO hay expediente principal Y el archivo no tiene expediente */}
                          {file.status === 'pending' && !expedienteNumero?.trim() && !file.expediente?.trim() && (
                            <Input
                              size="sm"
                              placeholder="Núm. expediente"
                              value={file.expediente || ''}
                              onChange={(e) => updateFileExpediente(file.id, e.target.value)}
                              className="w-full sm:w-48"
                              startContent={<FiFolder className="text-gray-400 w-3 h-3" />}
                              classNames={{
                                input: "text-xs",
                                inputWrapper: "h-8 min-h-8"
                              }}
                            />
                          )}

                          {/* Mostrar chip si hay expediente (del principal o individual) */}
                          {file.status === 'pending' && (expedienteNumero?.trim() || file.expediente?.trim()) && (
                            <Chip color="primary" size="sm" variant="flat">
                              {file.expediente || expedienteNumero}
                            </Chip>
                          )}

                          {file.status === 'success' && file.expediente && (
                            <Chip color="primary" size="sm" variant="flat">
                              {file.expediente}
                            </Chip>
                          )}
                        </div>

                        {/* Barra de progreso para archivos en subida */}
                        {file.status === 'uploading' && (
                          <div className="w-full">
                            <Progress
                              value={file.progress}
                              size="sm"
                              color="primary"
                              className="w-full"
                            />
                            {file.message && (
                              <p className="text-xs text-gray-500 mt-1 truncate">
                                {file.message}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Acciones y estado (lado derecho) */}
                  <div className="flex items-center justify-between sm:justify-end space-x-2 ml-8 sm:ml-0">
                    {/* Información adicional para archivos completados */}
                    {file.status === 'success' && file.resultado && (
                      <div className="text-xs text-green-600 truncate max-w-[150px] sm:max-w-[200px]">
                        ✓ Procesado
                      </div>
                    )}
                    
                    {/* Información de error */}
                    {file.status === 'error' && file.message && (
                      <div className="text-xs text-red-600 truncate max-w-[150px] sm:max-w-[200px]" title={file.message}>
                        ⚠ {file.message}
                      </div>
                    )}
                    
                    {/* Botón de eliminar solo para archivos pendientes */}
                    {file.status === 'pending' && (
                      <button
                        onClick={() => removeFile(file.id)}
                        className="p-2 text-gray-400 hover:text-red-500 transition-colors rounded-lg hover:bg-red-50 flex-shrink-0"
                      >
                        <FiX className="w-4 h-4" />
                      </button>
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
