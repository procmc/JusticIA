/**
 * Hook simplificado para subida y seguimiento de archivos con Celery
 * Mantiene persistencia en localStorage para continuar viendo progreso entre sesiones
 */
import { useRef } from 'react';
import ingestaService from '@/services/ingestaService';
import Toast from '@/components/ui/CustomAlert';
import { sanitizeErrorMessage, ErrorTypes } from '@/utils/fetchErrorHandler';

// Configuración
const PERSIST_KEY = 'ingesta_files';
const POLL_INTERVAL = 2000; // 2 segundos fijo
const MAX_NETWORK_RETRIES = 3;

// Estados terminales (alineados con backend)
const TERMINAL_STATES = ['completado', 'fallido', 'cancelado'];
const isTerminal = (status) => TERMINAL_STATES.includes(status?.toLowerCase());

/**
 * Limpiar objetos File para localStorage (no son serializables)
 */
const sanitizeForStorage = (files) => {
  return files.map(({ file, ...rest }) => rest);
};

/**
 * Truncar nombres de archivo largos para UI
 */
const truncateFileName = (fileName, maxLength = 30) => {
  if (!fileName || fileName.length <= maxLength) return fileName;
  
  const lastDot = fileName.lastIndexOf('.');
  if (lastDot === -1) return fileName.slice(0, maxLength - 3) + '...';
  
  const ext = fileName.slice(lastDot);
  const base = fileName.slice(0, lastDot);
  const availableLength = maxLength - ext.length - 3;
  
  return base.slice(0, availableLength) + '...' + ext;
};

export const useFileUploadProcess = (setFiles, setUploading) => {
  // Referencias para tracking de estado
  const processedFiles = useRef(new Set());  // IDs ya notificados con toast
  const activePollings = useRef(new Map()); // taskId -> { intervalId, retries }

  
  /**
   * Actualizar archivos y persistir en localStorage
   */
  const updateFiles = (updater) => {
    setFiles(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      
      // Persistir en localStorage
      try {
        const hasActiveFiles = next.some(f => 
          f.fileProcessId && !isTerminal(f.status)
        );
        
        if (hasActiveFiles) {
          localStorage.setItem(PERSIST_KEY, JSON.stringify(sanitizeForStorage(next)));
          setUploading(true);
        } else {
          localStorage.removeItem(PERSIST_KEY);
          setUploading(false);
        }
      } catch (error) {
        console.error('Error persistiendo en localStorage:', error);
      }
      
      return next;
    });
  };

  /**
   * Remover archivo completado exitosamente (con toast y delay)
   */
  const removeCompletedFile = (fileId, fileName) => {
    if (processedFiles.current.has(fileId)) return;
    
    processedFiles.current.add(fileId);
    
    Toast.success(
      '¡Archivo procesado!',
      `${truncateFileName(fileName)} se ha guardado exitosamente`
    );
    
    setTimeout(() => {
      updateFiles(prev => {
        const filtered = prev.filter(f => f.id !== fileId);
        if (filtered.length < prev.length) {
          processedFiles.current.delete(fileId);
        }
        return filtered;
      });
    }, 1500);
  };

  /**
   * Detener polling de una tarea específica
   */
  const stopPolling = (taskId) => {
    const polling = activePollings.current.get(taskId);
    if (polling?.intervalId) {
      clearInterval(polling.intervalId);
    }
    activePollings.current.delete(taskId);
  };


  /**
   * Iniciar polling para un archivo individual
   */
  const startPolling = (fileId, taskId) => {
    // Validaciones
    if (!taskId || !fileId) return;
    if (activePollings.current.has(taskId)) return; // Ya está en polling
    
    let networkRetries = 0;
    
    const pollFunction = async () => {
      try {
        const response = await ingestaService.consultarProgresoTarea(taskId);
        
        // Resetear contador de reintentos en éxito
        networkRetries = 0;
        
        const { status, progress, message, ready } = response;
        
        // Mapear estados del backend de forma inteligente
        let localProgress = progress || 0;
        let localMessage = message || 'Procesando...';
        
        // Determinar estado local basado en el progreso y estado del backend
        let localStatus = 'procesando'; // Default
        
        // Si el backend dice "pendiente" pero ya tenemos progreso local, mantener "procesando"
        if (status === 'pendiente' && localProgress < 5) {
          localStatus = 'pendiente';
        } else if (status === 'procesando' || localProgress > 0) {
          localStatus = 'procesando';
        }
        
        // Verificar estados terminales en orden: primero errores, luego éxito
        if (status === 'fallido' || status === 'cancelado') {
          localStatus = status; // Mantener 'fallido' o 'cancelado' tal cual
          localProgress = 0;
          
          const sanitized = sanitizeErrorMessage(localMessage, ErrorTypes.SERVER);
          
          // Obtener nombre del archivo del estado actual
          let fileName = 'Archivo';
          setFiles(prev => {
            const file = prev.find(f => f.id === fileId);
            if (file) fileName = file.name;
            return prev;
          });
          
          Toast.error(
            'Error en archivo',
            `${truncateFileName(fileName)}: ${sanitized}`
          );
          
          updateFiles(prev => prev.map(f => 
            f.id === fileId 
              ? { ...f, status: localStatus, progress: localProgress, message: sanitized }
              : f
          ));
          
          stopPolling(taskId);
          return;
        }
        
        if (status === 'completado' || (ready === true && status !== 'fallido' && status !== 'cancelado')) {
          localStatus = 'completado';
          localProgress = 100;
          localMessage = message || 'Procesado exitosamente';
          
          updateFiles(prev => prev.map(f => 
            f.id === fileId 
              ? { ...f, status: localStatus, progress: localProgress, message: localMessage }
              : f
          ));
          
          stopPolling(taskId);
          return;
        }
        
        // Estado en progreso - mantener estado coherente
        // No retroceder de "procesando" a "pendiente" si ya tenemos progreso
        updateFiles(prev => prev.map(f => {
          if (f.id === fileId) {
            // Si ya tenemos progreso > 5%, no volver a "pendiente"
            const shouldKeepProcessing = f.progress > 5 && status === 'pendiente';
            const finalStatus = shouldKeepProcessing ? 'procesando' : localStatus;
            
            return { 
              ...f, 
              status: finalStatus, 
              progress: Math.max(f.progress || 0, localProgress), // No retroceder progreso
              message: localMessage 
            };
          }
          return f;
        }));
        
      } catch (error) {
        networkRetries++;
        
        // Si es 404, la tarea no existe (error inmediato)
        if (error.message?.includes('404') || error.status === 404) {
          const errorMsg = 'La tarea no existe o fue cancelada';
          
          // Obtener nombre del archivo del estado actual
          let fileName = 'Archivo';
          setFiles(prev => {
            const file = prev.find(f => f.id === fileId);
            if (file) fileName = file.name;
            return prev;
          });
          
          Toast.error(
            'Error de seguimiento',
            `${truncateFileName(fileName)}: ${errorMsg}`
          );
          
          updateFiles(prev => prev.map(f => 
            f.id === fileId 
              ? { ...f, status: 'fallido', progress: 0, message: errorMsg }
              : f
          ));
          
          stopPolling(taskId);
          return;
        }
        
        // Para errores de red, reintentar hasta MAX_NETWORK_RETRIES
        if (networkRetries >= MAX_NETWORK_RETRIES) {
          const sanitized = sanitizeErrorMessage(
            error.message || 'Error de conexión',
            ErrorTypes.NETWORK
          );
          
          // Obtener nombre del archivo del estado actual
          let fileName = 'Archivo';
          setFiles(prev => {
            const file = prev.find(f => f.id === fileId);
            if (file) fileName = file.name;
            return prev;
          });
          
          Toast.error(
            'Error de conexión',
            `No se pudo consultar el estado de ${truncateFileName(fileName)}`
          );
          
          updateFiles(prev => prev.map(f => 
            f.id === fileId 
              ? { ...f, status: 'fallido', progress: 0, message: sanitized }
              : f
          ));
          
          stopPolling(taskId);
          return;
        }
        
        // Continuar reintentando (el intervalo ya está configurado)
        console.warn(`Error polling ${taskId}, reintento ${networkRetries}/${MAX_NETWORK_RETRIES}:`, error.message);
      }
    };
    
    // Ejecutar inmediatamente y luego cada POLL_INTERVAL
    pollFunction();
    const intervalId = setInterval(pollFunction, POLL_INTERVAL);
    
    activePollings.current.set(taskId, { intervalId, retries: 0 });
  };


  /**
   * Subir archivos y comenzar seguimiento
   */
  const uploadFiles = async (files) => {
    const listFiles = Array.isArray(files) ? files : Array.from(files || []);
    
    setUploading(true);
    
    try {
      // Validación: todos los archivos pendientes deben tener expediente
      const filesWithoutExpediente = listFiles.filter(f => 
        f.status === 'pendiente' && !f.expediente?.trim()
      );
      
      if (filesWithoutExpediente.length > 0) {
        Toast.error(
          'Error de validación',
          `${filesWithoutExpediente.length} archivo(s) sin número de expediente`
        );
        setUploading(false);
        return;
      }
      
      // Agrupar por expediente
      const filesByExpediente = listFiles.reduce((acc, file) => {
        if (file.status === 'pendiente' && file.expediente?.trim()) {
          const exp = file.expediente.trim();
          (acc[exp] = acc[exp] || []).push(file);
        }
        return acc;
      }, {});
      
      if (Object.keys(filesByExpediente).length === 0) {
        Toast.warning(
          'Sin archivos válidos',
          'No hay archivos pendientes para procesar'
        );
        setUploading(false);
        return;
      }
      
      Toast.info(
        'Subida iniciada',
        'Los archivos se están procesando en segundo plano'
      );
      
      // Procesar cada expediente
      for (const [expediente, expedienteFiles] of Object.entries(filesByExpediente)) {
        // Marcar como procesando
        updateFiles(prev => prev.map(f =>
          expedienteFiles.some(ef => ef.id === f.id)
            ? { ...f, status: 'procesando', progress: 5, message: 'Subiendo...', fileProcessId: null }
            : f
        ));
        
        try {
          const archivosReales = expedienteFiles.map(f => f.file);
          const resultado = await ingestaService.subirArchivos(expediente, archivosReales);
          
          const taskIds = resultado?.task_ids || [];
          
          if (taskIds.length !== expedienteFiles.length) {
            throw new Error(`Número de task_ids (${taskIds.length}) no coincide con archivos (${expedienteFiles.length})`);
          }
          
          // Asignar taskId a cada archivo y comenzar polling
          updateFiles(prev => prev.map(f => {
            const index = expedienteFiles.findIndex(ef => ef.id === f.id);
            if (index !== -1 && index < taskIds.length) {
              const taskId = taskIds[index];
              
              // Iniciar polling para este archivo
              setTimeout(() => startPolling(f.id, taskId), 100);
              
              return {
                ...f,
                fileProcessId: taskId,
                progress: 10,
                message: 'En cola...'
              };
            }
            return f;
          }));
          
        } catch (error) {
          console.error('Error subiendo archivos:', error);
          
          const sanitized = sanitizeErrorMessage(
            error.message || 'Error en subida',
            ErrorTypes.NETWORK
          );
          
          Toast.error(
            'Error en la subida',
            `No se pudieron subir los archivos del expediente ${expediente}`
          );
          
          updateFiles(prev => prev.map(f =>
            expedienteFiles.some(ef => ef.id === f.id)
              ? { ...f, status: 'fallido', progress: 0, message: sanitized }
              : f
          ));
        }
      }
      
    } finally {
      setUploading(false);
    }
  };


  /**
   * Restaurar estado desde localStorage y reanudar polling
   * Se ejecuta al montar el componente
   */
  const restoreFromStorage = () => {
    try {
      const stored = localStorage.getItem(PERSIST_KEY);
      if (!stored) return;
      
      const files = JSON.parse(stored);
      if (!Array.isArray(files) || files.length === 0) return;
      
      // Restaurar archivos en el estado
      setFiles(files);
      
      // Reanudar polling para archivos activos
      const activeFiles = files.filter(f => 
        f.fileProcessId && !isTerminal(f.status)
      );
      
      if (activeFiles.length > 0) {
        setUploading(true);
        
        activeFiles.forEach(file => {
          startPolling(file.id, file.fileProcessId);
        });
        
        console.log(`Restaurados ${activeFiles.length} archivos en progreso`);
      }
      
    } catch (error) {
      console.error('Error restaurando desde localStorage:', error);
      localStorage.removeItem(PERSIST_KEY);
    }
  };

  /**
   * Cancelar procesamiento de un archivo (modo híbrido: optimista con confirmación)
   */
  const cancelFileProcessing = async (fileId, fileProcessId, fileName) => {
    try {
      // 1. Detener polling inmediatamente (UI responsiva)
      if (fileProcessId) {
        stopPolling(fileProcessId);
      }
      
      // 2. Actualizar UI como cancelado (optimista)
      updateFiles(prev => prev.map(f =>
        f.id === fileId
          ? { ...f, status: 'cancelado', progress: 0, message: 'Cancelado' }
          : f
      ));
      
      // 3. Intentar cancelar en backend con timeout de 2s
      if (fileProcessId) {
        const cancelPromise = ingestaService.cancelarProcesamiento(fileProcessId);
        const timeoutPromise = new Promise(resolve => setTimeout(() => resolve({ timeout: true }), 2000));
        
        try {
          const result = await Promise.race([cancelPromise, timeoutPromise]);
          
          if (result?.timeout) {
            console.warn(`Backend tardó >2s en responder cancelación de ${fileProcessId}, pero UI ya actualizada`);
          } else {
            console.log(`Cancelación confirmada por backend para ${fileProcessId}`);
          }
        } catch (error) {
          console.warn('Error cancelando en backend:', error);
        }
      }
      
      // 4. Mensaje simple al usuario (siempre se muestra)
      Toast.info('Cancelado', `${truncateFileName(fileName || 'Archivo')} cancelado`);
      
    } catch (error) {
      console.error('Error cancelando:', error);
    }
  };

  /**
   * Detener todos los pollings activos (útil para cleanup)
   */
  const stopAllPollings = () => {
    activePollings.current.forEach((polling) => {
      if (polling.intervalId) {
        clearInterval(polling.intervalId);
      }
    });
    activePollings.current.clear();
  };

  return {
    uploadFiles,
    truncateFileName,
    removeCompletedFile,
    cancelFileProcessing,
    restoreFromStorage,
    stopAllPollings,
    processedFiles
  };
};