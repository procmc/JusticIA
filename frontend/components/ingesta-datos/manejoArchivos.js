import { useState } from 'react';
import { obtenerTipoArchivo } from './funciones';

export const usarManejoArchivos = () => {
  const [files, setFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);

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

  const handleFiles = (fileList, expedienteNumero = '') => {
    const newFiles = Array.from(fileList).map(file => ({
      id: Date.now() + Math.random(),
      file,
      name: file.name,
      size: file.size,
      type: obtenerTipoArchivo(file.name),
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

  const clearAllFiles = () => {
    setFiles([]);
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
    }, 2000);
  };

  // Estadísticas
  const pendingFiles = files.filter(f => f.status === 'pending').length;
  const successFiles = files.filter(f => f.status === 'success').length;
  const errorFiles = files.filter(f => f.status === 'error').length;
  const filesWithoutExpediente = files.filter(f => f.status === 'pending' && (!f.expediente || f.expediente.trim() === '')).length;

  return {
    files,
    dragActive,
    uploading,
    pendingFiles,
    successFiles,
    errorFiles,
    filesWithoutExpediente,
    handleDrag,
    handleDrop,
    handleChange,
    handleFiles,
    removeFile,
    updateFileExpediente,
    clearAllFiles,
    uploadFiles
  };
};
