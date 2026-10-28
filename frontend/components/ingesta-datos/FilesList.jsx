/**
 * Componente para la lista de archivos seleccionados
 * Versión simplificada con spinner y botón de cancelar
 */
import React from 'react';
import { Card, CardHeader, CardBody, Divider, Chip, Spinner, Button, Tooltip, Progress, Alert } from '@heroui/react';
import { motion, AnimatePresence } from 'framer-motion';
import { FiX, FiXCircle } from 'react-icons/fi';
import { formatearTamano } from '@/utils/ingesta-datos/ingestaUtils';
import { getFileIcon, getStatusColor } from '@/utils/ingesta-datos/iconos';

const FilesList = ({
  files,
  removeFile,
  cancelFileProcessing
}) => {
  // Avisos de carga ya cerrados por el usuario (RF-05.23): se cierran a mano, no desaparecen solos.
  const [avisosCerrados, setAvisosCerrados] = React.useState([]);

  if (files.length === 0) {
    return null;
  }

  // Un aviso por respuesta (por tema); todos los archivos de ese tema traen el mismo.
  const avisos = [];
  files.forEach((f) => {
    if (f.avisoCarga && !avisosCerrados.includes(f.avisoCarga.id) && !avisos.some(a => a.id === f.avisoCarga.id)) {
      avisos.push(f.avisoCarga);
    }
  });

  return (
    <div className="mb-6" data-files-list>
      <Card className="shadow-lg border border-gray-200">
        <CardHeader className="flex justify-between items-center p-6 bg-gray-50">
          <h3 className="text-lg font-semibold text-gray-800">Archivos Seleccionados</h3>
        </CardHeader>
        <Divider />
        <CardBody className="p-0">
          {avisos.length > 0 && (
            <div className="space-y-2 p-4 pb-2">
              {avisos.map((aviso) => (
                <Alert
                  key={aviso.id}
                  color={aviso.tipo}
                  variant="flat"
                  isClosable
                  onClose={() => setAvisosCerrados(prev => [...prev, aviso.id])}
                  classNames={{
                    base: 'min-w-0',
                    mainWrapper: 'min-w-0',
                    title: 'text-default-800 font-medium min-w-0 [overflow-wrap:anywhere]',
                    description: 'text-default-700 min-w-0 [overflow-wrap:anywhere]',
                  }}
                  title={`Tema ${aviso.tema}: ${aviso.mensaje}`}
                  description={aviso.motivos.length > 0 && (
                    <ul className="list-none space-y-0.5 min-w-0 [overflow-wrap:anywhere]">
                      {aviso.motivos.map((motivo, i) => <li key={i}>{motivo}</li>)}
                    </ul>
                  )}
                />
              ))}
            </div>
          )}
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
                          {file.status === 'pendiente' && 'Pendiente'}
                          {file.status === 'procesando' && 'Procesando'}
                          {file.status === 'completado' && 'Completado'}
                          {file.status === 'fallido' && 'Error'}
                          {file.status === 'cancelado' && 'Cancelado'}
                          {file.status === 'rechazado' && 'Rechazado'}
                        </Chip>
                      </div>

                      {/* Información adicional */}
                      <div className="flex items-center space-x-3 text-xs text-gray-500">
                        <span>{formatearTamano(file.size)}</span>

                        {/* Tema fijado al agregar el archivo (RF-06.50); sin campo editable por fila */}
                        {file.expediente?.trim() && (
                          <Chip color="primary" size="sm" variant="flat" classNames={{ content: 'break-all' }}>
                            {file.expediente}
                          </Chip>
                        )}
                      </div>

                      {/* Barra de progreso para archivos en procesamiento */}
                      {file.status === 'procesando' && (
                        <div className="space-y-2 mt-2">
                          {/* Línea superior: Spinner + Mensaje + Porcentaje */}
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <Spinner size="sm" color="primary" />
                              <span className="text-sm text-gray-600">
                                {file.message || 'Procesando archivo...'}
                              </span>
                            </div>
                            <span className="text-xs font-bold text-blue-600">
                              {Math.round(file.progress || 0)}%
                            </span>
                          </div>
                          
                          {/* Barra de progreso visual */}
                          <Progress 
                            value={file.progress || 0}
                            color="primary"
                            size="sm"
                            className="w-full"
                            aria-label="Progreso de procesamiento"
                          />
                        </div>
                      )}

                      {/* Mensaje de error */}
                      {(file.status === 'fallido' || file.status === 'cancelado' || file.status === 'rechazado') && file.message && (
                        <div className="text-xs text-red-600 mt-2">
                          {file.message}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Acciones */}
                  <div className="flex items-center space-x-2 flex-shrink-0 ml-4">
                    {/* Botón de eliminar para archivos pendientes, completados, con error o cancelados */}
                    {(file.status === 'pendiente' || file.status === 'completado' || file.status === 'fallido' || file.status === 'cancelado' || file.status === 'rechazado') && (
                      <Tooltip content="Quitar archivo" placement="top">
                        <Button
                          size="sm"
                          variant="light"
                          color="danger"
                          isIconOnly
                          onPress={() => removeFile(file.id)}
                        >
                          <FiX className="w-4 h-4" />
                        </Button>
                      </Tooltip>
                    )}
                    
                    {/* Botón de cancelar para archivos en procesamiento */}
                    {file.status === 'procesando' && cancelFileProcessing && (
                      <Tooltip content="Cancelar procesamiento" placement="top">
                        <Button
                          size="sm"
                          variant="light"
                          color="danger"
                          isIconOnly
                          onPress={() => cancelFileProcessing(file.id, file.fileProcessId, file.name)}
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
