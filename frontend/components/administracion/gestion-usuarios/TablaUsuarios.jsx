import React, { useState } from 'react';
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
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { 
  IoPeople, 
  IoEllipsisVertical, 
  IoEye, 
  IoPencil, 
  IoLockClosed, 
  IoCheckmark, 
  IoClose,
  IoShield,
  IoPerson
} from 'react-icons/io5';

const TablaUsuarios = ({ 
  usuarios, 
  onVerDetalle, 
  onEditarUsuario, 
  onCambiarEstado, 
  onResetearContrasena 
}) => {
  const [paginaActual, setPaginaActual] = useState(1);
  const usuariosPorPagina = 10;

  // Calcular usuarios para la página actual
  const indiceInicio = (paginaActual - 1) * usuariosPorPagina;
  const indiceFin = indiceInicio + usuariosPorPagina;
  const usuariosPagina = usuarios.slice(indiceInicio, indiceFin);
  const totalPaginas = Math.ceil(usuarios.length / usuariosPorPagina);

  const obtenerColorEstado = (estado) => {
    return estado === 'Activo' ? 'success' : 'danger';
  };

  const obtenerColorRol = (rol) => {
    return rol === 'Administrador' ? 'warning' : 'primary';
  };

  const obtenerIconoRol = (rol) => {
    return rol === 'Administrador' ? <IoShield className="text-sm" /> : <IoPerson className="text-sm" />;
  };

  const formatearFecha = (fechaString) => {
    if (!fechaString) return 'Nunca';
    try {
      return format(new Date(fechaString), 'dd/MM/yyyy HH:mm', { locale: es });
    } catch (error) {
      return 'Fecha inválida';
    }
  };

  const formatearFechaCorta = (fechaString) => {
    if (!fechaString) return 'N/A';
    try {
      return format(new Date(fechaString), 'dd/MM/yyyy', { locale: es });
    } catch (error) {
      return 'N/A';
    }
  };

  const handleAccionUsuario = (accion, usuario) => {
    switch (accion) {
      case 'ver':
        onVerDetalle(usuario);
        break;
      case 'editar':
        onEditarUsuario(usuario);
        break;
      case 'activar':
        onCambiarEstado(usuario, 'Activo');
        break;
      case 'desactivar':
        onCambiarEstado(usuario, 'Inactivo');
        break;
      case 'resetear':
        onResetearContrasena(usuario);
        break;
      default:
        break;
    }
  };

  return (
    <Card>
      <CardHeader className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <IoPeople className="text-lg text-primary" />
          <h3 className="text-lg font-semibold">
            Lista de Usuarios ({usuarios.length})
          </h3>
        </div>
      </CardHeader>
      
      <CardBody className="p-0">
        {usuarios.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <IoPeople className="text-6xl mb-4 opacity-50" />
            <p className="text-lg">No se encontraron usuarios</p>
            <p className="text-sm">Intenta ajustar los filtros de búsqueda</p>
          </div>
        ) : (
          <>
            <Table
              aria-label="Tabla de usuarios"
              classNames={{
                wrapper: "rounded-none shadow-none",
              }}
              color='primary'
            >
              <TableHeader>
                <TableColumn>USUARIO</TableColumn>
                <TableColumn className="text-center">ROL</TableColumn>
                <TableColumn className="text-center">ESTADO</TableColumn>
                <TableColumn className="text-center">ÚLTIMO ACCESO</TableColumn>
                <TableColumn className="text-center">FECHA CREACIÓN</TableColumn>
                <TableColumn className="text-center">ACCIONES</TableColumn>
              </TableHeader>
              
              <TableBody>
                {usuariosPagina.map((usuario) => (
                  <TableRow key={usuario.id}>
                    <TableCell>
                      <div className="flex flex-col items-start">
                        <div className="font-semibold text-gray-900 dark:text-white">
                          {usuario.nombre}
                        </div>
                        <div className="text-sm text-gray-500">
                          {usuario.correo}
                        </div>
                        <div className="text-xs text-gray-400">
                          @{usuario.nombreUsuario}
                        </div>
                      </div>
                    </TableCell>
                    
                    <TableCell className="text-center">
                      <div className="flex justify-center">
                        <Chip
                          color={obtenerColorRol(usuario.rolNombre)}
                          variant="flat"
                          startContent={obtenerIconoRol(usuario.rolNombre)}
                          size="sm"
                        >
                          {usuario.rolNombre}
                        </Chip>
                      </div>
                    </TableCell>
                    
                    <TableCell className="text-center">
                      <div className="flex justify-center">
                        <Chip
                          color={obtenerColorEstado(usuario.estadoNombre)}
                          variant="flat"
                          size="sm"
                        >
                          {usuario.estadoNombre}
                        </Chip>
                      </div>
                    </TableCell>
                    
                    <TableCell className="text-center">
                      <div className="text-sm">
                        {formatearFecha(usuario.ultimoAcceso)}
                      </div>
                    </TableCell>
                    
                    <TableCell className="text-center">
                      <div className="text-sm">
                        {formatearFechaCorta(usuario.fechaCreacion)}
                      </div>
                    </TableCell>
                    
                    <TableCell className="text-center">
                      <div className="flex items-center justify-center gap-2">
                        <Tooltip content="Ver detalles">
                          <Button
                            isIconOnly
                            size="sm"
                            variant="light"
                            onPress={() => handleAccionUsuario('ver', usuario)}
                          >
                            <IoEye className="h-6 w-6 text-default-700" />
                          </Button>
                        </Tooltip>
                        
                        <Dropdown>
                          <DropdownTrigger>
                            <Button
                              isIconOnly
                              size="sm"
                              variant="light"
                            >
                              <IoEllipsisVertical className="h-6 w-6 text-default-700" />
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
                            
                            {usuario.estadoNombre === 'Activo' ? (
                              <DropdownItem
                                key="desactivar"
                                className="text-danger"
                                color="danger"
                                startContent={<IoClose className="h-4 w-4" />}
                                onPress={() => handleAccionUsuario('desactivar', usuario)}
                              >
                                Desactivar Usuario
                              </DropdownItem>
                            ) : (
                              <DropdownItem
                                key="activar"
                                className="text-success"
                                color="success"
                                startContent={<IoCheckmark className="h-4 w-4" />}
                                onPress={() => handleAccionUsuario('activar', usuario)}
                              >
                                Activar Usuario
                              </DropdownItem>
                            )}
                          </DropdownMenu>
                        </Dropdown>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            
            {/* Paginación */}
            {totalPaginas > 1 && (
              <div className="flex justify-center py-4">
                <Pagination
                  total={totalPaginas}
                  page={paginaActual}
                  onChange={setPaginaActual}
                  showControls
                  showShadow
                  color="primary"
                />
              </div>
            )}
          </>
        )}
      </CardBody>
    </Card>
  );
};

export default TablaUsuarios;
