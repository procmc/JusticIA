import React, { useState, useRef } from 'react';
import { Card, CardBody, CardHeader, Button, Progress, Chip, Divider, Input } from '@heroui/react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FiUploadCloud,
  FiFile,
  FiMusic,
  FiX,
  FiCheck,
  FiAlertCircle,
  FiDownload,
  FiFolder,
  FiSave,
  FiLoader
} from 'react-icons/fi';
import {
  IoCloudUpload,
  IoDocument,
  IoCheckmarkCircle,
  IoWarning
} from 'react-icons/io5';
import { PiBroomLight } from 'react-icons/pi';
import ConfirmModal from '@/components/ui/ConfirmModal';
import { validarFormatoExpediente, formatearTamano } from './funciones';
import ingestaService from '../../services/ingestaService';

const IngestaDatosCorregido = () => {
  const [files, setFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [expedienteNumero, setExpedienteNumero] = useState('');
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const fileInputRef = useRef(null);
  const dragZoneRef = useRef(null);

  // Tipos de archivos permitidos
  const allowedTypes = {
    documents: ['.pdf', '.doc', '.docx', '.rtf', '.txt'],
    audio: ['.mp3', '.wav', '.m4a', '.ogg']
  };

  const getFileType = (fileName) => {
    const extension = '.' + fileName.split('.').pop().toLowerCase();
    if (allowedTypes.documents.includes(extension)) return 'document';
    if (allowedTypes.audio.includes(extension)) return 'audio';
    return 'unknown';
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files);
    }
  };

  const handleFiles = (fileList) => {
    const newFiles = Array.from(fileList).map(file => ({
      id: Date.now() + Math.random(),
      file,
      name: file.name,
      size: file.size,
      type: getFileType(file.name),
      status: 'pending', // pending, uploading, success, error
      progress: 0,
      expediente: expedienteNumero
    }));

    setFiles(prev => [...prev, ...newFiles]);
    
    // Scroll automático a la lista de archivos después de cargar archivos
    setTimeout(() => {
      // Si hay archivos, hacer scroll a la lista de archivos
      if (newFiles.length > 0) {
        const fileListElement = document.querySelector('[data-files-list]');
        if (fileListElement) {
          fileListElement.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
          });
        }
      }
    }, 100);
  };

  const removeFile = (id) => {
    setFiles(prev => prev.filter(file => file.id !== id));
  };

  const updateFileExpediente = (id, newExpediente) => {
    setFiles(prev => prev.map(f =>
      f.id === id ? { ...f, expediente: newExpediente } : f
    ));
  };

  const isExpedienteValid = validarFormatoExpediente(expedienteNumero);

  const handleSaveClick = () => {
    setShowConfirmModal(true);
  };

  const uploadFiles = async () => {
    setUploading(true);

    // Agrupar archivos por expediente
    const filesByExpediente = {};
    files.forEach(file => {
      if (file.status === 'pending' && file.expediente?.trim()) {
        const exp = file.expediente.trim();
        if (!filesByExpediente[exp]) {
          filesByExpediente[exp] = [];
        }
        filesByExpediente[exp].push(file);
      }
    });

    // Procesar cada grupo de expediente
    for (const [expediente, expedienteFiles] of Object.entries(filesByExpediente)) {
      // Actualizar estado a uploading para archivos de este expediente
      setFiles(prev => prev.map(f =>
        expedienteFiles.some(ef => ef.id === f.id) 
          ? { ...f, status: 'uploading', progress: 0, fileProcessId: null } 
          : f
      ));

      try {
        // Obtener archivos reales
        const archivosReales = expedienteFiles.map(f => f.file);

        // Hacer la petición real - ahora devuelve IDs individuales
        const resultado = await ingestaService.subirArchivos(expediente, archivosReales);
        console.log('Respuesta del servidor:', resultado);

        // Asignar IDs individuales a cada archivo
        if (resultado && resultado.file_process_ids) {
          setFiles(prev => prev.map(f => {
            const fileIndex = expedienteFiles.findIndex(ef => ef.id === f.id);
            if (fileIndex !== -1 && fileIndex < resultado.file_process_ids.length) {
              return { 
                ...f, 
                fileProcessId: resultado.file_process_ids[fileIndex],
                progress: 10,
                message: 'Procesando...'
              };
            }
            return f;
          }));

          // Iniciar polling para cada archivo
          iniciarPollingArchivos(expedienteFiles, resultado.file_process_ids);
        }

      } catch (error) {
        console.error('Error subiendo archivos:', error);
        
        // Marcar archivos de este expediente como error
        setFiles(prev => prev.map(f =>
          expedienteFiles.some(ef => ef.id === f.id) 
            ? { ...f, status: 'error', progress: 0, message: 'Error en subida' } 
            : f
        ));
      }
    }

    setUploading(false);
  };

  // Nueva función para polling individual
  const iniciarPollingArchivos = (expedienteFiles, fileProcessIds) => {
    const polling = setInterval(async () => {
      try {
        const estados = await ingestaService.consultarEstadoArchivos(fileProcessIds);
        
        let todosCompletos = true;

        estados.forEach((estado, index) => {
          if (estado.success && estado.data) {
            const statusData = estado.data;
            const archivoLocal = expedienteFiles[index];

            setFiles(prev => prev.map(f => {
              if (f.id === archivoLocal.id) {
                const actualizado = {
                  ...f,
                  progress: statusData.progress || 0,
                  message: statusData.message || '',
                };

                if (statusData.status === 'completado') {
                  actualizado.status = 'success';
                  actualizado.progress = 100;
                  actualizado.resultado = statusData.resultado;
                } else if (statusData.status === 'error') {
                  actualizado.status = 'error';
                  actualizado.progress = 0;
                  actualizado.message = statusData.message || 'Error en procesamiento';
                } else {
                  todosCompletos = false;
                }

                return actualizado;
              }
              return f;
            }));
          } else {
            todosCompletos = false;
          }
        });

        // Si todos están completos, detener polling
        if (todosCompletos) {
          clearInterval(polling);
          
          // Limpiar después de 3 segundos
          setTimeout(() => {
            setFiles([]);
            setExpedienteNumero('');
          }, 3000);
        }

      } catch (error) {
        console.error('Error en polling:', error);
        clearInterval(polling);
      }
    }, 2000); // Consultar cada 2 segundos

    // Limpiar polling después de 5 minutos máximo
    setTimeout(() => {
      clearInterval(polling);
    }, 300000);
  };

  const getFileIcon = (type) => {
    switch (type) {
      case 'document':
        return <FiFile className="w-6 h-6 text-blue-500" />;
      case 'audio':
        return <FiMusic className="w-6 h-6 text-purple-500" />;
      default:
        return <FiFile className="w-6 h-6 text-gray-500" />;
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return <FiCheck className="w-5 h-5 text-green-500" />;
      case 'error':
        return <FiAlertCircle className="w-5 h-5 text-red-500" />;
      case 'uploading':
        return <FiLoader className="w-5 h-5 text-blue-500 animate-spin" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'success':
        return 'success';
      case 'error':
        return 'danger';
      case 'uploading':
        return 'primary';
      default:
        return 'default';
    }
  };

  const pendingFiles = files.filter(f => f.status === 'pending').length;
  const successFiles = files.filter(f => f.status === 'success').length;
  const errorFiles = files.filter(f => f.status === 'error').length;
  const filesWithoutExpediente = files.filter(f => f.status === 'pending' && (!f.expediente || f.expediente.trim() === '')).length;

  // Condiciones para deshabilitar el botón
  const isButtonDisabled = uploading || pendingFiles === 0 || filesWithoutExpediente > 0 || !expedienteNumero.trim() || !isExpedienteValid;

  return (
    <div className="p-6 space-y-6  mx-auto">
      {/* Header estandarizado con estadísticas siempre visibles */}
      <Card className="bg-primary text-white shadow-lg border-none">
        <CardBody className="p-4 sm:p-6 lg:p-8">
          <div className="space-y-6">
            {/* Fila superior: Título y estado del expediente */}
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3 sm:gap-4">
                <div className="p-2 sm:p-3 bg-white/15 rounded-xl border border-white/20 flex-shrink-0">
                  <IoCloudUpload className="text-2xl sm:text-3xl lg:text-4xl text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-white mb-1 sm:mb-2 truncate">
                    Ingesta de Datos
                  </h1>
                  <p className="text-white/80 text-sm sm:text-base">
                    Carga y procesamiento de documentos jurídicos
                  </p>
                </div>
              </div>

              {/* Indicadores de estado en la esquina superior derecha */}
              <div className="flex items-center gap-3">
                {/* Estado del expediente */}
                {expedienteNumero && (
                  <div className="flex items-center gap-2 bg-white/15 px-4 py-2 rounded-lg border border-white/30">
                    {isExpedienteValid ? (
                      <>
                        <IoCheckmarkCircle className="text-emerald-400 text-sm" />
                        <div className="flex items-center gap-1.5">
                          <span className="text-white/90 font-semibold text-sm">Expediente</span>
                          <span className="text-white/70 text-xs font-medium uppercase">Válido</span>
                        </div>
                      </>
                    ) : (
                      <>
                        <IoWarning className="text-yellow-400 text-sm" />
                        <div className="flex items-center gap-1.5">
                          <span className="text-white/90 font-semibold text-sm">Expediente</span>
                          <span className="text-white/70 text-xs font-medium uppercase">Inválido</span>
                        </div>
                      </>
                    )}
                  </div>
                )}

                {/* Indicador de proceso de subida */}
                {uploading && (
                  <div className="flex items-center gap-2 bg-white/15 px-4 py-2 rounded-lg border border-white/30">
                    <FiLoader className="text-white/90 text-sm animate-spin" />
                    <div className="flex items-center gap-1.5">
                      <span className="text-white/90 font-semibold text-sm">Procesando</span>
                      <span className="text-white/70 text-xs font-medium uppercase">Archivos</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Estadísticas siempre visibles */}
            <div className="pt-2">
              <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                {/* Total de archivos */}
                <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                  <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-blue-400 flex-shrink-0"></div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-white/90 font-semibold text-sm">{files.length}</span>
                    <span className="text-white/70 text-xs font-medium uppercase">Archivos</span>
                  </div>
                </div>

                {/* Archivos pendientes */}
                <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                  <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-yellow-400 flex-shrink-0"></div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-white/90 font-semibold text-sm">{pendingFiles}</span>
                    <span className="text-white/70 text-xs font-medium uppercase">Pendientes</span>
                  </div>
                </div>

                {/* Archivos completados */}
                <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                  <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-emerald-400 flex-shrink-0"></div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-white/90 font-semibold text-sm">{successFiles}</span>
                    <span className="text-white/70 text-xs font-medium uppercase">Completados</span>
                  </div>
                  {files.length > 0 && (
                    <div className="px-1.5 py-0.5 bg-emerald-500/20 rounded-full border border-emerald-400/30 flex-shrink-0">
                      <span className="text-emerald-200 text-xs font-bold">{Math.round((successFiles / files.length) * 100)}%</span>
                    </div>
                  )}
                </div>

                {/* Archivos con error */}
                <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                  <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-red-400 flex-shrink-0"></div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-white/90 font-semibold text-sm">{errorFiles}</span>
                    <span className="text-white/70 text-xs font-medium uppercase">Errores</span>
                  </div>
                  {files.length > 0 && (
                    <div className="px-1.5 py-0.5 bg-red-500/20 rounded-full border border-red-400/30 flex-shrink-0">
                      <span className="text-red-200 text-xs font-bold">{Math.round((errorFiles / files.length) * 100)}%</span>
                    </div>
                  )}
                </div>

                {/* Tamaño total */}
                <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                  <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-purple-400 flex-shrink-0"></div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-white/90 font-semibold text-sm">
                      {files.length > 0 ? formatearTamano(files.reduce((total, archivo) => total + (archivo.size || 0), 0)) : '0 B'}
                    </span>
                    <span className="text-white/70 text-xs font-medium uppercase">Tamaño Total</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Área de carga principal */}
      <Card className="shadow-lg border border-gray-200">
        <CardBody className="p-6 lg:p-8">
          {/* Input de expediente y botón guardar alineados con estilos de búsqueda similares */}
          
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

          {/* Lista de archivos cargados - Posicionada arriba del área de carga */}
          {files.length > 0 && (
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
                          className={`flex items-center justify-between p-4 hover:bg-gray-50 border-b border-gray-100 last:border-b-0 transition-colors ${file.status === 'pending' && (!file.expediente || file.expediente.trim() === '')
                            ? 'bg-orange-50 border-orange-200'
                            : ''
                            }`}
                        >
                          <div className="flex items-center space-x-4 flex-1">
                            {getFileIcon(file.type)}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center space-x-2">
                                <p className="text-sm font-medium text-gray-900 truncate">
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
                              <div className="flex items-center space-x-4 mt-2">
                                <p className="text-xs text-gray-500">
                                  {formatearTamano(file.size)}
                                </p>
                                {file.status === 'pending' && (
                                  <div className="flex items-center space-x-2">
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
                                  </div>
                                )}
                                {file.status === 'success' && file.expediente && (
                                  <Chip color="primary" size="sm" variant="flat">
                                    {file.expediente}
                                  </Chip>
                                )}
                                {file.status === 'uploading' && (
                                  <div className="flex-1 max-w-xs">
                                    <Progress
                                      value={file.progress}
                                      size="sm"
                                      color="primary"
                                      className="max-w-md"
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

                          <div className="flex items-center space-x-2">
                            {getStatusIcon(file.status)}
                            
                            {/* Información adicional para archivos completados */}
                            {file.status === 'success' && file.resultado && (
                              <div className="text-xs text-green-600 truncate max-w-[200px]">
                                ✓ ID: {file.resultado.documento_id || 'Procesado'}
                              </div>
                            )}
                            
                            {/* Información de error */}
                            {file.status === 'error' && file.message && (
                              <div className="text-xs text-red-600 truncate max-w-[200px]" title={file.message}>
                                ⚠ {file.message}
                              </div>
                            )}
                            
                            {file.status === 'pending' && (
                              <button
                                onClick={() => removeFile(file.id)}
                                className="p-2 text-gray-400 hover:text-red-500 transition-colors rounded-lg hover:bg-red-50"
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
          )}

          {/* Zona de arrastre mejorada */}
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
                  </div>
                )}
              </div>

              {/* Formatos soportados - simple */}
              <div className="mt-6 text-xs text-gray-500 text-center">
                Formatos soportados: PDF, DOC, DOCX, RTF, TXT, MP3, WAV, M4A, OGG
              </div>
            </motion.div>

            <input
              ref={fileInputRef}
              type="file"
              multiple
              onChange={handleChange}
              accept={[...allowedTypes.documents, ...allowedTypes.audio].join(',')}
              className="hidden"
            />
          </div>
        </CardBody>
      </Card>

      {/* Modal de confirmación */}
      <ConfirmModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        title="Confirmar Guardado de Archivos"
        description={
          <div className="space-y-4 text-left">
            {/* Warning al inicio */}
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex items-start space-x-3">
                <FiAlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
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
                  <FiFolder className="w-4 h-4 text-blue-600" />
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
                              <FiFolder className="w-3 h-3 text-gray-400" />
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
        onConfirm={uploadFiles}
        icon={<FiUploadCloud className="w-6 h-6" />}
        size="lg"
        showIcon={true}
        centered={true}
      />
    </div>
  );
};

export default IngestaDatosCorregido;
