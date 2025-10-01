/**
 * Hook personalizado para manejar la subida de archivos con polling individual
 */
import { useRef } from 'react';
import ingestaService from '@/services/ingestaService';
import Toast from '@/components/ui/CustomAlert';

export const useFileUploadProcess = (setFiles, setUploading) => {
  const processedFiles = useRef(new Set());            // ids internos ya completados
  const activePollings = useRef(new Map());            // fileProcessId -> intervalId
  const persistKey = 'ingesta_files_v1';               // clave storage

  // Helpers utilitarios compactos
  const isTerminal = (s) => ['success', 'error'].includes((s || '').toLowerCase());
  const sanitizeForStorage = (arr) => Array.isArray(arr) ? arr.map(({ file, ...meta }) => meta) : arr;
  const hasActiveFlags = (f) => {
    if (!f) return false;
    const st = (f.status || '').toLowerCase();
    return !isTerminal(st) && (st === 'pending' || st === 'uploading' || !!f.fileProcessId);
  };

  // Helper para actualizar files y persistir en localStorage
  const updateFiles = (updater) => setFiles(prev => {
    const next = typeof updater === 'function' ? updater(prev) : updater;
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const serialized = sanitizeForStorage(next);
        localStorage.setItem(persistKey, JSON.stringify(serialized));
        const active = Array.isArray(next) && next.some(hasActiveFlags);
        if (typeof setUploading === 'function') setUploading(active);
        if (!active) try { localStorage.removeItem(persistKey); } catch (_) { /* ignore */ }
      }
    } catch (_) { /* ignore */ }
    return next;
  });

  // Función para truncar nombres de archivo largos
  const truncateFileName = (fileName, maxLength = 30) => {
    if (!fileName || fileName.length <= maxLength) return fileName;
    const lastDot = fileName.lastIndexOf('.');
    if (lastDot === -1) return fileName.slice(0, maxLength - 3) + '...';
    const ext = fileName.slice(lastDot + 1);
    const base = fileName.slice(0, lastDot);
    return base.slice(0, maxLength - ext.length - 4) + '...' + ext;
  };

  const removeCompletedFile = (fileId, fileName) => {
    // Evitar duplicados
    if (processedFiles.current.has(fileId)) {
      return;
    }

    processedFiles.current.add(fileId);

    // Mostrar toast de éxito con nombre truncado
    const displayName = truncateFileName(fileName);
    Toast.success(
      '¡Archivo procesado!',
      `${displayName} se ha guardado exitosamente`
    );

    // Remover el archivo después de un breve delay para que se vea el toast
    setTimeout(() => {
      updateFiles(prev => {
        const filtered = prev.filter(f => f.id !== fileId);
        // Si se removió el archivo, también remover del Set
        if (filtered.length < prev.length) {
          processedFiles.current.delete(fileId);
        }
        return filtered;
      });
    }, 1500);
  };

  // Detener polling específico
  const stopPolling = (fileProcessId) => {
    const pollingRef = activePollings.current.get(fileProcessId);
    if (!pollingRef) return;
    if (pollingRef.current) {
      clearTimeout(pollingRef.current);
    }
    activePollings.current.delete(fileProcessId);
  };

  // Crear polling para un archivo (id de proceso + metadatos locales)
  const startPollingForFile = (archivoLocal, fileProcessId) => {
    if (!fileProcessId || activePollings.current.has(fileProcessId) || isTerminal(archivoLocal.status)) return;

    // Contador de reintentos para manejar 404s temporales
    let retryCount = 0;
    let consecutive404s = 0;
    const maxRetries = 5;
    const max404s = 3;
    let currentInterval = 1500; // Empezar con 1.5 segundos inicial
    const maxInterval = 8000;   // Máximo 8 segundos

    const pollFunction = async () => {
      try {
        const estados = await ingestaService.consultarEstadoArchivos([fileProcessId]);
        const estado = estados[0];

        // Resetear contador de reintentos en éxito
        retryCount = 0;
        
        // Si obtenemos datos exitosos, ajustar intervalo
        if (estado && estado.success && estado.data) {
          currentInterval = Math.max(1500, currentInterval * 0.9); // Reducir gradualmente
          consecutive404s = 0;
          
          const statusData = estado.data;
          
          // 🆕 Verificar si fue auto-limpiada
          if (statusData.was_auto_cleaned) {
            // La tarea fue auto-limpiada, usar el estado final guardado
            const finalStatus = statusData.status;
            const wasSuccessful = statusData.status === 'completed';
            
            updateFiles(prev => prev.map(f => {
              if (f.id === archivoLocal.id) {
                return { 
                  ...f, 
                  status: wasSuccessful ? 'success' : 'error',
                  progress: wasSuccessful ? 100 : 0, 
                  message: statusData.message || (wasSuccessful ? 'Procesado completamente' : 'Error en procesamiento'),
                  was_auto_cleaned: true
                };
              }
              return f;
            }));
            stopPolling(fileProcessId);
            return;
          }
          
          // Continuar con lógica normal para tareas activas
          const isGranular = estado.isGranular;

          let reachedTerminal = false;
          let finalStatus = '';
          let progressValue = 0;
          let messageText = '';

          // Procesar respuesta según el tipo (granular vs legacy)
          if (isGranular) {
            // Nuevo sistema de progreso granular (estados en español desde backend)
            finalStatus = statusData.status;
            progressValue = statusData.progress || 0;
            messageText = statusData.message || '';

            // Estados ya vienen en español: pendiente, procesando, completado, fallido, cancelado
            if (finalStatus === 'completado') {
              reachedTerminal = true;
              progressValue = 100;
            } else if (finalStatus === 'fallido') {
              reachedTerminal = true;
              finalStatus = 'error';
              progressValue = 0;
            } else if (finalStatus === 'cancelado') {
              reachedTerminal = true;
              finalStatus = 'error';
              progressValue = 0;
            } else if (finalStatus === 'procesando') {
              // Mantener como está
            } else if (finalStatus === 'pendiente') {
              // Mantener como está
            }
          } else {
            // Sistema legacy
            finalStatus = statusData.status;
            progressValue = statusData.progress || 0;
            messageText = statusData.message || '';

            // Para legacy, si está "Procesado" considerarlo como completado
            if (finalStatus?.toLowerCase() === 'procesado') {
              reachedTerminal = true;
              finalStatus = 'completado';
              progressValue = 100;
            }
          }

          updateFiles(prev => prev.map(f => {
            if (f.id === archivoLocal.id) {
              const base = { 
                ...f, 
                progress: progressValue, 
                message: messageText,
                isGranular: isGranular,
                metadata: isGranular ? statusData.metadata : f.metadata
              };

              if (finalStatus === 'completado') {
                reachedTerminal = true;
                return { 
                  ...base, 
                  status: 'success', 
                  progress: 100, 
                  resultado: statusData.resultado || statusData.metadata,
                  metadata: isGranular ? statusData.metadata : f.metadata
                };
              }
              
              if (finalStatus === 'error') {
                reachedTerminal = true;
                const msg = messageText || 'Error en procesamiento';
                const displayName = truncateFileName(archivoLocal.name);
                Toast.error('Error en archivo', `${displayName}: ${msg}`);
                return { ...base, status: 'error', progress: 0, message: msg };
              }

              // Estados en progreso (pendiente o procesando)
              return { ...base, status: 'uploading' };
            }
            return f;
          }));

          if (reachedTerminal) {
            stopPolling(fileProcessId);
            return;
          }
        } 
        
        // Manejar 404s específicamente
        if (estado && estado.is404) {
          consecutive404s++;
          
          if (consecutive404s >= max404s) {
            // ⚠️ Después de varios 404s, la tarea probablemente no existe o fue auto-limpiada
            // NO asumimos que fue exitosa, la marcamos como desconocida
            updateFiles(prev => prev.map(f => {
              if (f.id === archivoLocal.id) {
                return { 
                  ...f, 
                  status: 'error', 
                  progress: 0, 
                  message: 'No se pudo verificar el estado del archivo. Puede haber sido procesado pero el seguimiento expiró.' 
                };
              }
              return f;
            }));
            stopPolling(fileProcessId);
            return;
          }
          
          // Incrementar intervalo para 404s pero continuar
          currentInterval = Math.min(currentInterval * 1.3, maxInterval);
        }
        
        // Agendar siguiente poll con intervalo dinámico
        setTimeout(pollFunction, currentInterval);
        
      } catch (error) {
        retryCount++;
        consecutive404s = 0; // Resetear contador de 404s en errores reales
        
        // Para errores de red, reintentar con backoff exponencial
        if (retryCount <= maxRetries) {
          currentInterval = Math.min(currentInterval * 1.8, maxInterval);
          setTimeout(pollFunction, currentInterval);
          return;
        }
        
        // Después de muchos errores, marcar como error y detener
        if (!isTerminal(archivoLocal.status)) {
          const displayName = truncateFileName(archivoLocal.name);
          Toast.error('Error de conexión', `No se pudo consultar el estado de ${displayName}`);
          updateFiles(prev => prev.map(f => {
            if (f.id === archivoLocal.id) {
              return { ...f, status: 'error', progress: 0, message: 'Error de conexión persistente' };
            }
            return f;
          }));
        }
        stopPolling(fileProcessId);
      }
    };

    // Ejecutar primera consulta inmediatamente
    pollFunction();
    
    // Guardar una referencia para poder cancelar
    const timeoutRef = { current: null };
    activePollings.current.set(fileProcessId, timeoutRef);
  };

  // Iniciar polling para lote de archivos
  const iniciarPollingArchivos = (expedienteFiles, fileProcessIds) => {
    expedienteFiles.forEach((archivoLocal, idx) => {
      const fileProcessId = fileProcessIds[idx];
      startPollingForFile(archivoLocal, fileProcessId);
    });
  };

  // Detener todos los pollings activos (p.ej. al desmontar componente si se implementa)
  const stopAllPollings = () => { 
    activePollings.current.forEach((pollingRef) => {
      if (pollingRef && pollingRef.current) {
        clearTimeout(pollingRef.current);
      }
    }); 
    activePollings.current.clear();
  };

  const uploadFiles = async (files) => {
    // Normalizar archivos (aceptar tanto array como objeto-array del hook)
    const listFiles = Array.isArray(files) ? files : Array.from(files || []);

    setUploading(true);
    try {
      // Validación previa: verificar que todos los archivos pendientes tengan expediente
      const filesWithoutExpediente = listFiles.filter(file => 
        file && file.status === 'pending' && (!file.expediente || !file.expediente.trim())
      );
      
      if (filesWithoutExpediente.length > 0) {
        Toast.error(
          'Error de validación',
          `${filesWithoutExpediente.length} archivo(s) no tienen número de expediente asignado`
        );
        setUploading(false);
        return;
      }

      // Notificación de inicio
      Toast.info(
        'Subida iniciada',
        'Los archivos se están procesando en segundo plano'
      );

      // Agrupar archivos por expediente
      const filesByExpediente = listFiles.reduce((acc, file) => {
        if (file && file.status === 'pending' && file.expediente?.trim()) {
          const exp = file.expediente.trim();
          (acc[exp] ||= []).push(file);
        }
        return acc;
      }, {});

      // Verificar si hay archivos para procesar
      if (Object.keys(filesByExpediente).length === 0) {
        Toast.warning(
          'Sin archivos válidos',
          'No hay archivos válidos con número de expediente para procesar'
        );
        setUploading(false);
        return;
      }

      // Procesar cada grupo de expediente
      for (const [expediente, expedienteFiles] of Object.entries(filesByExpediente)) {

        // Actualizar estado a uploading para archivos de este expediente
        updateFiles(prev => prev.map(f =>
          expedienteFiles.some(ef => ef.id === f.id)
            ? { ...f, status: 'uploading', progress: 0, fileProcessId: null }
            : f
        ));

        try {
          // Obtener archivos reales
          const archivosReales = expedienteFiles.map(f => f.file);

          const resultado = await ingestaService.subirArchivos(expediente, archivosReales);

          // Asignar IDs individuales a cada archivo (task_ids de Celery)
          const taskIds = resultado?.task_ids || resultado?.file_process_ids || [];
          
          if (taskIds.length > 0) {
            updateFiles(prev => prev.map(f => {
              const fileIndex = expedienteFiles.findIndex(ef => ef.id === f.id);
              if (fileIndex !== -1 && fileIndex < taskIds.length) {
                return {
                  ...f,
                  fileProcessId: taskIds[fileIndex],
                  progress: 10,
                  message: 'Procesando...'
                };
              }
              return f;
            }));
            // Iniciar polling para cada archivo
            iniciarPollingArchivos(expedienteFiles, taskIds);
          }

        } catch (error) {
          console.error('Error subiendo archivos del expediente', expediente, ':', error);

          // Mostrar toast de error general
          Toast.error(
            'Error en la subida',
            `No se pudieron subir los archivos del expediente ${expediente}`
          );

          // Marcar archivos de este expediente como error
          updateFiles(prev => prev.map(f =>
            expedienteFiles.some(ef => ef.id === f.id)
              ? { ...f, status: 'error', progress: 0, message: error.message || 'Error en subida' }
              : f
          ));
        }
      }
    } finally {
      // Asegurar que uploading se limpie siempre
      setUploading(false);
    }
  };

  // Restaurar desde localStorage y reanudar polling si es necesario
  const restoreFromStorage = () => {
    try {
      if (typeof window === 'undefined' || !window.localStorage) return;
      const raw = localStorage.getItem(persistKey);
      if (!raw) return;
      const stored = JSON.parse(raw);
      if (!Array.isArray(stored) || stored.length === 0) return;

      // Deduplicar por fileProcessId para evitar múltiples entradas del mismo proceso
      const seen = new Set();
      const deduped = stored.filter(f => {
        if (!f?.fileProcessId) return true;
        if (seen.has(f.fileProcessId)) return false;
        seen.add(f.fileProcessId);
        return true;
      });

      // Rehidratar estado de archivos sin duplicados
      setFiles(deduped);

      // Detectar archivos activos (tienen fileProcessId y no están en success/error)
      const activosByExp = deduped.reduce((acc, f) => {
        if (f.fileProcessId && !isTerminal(f.status)) {
          const exp = f.expediente || 'NO_EXP';
          (acc[exp] ||= []).push(f);
        }
        return acc;
      }, {});

      const todasLasIds = [];
      Object.entries(activosByExp).forEach(([exp, archivos]) => {
        const ids = archivos.map(a => a.fileProcessId).filter(Boolean);
        if (ids.length > 0) {
          iniciarPollingArchivos(archivos, ids);
          todasLasIds.push(...ids);
        }
      });

      // Marcar uploading si hay polls activos
      setUploading(todasLasIds.length > 0);
    } catch (e) {
      console.error('Error restaurando estado de archivos:', e);
    }
  };

  // Función para cancelar el procesamiento de un archivo
  const cancelFileProcessing = async (fileId, fileProcessId) => {
    try {
      // Detener el polling inmediatamente
      if (fileProcessId) {
        stopPolling(fileProcessId);
      }
      
      // Marcar el archivo como cancelado
      updateFiles(prev => prev.map(f => {
        if (f.id === fileId) {
          return { 
            ...f, 
            status: 'error', 
            progress: 0, 
            message: 'Cancelado por el usuario' 
          };
        }
        return f;
      }));

      // Intentar cancelar en el backend si es posible
      if (fileProcessId) {
        try {
          await ingestaService.cancelarProcesamiento(fileProcessId);
        } catch (error) {
          // No es crítico si falla la cancelación en el backend
        }
      }

      Toast.warning(
        'Procesamiento cancelado',
        'El archivo ha sido cancelado exitosamente'
      );

    } catch (error) {
      console.error('Error cancelando procesamiento:', error);
      Toast.error('Error', 'No se pudo cancelar el procesamiento');
    }
  };

  return {
    uploadFiles,
    truncateFileName,
    removeCompletedFile,
    cancelFileProcessing,
    iniciarPollingArchivos,
    processedFiles,
    restoreFromStorage,
    stopAllPollings
  };
};