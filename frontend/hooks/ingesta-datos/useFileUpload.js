import { useState, useCallback, useRef } from 'react';
import { getAllowedFileExtensions, obtenerTipoArchivo } from '@/utils/ingesta-datos/ingestaUtils';
import Toast from '@/components/ui/CustomAlert';

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
  const [expedienteNumero, setExpedienteNumeroEstado] = useState('');
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [filesArray, setFilesArray] = useState([]);
  const [dragActive, setDragActive] = useState(false);

  // Configuración
  const allowedTypes = getAllowedFileExtensions();

  // El campo del tema (llamado `expedienteNumero` por herencia). La referencia se actualiza al mismo tiempo que el estado, para
  // que agregar archivos justo después de escribir tome el texto actual (RF-06.50).
  const setExpedienteNumero = useCallback((valor) => {
    expedienteRef.current = valor;
    setExpedienteNumeroEstado(valor);
  }, []);

  // RF-06.50: el tema de cada archivo se fija al agregarlo; cambiar el campo después NO altera los pendientes ya agregados.
  // Confirmar el campo (Enter o foco perdido) solo da el tema a los pendientes que siguen sin él.
  const confirmarTema = useCallback(() => {
    const tema = expedienteRef.current.trim();
    if (!tema) return;
    setFilesArray(prev => (
      prev.some(f => f.status === 'pendiente' && !f.expediente?.trim())
        ? prev.map(f => (f.status === 'pendiente' && !f.expediente?.trim() ? { ...f, expediente: tema } : f))
        : prev
    ));
  }, []);

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
        // Usar la referencia que siempre tiene el valor actual
        const currentExpediente = expedienteRef.current.trim();
        
        const filesWithMetadata = validFiles.map(file => ({
          id: Date.now() + Math.random(),
          file: file,
          name: file.name,
          size: file.size,
          type: obtenerTipoArchivo(file.name),
          status: 'pendiente',
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
  
  // Calcular archivos sin expediente
  const filesWithoutExpediente = filesArray.filter(f => {
    return f.status === 'pendiente' && (!f.expediente || f.expediente.trim() === '');
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
    confirmarTema,
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
