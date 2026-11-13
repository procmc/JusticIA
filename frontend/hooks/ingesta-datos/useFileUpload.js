import { useState, useCallback, useRef, useMemo } from 'react';
import { getAllowedFileExtensions, obtenerTipoArchivo } from '@/utils/ingesta-datos/ingestaUtils';
import Toast from '@/components/ui/CustomAlert';

/**
 * Hook unificado para manejo de archivos con compatibilidad total del componente original
 */
export const useFileUpload = () => {
  // Referencias
  const fileInputRef = useRef(null);
  const dragZoneRef = useRef(null);
  
  // Estados simples
  const [uploading, setUploading] = useState(false);
  const [expedienteNumero, setExpedienteNumero] = useState(''); // el campo «Tema» (nombre heredado)
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [filesArray, setFilesArray] = useState([]);
  const [dragActive, setDragActive] = useState(false);

  // Configuración
  const allowedTypes = getAllowedFileExtensions();

  // Manejar archivos nuevos (definir ANTES de los handlers que lo usan)
  const handleFiles = useCallback((newFiles) => {
    // Validar extensiones permitidas
    const validFiles = newFiles.filter(file => {
      const extension = '.' + file.name.split('.').pop().toLowerCase();
      return allowedTypes.includes(extension);
    });

    // Usar setFilesArray con función para acceder al estado actual
    setFilesArray(currentFiles => {
      if (validFiles.length > 0) {
        const filesWithMetadata = validFiles.map(file => ({
          id: Date.now() + Math.random(),
          file: file,
          name: file.name,
          size: file.size,
          type: obtenerTipoArchivo(file.name),
          status: 'pendiente',
          progress: 0,
          message: '',
          fileProcessId: null,
          resultado: null
        }));

        // Scroll automático hacia la zona de arrastre después de un breve delay
        setTimeout(() => {
          if (dragZoneRef.current) {
            dragZoneRef.current.scrollIntoView({ 
              behavior: 'smooth', 
              block: 'center' 
            });
          }
        }, 100);

        return [...currentFiles, ...filesWithMetadata];
      }

      return currentFiles; // No hay archivos para agregar
    });
  }, [allowedTypes]); // Solo allowedTypes como dependencia

  // Manejadores de drag & drop (definir DESPUÉS de handleFiles)
  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    handleFiles(droppedFiles);
  }, [handleFiles]);

  const handleChange = useCallback((e) => {
    e.preventDefault();
    const selectedFiles = Array.from(e.target.files);
    handleFiles(selectedFiles);
    
    // Resetear el input para permitir seleccionar el mismo archivo nuevamente
    if (e.target) {
      e.target.value = '';
    }
  }, [handleFiles]);

  // Funciones de gestión
  const removeFile = useCallback((fileId) => {
    setFilesArray(prev => prev.filter(f => f.id !== fileId));
  }, []);

  const updateFileExpediente = useCallback((fileId, expediente) => {
    setFilesArray(prev => prev.map(f => 
      f.id === fileId ? { ...f, expediente } : f
    ));
  }, []);

  const setFiles = useCallback((newFiles) => {
    if (typeof newFiles === 'function') {
      setFilesArray(newFiles);
    } else {
      setFilesArray(newFiles);
    }
  }, []);

  // Estados calculados
  const pendingFiles = filesArray.filter(f => f.status === 'pendiente').length;
  const successFiles = filesArray.filter(f => f.status === 'completado').length;
  const errorFiles = filesArray.filter(f => f.status === 'fallido' || f.status === 'cancelado').length;
  
  // Pendientes sin tema: todos, mientras el campo esté vacío (RF-06.50, FF1)
  const filesWithoutExpediente = expedienteNumero.trim() === '' ? pendingFiles : 0;

  // RF-06.50 (FF1): un pendiente no guarda tema propio; toma el del campo en este momento, así la fila, la confirmación y el envío
  // coinciden con lo que se ve. Los demás (ya enviados) conservan el tema con el que se enviaron.
  const files = useMemo(() => {
    const tema = expedienteNumero.trim();
    return Object.assign(
      filesArray.map(f => (f.status === 'pendiente' ? { ...f, expediente: tema } : f)),
      { dragActive }
    );
  }, [filesArray, expedienteNumero, dragActive]);

  return {
    // Estados principales
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
    
    // Configuración
    allowedTypes,
    
    // Manejadores de eventos
    handleDrag,
    handleDrop,
    handleChange,
    handleFiles,
    
    // Gestión de archivos
    removeFile,
    updateFileExpediente,
    
    // Estados calculados
    pendingFiles,
    successFiles,
    errorFiles,
    filesWithoutExpediente
  };
};

export default useFileUpload;
