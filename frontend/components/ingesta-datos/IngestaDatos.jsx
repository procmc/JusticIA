import React from 'react';
import { Card, CardBody } from '@heroui/react';
import { validarFormatoExpediente } from '@/utils/ingesta-datos/funciones';

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

  // Hook para manejar el proceso de subida y polling
  const { uploadFiles, restoreFromStorage } = useFileUploadProcess(setFiles, setUploading);

  // Al montar: intentar restaurar estado y reanudar polling si había archivos activos
  React.useEffect(() => {
    restoreFromStorage();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
        onConfirm={() => uploadFiles(files)}
        files={files}
        pendingFiles={pendingFiles}
        expedienteNumero={expedienteNumero}
      />
    </div>
  );
};

export default IngestaDatos;
