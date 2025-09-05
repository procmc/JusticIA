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

  // Detener polling específico
  const stopPolling = (fileProcessId) => {
    const intId = activePollings.current.get(fileProcessId);
    if (!intId) return;
    clearInterval(intId);
    activePollings.current.delete(fileProcessId);
  };

  // Crear polling para un archivo (id de proceso + metadatos locales)
  const startPollingForFile = (archivoLocal, fileProcessId) => {
    if (!fileProcessId || activePollings.current.has(fileProcessId) || isTerminal(archivoLocal.status)) return;

    const intervalId = setInterval(async () => {
      try {
        const estados = await ingestaService.consultarEstadoArchivos([fileProcessId]);
        const estado = estados[0];

        if (estado && estado.success && estado.data) {
          const statusData = estado.data;

          let reachedTerminal = false;
          updateFiles(prev => prev.map(f => {
            if (f.id === archivoLocal.id) {
              const st = statusData.status;
              const base = { ...f, progress: statusData.progress || 0, message: statusData.message || '' };
              if (st === 'completado') {
                reachedTerminal = true;
                return { ...base, status: 'success', progress: 100, resultado: statusData.resultado };
              }
              if (st === 'error') {
                reachedTerminal = true;
                const msg = statusData.message || 'Error en procesamiento';
                const displayName = truncateFileName(archivoLocal.name);
                Toast.error('Error en archivo', `${displayName}: ${msg}`);
                return { ...base, status: 'error', progress: 0, message: msg };
              }
              return base;
            }
            return f;
          }));

          if (reachedTerminal) {
            stopPolling(fileProcessId);
            // Remover visualmente luego de un breve delay si success
            const estadoFinal = statusData.status;
            if (estadoFinal === 'completado') {
              setTimeout(() => removeCompletedFile(archivoLocal.id, archivoLocal.name), 120);
            }
          }
        }
      } catch (error) {
        // Detectar 404 => proceso ya no existe (posiblemente backend lo limpió) => marcar como success silencioso
  if (error?.response?.status === 404) {
          updateFiles(prev => prev.map(f => {
            if (f.id === archivoLocal.id) {
              return { ...f, status: 'success', progress: 100, message: 'Procesado (registro no encontrado)' };
            }
            return f;
          }));
          stopPolling(fileProcessId);
          setTimeout(() => removeCompletedFile(archivoLocal.id, archivoLocal.name), 120);
          return;
        }
        console.error(`Error en polling para archivo ${archivoLocal.name}:`, error);
  if (!isTerminal(archivoLocal.status)) { // evitar spam
          const displayName = truncateFileName(archivoLocal.name);
          Toast.error('Error de conexión', `No se pudo consultar el estado de ${displayName}`);
        }
        stopPolling(fileProcessId);
      }
    }, 2500);

    activePollings.current.set(fileProcessId, intervalId);
  };

  // Iniciar polling para lote de archivos
  const iniciarPollingArchivos = (expedienteFiles, fileProcessIds) => {
    expedienteFiles.forEach((archivoLocal, idx) => {
      const fileProcessId = fileProcessIds[idx];
      startPollingForFile(archivoLocal, fileProcessId);
    });
  };

  // Detener todos los pollings activos (p.ej. al desmontar componente si se implementa)
  const stopAllPollings = () => { activePollings.current.forEach(clearInterval); activePollings.current.clear(); };

  const uploadFiles = async (files) => {
    // Normalizar archivos (aceptar tanto array como objeto-array del hook)
    const listFiles = Array.isArray(files) ? files : Array.from(files || []);

    setUploading(true);
    try {
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
        console.log('No hay archivos con expediente para procesar');
        Toast.warning(
          'Sin archivos',
          'No hay archivos válidos con número de expediente para procesar'
        );
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

  return {
    uploadFiles,
    truncateFileName,
    removeCompletedFile,
  iniciarPollingArchivos,
  processedFiles,
  restoreFromStorage,
  stopAllPollings
  };
};