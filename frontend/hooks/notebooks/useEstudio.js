import { useCallback, useEffect, useRef, useState } from 'react';
import estudioService from '@/services/estudioService';
import Toast from '@/components/ui/CustomAlert';

const ETIQUETAS = { resumen: 'Resumen', informe: 'Informe', mapa_mental: 'Mapa mental', nota: 'Nota' };

/**
 * Estado del panel «Estudio» de un notebook (spec 010): los resultados guardados, el que está abierto y la generación en curso.
 *
 * Cambiar de notebook o salir de la pantalla cancela la generación y no guarda nada (RF-11.128). `documentos` son los
 * identificadores de las fuentes marcadas; se toman al pulsar el botón, como en el chat (RF-11.102).
 */
const useEstudio = (notebookId, documentos) => {
  const [resultados, setResultados] = useState([]);
  const [cargando, setCargando] = useState(false);
  const [abierto, setAbierto] = useState(null); // el resultado con su contenido
  const [generando, setGenerando] = useState(null); // {tipo, etapa, actual, total} mientras se genera
  const controladorRef = useRef(null);
  const notebookRef = useRef(notebookId);
  notebookRef.current = notebookId;
  const documentosRef = useRef(documentos);
  documentosRef.current = documentos;

  const cancelar = useCallback(() => {
    controladorRef.current?.abort();
  }, []);

  const recargar = useCallback(async (id = notebookRef.current) => {
    if (!id) return;
    const respuesta = await estudioService.listarResultados(id);
    if (notebookRef.current !== id) return; // se abrió otro notebook mientras tanto
    if (respuesta.success) setResultados(respuesta.resultados);
  }, []);

  // Al cambiar de notebook: se cancela lo que se generaba, se vacía lo del anterior y se leen los resultados del nuevo.
  useEffect(() => {
    setAbierto(null);
    setResultados([]);
    setGenerando(null);
    if (!notebookId) return undefined;
    setCargando(true);
    recargar(notebookId).finally(() => setCargando(false));
    return () => controladorRef.current?.abort();
  }, [notebookId, recargar]);

  const generar = useCallback(async (tipo) => {
    const id = notebookRef.current;
    if (!id || controladorRef.current) return;
    const controlador = new AbortController();
    controladorRef.current = controlador;
    setGenerando({ tipo, etapa: 'Preparando…', actual: 0, total: 0 });
    const respuesta = await estudioService.generar(id, tipo, documentosRef.current, {
      signal: controlador.signal,
      onProgreso: (p) => setGenerando({ tipo, etapa: p.etapa, actual: p.actual, total: p.total }),
    });
    controladorRef.current = null;
    if (notebookRef.current !== id) return; // salió del notebook: no se muestra nada (ya se canceló)
    setGenerando(null);
    if (respuesta.success) {
      Toast.success('Resultado guardado', `${ETIQUETAS[tipo]} guardado en el notebook.`);
      await recargar(id);
      const abierta = await estudioService.abrirResultado(id, respuesta.resultado.id);
      if (abierta.success) setAbierto(abierta.resultado);
    } else if (respuesta.cancelada) {
      Toast.info('Generación cancelada.');
    } else {
      Toast.error('No se pudo generar', respuesta.message);
    }
  }, [recargar]);

  const abrir = useCallback(async (resultado) => {
    const id = notebookRef.current;
    const respuesta = await estudioService.abrirResultado(id, resultado.id);
    if (notebookRef.current !== id) return;
    if (respuesta.success) {
      setAbierto(respuesta.resultado);
    } else if (respuesta.status === 404) {
      Toast.warning('El resultado ya no está disponible.');
      recargar(id);
    } else {
      Toast.error('No se pudo abrir', respuesta.message);
    }
  }, [recargar]);

  const cerrar = useCallback(() => setAbierto(null), []);

  const quitar = useCallback(async (resultado) => {
    const id = notebookRef.current;
    const respuesta = await estudioService.quitarResultado(id, resultado.id);
    if (notebookRef.current !== id) return;
    if (respuesta.success || respuesta.status === 404) {
      setResultados((prev) => prev.filter((r) => r.id !== resultado.id));
      setAbierto((prev) => (prev?.id === resultado.id ? null : prev));
    } else {
      Toast.error('No se pudo quitar', respuesta.message);
    }
  }, []);

  const guardarNota = useCallback(async ({ pregunta, respuesta, fuentes }) => {
    const id = notebookRef.current;
    const resultado = await estudioService.guardarNota(id, { pregunta, respuesta, fuentes });
    if (notebookRef.current !== id) return false;
    if (resultado.success) {
      Toast.success('Nota guardada', 'La respuesta quedó guardada en el panel Estudio.');
      recargar(id);
      return true;
    }
    Toast.error('No se pudo guardar la nota', resultado.message);
    return false;
  }, [recargar]);

  return { resultados, cargando, abierto, generando, generar, cancelar, abrir, cerrar, quitar, guardarNota };
};

export default useEstudio;
