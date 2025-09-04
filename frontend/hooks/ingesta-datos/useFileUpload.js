import { useState, useCallback, useRef, useEffect } from 'react';
import { getAllowedFileExtensions } from '@/utils/ingesta-datos/funciones';

/**
 * Hook unificado para manejo de archivos con compatibilidad total del componente original
 */
export const useFileUpload = () => {
  // Referencias
  const fileInputRef = useRef(null);
  const dragZoneRef = useRef(null);
  
  // Estados simples
  const [uploading, setUploading] = useState(false);
  const [expedienteNumero, setExpedienteNumero] = useState('');
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [filesArray, setFilesArray] = useState([]);
  const [dragActive, setDragActive] = useState(false);

  // Configuración
  const allowedTypes = getAllowedFileExtensions();

  // Efecto para actualizar automáticamente el expediente de todos los archivos pendientes
  useEffect(() => {
    setFilesArray(prev => {
      // Actualizar TODOS los archivos pendientes con el expediente actual
      const updated = prev.map(file => 
        file.status === 'pending' 
          ? { ...file, expediente: expedienteNumero.trim() }
          : file
      );
      
      // Forzar actualización solo si hay cambios
      const hasChanges = prev.some((file, index) => 
        file.status === 'pending' && file.expediente !== updated[index]?.expediente
      );
      
      return hasChanges ? updated : prev;
    });
  }, [expedienteNumero]);

  // Manejadores de drag & drop
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
  }, []);

  const handleChange = useCallback((e) => {
    e.preventDefault();
    const selectedFiles = Array.from(e.target.files);
    handleFiles(selectedFiles);
  }, []);

  // Manejar archivos nuevos
  const handleFiles = useCallback((newFiles) => {
    const validFiles = newFiles.filter(file => {
      const extension = '.' + file.name.split('.').pop().toLowerCase();
      return allowedTypes.includes(extension);
    });

    if (validFiles.length > 0) {
      const filesWithMetadata = validFiles.map(file => ({
        id: Date.now() + Math.random(),
        file: file,
        name: file.name,
        size: file.size,
        type: file.type.startsWith('audio/') ? 'audio' : 'document',
        status: 'pending',
        expediente: expedienteNumero.trim(), // SIEMPRE usar el expediente principal actual
        progress: 0,
        message: '',
        fileProcessId: null,
        resultado: null
      }));

      setFilesArray(prev => [...prev, ...filesWithMetadata]);

      // Scroll automático hacia la zona de arrastre después de un breve delay
      setTimeout(() => {
        if (dragZoneRef.current) {
          dragZoneRef.current.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
          });
        }
      }, 100);
    }
  }, [allowedTypes, expedienteNumero]); // Incluir expedienteNumero en dependencias

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

  // Estados calculados - asegurar que nunca muestre input
  const pendingFiles = filesArray.filter(f => f.status === 'pending').length;
  const successFiles = filesArray.filter(f => f.status === 'success').length;
  const errorFiles = filesArray.filter(f => f.status === 'error').length;
  // Forzar que NO haya archivos sin expediente si hay expediente principal
  const filesWithoutExpediente = expedienteNumero.trim() 
    ? 0 
    : filesArray.filter(f => f.status === 'pending' && !f.expediente?.trim()).length;

  // Crear objeto files con dragActive y métodos de array
  const files = Object.assign(filesArray, {
    dragActive: dragActive
  });

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
