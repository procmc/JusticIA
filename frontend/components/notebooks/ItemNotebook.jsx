import React, { useState, useRef } from 'react';
import { Button, Input } from '@heroui/react';
import { FiEdit2, FiTrash2 } from 'react-icons/fi';

/**
 * Fila de la lista de notebooks (spec 009): nombre, renombrar en línea y eliminar.
 *
 * La validación del nombre es del servidor (RF-17.81, 17.82, 17.84): el campo no lleva `maxLength` y también envía el vacío,
 * para mostrar el mensaje del servidor bajo el campo. `onRenombrar(nombre)` devuelve `{ success }` o `{ message }`.
 */
const ItemNotebook = ({ notebook, activo, onSeleccionar, onRenombrar, onEliminar }) => {
  const [editando, setEditando] = useState(false);
  const [nombre, setNombre] = useState('');
  const [error, setError] = useState('');
  const [guardando, setGuardando] = useState(false);
  const guardandoRef = useRef(false); // envío único aunque Enter y «Guardar» lleguen juntos

  const empezar = () => {
    setNombre(notebook.nombre);
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
      <div className="px-2 py-2 rounded-lg bg-default-50 space-y-2">
        <Input
          size="sm"
          autoFocus
          aria-label="Nuevo nombre del notebook"
          value={nombre}
          onValueChange={setNombre}
          isInvalid={!!error}
          errorMessage={error}
          onKeyDown={(e) => {
            if (e.key === 'Enter') guardar();
            else if (e.key === 'Escape') cancelar();
          }}
        />
        <div className="flex gap-2 justify-end">
          <Button size="sm" variant="flat" onPress={cancelar}>Cancelar</Button>
          <Button size="sm" color="primary" isLoading={guardando} onPress={guardar}>Guardar</Button>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`flex items-center gap-1 rounded-lg transition-colors ${
        activo ? 'bg-blue-50 dark:bg-blue-950/40' : 'hover:bg-default-100'
      }`}
    >
      <button
        type="button"
        onClick={onSeleccionar}
        title={notebook.nombre}
        className={`flex-1 min-w-0 truncate text-left px-3 py-2 text-sm ${
          activo ? 'text-[#003d82] dark:text-blue-300 font-medium' : 'text-default-700'
        }`}
      >
        {notebook.nombre}
      </button>
      <div className="flex shrink-0 pr-1">
        <Button isIconOnly size="sm" variant="light" aria-label="Renombrar notebook" onPress={empezar}>
          <FiEdit2 />
        </Button>
        <Button isIconOnly size="sm" variant="light" color="danger" aria-label="Eliminar notebook" onPress={onEliminar}>
          <FiTrash2 />
        </Button>
      </div>
    </div>
  );
};

export default ItemNotebook;
