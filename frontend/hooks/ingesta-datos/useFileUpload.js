import { useState, useCallback, useRef, useEffect } from 'react';
import { getAllowedFileExtensions } from '@/utils/ingesta-datos/ingestaUtils';

/**
 * Hook unificado para manejo de archivos con compatibilidad total del componente original
 */
export const useFileUpload = () => {
  // Referencias
  const fileInputRef = useRef(null);
  const dragZoneRef = useRef(null);
  const expedienteRef = useRef(''); // Referencia para el expediente actual
  
  // Estados simples
  const [uploading, setUploading] = useState(false);
  const [expedienteNumero, setExpedienteNumero] = useState('');
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [filesArray, setFilesArray] = useState([]);
  const [dragActive, setDragActive] = useState(false);

  // Configuración
  const allowedTypes = getAllowedFileExtensions();

  // Mantener la referencia sincronizada con el estado
  useEffect(() => {
    expedienteRef.current = expedienteNumero;
  }, [expedienteNumero]);

  // Efecto simple para sincronizar expediente cuando cambia
  useEffect(() => {
    const expedienteTrimmed = expedienteNumero.trim();
    
    if (expedienteTrimmed) {
      setFilesArray(prev => prev.map(file => 
        file.status === 'pending' 
          ? { ...file, expediente: expedienteTrimmed }
          : file
      ));
    }
  }, [expedienteNumero]); // Solo cuando cambia el expediente

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
    // Validar extensiones permitidas
    const validFiles = newFiles.filter(file => {
      const extension = '.' + file.name.split('.').pop().toLowerCase();
      return allowedTypes.includes(extension);
    });

    // Usar setFilesArray con función para acceder al estado actual
    setFilesArray(currentFiles => {
      // Validar límite de 10 archivos usando el estado actual
      const currentFileCount = currentFiles.filter(f => f.status !== 'removed').length;
      const maxFiles = 10;
      const availableSlots = maxFiles - currentFileCount;
      
      if (availableSlots <= 0) {
        alert(`Ya tienes el máximo de ${maxFiles} archivos. Elimina algunos antes de agregar más.`);
        return currentFiles; // No cambiar el estado
      }
      
      const filesToAdd = validFiles.slice(0, availableSlots);
      
      if (validFiles.length > availableSlots) {
        alert(`Solo se pueden agregar ${availableSlots} archivos más. Se agregaron los primeros ${filesToAdd.length} archivos.`);
      }

      if (filesToAdd.length > 0) {
        // Usar la referencia que siempre tiene el valor actual
        const currentExpediente = expedienteRef.current.trim();
        
        const filesWithMetadata = filesToAdd.map(file => ({
          id: Date.now() + Math.random(),
          file: file,
          name: file.name,
          size: file.size,
          type: file.type.startsWith('audio/') ? 'audio' : 'document',
          status: 'pending',
          expediente: currentExpediente,
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
  const pendingFiles = filesArray.filter(f => f.status === 'pending').length;
  const successFiles = filesArray.filter(f => f.status === 'success').length;
  const errorFiles = filesArray.filter(f => f.status === 'error').length;
  
  // Calcular archivos sin expediente
  const filesWithoutExpediente = filesArray.filter(f => {
    return f.status === 'pending' && (!f.expediente || f.expediente.trim() === '');
  }).length;

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
