import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Ancho ajustable de las columnas de `/notebooks` (spec 010, cambio JJ1; RNF-04.124 a RNF-04.129).
 *
 * Tres columnas se ajustan arrastrando la línea que las divide: la lista de notebooks, «Fuentes» y «Estudio»; el chat ocupa el
 * resto. Cada una tiene un ancho de fábrica, un mínimo y un máximo, y el chat conserva un mínimo (RNF-04.125). El ancho elegido se
 * recuerda en este navegador, sin que nada dependa de ello (RNF-04.126). Una columna plegada conserva su riel y no tiene línea.
 *
 * El ancho que se MUESTRA (`anchos`) puede ser menor que el guardado cuando el área es angosta, para que el chat conserve su
 * mínimo; ese ajuste no se guarda, así que al ensanchar la ventana vuelve el ancho elegido (RNF-04.129).
 *
 * Ver también: `components/notebooks/DivisorDeColumna.jsx` (la línea) y `pages/notebooks/index.js` (donde se usa).
 */
export const COLUMNAS = {
  lista: { fabrica: 224, minimo: 180, maximo: 400, riel: 48, etiqueta: 'Cambiar el ancho de la lista de notebooks' },
  fuentes: { fabrica: 240, minimo: 200, maximo: 480, riel: 44, etiqueta: 'Cambiar el ancho de Fuentes' },
  estudio: { fabrica: 256, minimo: 220, maximo: 560, riel: 44, etiqueta: 'Cambiar el ancho de Estudio' },
};
export const ANCHO_MINIMO_CHAT = 280;
export const CLAVE_ANCHOS_COLUMNAS = 'notebooks_anchos_columnas';
const PASO = 16;
const PASO_GRANDE = 64;
const IDS = Object.keys(COLUMNAS);

const acotar = (id, valor) => Math.round(Math.max(COLUMNAS[id].minimo, Math.min(COLUMNAS[id].maximo, valor)));

/** Los anchos de fábrica. */
export const anchosDeFabrica = () => Object.fromEntries(IDS.map((id) => [id, COLUMNAS[id].fabrica]));

/** Corrige lo leído del almacenamiento: lo que no es un número queda de fábrica y lo que sale de los límites, en el más cercano. */
export function sanear(guardado) {
  const origen = guardado && typeof guardado === 'object' ? guardado : {};
  return Object.fromEntries(IDS.map((id) => {
    const valor = origen[id];
    return [id, typeof valor === 'number' && Number.isFinite(valor) ? acotar(id, valor) : COLUMNAS[id].fabrica];
  }));
}

/** Lo que ocupan las demás columnas (su ancho, o su riel si están plegadas), sin contar `id`. */
const ocupadoPorOtras = (id, anchos, plegados) => IDS.filter((otra) => otra !== id)
  .reduce((suma, otra) => suma + (plegados[otra] ? COLUMNAS[otra].riel : anchos[otra]), 0);

/**
 * El ancho que puede tener `id`: el deseado, entre su mínimo y su máximo, y sin dejar al chat por debajo de su mínimo (RNF-04.125).
 * Si el área es tan angosta que ni así cabe, queda en su mínimo.
 */
export function limitarAncho(id, deseado, anchos, plegados, disponible) {
  const tope = disponible > 0
    ? Math.max(COLUMNAS[id].minimo, disponible - ANCHO_MINIMO_CHAT - ocupadoPorOtras(id, anchos, plegados))
    : COLUMNAS[id].maximo;
  return Math.round(Math.max(COLUMNAS[id].minimo, Math.min(COLUMNAS[id].maximo, tope, deseado)));
}

/** Los anchos que se muestran: los guardados, reducidos hacia su mínimo (sin tocar lo guardado) si el chat quedaría sin su mínimo. */
export function anchosEfectivos(anchos, plegados, disponible) {
  if (!(disponible > 0)) return anchos;
  const visibles = IDS.filter((id) => !plegados[id]);
  const rieles = IDS.filter((id) => plegados[id]).reduce((suma, id) => suma + COLUMNAS[id].riel, 0);
  const ocupado = visibles.reduce((suma, id) => suma + anchos[id], 0) + rieles;
  let exceso = ocupado + ANCHO_MINIMO_CHAT - disponible;
  if (exceso <= 0) return anchos;
  const reducidos = { ...anchos };
  const holgura = visibles.reduce((suma, id) => suma + (anchos[id] - COLUMNAS[id].minimo), 0);
  if (holgura <= 0) return reducidos;
  const recorte = Math.min(exceso, holgura);
  visibles.forEach((id) => {
    reducidos[id] = Math.round(anchos[id] - recorte * ((anchos[id] - COLUMNAS[id].minimo) / holgura));
  });
  return reducidos;
}

export default function useAnchosDeColumnas(plegados) {
  const [guardados, setGuardados] = useState(anchosDeFabrica);
  const [disponible, setDisponible] = useState(0);
  const contenedorRef = useRef(null);
  const arrastre = useRef(null);
  const ultimos = useRef(guardados);
  ultimos.current = guardados;

  // Lo recordado en este navegador (con la pantalla ya montada, para no desajustar el HTML del servidor).
  useEffect(() => {
    try {
      setGuardados(sanear(JSON.parse(localStorage.getItem(CLAVE_ANCHOS_COLUMNAS) || 'null')));
    } catch { /* sin almacenamiento o un valor dañado: quedan los de fábrica */ }
  }, []);

  // El área de contenido: lo que de verdad cabe, sin el menú lateral.
  useEffect(() => {
    const elemento = contenedorRef.current;
    if (!elemento || typeof ResizeObserver === 'undefined') return undefined;
    const observador = new ResizeObserver(() => setDisponible(elemento.clientWidth));
    observador.observe(elemento);
    setDisponible(elemento.clientWidth);
    return () => observador.disconnect();
  }, []);

  const anchos = anchosEfectivos(guardados, plegados, disponible);

  const guardar = useCallback((siguiente) => {
    try { localStorage.setItem(CLAVE_ANCHOS_COLUMNAS, JSON.stringify(siguiente)); } catch { /* idem */ }
  }, []);

  const fijar = useCallback((id, deseado, persistir) => {
    const actuales = ultimos.current;
    const siguiente = { ...actuales, [id]: limitarAncho(id, deseado, actuales, plegados, disponible) };
    setGuardados(siguiente);
    if (persistir) guardar(siguiente);
  }, [plegados, disponible, guardar]);

  const terminarArrastre = useCallback((evento) => {
    if (!arrastre.current) return;
    try { evento.currentTarget.releasePointerCapture(evento.pointerId); } catch { /* ya liberado */ }
    arrastre.current = null;
    document.body.style.userSelect = '';
    document.body.style.cursor = '';
    guardar(ultimos.current);
  }, [guardar]);

  /** Los controladores de la línea de la columna `id` (puntero, doble clic y teclado). */
  const controlesDe = useCallback((id) => {
    // La línea del Estudio está en su borde izquierdo: arrastrarla a la derecha la achica.
    const signo = id === 'estudio' ? -1 : 1;
    return {
      onPointerDown: (evento) => {
        if (evento.button !== undefined && evento.button !== 0) return;
        evento.currentTarget.setPointerCapture(evento.pointerId);
        arrastre.current = { id, x: evento.clientX, inicio: anchos[id] };
        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'col-resize';
      },
      onPointerMove: (evento) => {
        if (!arrastre.current || arrastre.current.id !== id) return;
        fijar(id, arrastre.current.inicio + signo * (evento.clientX - arrastre.current.x), false);
      },
      onPointerUp: terminarArrastre,
      onPointerCancel: terminarArrastre,
      onDoubleClick: () => fijar(id, COLUMNAS[id].fabrica, true),
      onKeyDown: (evento) => {
        const paso = evento.shiftKey ? PASO_GRANDE : PASO;
        if (evento.key === 'ArrowRight') fijar(id, anchos[id] + signo * paso, true);
        else if (evento.key === 'ArrowLeft') fijar(id, anchos[id] - signo * paso, true);
        else if (evento.key === 'Home') fijar(id, COLUMNAS[id].fabrica, true);
        else return;
        evento.preventDefault();
      },
    };
  }, [anchos, fijar, terminarArrastre]);

  return { anchos, contenedorRef, controlesDe };
}
