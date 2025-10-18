import React, { useState, useEffect } from 'react';
import { 
  Table, 
  TableHeader, 
  TableColumn, 
  TableBody, 
  TableRow, 
  TableCell, 
  Button, 
  Chip, 
  Pagination,
  Card,
  CardBody,
  CardHeader,
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
  Tooltip
} from '@heroui/react';
import { 
  IoPeople, 
  IoEllipsisVertical, 
  IoEye,
  IoPencil, 
  IoLockClosed, 
  IoShield,
  IoPerson,
  IoPersonAdd
} from 'react-icons/io5';
import { formatearSoloFechaCostaRica, formatearSoloHoraCostaRica } from '../../../utils/dateUtils';

const TablaUsuarios = ({ 
  usuarios, 
  cargando = false,
  onVerDetalle, 
  onEditarUsuario, 
  onResetearContrasena 
}) => {
  const [paginaActual, setPaginaActual] = useState(1);
  const usuariosPorPagina = 10;

  // Resetear a página 1 cuando cambien los usuarios (por filtros)
  useEffect(() => {
    setPaginaActual(1);
  }, [usuarios.length]);

  // Calcular usuarios para la página actual
  const indiceInicio = (paginaActual - 1) * usuariosPorPagina;
  const indiceFin = indiceInicio + usuariosPorPagina;
  const usuariosPagina = usuarios.slice(indiceInicio, indiceFin);
  const totalPaginas = Math.ceil(usuarios.length / usuariosPorPagina);

  // Ajustar página si está fuera de rango (por ejemplo, después de filtrar)
  useEffect(() => {
    if (totalPaginas > 0 && paginaActual > totalPaginas) {
      setPaginaActual(totalPaginas);
    }
  }, [totalPaginas, paginaActual]);

  const obtenerColorEstado = (estado) => {
    return estado === 'Activo' ? 'success' : 'danger';
  };

  const obtenerColorRol = (rol) => {
    return rol === 'Administrador' ? 'warning' : 'primary';
  };

  const obtenerIconoRol = (rol) => {
    return rol === 'Administrador' ? <IoShield className="text-sm" /> : <IoPerson className="text-sm" />;
  };

  const formatearFecha = (fechaString, esUltimoAcceso = false) => {
    if (!fechaString) return esUltimoAcceso ? 'Nunca' : 'N/A';
    try {
      return formatearSoloFechaCostaRica(fechaString);
    } catch (error) {
      return esUltimoAcceso ? 'Nunca' : 'N/A';
    }
  };

  const formatearHora = (fechaString) => {
    if (!fechaString) return '';
    try {
      return formatearSoloHoraCostaRica(fechaString);
    } catch (error) {
      return '';
    }
  };

  const columns = [
    { key: "usuario", label: "USUARIO" },
    { key: "rol", label: "ROL" },
    { key: "estado", label: "ESTADO" },
    { key: "ultimoAcceso", label: "ÚLTIMO ACCESO" },
    { key: "fechaCreacion", label: "FECHA CREACIÓN" },
    { key: "acciones", label: "ACCIONES" },
  ];

  const renderCell = (usuario, columnKey) => {
    switch (columnKey) {
      case "usuario":
        return (
          <div className="flex flex-col">
            <p className="font-medium text-small">
              {`${usuario.CT_Nombre} ${usuario.CT_Apellido_uno} ${usuario.CT_Apellido_dos || ''}`.trim()}
            </p>
            <p className="text-tiny text-default-700">
              {usuario.CT_Correo}
            </p>
          </div>
        );
      case "rol":
        return (
          <Chip
            color={obtenerColorRol(usuario.rol?.nombre)}
            variant="flat"
            startContent={obtenerIconoRol(usuario.rol?.nombre)}
            size="sm"
          >
            {usuario.rol?.nombre || 'Sin rol'}
          </Chip>
        );
      case "estado":
        return (
          <Chip
            color={obtenerColorEstado(usuario.estado?.nombre)}
            variant="flat"
            size="sm"
          >
            {usuario.estado?.nombre || 'Sin estado'}
          </Chip>
        );
      case "ultimoAcceso":
        return (
          <div className="flex flex-col" suppressHydrationWarning>
            <p className="font-medium text-small">
              {formatearFecha(usuario.CF_Ultimo_acceso, true)}
            </p>
            {usuario.CF_Ultimo_acceso && (
              <p className="text-tiny text-default-700">
                {formatearHora(usuario.CF_Ultimo_acceso)}
              </p>
            )}
          </div>
        );
      case "fechaCreacion":
        return (
          <div className="text-small" suppressHydrationWarning>
            {formatearFecha(usuario.CF_Fecha_creacion)}
          </div>
        );
      case "acciones":
        return (
          <div className="flex items-center justify-center gap-2">
            <Tooltip content="Ver detalles">
              <Button
                isIconOnly
                size="sm"
                variant="light"
                onPress={() => onVerDetalle(usuario)}
              >
                <IoEye className="h-6 w-6 text-default-600" />
              </Button>
            </Tooltip>
            
            <Dropdown>
              <DropdownTrigger>
                <Button
                  isIconOnly
                  size="sm"
                  variant="light"
                >
                  <IoEllipsisVertical className="h-6 w-6 text-default-600" />
                </Button>
              </DropdownTrigger>
              
              <DropdownMenu aria-label="Acciones del usuario">
                <DropdownItem
                  key="editar"
                  startContent={<IoPencil className="h-4 w-4" />}
                  onPress={() => handleAccionUsuario('editar', usuario)}
                >
                  Editar Usuario
                </DropdownItem>
                
                <DropdownItem
                  key="resetear"
                  startContent={<IoLockClosed className="h-4 w-4" />}
                  onPress={() => handleAccionUsuario('resetear', usuario)}
                >
                  Resetear Contraseña
                </DropdownItem>
              </DropdownMenu>
            </Dropdown>
          </div>
        );
      default:
        return null;
    }
  };

  const handleAccionUsuario = async (accion, usuario) => {
    switch (accion) {
      case 'editar':
        onEditarUsuario(usuario);
        break;
      case 'resetear':
        await onResetearContrasena(usuario);
        break;
      default:
        break;
    }
  };

  return (
    <Card>
      <CardHeader className="bg-white px-8 pt-6 pb-6">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 w-full">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-primary rounded-xl flex items-center justify-center shadow-md">
              <IoPeople className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900">Gestión de Usuarios</h3>
              <p className="text-sm text-gray-600 mt-1">
                Administra los usuarios del sistema
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-xl shadow-sm border border-gray-200/60">
              <IoPersonAdd className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-semibold text-gray-700">
                {usuarios.length} usuario{usuarios.length !== 1 ? 's' : ''} registrado{usuarios.length !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        </div>
      </CardHeader>
      
      <CardBody className="px-0 py-0">
        {cargando ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary mb-4"></div>
            <p className="text-gray-600 font-medium">Cargando usuarios...</p>
            <p className="text-sm text-gray-500 mt-2">Por favor, espera un momento</p>
          </div>
        ) : usuarios.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-12">
            <div className="bg-gray-100 rounded-full p-6 mb-4">
              <IoPeople className="w-14 h-14 text-gray-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">No se encontraron usuarios</h3>
            <p className="text-sm text-gray-500 text-center max-w-sm">
              Intenta ajustar los filtros de búsqueda para encontrar los usuarios que necesitas.
            </p>
          </div>
        ) : (
          <div className="px-6">
            <Table
              aria-label="Tabla de usuarios"
              removeWrapper
              isStriped
              classNames={{
                th: "bg-primary text-white first:rounded-l-lg last:rounded-r-lg",
                tbody: "divide-y divide-gray-200",
                tr: "hover:bg-gray-50 transition-colors duration-200",
              }}
            >
              <TableHeader columns={columns}>
                {(column) => (
                  <TableColumn
                    key={column.key}
                    className={`font-semibold ${column.key === 'acciones' ? 'text-center' : 'text-start'}`}
                  >
                    {column.label}
                  </TableColumn>
                )}
              </TableHeader>
              <TableBody items={usuariosPagina}>
                {(usuario) => (
                  <TableRow key={usuario.CN_Id_usuario}>
                    {(columnKey) => (
                      <TableCell className="py-4">{renderCell(usuario, columnKey)}</TableCell>
                    )}
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        )}
      </CardBody>

      {/* Paginación mejorada y responsive */}
      {!cargando && usuarios.length > 0 && totalPaginas > 1 && (
        <div className="flex flex-col sm:flex-row w-full justify-between items-center gap-4 px-4 sm:px-6 py-4 border-t border-gray-200">
          {/* Información de resultados - Oculta en móvil, visible en tablet+ */}
          <div className="hidden sm:block text-small text-default-700">
            Mostrando {indiceInicio + 1} a {Math.min(indiceFin, usuarios.length)} de {usuarios.length} resultados
          </div>
          
          {/* Información compacta para móvil */}
          <div className="block sm:hidden text-tiny text-default-700 text-center">
            {indiceInicio + 1}-{Math.min(indiceFin, usuarios.length)} de {usuarios.length}
          </div>
          
          {/* Paginación adaptativa */}
          <div className="flex justify-center w-full sm:w-auto">
            <Pagination
              isCompact
              showControls={totalPaginas > 3}
              showShadow
              color="primary"
              page={paginaActual}
              total={totalPaginas}
              onChange={setPaginaActual}
              initialPage={1}
              size="sm"
              siblings={1}
              boundaries={1}
            />
          </div>
        </div>
      )}
    </Card>
  );
};

export default TablaUsuarios;
