import React from 'react';
import {
  Chip,
  Avatar,
  Card,
  CardBody,
  Divider,
  Badge
} from '@heroui/react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { 
  IoPerson, 
  IoMail, 
  IoCalendar, 
  IoTime, 
  IoShield,
  IoCheckmarkCircle,
  IoCloseCircle,
  IoPersonCircle,
  IoStatsChart
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
    const colores = {
      'Administrador': 'warning',
      'Usuario': 'primary',
      'Supervisor': 'secondary',
      'Editor': 'success'
    };
    return colores[rol] || 'default';
  };

  const obtenerIconoRol = (rol) => {
    const iconos = {
      'Administrador': <IoShield className="w-4 h-4" />,
      'Usuario': <IoPersonCircle className="w-4 h-4" />,
      'Supervisor': <IoShield className="w-4 h-4" />,
      'Editor': <IoPerson className="w-4 h-4" />
    };
    return iconos[rol] || <IoPerson className="w-4 h-4" />;
  };

  const obtenerIniciales = (nombre, correo) => {
    if (nombre && nombre.length >= 2) {
      return nombre.substring(0, 2).toUpperCase();
    }
    if (correo && correo.length >= 2) {
      return correo.substring(0, 2).toUpperCase();
    }
    return 'US';
  };

  const calcularDiasDesdeCreacion = (fechaCreacion) => {
    if (!fechaCreacion) return 0;
    const fecha = new Date(fechaCreacion);
    const hoy = new Date();
    const diferencia = hoy - fecha;
    return Math.floor(diferencia / (1000 * 60 * 60 * 24));
  };

  return (
    <DrawerGeneral
      isOpen={isOpen}
      onOpenChange={(open) => !open && onClose()}
      titulo=""
      size="lg"
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
      <div className="space-y-6">
        {/* Header Premium */}
        <div className="relative overflow-hidden">
          {/* Background Pattern */}
          <div className="absolute inset-0 bg-primary/5"></div>
          <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 rounded-full -translate-y-16 translate-x-16"></div>
          <div className="absolute bottom-0 left-0 w-24 h-24 bg-primary/10 rounded-full translate-y-12 -translate-x-12"></div>
          
          <div className="relative p-6 text-center">
            <div className="inline-block relative mb-4">
              <div className="w-20 h-20 bg-gradient-to-br from-primary to-primary/70 rounded-full flex items-center justify-center shadow-lg">
                <span className="text-white text-xl font-bold">
                  {obtenerIniciales(usuario.CT_Nombre_usuario, usuario.CT_Correo)}
                </span>
              </div>
              <div className="absolute -bottom-1 -right-1">
                <div className={`w-6 h-6 rounded-full border-2 border-white shadow-sm flex items-center justify-center ${
                  usuario.estado?.nombre === 'Activo' ? 'bg-green-500' : 'bg-red-500'
                }`}>
                  {usuario.estado?.nombre === 'Activo' ? 
                    <IoCheckmarkCircle className="w-3 h-3 text-white" /> : 
                    <IoCloseCircle className="w-3 h-3 text-white" />
                  }
                </div>
              </div>
            </div>
            
            <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-1">
              {usuario.CT_Correo || usuario.correo}
            </h1>
            
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
              @{usuario.CT_Nombre_usuario || usuario.nombreUsuario}
            </p>
            
            <div className="flex justify-center gap-2">
              <div className={`px-4 py-2 rounded-full text-sm font-medium flex items-center gap-2 ${
                obtenerColorRol(usuario.rol?.nombre) === 'warning' 
                  ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400'
                  : 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
              }`}>
                {obtenerIconoRol(usuario.rol?.nombre)}
                <span>{usuario.rol?.nombre || 'Sin rol'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950/50 dark:to-blue-900/30 rounded-md p-2 text-center">
            <div className="w-6 h-6 bg-blue-500 rounded-sm flex items-center justify-center mx-auto mb-1">
              <IoCalendar className="w-3 h-3 text-white" />
            </div>
            <p className="text-sm font-bold text-blue-600 dark:text-blue-400">
              {calcularDiasDesdeCreacion(usuario.CF_Fecha_creacion)}
            </p>
            <p className="text-xs text-gray-600 dark:text-gray-400">Días activo</p>
          </div>
          
          <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-950/50 dark:to-emerald-900/30 rounded-md p-2 text-center">
            <div className="w-6 h-6 bg-emerald-500 rounded-sm flex items-center justify-center mx-auto mb-1">
              <IoShield className="w-3 h-3 text-white" />
            </div>
            <p className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
              {usuario.CN_Id_usuario}
            </p>
            <p className="text-xs text-gray-600 dark:text-gray-400">Identidad</p>
          </div>
          
          <div className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-950/50 dark:to-purple-900/30 rounded-md p-2 text-center">
            <div className="w-6 h-6 bg-purple-500 rounded-sm flex items-center justify-center mx-auto mb-1">
              {usuario.estado?.nombre === 'Activo' ? 
                <IoCheckmarkCircle className="w-3 h-3 text-white" /> : 
                <IoCloseCircle className="w-3 h-3 text-white" />
              }
            </div>
            <p className="text-sm font-bold text-purple-600 dark:text-purple-400">
              {usuario.estado?.nombre === 'Activo' ? 'ON' : 'OFF'}
            </p>
            <p className="text-xs text-gray-600 dark:text-gray-400">Estado</p>
          </div>
        </div>

        {/* Detailed Information */}
        <div className="space-y-4">
          {/* Timeline Style Info */}
          <div className="relative">
            <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gradient-to-b from-blue-500 to-purple-500"></div>
            
            <div className="relative pl-10 pb-6">
              <div className="absolute left-2 w-4 h-4 bg-blue-500 rounded-full border-2 border-white shadow-sm"></div>
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-100 dark:border-gray-700">
                <div className="flex items-center gap-2 mb-2">
                  <IoCalendar className="w-4 h-4 text-blue-500" />
                  <span className="font-medium text-gray-900 dark:text-white">Cuenta creada</span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {format(new Date(usuario.CF_Fecha_creacion || new Date()), 'EEEE, dd \'de\' MMMM \'de\' yyyy', { locale: es })}
                </p>
                <p className="text-xs text-blue-500 mt-1">
                  Hace {calcularDiasDesdeCreacion(usuario.CF_Fecha_creacion)} días
                </p>
              </div>
            </div>
            
            <div className="relative pl-10">
              <div className="absolute left-2 w-4 h-4 bg-purple-500 rounded-full border-2 border-white shadow-sm"></div>
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-100 dark:border-gray-700">
                <div className="flex items-center gap-2 mb-2">
                  <IoTime className="w-4 h-4 text-purple-500" />
                  <span className="font-medium text-gray-900 dark:text-white">Último acceso</span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {usuario.CF_Ultimo_acceso 
                    ? format(new Date(usuario.CF_Ultimo_acceso), 'dd/MM/yyyy \'a las\' HH:mm', { locale: es })
                    : 'Nunca ha iniciado sesión'
                  }
                </p>
                {usuario.CF_Ultimo_acceso && (
                  <div className="flex items-center gap-1 mt-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-xs text-green-600 dark:text-green-400">Activo recientemente</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* User Details Card */}
          <div className="bg-gradient-to-r from-gray-50 via-white to-gray-50 dark:from-gray-800 dark:via-gray-900 dark:to-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <IoPerson className="w-5 h-5 text-primary" />
              Información de Usuario
            </h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Nombre de Usuario
                </label>
                <p className="text-sm font-medium text-gray-900 dark:text-white mt-1">
                  {usuario.CT_Nombre_usuario || usuario.nombreUsuario}
                </p>
              </div>
              
              <div>
                <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Email
                </label>
                <p className="text-sm font-medium text-gray-900 dark:text-white mt-1 break-all">
                  {usuario.CT_Correo || usuario.correo}
                </p>
              </div>
            </div>
            
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${
                    usuario.estado?.nombre === 'Activo' ? 'bg-green-500' : 'bg-red-500'
                  }`}></div>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {usuario.estado?.nombre || 'Sin estado'}
                  </span>
                </div>
                
                <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                  {obtenerIconoRol(usuario.rol?.nombre)}
                  <span>{usuario.rol?.nombre || 'Sin rol'}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DrawerGeneral>
  );
};

export default DetalleUsuario;
