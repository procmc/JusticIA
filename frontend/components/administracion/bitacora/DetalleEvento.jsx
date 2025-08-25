import React from 'react';
import { 
  Chip,
  Divider
} from '@heroui/react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import DrawerGeneral from '../../ui/DrawerGeneral';

const DetalleEvento = ({ registro, isOpen, onClose }) => {
  if (!registro) return null;

  const obtenerColorEstado = (estado) => {
    switch (estado) {
      case 'Procesado':
        return 'success';
      case 'Pendiente':
        return 'warning';
      case 'Error':
        return 'danger';
      default:
        return 'default';
    }
  };

  const obtenerColorTipoAccion = (tipo) => {
    switch (tipo) {
      case 'Consulta':
        return 'primary';
      case 'Carga':
        return 'secondary';
      case 'Búsqueda similares':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <DrawerGeneral
      titulo={`Detalle del Evento #${registro.id}`}
      isOpen={isOpen}
      onOpenChange={onClose}
      size="xl"
      botonCerrar={{ 
        mostrar: true, 
        texto: "Cerrar",
        onPress: () => onClose(false)
      }}
    >
      <div className="space-y-6">
        {/* Información Principal */}
        <div className="space-y-4">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-slate-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
              </svg>
            </div>
            <h4 className="text-lg font-semibold text-gray-800">
              Información del Evento
            </h4>
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-8 gap-y-4">
            <div className="flex flex-col space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-slate-400 rounded-full"></div>
                <p className="text-sm font-medium text-gray-600 uppercase tracking-wide">Fecha y Hora</p>
              </div>
              <div className="ml-4 space-y-1">
                <p className="font-semibold text-gray-900 text-lg">
                  {format(registro.fechaHora, 'dd/MM/yyyy', { locale: es })}
                </p>
                <p className="text-sm text-gray-600 font-mono">
                  {format(registro.fechaHora, 'HH:mm:ss')}
                </p>
              </div>
            </div>

            <div className="flex flex-col space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-slate-400 rounded-full"></div>
                <p className="text-sm font-medium text-gray-600 uppercase tracking-wide">Estado</p>
              </div>
              <div className="ml-4">
                <Chip 
                  color={obtenerColorEstado(registro.estado)}
                  variant="flat"
                  size="md"
                  className="font-medium"
                >
                  {registro.estado}
                </Chip>
              </div>
            </div>

            <div className="flex flex-col space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-slate-400 rounded-full"></div>
                <p className="text-sm font-medium text-gray-600 uppercase tracking-wide">Tipo de Acción</p>
              </div>
              <div className="ml-4">
                <Chip 
                  color={obtenerColorTipoAccion(registro.tipoAccion)}
                  variant="flat"
                  size="md"
                  className="font-medium"
                >
                  {registro.tipoAccion}
                </Chip>
              </div>
            </div>

            <div className="flex flex-col space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-slate-400 rounded-full"></div>
                <p className="text-sm font-medium text-gray-600 uppercase tracking-wide">Expediente</p>
              </div>
              <div className="ml-4">
                <code className="text-sm font-mono bg-gray-100 px-3 py-1 rounded text-gray-800">
                  {registro.expediente}
                </code>
              </div>
            </div>
          </div>
        </div>

        <Divider className="bg-gradient-to-r from-transparent via-gray-300 to-transparent h-px" />

        {/* Información del Usuario */}
        <div className="space-y-4">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-slate-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
              </svg>
            </div>
            <h4 className="text-lg font-semibold text-gray-800">
              Usuario
            </h4>
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-8 gap-y-4">
            <div className="flex flex-col space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-slate-400 rounded-full"></div>
                <p className="text-sm font-medium text-gray-600 uppercase tracking-wide">Usuario</p>
              </div>
              <p className="ml-4 text-gray-900 font-medium text-base">{registro.usuario}</p>
            </div>

            <div className="flex flex-col space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-slate-400 rounded-full"></div>
                <p className="text-sm font-medium text-gray-600 uppercase tracking-wide">Correo</p>
              </div>
              <p className="ml-4 text-gray-900 font-medium text-base">{registro.correoUsuario}</p>
            </div>

            <div className="flex flex-col space-y-2 lg:col-span-2">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-slate-400 rounded-full"></div>
                <p className="text-sm font-medium text-gray-600 uppercase tracking-wide">Rol del Sistema</p>
              </div>
              <p className="ml-4 text-gray-900 font-medium text-base">{registro.rolUsuario}</p>
            </div>
          </div>
        </div>

        <Divider className="bg-gradient-to-r from-transparent via-gray-300 to-transparent h-px" />

        {/* Detalles de la Acción */}
        <div className="space-y-4">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-slate-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm0 4a1 1 0 011-1h12a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1V8zm6 2a1 1 0 000 2h2a1 1 0 100-2H9z" clipRule="evenodd" />
              </svg>
            </div>
            <h4 className="text-lg font-semibold text-gray-800">
              Detalles de la Acción
            </h4>
          </div>
          
          <div className="space-y-4">
            <div className="flex flex-col space-y-3">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-slate-400 rounded-full"></div>
                <p className="text-sm font-medium text-gray-600 uppercase tracking-wide">Descripción</p>
              </div>
              <div className="ml-4 pl-4 border-l-2 border-gray-200">
                <p className="text-gray-800 text-base leading-relaxed">
                  {registro.texto || 'Sin descripción disponible'}
                </p>
              </div>
            </div>

            {registro.informacionAdicional && (
              <div className="flex flex-col space-y-3">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-slate-400 rounded-full"></div>
                  <p className="text-sm font-medium text-gray-600 uppercase tracking-wide">Información Adicional</p>
                </div>
                <div className="ml-4 pl-4 border-l-2 border-gray-200">
                  <p className="text-gray-800 text-base leading-relaxed">
                    {registro.informacionAdicional}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </DrawerGeneral>
  );
};

export default DetalleEvento;
