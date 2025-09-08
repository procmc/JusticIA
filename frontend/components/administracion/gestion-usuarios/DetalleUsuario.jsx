import React from 'react';
import {
  Chip
} from '@heroui/react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { 
  IoPerson, 
  IoMail, 
  IoCalendar, 
  IoTime, 
  IoShield
} from 'react-icons/io5';
import DrawerGeneral from '../../ui/DrawerGeneral';

const DetalleUsuario = ({ 
  usuario, 
  isOpen, 
  onClose, 
  onEditar
}) => {
  if (!usuario) return null;

  const formatearFecha = (fechaString, esUltimoAcceso = false) => {
    if (!fechaString) return esUltimoAcceso ? 'El usuario nunca ha iniciado sesión' : 'No disponible';
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

  return (
    <DrawerGeneral
      isOpen={isOpen}
      onOpenChange={(open) => !open && onClose()}
      titulo="Detalles del Usuario"
      size="xl"
      botonCerrar={{
        mostrar: true,
        texto: "Cerrar"
      }}
      botonAccion={{
        texto: "Editar Usuario",
        onPress: () => {
          onEditar(usuario);
          onClose();
        },
        color: "primary"
      }}
    >
      <div className="space-y-8">
        <div className="border-l-4 border-gray-300 dark:border-gray-600 pl-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Información completa del usuario seleccionado
          </p>
        </div>

        {/* Información de Acceso */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-2">
            Información de Acceso
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-600 dark:text-gray-300">
                Nombre de Usuario
              </label>
              <p className="text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-800 px-3 py-2 rounded border">
                {usuario.CT_Nombre_usuario || usuario.nombreUsuario}
              </p>
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-600 dark:text-gray-300">
                Correo Electrónico
              </label>
              <p className="text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-800 px-3 py-2 rounded border">
                {usuario.CT_Correo || usuario.correo}
              </p>
            </div>
          </div>
        </div>

        {/* Rol y Estado */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-2">
            Permisos y Estado
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-600 dark:text-gray-300">
                Rol Asignado
              </label>
              <div>
                <Chip
                  color={obtenerColorRol(usuario.rol?.nombre)}
                  variant="flat"
                  size="md"
                  className="font-medium"
                >
                  {usuario.rol?.nombre || 'Sin rol'}
                </Chip>
              </div>
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-600 dark:text-gray-300">
                Estado Actual
              </label>
              <div>
                <Chip
                  color={obtenerColorEstado(usuario.estado?.nombre)}
                  variant="flat"
                  size="md"
                  className="font-medium"
                >
                  {usuario.estado?.nombre || 'Sin estado'}
                </Chip>
              </div>
            </div>
          </div>
        </div>

        {/* Actividad del Usuario */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-2">
            Historial de Actividad
          </h3>
          
          <div className="space-y-4">
            <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded border">
              <div className="flex items-center gap-3 mb-2">
                <IoCalendar className="text-gray-500" />
                <p className="font-medium text-gray-900 dark:text-white">
                  Fecha de Creación
                </p>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-300 ml-6">
                {formatearFecha(usuario.CF_Fecha_creacion)}
              </p>
            </div>
            
            <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded border">
              <div className="flex items-center gap-3 mb-2">
                <IoTime className="text-gray-500" />
                <p className="font-medium text-gray-900 dark:text-white">
                  Último Acceso
                </p>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-300 ml-6">
                {formatearFecha(usuario.CF_Ultimo_acceso, true)}
              </p>
            </div>
          </div>
        </div>
      </div>
    </DrawerGeneral>
  );
};

export default DetalleUsuario;
