/**
 * Hook personalizado para manejar la subida de archivos con polling individual
 */
import { useRef } from 'react';
import ingestaService from '@/services/ingestaService';
import Toast from '@/components/ui/CustomAlert';

export const useFileUploadProcess = (setFiles, setUploading) => {
  // Set para rastrear archivos ya procesados
  const processedFiles = useRef(new Set());
  const persistKey = 'ingesta_files_v1';

  // Helper para actualizar files y persistir en localStorage
  const updateFiles = (updater) => {
    setFiles(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      try {
        if (typeof window !== 'undefined' && window.localStorage) {
          // Sanitizar: no persistir el objeto File (no serializable)
          const toStore = Array.isArray(next)
            ? next.map(({ file, ...meta }) => meta)
            : next;
          localStorage.setItem(persistKey, JSON.stringify(toStore));
        }
      } catch (e) {
        /* ignore storage errors */
      }
      return next;
    });
  };

  // Función para truncar nombres de archivo largos
  const truncateFileName = (fileName, maxLength = 30) => {
    if (fileName.length <= maxLength) return fileName;
    
    const extension = fileName.split('.').pop();
    const nameWithoutExt = fileName.slice(0, fileName.lastIndexOf('.'));
    const truncatedName = nameWithoutExt.slice(0, maxLength - extension.length - 4);
    
    return `${truncatedName}...${extension}`;
  };

  const removeCompletedFile = (fileId, fileName) => {
    // Evitar duplicados
    if (processedFiles.current.has(fileId)) {
      console.log('Archivo ya procesado, evitando duplicado:', fileName);
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

  // Nueva función para polling individual mejorado
  const iniciarPollingArchivos = (expedienteFiles, fileProcessIds) => {
    const pollingIntervals = [];

    // Crear un polling individual para cada archivo
    expedienteFiles.forEach((archivoLocal, index) => {
      const fileProcessId = fileProcessIds[index];

      const polling = setInterval(async () => {
        try {
          const estados = await ingestaService.consultarEstadoArchivos([fileProcessId]);
          const estado = estados[0];

          if (estado.success && estado.data) {
            const statusData = estado.data;

            updateFiles(prev => prev.map(f => {
              if (f.id === archivoLocal.id) {
                const actualizado = {
                  ...f,
                  progress: statusData.progress || 0,
                  message: statusData.message || '',
                };

                if (statusData.status === 'completado') {
                  actualizado.status = 'success';
                  actualizado.progress = 100;
                  actualizado.resultado = statusData.resultado;

                  // Detener polling para este archivo
                  clearInterval(polling);

                  // Solo remover si no estaba ya marcado como success
                  if (f.status !== 'success') {
                    setTimeout(() => {
                      removeCompletedFile(archivoLocal.id, archivoLocal.name);
                    }, 100);
                  }

                } else if (statusData.status === 'error') {
                  actualizado.status = 'error';
                  actualizado.progress = 0;
                  actualizado.message = statusData.message || 'Error en procesamiento';

                  // Mostrar toast de error con nombre truncado
                  const displayName = truncateFileName(archivoLocal.name);
                  Toast.error(
                    'Error en archivo',
                    `${displayName}: ${actualizado.message}`
                  );

                  // Detener polling para este archivo
                  clearInterval(polling);
                }

                return actualizado;
              }
              return f;
            }));
          }

        } catch (error) {
          console.error(`Error en polling para archivo ${archivoLocal.name}:`, error);

          // Mostrar toast de error de conexión con nombre truncado
          const displayName = truncateFileName(archivoLocal.name);
          Toast.error(
            'Error de conexión',
            `No se pudo consultar el estado de ${displayName}`
          );

          clearInterval(polling);
        }
      }, 2500); // Consultar cada 2 segundos

      pollingIntervals.push(polling);
    });

    // Limpiar todos los pollings si es necesario
    return () => {
      pollingIntervals.forEach(interval => clearInterval(interval));
    };
  };

  const uploadFiles = async (files) => {
    setUploading(true);

    // Notificación de inicio
    Toast.info(
      'Subida iniciada',
      'Los archivos se están procesando en segundo plano'
    );

    // Agrupar archivos por expediente
    const filesByExpediente = {};
    files.forEach(file => {
      if (file.status === 'pending' && file.expediente?.trim()) {
        const exp = file.expediente.trim();
        if (!filesByExpediente[exp]) {
          filesByExpediente[exp] = [];
        }
        filesByExpediente[exp].push(file);
      }
    });

    // Verificar si hay archivos para procesar
    if (Object.keys(filesByExpediente).length === 0) {
      console.log('No hay archivos con expediente para procesar');
      Toast.warning(
        'Sin archivos',
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

        // Asignar IDs individuales a cada archivo
        if (resultado && resultado.file_process_ids) {
          updateFiles(prev => prev.map(f => {
            const fileIndex = expedienteFiles.findIndex(ef => ef.id === f.id);
            if (fileIndex !== -1 && fileIndex < resultado.file_process_ids.length) {
              return {
                ...f,
                fileProcessId: resultado.file_process_ids[fileIndex],
                progress: 10,
                message: 'Procesando...'
              };
            }
            return f;
          }));
          // Iniciar polling para cada archivo
          iniciarPollingArchivos(expedienteFiles, resultado.file_process_ids);
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

    setUploading(false);
  };

  // Restaurar desde localStorage y reanudar polling si es necesario
  const restoreFromStorage = () => {
    try {
      if (typeof window === 'undefined' || !window.localStorage) return;
      const raw = localStorage.getItem(persistKey);
      if (!raw) return;
      const stored = JSON.parse(raw);
      if (!Array.isArray(stored) || stored.length === 0) return;

      // Rehidratar estado de archivos
      setFiles(stored);

      // Detectar archivos activos (tienen fileProcessId y no están en success/error)
      const activosByExp = {};
      stored.forEach(f => {
        if (f.fileProcessId && f.status && f.status !== 'success' && f.status !== 'error') {
          const exp = f.expediente || 'NO_EXP';
          if (!activosByExp[exp]) activosByExp[exp] = [];
          activosByExp[exp].push(f);
        }
      });

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

  return {
    uploadFiles,
    truncateFileName,
    removeCompletedFile,
    iniciarPollingArchivos,
    processedFiles,
    restoreFromStorage
  };
};
