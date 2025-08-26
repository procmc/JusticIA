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
import ConfirmModal from '@/components/ui/ConfirmModal';
import { validarFormatoExpediente, formatearTamano } from './funciones';

const IngestaDatosCorregido = () => {
  const [files, setFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [expedienteNumero, setExpedienteNumero] = useState('');
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const fileInputRef = useRef(null);

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
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (file.status !== 'pending') continue;

      // Validar que tenga número de expediente
      if (!file.expediente || file.expediente.trim() === '') {
        setFiles(prev => prev.map(f => 
          f.id === file.id ? { ...f, status: 'error', progress: 0 } : f
        ));
        continue;
      }

      // Actualizar estado a uploading
      setFiles(prev => prev.map(f => 
        f.id === file.id ? { ...f, status: 'uploading', progress: 0 } : f
      ));

      try {
        // Simular progreso de carga
        for (let progress = 0; progress <= 100; progress += 10) {
          await new Promise(resolve => setTimeout(resolve, 100));
          setFiles(prev => prev.map(f => 
            f.id === file.id ? { ...f, progress } : f
          ));
        }

        // Marcar como exitoso
        setFiles(prev => prev.map(f => 
          f.id === file.id ? { ...f, status: 'success', progress: 100 } : f
        ));

      } catch (error) {
        setFiles(prev => prev.map(f => 
          f.id === file.id ? { ...f, status: 'error', progress: 0 } : f
        ));
      }
    }

    setUploading(false);
    
    // Reiniciar el formulario después de completar todas las subidas
    setTimeout(() => {
      setFiles([]);
      setExpedienteNumero('');
    }, 2000);
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
    <div className="p-4 max-w-6xl mx-auto">
      {/* Área de carga principal */}
      <Card className="mb-4">
        <CardBody className="p-6">
          {/* Header dentro de la tarjeta */}
          <div className="mb-4">
            <div className="flex items-center space-x-3 mb-3">
              <FiUploadCloud className="w-8 h-8 text-blue-600" />
              <h1 className="text-2xl font-bold text-tituloSeccion">
                Ingesta de Datos
              </h1>
            </div>
            
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="space-y-3">
                <p className="text-sm text-gray-700">
                  Incorpora documentos legales y archivos de audio al sistema de conocimiento de JusticIA
                </p>
                <div className="flex items-start space-x-3 text-blue-700">
                  <FiAlertCircle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                  <p className="text-sm">
                    <span className="font-medium">Requisito:</span> Cada archivo debe estar asociado a un número de expediente para su correcta organización.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Input de expediente compacto y botón integrado */}
          <div className="flex flex-col sm:flex-row gap-3 mb-4 sm:items-start">
            <div className="flex-1 max-w-xs">
              <Input
                label="Num. Expediente"
                labelPlacement='outside'
                placeholder="98-003287-0166-LA"
                value={expedienteNumero}
                onChange={(e) => setExpedienteNumero(e.target.value)}
                startContent={<FiFolder className="text-xl text-default-400 pointer-events-none shrink-0" />}
                size="md"
                variant="bordered"
                radius="md"
                color='primary'
                description="Formato: AA-NNNNNN-OOOO-MM (Año-Consecutivo-Oficina-Materia)"
                isRequired
                classNames={{
                  input: "placeholder:text-gray-400",
                }}
              />
            </div>
            <div className="pt-6">
              <Button
                color="primary"
                onPress={handleSaveClick}
                disabled={isButtonDisabled}
                isLoading={uploading}
                size="md"
                radius="lg"
                className={`min-w-[100px] font-medium transition-all duration-200 ${
                  isButtonDisabled 
                    ? 'opacity-50 cursor-not-allowed bg-gray-300 text-gray-500' 
                    : 'bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 shadow-md hover:shadow-lg transform hover:scale-105 hover:-translate-y-0.5'
                }`}
                startContent={!uploading && <FiSave className="w-5 h-5" />}
              >
                {uploading 
                  ? 'Guardando...' 
                  : pendingFiles > 0
                    ? `Guardar ${pendingFiles}`
                    : 'Guardar'
                }
              </Button>
            </div>
          </div>

          <div
            className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 ${
              !isExpedienteValid
                ? 'border-gray-200 bg-gray-50 opacity-50 cursor-not-allowed'
                : dragActive 
                  ? 'border-blue-500 bg-blue-50' 
                  : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
            }`}
            onDragEnter={isExpedienteValid ? handleDrag : undefined}
            onDragLeave={isExpedienteValid ? handleDrag : undefined}
            onDragOver={isExpedienteValid ? handleDrag : undefined}
            onDrop={isExpedienteValid ? handleDrop : undefined}
          >
            {!isExpedienteValid && (
              <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-90 rounded-xl z-10">
                <div className="text-center">
                  <FiAlertCircle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
                  <p className="text-sm font-medium text-gray-700 mb-1">
                    Área bloqueada
                  </p>
                  <p className="text-xs text-gray-500">
                    Ingrese un número de expediente válido para continuar
                  </p>
                </div>
              </div>
            )}
            <motion.div
              animate={{ scale: dragActive ? 1.04 : 1 }}
              transition={{ duration: 0.2 }}
              className="flex flex-col items-center space-y-3"
            >
              <div className={`p-3 rounded-full ${dragActive ? 'bg-blue-100' : 'bg-gray-100'}`}>
                <FiUploadCloud className={`w-10 h-10 ${dragActive ? 'text-blue-600' : 'text-gray-400'}`} />
              </div>
              
              <div className="space-y-1">
                <h3 className="text-lg font-semibold text-gray-700">
                  {dragActive ? '¡Suelta los archivos aquí!' : 'Arrastra archivos aquí'}
                </h3>
                <p className="text-sm text-gray-500">
                  o{' '}
                  <button
                    onClick={() => isExpedienteValid && fileInputRef.current?.click()}
                    className={`font-medium underline ${
                      isExpedienteValid 
                        ? 'text-blue-600 hover:text-blue-700 cursor-pointer' 
                        : 'text-gray-400 cursor-not-allowed'
                    }`}
                    disabled={!isExpedienteValid}
                  >
                    examina tu dispositivo
                  </button>
                </p>
              </div>

              <div className="flex flex-wrap gap-2 justify-center">
                <Chip color="primary" variant="flat" size="sm">PDF</Chip>
                <Chip color="primary" variant="flat" size="sm">DOC/DOCX</Chip>
                <Chip color="primary" variant="flat" size="sm">RTF</Chip>
                <Chip color="primary" variant="flat" size="sm">TXT</Chip>
                <Chip color="secondary" variant="flat" size="sm">MP3</Chip>
                <Chip color="secondary" variant="flat" size="sm">WAV</Chip>
                <Chip color="secondary" variant="flat" size="sm">M4A</Chip>
                <Chip color="secondary" variant="flat" size="sm">OGG</Chip>
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

      {/* Resumen de archivos */}
      {files.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          <Card>
            <CardBody className="text-center p-3">
              <div className="text-xl font-bold text-blue-600">{pendingFiles}</div>
              <div className="text-xs text-gray-600">Pendientes</div>
            </CardBody>
          </Card>
          <Card>
            <CardBody className="text-center p-3">
              <div className="text-xl font-bold text-green-600">{successFiles}</div>
              <div className="text-xs text-gray-600">Completados</div>
            </CardBody>
          </Card>
          <Card>
            <CardBody className="text-center p-3">
              <div className="text-xl font-bold text-red-600">{errorFiles}</div>
              <div className="text-xs text-gray-600">Con error</div>
            </CardBody>
          </Card>
        </div>
      )}

      {/* Lista de archivos */}
      {files.length > 0 && (
        <Card>
          <CardHeader className="flex justify-between items-center p-4">
            <h3 className="text-base font-semibold text-tituloSeccion">Archivos Seleccionados</h3>
            <div className="flex gap-2">
              <Button
                color="danger"
                variant="flat"
                size="sm"
                onClick={() => setFiles([])}
                disabled={uploading}
              >
                Limpiar Todo
              </Button>
            </div>
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
                    className={`flex items-center justify-between p-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0 ${
                      file.status === 'pending' && (!file.expediente || file.expediente.trim() === '') 
                        ? 'bg-orange-50 border-orange-200' 
                        : ''
                    }`}
                  >
                    <div className="flex items-center space-x-3 flex-1">
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
                                className="w-40"
                                startContent={<FiFolder className="text-gray-400 w-3 h-3" />}
                                classNames={{
                                  input: "text-xs",
                                  inputWrapper: "h-7 min-h-7"
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
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {getStatusIcon(file.status)}
                      {file.status === 'pending' && (
                        <button
                          onClick={() => removeFile(file.id)}
                          className="p-1 text-gray-400 hover:text-red-500 transition-colors"
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
      )}

      {/* Información adicional */}
      <Card className="mt-8">
        <CardBody className="p-4">
          <h3 className="text-base font-bold mb-3 flex items-center space-x-2 text-tituloSeccion">
            <FiDownload className="w-4 h-4" />
            <span>Tipos de archivo soportados</span>
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="font-medium text-gray-800 mb-2 flex items-center space-x-2">
                <FiFile className="w-4 h-4 text-blue-500" />
                <span>Documentos</span>
              </h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• PDF - Documentos legales, sentencias, resoluciones</li>
                <li>• DOC/DOCX - Documentos de texto</li>
                <li>• RTF - Formato de texto enriquecido</li>
                <li>• TXT - Archivos de texto plano</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-gray-800 mb-2 flex items-center space-x-2">
                <FiMusic className="w-4 h-4 text-purple-500" />
                <span>Audio</span>
              </h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• MP3 - Audiencias, declaraciones</li>
                <li>• WAV - Grabaciones de alta calidad</li>
                <li>• M4A - Formato de audio comprimido</li>
                <li>• OGG - Formato de audio libre</li>
              </ul>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Modal de confirmación */}
      <ConfirmModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        title="Confirmar Guardado de Archivos"
        description={
          <div className="space-y-2 text-left">
            {/* Warning al inicio */}
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg mb-6">
              <div className="flex items-start space-x-2">
                <FiAlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-amber-800">
                  <p className="font-medium mb-1">Importante:</p>
                  <p>Esta acción asociará permanentemente los archivos a sus respectivos expedientes. Verifique cuidadosamente que toda la información sea correcta antes de continuar.</p>
                </div>
              </div>
            </div>

            <div className="text-gray-700">
              <p className="mb-3">
                ¿Está seguro que desea guardar <span className="font-semibold text-blue-600">{pendingFiles} archivo{pendingFiles !== 1 ? 's' : ''}</span> en el sistema?
              </p>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                <div className="flex items-center space-x-2">
                  <FiFolder className="w-4 h-4 text-blue-600" />
                  <span className="font-medium text-blue-800">Expediente Principal:</span>
                  <span className="font-mono font-bold text-blue-700">{expedienteNumero}</span>
                </div>
              </div>
            </div>
            
            <div>
              <h4 className="font-medium text-gray-800 mb-3 flex items-center space-x-2 mt-6">
                <FiFile className="w-4 h-4" />
                <span>Archivos a procesar:</span>
              </h4>
              
              <div className="max-h-60 overflow-y-auto custom-blue-scroll space-y-2 border border-gray-200 rounded-lg p-3 bg-gray-50">
                {files
                  .filter(f => f.status === 'pending')
                  .map((file, index) => (
                    <div 
                      key={file.id}
                      className="flex items-center justify-between p-2 bg-white rounded border border-gray-100 hover:border-gray-200 transition-colors"
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
