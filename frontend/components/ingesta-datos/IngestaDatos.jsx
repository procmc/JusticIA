import React from 'react';
import { Card, CardBody } from '@heroui/react';
import { validarFormatoExpediente } from '@/utils/ingesta-datos/funciones';
import ingestaService from '@/services/ingestaService';

// Hook unificado
import { useFileUpload } from '@/hooks/ingesta-datos/useFileUpload';

// Componentes separados
import HeaderStats from './HeaderStats';
import ExpedienteInput from './ExpedienteInput';
import FilesList from './FilesList';
import DropZone from './DropZone';
import UploadConfirmModal from './UploadConfirmModal';

const IngestaDatos = () => {
  // Usar el hook unificado que contiene toda la lógica
  const {
    // Estado
    files,
    setFiles,
    uploading,
    setUploading,
    expedienteNumero,
    setExpedienteNumero,
    showConfirmModal,
    setShowConfirmModal,
    
    // Referencias
    fileInputRef,
    dragZoneRef,
    
    // Funciones
    handleDrag,
    handleDrop,
    handleChange,
    removeFile,
    updateFileExpediente,
    
    // Estados calculados
    pendingFiles,
    successFiles,
    errorFiles,
    filesWithoutExpediente
  } = useFileUpload();

  const isExpedienteValid = validarFormatoExpediente(expedienteNumero);

  const handleSaveClick = () => {
    setShowConfirmModal(true);
  };

  const uploadFiles = async () => {
    console.log('📤 uploadFiles llamada desde IngestaDatos');
    console.log('📤 files:', files);
    console.log('📤 uploading state:', uploading);
    
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

  // Condiciones para deshabilitar el botón
  const isButtonDisabled = uploading || pendingFiles === 0 || filesWithoutExpediente > 0 || !expedienteNumero.trim() || !isExpedienteValid;

  return (
    <div className="p-6 space-y-6 mx-auto">
      {/* Header con estadísticas */}
      <HeaderStats
        files={files}
        pendingFiles={pendingFiles}
        successFiles={successFiles}
        errorFiles={errorFiles}
        expedienteNumero={expedienteNumero}
        isExpedienteValid={isExpedienteValid}
        uploading={uploading}
      />

      {/* Área de carga principal */}
      <Card className="shadow-lg border border-gray-200">
        <CardBody className="p-6 lg:p-8">
          {/* Input de expediente y botones */}
          <ExpedienteInput
            expedienteNumero={expedienteNumero}
            setExpedienteNumero={setExpedienteNumero}
            handleSaveClick={handleSaveClick}
            isButtonDisabled={isButtonDisabled}
            uploading={uploading}
            pendingFiles={pendingFiles}
            files={files}
            setFiles={setFiles}
          />

          {/* Lista de archivos cargados */}
          <FilesList
            files={files}
            updateFileExpediente={updateFileExpediente}
            removeFile={removeFile}
            expedienteNumero={expedienteNumero}
          />

          {/* Zona de arrastre */}
          <DropZone
            dragZoneRef={dragZoneRef}
            fileInputRef={fileInputRef}
            isExpedienteValid={isExpedienteValid}
            dragActive={files.dragActive}
            handleDrag={handleDrag}
            handleDrop={handleDrop}
            handleChange={handleChange}
            files={files}
            pendingFiles={pendingFiles}
          />
        </CardBody>
      </Card>

      {/* Modal de confirmación */}
      <UploadConfirmModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        onConfirm={uploadFiles}
        files={files}
        pendingFiles={pendingFiles}
        expedienteNumero={expedienteNumero}
      />
    </div>
  );
};

export default IngestaDatos;
