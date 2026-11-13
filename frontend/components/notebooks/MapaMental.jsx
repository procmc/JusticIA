import React from 'react';

/**
 * Mapa mental del Estudio (spec 010, RF-11.122): el tema central y sus ramas, dibujados de izquierda a derecha con HTML y
 * Tailwind. No usa ninguna librería de dibujo ni carga recursos externos (RNF-09.120). El mapa llega ya validado y podado por
 * el servidor (hasta tres niveles bajo el tema central); si no cabe en el ancho del panel, se desplaza dentro de su propio
 * recuadro, sin desplazar la página (RNF-04.121). Con `grande` se dibuja con letra y cajas mayores, para verlo completo en
 * una pantalla amplia. Las líneas son tramos rectos (horizontales y verticales) que salen del borde de cada caja y llegan al
 * de cada rama (spec 010, pedido del 10/11/2026).
 */
const ESTILOS = [
  'bg-primary text-white font-semibold',
  'bg-primary-100 text-primary-800 font-medium',
  'bg-default-100 text-default-800',
  'bg-default-50 text-default-700 border border-default-200',
];

// Conectores en ángulos rectos: de la caja sale un tramo horizontal («salida») hasta una línea vertical común a sus ramas, y de
// ella entra un tramo horizontal («entrada») al borde izquierdo de cada rama. La vertical va del centro de la primera rama al
// de la última; cada rama la dibuja su mitad (la primera solo hacia abajo, la última solo hacia arriba), así no sobresale.
const Nodo = ({ nodo, nivel, grande }) => {
  const ramas = nodo.ramas || [];
  const tramo = grande ? 'w-8' : 'w-6';
  const separacion = grande ? 'pl-8 py-1.5' : 'pl-6 py-1';
  return (
    <div className="flex items-center">
      <div
        className={`rounded-lg break-words ${grande ? 'px-4 py-2 text-base max-w-[340px]' : 'px-3 py-1.5 text-xs sm:text-sm max-w-[200px]'} ${ESTILOS[Math.min(nivel, ESTILOS.length - 1)]}`}
      >
        {nodo.titulo}
      </div>
      {ramas.length > 0 && (
        <>
          <span aria-hidden="true" data-conector="salida" className={`${tramo} shrink-0 border-t-2 border-default-300`} />
          <div className="flex flex-col">
            {ramas.map((rama, i) => (
              <div key={`${rama.titulo}-${i}`} className={`relative flex items-center ${separacion}`}>
                <span
                  aria-hidden="true"
                  className={`absolute left-0 w-0.5 bg-default-300 ${i === 0 ? 'top-1/2' : 'top-0'} ${i === ramas.length - 1 ? 'bottom-1/2' : 'bottom-0'}`}
                />
                <span aria-hidden="true" data-conector="entrada" className={`absolute left-0 top-1/2 -mt-px ${tramo} border-t-2 border-default-300`} />
                <Nodo nodo={rama} nivel={nivel + 1} grande={grande} />
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

const MapaMental = ({ mapa, grande = false }) => (
  <div
    role="group"
    aria-label={`Mapa mental: ${mapa.titulo}`}
    className={`overflow-x-auto rounded-lg border border-default-200 bg-white ${grande ? 'p-6' : 'p-3'}`}
  >
    <div className="inline-block min-w-min">
      <Nodo nodo={mapa} nivel={0} grande={grande} />
    </div>
  </div>
);

export default MapaMental;
