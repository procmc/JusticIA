import React, { useRef, useState } from 'react';
import {
  Button, Spinner, Dropdown, DropdownTrigger, DropdownMenu, DropdownItem, Modal, ModalContent, ModalHeader, ModalBody
} from '@heroui/react';
import {
  FiFileText, FiList, FiShare2, FiEdit3, FiMoreVertical, FiArrowLeft, FiCopy, FiCheck, FiAlertTriangle, FiMaximize2
} from 'react-icons/fi';

import ConfirmModal from '@/components/ui/ConfirmModal';
import MarkdownRenderer from '@/components/consulta-datos/chat/MarkdownRenderer';
import MapaMental from '@/components/notebooks/MapaMental';
import { copyToClipboard } from '@/utils/chat/markdownUtils';

/**
 * Panel «Estudio» de NotebookServIA (spec 010): los botones para generar un Resumen, un Informe o un Mapa mental con las
 * fuentes marcadas, la generación en curso con su avance, y la lista de los resultados guardados del notebook. Es solo
 * presentación: el estado y las llamadas a la API están en `useEstudio` (constitución, principio 3).
 */
const GENERABLES = [
  { tipo: 'resumen', etiqueta: 'Resumen', icono: FiFileText },
  { tipo: 'informe', etiqueta: 'Informe', icono: FiList },
  { tipo: 'mapa_mental', etiqueta: 'Mapa mental', icono: FiShare2 },
];
const ICONOS = { resumen: FiFileText, informe: FiList, mapa_mental: FiShare2, nota: FiEdit3 };
const ETIQUETAS = { resumen: 'Resumen', informe: 'Informe', mapa_mental: 'Mapa mental', nota: 'Nota' };
const AVISO_FUENTES = 'Una o más fuentes de este resultado ya no están en el notebook.';

const formatearFecha = (iso) => {
  try {
    return new Intl.DateTimeFormat('es-CR', {
      timeZone: 'America/Costa_Rica', day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
    }).format(new Date(iso));
  } catch (error) {
    return '';
  }
};

// El mapa como lista de ideas anidada, para copiarlo (RF-14.122).
const textoDeMapa = (mapa) => {
  const lineas = [mapa.titulo];
  const recorrer = (ramas, nivel) => ramas.forEach((r) => {
    lineas.push(`${'  '.repeat(nivel)}- ${r.titulo}`);
    recorrer(r.ramas || [], nivel + 1);
  });
  recorrer(mapa.ramas || [], 0);
  return lineas.join('\n');
};

const textoParaCopiar = (resultado) => {
  if (resultado.tipo === 'mapa_mental') return textoDeMapa(resultado.contenido);
  if (resultado.tipo === 'nota') return `${resultado.contenido.pregunta}\n\n${resultado.contenido.respuesta}`;
  return resultado.contenido;
};

const Fuentes = ({ resultado }) => (
  <div className="mt-4 border-t border-default-200 pt-3">
    {resultado.fuentes_faltantes && (
      <p role="status" className="mb-2 flex items-start gap-1.5 text-xs text-warning-700">
        <FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" /> {AVISO_FUENTES}
      </p>
    )}
    {resultado.fuentes.length > 0 && (
      <>
        <p className="text-xs font-medium text-default-600">Fuentes con que se generó:</p>
        <ul className="mt-1 list-disc pl-5 text-xs text-default-600 break-words">
          {resultado.fuentes.map((f, i) => <li key={`${f.nombre}-${i}`}>{f.nombre}</li>)}
        </ul>
      </>
    )}
  </div>
);

const Contenido = ({ resultado }) => {
  if (resultado.tipo === 'mapa_mental') return <MapaMental mapa={resultado.contenido} />;
  if (resultado.tipo === 'nota') {
    return (
      <div className="text-sm">
        <p className="mb-1 text-xs font-medium text-default-600">Pregunta</p>
        <p className="mb-3 whitespace-pre-wrap rounded-lg bg-default-100 px-3 py-2 break-words">{resultado.contenido.pregunta}</p>
        <p className="mb-1 text-xs font-medium text-default-600">Respuesta</p>
        <MarkdownRenderer content={resultado.contenido.respuesta} forceKey={0} />
      </div>
    );
  }
  return <div className="text-sm break-words"><MarkdownRenderer content={resultado.contenido} forceKey={0} /></div>;
};

const PanelEstudio = ({ estudio, sinFuenteMarcada }) => {
  const { resultados, cargando, abierto, generando, generar, cancelar, abrir, cerrar, quitar } = estudio;
  const [porQuitar, setPorQuitar] = useState(null);
  const confirmacionRef = useRef(null); // el mismo resultado; se vacía en el primer «Quitar» para absorber el doble clic
  const [copiado, setCopiado] = useState(false);
  const [ampliado, setAmpliado] = useState(false); // el resultado abierto, a pantalla completa

  // Desde el menú ⋮ de la lista: lo abre (lee su contenido) y lo muestra a pantalla completa. Si no se pudo abrir, no hay nada
  // que ampliar y `abrir` ya avisó del motivo.
  const ampliarDesdeLaLista = async (resultado) => {
    await abrir(resultado);
    setAmpliado(true);
  };

  const pedirQuitar = (resultado) => {
    confirmacionRef.current = resultado;
    setPorQuitar(resultado);
  };
  const confirmarQuitar = () => {
    const pendiente = confirmacionRef.current;
    confirmacionRef.current = null;
    if (pendiente) quitar(pendiente);
  };
  const copiar = async () => {
    if (await copyToClipboard(textoParaCopiar(abierto))) {
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    }
  };

  return (
    <section aria-label="Estudio" className="flex h-full min-h-0 flex-col">
      <div className="border-b border-gray-200 p-4">
        <h3 className="font-semibold text-gray-800">Estudio</h3>
        <p className="mt-0.5 text-xs text-gray-500">Genere un resultado con las fuentes marcadas.</p>
      </div>

      {abierto ? (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex items-center gap-2 border-b border-gray-200 p-3">
            <Button isIconOnly size="sm" variant="light" onPress={cerrar} aria-label="Volver a la lista">
              <FiArrowLeft />
            </Button>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-gray-800">{abierto.titulo}</p>
              <p className="text-xs text-gray-500">{formatearFecha(abierto.fecha_creacion)}</p>
            </div>
            <Button isIconOnly size="sm" variant="flat" onPress={() => setAmpliado(true)} aria-label="Ver en pantalla completa">
              <FiMaximize2 />
            </Button>
            <Button size="sm" variant="flat" startContent={copiado ? <FiCheck /> : <FiCopy />} onPress={copiar}>
              {copiado ? 'Copiado' : 'Copiar'}
            </Button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto p-4">
            <Contenido resultado={abierto} />
            <Fuentes resultado={abierto} />
          </div>
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="border-b border-gray-200 p-3">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-1">
              {GENERABLES.map(({ tipo, etiqueta, icono: Icono }) => (
                <Button
                  key={tipo}
                  size="sm"
                  variant="flat"
                  color="primary"
                  className="justify-start"
                  startContent={<Icono aria-hidden="true" />}
                  isDisabled={sinFuenteMarcada || Boolean(generando)}
                  onPress={() => generar(tipo)}
                >
                  {etiqueta}
                </Button>
              ))}
            </div>
            {sinFuenteMarcada && !generando && (
              <p role="status" className="mt-2 text-xs text-warning-700">Marque al menos una fuente para generar un resultado.</p>
            )}
            {generando && (
              <div role="status" aria-live="polite" className="mt-3 rounded-lg bg-primary-50 p-3">
                <div className="flex items-center gap-2 text-sm text-primary-800">
                  <Spinner size="sm" aria-hidden="true" />
                  <span>{generando.etapa}</span>
                </div>
                <Button size="sm" variant="flat" color="danger" className="mt-2" onPress={cancelar} aria-label="Cancelar la generación">
                  Cancelar
                </Button>
              </div>
            )}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto p-3">
            {cargando ? (
              <div className="flex justify-center p-4"><Spinner size="sm" /></div>
            ) : resultados.length === 0 ? (
              <p className="p-2 text-center text-sm text-gray-400">Todavía no hay resultados. Genere uno con las fuentes marcadas.</p>
            ) : (
              <ul aria-label="Resultados guardados" className="m-0 flex list-none flex-col gap-1 p-0">
                {resultados.map((r) => {
                  const Icono = ICONOS[r.tipo] || FiFileText;
                  return (
                    <li key={r.id} className="flex items-center gap-1 rounded-lg border border-gray-100 bg-white px-2 py-1.5">
                      <button
                        type="button"
                        onClick={() => abrir(r)}
                        className="flex min-w-0 flex-1 items-center gap-2 text-left"
                        aria-label={`Abrir ${r.titulo}`}
                      >
                        <Icono className="shrink-0 text-primary" aria-hidden="true" />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm text-gray-800">{r.titulo}</span>
                          <span className="block text-xs text-gray-500">
                            {ETIQUETAS[r.tipo]} · {formatearFecha(r.fecha_creacion)}
                          </span>
                        </span>
                        {r.fuentes_faltantes && (
                          <FiAlertTriangle className="shrink-0 text-warning" title={AVISO_FUENTES} aria-label={AVISO_FUENTES} />
                        )}
                      </button>
                      <Dropdown>
                        <DropdownTrigger>
                          <Button isIconOnly size="sm" variant="light" aria-label={`Opciones de ${r.titulo}`}>
                            <FiMoreVertical />
                          </Button>
                        </DropdownTrigger>
                        <DropdownMenu aria-label={`Acciones de ${r.titulo}`}>
                          <DropdownItem key="ampliar" startContent={<FiMaximize2 aria-hidden="true" />} onPress={() => ampliarDesdeLaLista(r)}>
                            Ver en pantalla completa
                          </DropdownItem>
                          <DropdownItem key="quitar" color="danger" className="text-danger" onPress={() => pedirQuitar(r)}>
                            Quitar resultado
                          </DropdownItem>
                        </DropdownMenu>
                      </Dropdown>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* El resultado abierto, a todo el ancho de la pantalla: el mapa mental dibujado en grande y el texto en una columna legible */}
      <Modal isOpen={ampliado && Boolean(abierto)} onClose={() => setAmpliado(false)} size="full" scrollBehavior="inside">
        <ModalContent>
          <ModalHeader className="flex-col items-start break-words">
            <span>{abierto?.titulo}</span>
            {abierto && <span className="text-xs font-normal text-gray-500">{formatearFecha(abierto.fecha_creacion)}</span>}
          </ModalHeader>
          <ModalBody className="pb-6">
            {abierto?.tipo === 'mapa_mental' ? (
              <MapaMental mapa={abierto.contenido} grande />
            ) : abierto && (
              <div className="mx-auto w-full max-w-3xl">
                <Contenido resultado={abierto} />
                <Fuentes resultado={abierto} />
              </div>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>

      <ConfirmModal
        isOpen={!!porQuitar}
        onClose={() => setPorQuitar(null)}
        onConfirm={confirmarQuitar}
        title="Quitar resultado"
        description={`¿Quitar "${porQuitar?.titulo ?? ''}" de la lista del notebook?`}
        confirmText="Quitar"
        cancelText="Cancelar"
        confirmColor="danger"
      />
    </section>
  );
};

export default PanelEstudio;
