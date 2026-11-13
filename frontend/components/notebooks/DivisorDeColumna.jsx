import React from 'react';

/**
 * La línea que divide dos columnas de `/notebooks` y que se arrastra para cambiar el ancho de una (spec 010, JJ1; RNF-04.124,
 * RNF-04.127, RNF-04.128). Solo desde pantallas de escritorio (`lg`): debajo se ve un panel a la vez.
 *
 * Ocupa 0 px de ancho en el diseño (no mueve nada) y su zona para agarrarla se extiende 6 px a cada lado. Se usa con el mouse o el
 * dedo (eventos de puntero), con el teclado (flechas, Mayús para pasos mayores, Inicio para restablecer) y con doble clic.
 *
 * Props: `etiqueta` (su nombre accesible), `valor`, `minimo` y `maximo` (el ancho de la columna) y `controles` (los controladores
 * que entrega `useAnchosDeColumnas`).
 */
const DivisorDeColumna = ({ etiqueta, valor, minimo, maximo, controles }) => (
  <div className="relative hidden lg:block w-0 shrink-0 z-20">
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={etiqueta}
      aria-valuenow={valor}
      aria-valuemin={minimo}
      aria-valuemax={maximo}
      tabIndex={0}
      className="group absolute top-0 -left-1.5 h-full w-3 flex justify-center cursor-col-resize touch-none select-none outline-none"
      {...controles}
    >
      <span className="h-full w-0.5 bg-transparent transition-colors group-hover:bg-primary/60 group-focus-visible:bg-primary group-active:bg-primary" />
    </div>
  </div>
);

export default DivisorDeColumna;
