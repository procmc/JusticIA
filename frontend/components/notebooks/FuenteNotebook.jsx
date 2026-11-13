import React, { useState, useRef } from 'react';
import { Button, Checkbox, Dropdown, DropdownTrigger, DropdownMenu, DropdownItem, Input, Tooltip } from '@heroui/react';
import { FiEdit2, FiFile, FiMoreVertical, FiTrash2 } from 'react-icons/fi';

/**
 * Fila de una fuente del notebook (spec 009b): nombre que abre la vista previa y menú ⋮ de opciones.
 *
 * El menú es un control aparte del botón del nombre, así que abrirlo no abre la vista previa (RF-19.100). «Quitar fuente»
 * sigue el flujo de siempre: `onQuitar` pide la confirmación (RF-19.101). Mientras se quita, la fila queda deshabilitada.
 *
 * «Cambiar el nombre de la fuente» edita en línea solo la base: la extensión viene del nombre interno y el servidor la añade
 * (RF-19.102). La validación es del servidor: el campo no lleva `maxLength` y también envía el vacío, para mostrar su mensaje
 * bajo el campo. `onRenombrar(base)` devuelve `{ success }` o `{ message }` (como en `ItemNotebook`). Con la fuente en proceso
 * (ni Procesado ni Error) la opción se muestra desactivada (RF-19.107).
 *
 * El nombre se recorta con «…» en una línea; al pasar el mouse o enfocarlo sale un aviso con el nombre completo y, si la fuente
 * está Procesado, «Haga clic para ver el archivo original» (RF-19.116). El aviso muestra el nombre como texto (RF-19.118).
 */
const FuenteNotebook = ({ fuente, marcada, abriendo, quitando, onAlternar, onAbrir, onQuitar, onRenombrar }) => {
  const [editando, setEditando] = useState(false);
  const [nombre, setNombre] = useState('');
  const [error, setError] = useState('');
  const [guardando, setGuardando] = useState(false);
  const guardandoRef = useRef(false); // envío único aunque Enter y «Guardar» lleguen juntos

  const procesado = fuente.estado === 'Procesado';
  const enProceso = !procesado && fuente.estado !== 'Error';
  const extension = fuente.extension || '';
  const color = procesado
    ? 'text-success-700 dark:text-success-400'
    : fuente.estado === 'Error'
      ? 'text-danger-700 dark:text-danger-400'
      : 'text-default-700';

  // Se marca como deshabilitada (lo leen los lectores de pantalla y las pruebas); va en un objeto porque la regla de
  // lint no admite aria-disabled en un listitem aunque sea válido en el árbol de accesibilidad.
  const deshabilitada = quitando ? { 'aria-disabled': 'true', 'data-disabled': 'true' } : {};

  const empezar = () => {
    const nombreCompleto = fuente.nombre_archivo || '';
    setNombre(extension && nombreCompleto.endsWith(extension) ? nombreCompleto.slice(0, -extension.length) : nombreCompleto);
    setError('');
    setEditando(true);
  };

  const cancelar = () => {
    setEditando(false);
    setError('');
  };

  const guardar = async () => {
    if (guardandoRef.current) return;
    guardandoRef.current = true;
    setGuardando(true);
    const resultado = await onRenombrar(nombre);
    guardandoRef.current = false;
    setGuardando(false);
    if (resultado?.success) {
      cancelar();
    } else {
      setError(resultado?.message || ''); // sin mensaje: la página ya mostró un aviso
    }
  };

  if (editando) {
    return (
      <li {...deshabilitada} className="px-2 py-2 rounded-lg bg-default-50 space-y-2 min-w-0">
        <Input
          size="sm"
          autoFocus
          aria-label="Nuevo nombre de la fuente"
          value={nombre}
          onValueChange={setNombre}
          isInvalid={!!error}
          errorMessage={error}
          endContent={extension ? <span className="text-small text-default-500 shrink-0">{extension}</span> : null}
          onKeyDown={(e) => {
            if (e.key === 'Enter') guardar();
            else if (e.key === 'Escape') cancelar();
          }}
        />
        <div className="flex gap-2 justify-end">
          <Button size="sm" variant="flat" onPress={cancelar}>Cancelar</Button>
          <Button size="sm" color="primary" isLoading={guardando} onPress={guardar}>Guardar</Button>
        </div>
      </li>
    );
  }

  return (
    <li
      {...deshabilitada}
      className={`flex items-center gap-1 rounded-lg bg-default-100 pl-2 min-w-0${quitando ? ' opacity-50 pointer-events-none' : ''}`}
    >
      {/* Casilla: usar o no la fuente en el chat (RF-11.100). Sin texto visible; el nombre accesible lo lleva aria-label. */}
      <Checkbox
        size="sm"
        isSelected={marcada}
        onValueChange={onAlternar}
        aria-label={`Usar ${fuente.nombre_archivo} en el chat`}
        classNames={{ base: 'shrink-0 m-0 p-0 max-w-none', wrapper: 'mr-0' }}
      />
      <FiFile className="shrink-0 text-default-500" aria-hidden="true" />
      <Tooltip
        delay={0}
        closeDelay={0}
        placement="top"
        content={(
          <div className="max-w-xs break-all text-small">
            <div>{fuente.nombre_archivo}</div>
            {procesado && <div className="mt-1 text-tiny text-default-500">Haga clic para ver el archivo original</div>}
          </div>
        )}
      >
        <button
          type="button"
          onClick={onAbrir}
          className={`flex-1 min-w-0 truncate text-left px-1 py-1 text-sm ${color} ${procesado ? 'cursor-pointer' : 'cursor-default'}`}
        >
          {abriendo ? 'Abriendo…' : fuente.nombre_archivo}
        </button>
      </Tooltip>
      <Dropdown>
        <DropdownTrigger>
          <Button
            isIconOnly
            size="sm"
            variant="light"
            className="shrink-0"
            aria-label={`Opciones de ${fuente.nombre_archivo}`}
          >
            <FiMoreVertical />
          </Button>
        </DropdownTrigger>
        <DropdownMenu aria-label={`Acciones de ${fuente.nombre_archivo}`}>
          <DropdownItem
            key="renombrar"
            startContent={<FiEdit2 />}
            isDisabled={enProceso}
            description={enProceso ? 'Espere a que termine de procesarse.' : undefined}
            onPress={empezar}
          >
            Cambiar el nombre de la fuente
          </DropdownItem>
          <DropdownItem
            key="quitar"
            color="danger"
            className="text-danger"
            startContent={<FiTrash2 />}
            onPress={onQuitar}
          >
            Quitar fuente
          </DropdownItem>
        </DropdownMenu>
      </Dropdown>
    </li>
  );
};

export default FuenteNotebook;
