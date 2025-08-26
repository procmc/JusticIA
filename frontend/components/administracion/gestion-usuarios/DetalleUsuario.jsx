import React from 'react';
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Card,
  CardBody,
  Chip,
  Divider
} from '@heroui/react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { 
  IoPerson, 
  IoMail, 
  IoCall, 
  IoCard, 
  IoBriefcase, 
  IoCalendar, 
  IoTime, 
  IoShield,
  IoPencil,
  IoCheckmark,
  IoClose
} from 'react-icons/io5';

const DetalleUsuario = ({ 
  usuario, 
  isOpen, 
  onClose, 
  onEditar, 
  onCambiarEstado 
}) => {
  if (!usuario) return null;

  const formatearFecha = (fechaString) => {
    if (!fechaString) return 'No disponible';
    try {
      return format(new Date(fechaString), 'dd \'de\' MMMM \'de\' yyyy \'a las\' HH:mm', { locale: es });
    } catch (error) {
      return 'Fecha inválida';
    }
  };

  const obtenerColorEstado = (estado) => {
    return estado === 'Activo' ? 'success' : 'danger';
  };

  const obtenerColorRol = (rol) => {
    return rol === 'Administrador' ? 'warning' : 'primary';
  };

  const obtenerIconoRol = (rol) => {
    return rol === 'Administrador' ? <IoShield className="text-lg" /> : <IoPerson className="text-lg" />;
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      size="2xl"
      scrollBehavior="inside"
      placement="center"
    >
      <ModalContent>
        <ModalHeader className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            {obtenerIconoRol(usuario.rolNombre)}
            <span>Detalles del Usuario</span>
          </div>
          <p className="text-sm text-gray-500 font-normal">
            Información completa del usuario seleccionado
          </p>
        </ModalHeader>
        
        <ModalBody>
          <div className="space-y-6">
            {/* Información Personal */}
            <Card>
              <CardBody className="space-y-4">
                <h4 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <IoPerson className="text-primary" />
                  Información Personal
                </h4>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-600 dark:text-gray-300">
                      Nombre Completo
                    </label>
                    <p className="text-gray-900 dark:text-white font-medium">
                      {usuario.nombre}
                    </p>
                  </div>
                  
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-600 dark:text-gray-300">
                      Nombre de Usuario
                    </label>
                    <p className="text-gray-900 dark:text-white font-mono">
                      @{usuario.nombreUsuario}
                    </p>
                  </div>
                  
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-600 dark:text-gray-300 flex items-center gap-1">
                      <IoMail className="text-sm" />
                      Correo Electrónico
                    </label>
                    <p className="text-gray-900 dark:text-white">
                      {usuario.correo}
                    </p>
                  </div>
                  
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-600 dark:text-gray-300 flex items-center gap-1">
                      <IoCall className="text-sm" />
                      Teléfono
                    </label>
                    <p className="text-gray-900 dark:text-white">
                      {usuario.telefono}
                    </p>
                  </div>
                  
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-600 dark:text-gray-300 flex items-center gap-1">
                      <IoCard className="text-sm" />
                      Cédula
                    </label>
                    <p className="text-gray-900 dark:text-white">
                      {usuario.cedula}
                    </p>
                  </div>
                  
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-600 dark:text-gray-300 flex items-center gap-1">
                      <IoBriefcase className="text-sm" />
                      Cargo
                    </label>
                    <p className="text-gray-900 dark:text-white">
                      {usuario.cargo}
                    </p>
                  </div>
                </div>
              </CardBody>
            </Card>

            {/* Estado y Rol */}
            <Card>
              <CardBody className="space-y-4">
                <h4 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <IoShield className="text-primary" />
                  Rol y Estado
                </h4>
                
                <div className="flex flex-wrap gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-600 dark:text-gray-300">
                      Rol Asignado
                    </label>
                    <div>
                      <Chip
                        color={obtenerColorRol(usuario.rolNombre)}
                        variant="flat"
                        startContent={obtenerIconoRol(usuario.rolNombre)}
                        size="md"
                      >
                        {usuario.rolNombre}
                      </Chip>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-600 dark:text-gray-300">
                      Estado Actual
                    </label>
                    <div>
                      <Chip
                        color={obtenerColorEstado(usuario.estadoNombre)}
                        variant="flat"
                        size="md"
                      >
                        {usuario.estadoNombre}
                      </Chip>
                    </div>
                  </div>
                </div>
              </CardBody>
            </Card>

            {/* Fechas de Actividad */}
            <Card>
              <CardBody className="space-y-4">
                <h4 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <IoTime className="text-primary" />
                  Actividad del Usuario
                </h4>
                
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <IoCalendar className="text-green-500 mt-1" />
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">
                        Fecha de Creación
                      </p>
                      <p className="text-sm text-gray-600 dark:text-gray-300">
                        {formatearFecha(usuario.fechaCreacion)}
                      </p>
                    </div>
                  </div>
                  
                  <Divider />
                  
                  <div className="flex items-start gap-3">
                    <IoTime className="text-blue-500 mt-1" />
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">
                        Último Acceso
                      </p>
                      <p className="text-sm text-gray-600 dark:text-gray-300">
                        {formatearFecha(usuario.ultimoAcceso)}
                      </p>
                    </div>
                  </div>
                </div>
              </CardBody>
            </Card>
          </div>
        </ModalBody>
        
        <ModalFooter>
          <Button
            color="danger"
            variant="flat"
            onPress={onClose}
          >
            Cerrar
          </Button>
          
          <Button
            color="primary"
            startContent={<IoPencil className="text-lg" />}
            onPress={() => {
              onEditar(usuario);
              onClose();
            }}
          >
            Editar Usuario
          </Button>
          
          {usuario.estadoNombre === 'Activo' ? (
            <Button
              color="warning"
              variant="flat"
              startContent={<IoClose className="text-lg" />}
              onPress={() => {
                onCambiarEstado(usuario, 'Inactivo');
                onClose();
              }}
            >
              Desactivar
            </Button>
          ) : (
            <Button
              color="success"
              variant="flat"
              startContent={<IoCheckmark className="text-lg" />}
              onPress={() => {
                onCambiarEstado(usuario, 'Activo');
                onClose();
              }}
            >
              Activar
            </Button>
          )}
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default DetalleUsuario;
