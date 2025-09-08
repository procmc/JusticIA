import { useState, useCallback, useRef, useEffect } from 'react';
import { getAllowedFileExtensions } from '@/utils/ingesta-datos/ingestaUtils';

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
      
      // Siempre devolver el array actualizado si hay archivos pendientes
      const hasPendingFiles = prev.some(file => file.status === 'pending');
      
      return hasPendingFiles ? updated : prev;
    });
  }, [expedienteNumero]);

  // Efecto adicional para asegurar que archivos recién agregados tengan expediente
  useEffect(() => {
    if (expedienteNumero.trim()) {
     
      setFilesArray(prev => {
        const needsUpdate = prev.some(file => 
          file.status === 'pending' && file.expediente !== expedienteNumero.trim()
        );
        
        if (needsUpdate) {
         
          return prev.map(file => 
            file.status === 'pending' 
              ? { ...file, expediente: expedienteNumero.trim() }
              : file
          );
        }
        
        return prev;
      });
    }
  }, [filesArray.length, expedienteNumero]);

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

    // Validar límite de 10 archivos
    const currentFileCount = files.filter(f => f.status !== 'removed').length;
    const maxFiles = 10;
    const availableSlots = maxFiles - currentFileCount;
    
    if (availableSlots <= 0) {
      alert(`Ya tienes el máximo de ${maxFiles} archivos. Elimina algunos antes de agregar más.`);
      return;
    }
    
    const filesToAdd = validFiles.slice(0, availableSlots);
    
    if (validFiles.length > availableSlots) {
      alert(`Solo se pueden agregar ${availableSlots} archivos más. Se agregaron los primeros ${filesToAdd.length} archivos.`);
    }

    if (filesToAdd.length > 0) {
      const filesWithMetadata = filesToAdd.map(file => ({
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
