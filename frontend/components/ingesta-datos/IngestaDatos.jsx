import React from 'react';
import { Card, CardBody } from '@heroui/react';

// Hooks unificados
import { useFileUpload } from '@/hooks/ingesta-datos/useFileUpload';
import { useFileUploadProcess } from '@/hooks/ingesta-datos/useFileUploadProcess';

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
    confirmarTema,
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

    // Estados calculados
    pendingFiles,
    successFiles,
    errorFiles,
    filesWithoutExpediente
  } = useFileUpload();

  // El tema es de nombre libre: la pantalla solo exige que no falte; el servidor valida el resto (RF-06.52).
  const handleSaveClick = () => {
    setShowConfirmModal(true);
  };

  const handleConfirmUpload = () => {
    uploadFiles(files);
  };

  // Hook para manejar el proceso de subida y polling
  const { uploadFiles, restoreFromStorage, stopAllPollings, cancelFileProcessing } = useFileUploadProcess(setFiles, setUploading);

  // Al montar: intentar restaurar estado y reanudar polling si había archivos activos
  React.useEffect(() => {
    let restored = false;
    if (!restored) {
      restoreFromStorage();
      restored = true;
    }
    return () => {
      // Limpiar cualquier polling activo al salir de la vista
      stopAllPollings();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Guardar se deshabilita si no hay pendientes o alguno sigue sin tema
  const isButtonDisabled = uploading ||
                          pendingFiles === 0 ||
                          filesWithoutExpediente > 0;

  return (
    <div className="p-6 space-y-6 mx-auto">
      {/* Header con estadísticas */}
      <HeaderStats
        files={files}
        pendingFiles={pendingFiles}
        successFiles={successFiles}
        errorFiles={errorFiles}
      />

      {/* Área de carga principal */}
      <Card className="shadow-lg border border-gray-200">
        <CardBody className="p-6 lg:p-8">
          {/* Input de expediente y botones */}
          <ExpedienteInput
            expedienteNumero={expedienteNumero}
            setExpedienteNumero={setExpedienteNumero}
            confirmarTema={confirmarTema}
            handleSaveClick={handleSaveClick}
            isButtonDisabled={isButtonDisabled}
            uploading={uploading}
            pendingFiles={pendingFiles}
            filesWithoutExpediente={filesWithoutExpediente}
            files={files}
            setFiles={setFiles}
          />

          {/* Lista de archivos cargados */}
          <FilesList
            files={files}
            removeFile={removeFile}
            cancelFileProcessing={cancelFileProcessing}
          />

          {/* Zona de arrastre */}
          <DropZone
            dragZoneRef={dragZoneRef}
            fileInputRef={fileInputRef}
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
        onConfirm={handleConfirmUpload}
        files={files}
        pendingFiles={pendingFiles}
      />
    </div>
  );
};

export default IngestaDatos;
