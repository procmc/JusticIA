import React from 'react';
import { Button, Card, CardBody } from '@heroui/react';
import { 
  IoPeople, 
  IoAdd, 
  IoSearch,
} from 'react-icons/io5';

const HeaderGestionUsuarios = ({ 
  filtroTexto, 
  onFiltroChange, 
  onCrearUsuario, 
  estadisticas, 
  usuariosFiltrados 
}) => {
  return (
    <Card className="bg-primary text-white shadow-lg border-none">
      <CardBody className="p-4 sm:p-6 lg:p-8">
        <div className="space-y-6">
          {/* Fila superior: Título, Input de búsqueda y botón */}
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 lg:gap-6">
            {/* Título y descripción */}
            <div className="flex items-center gap-3 sm:gap-4 flex-1">
              <div className="p-2 sm:p-3 bg-white/15 rounded-xl border border-white/20 flex-shrink-0">
                <IoPeople className="text-2xl sm:text-3xl lg:text-4xl text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-white mb-1 sm:mb-2 truncate">
                  Gestión de Usuarios
                </h1>
                <p className="text-white/80 text-sm sm:text-base">
                  Administra usuarios del sistema JusticIA
                </p>
              </div>
            </div>

            {/* Input de búsqueda y Botón Agregar */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 sm:gap-4">
              {/* Input de búsqueda */}
              <div className="relative w-full sm:w-52 lg:w-64 h-10 sm:h-12">
                <IoSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/70 text-base sm:text-lg pointer-events-none" />
                <input
                  type="text"
                  placeholder="Buscar usuarios..."
                  value={filtroTexto}
                  onChange={(e) => onFiltroChange(e.target.value)}
                  className="w-full h-full bg-white/10 border border-white/20 rounded-xl pl-9 sm:pl-10 pr-3 sm:pr-4 text-sm sm:text-base text-white placeholder:text-white/50 outline-none focus:border-white/40 focus:bg-white/15"
                />
              </div>

              {/* Botón Agregar */}
              <Button
                color="secondary"
                size="lg"
                startContent={<IoAdd className="text-lg sm:text-xl" />}
                className="bg-white text-primary font-bold hover:bg-white/95 px-3 sm:px-4 lg:px-6 py-2 sm:py-3 rounded-xl text-sm sm:text-base whitespace-nowrap"
                onPress={onCrearUsuario}
              >
                <span className="hidden sm:inline">Agregar Usuario</span>
                <span className="sm:hidden">Agregar</span>
              </Button>
            </div>
          </div>

          {/* Estadísticas */}
          <div className="pt-2">
            {estadisticas && (
              <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                {/* Activos */}
                <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                  <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-emerald-400 flex-shrink-0"></div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-white/90 font-semibold text-sm">{estadisticas.usuariosActivos}</span>
                    <span className="text-white/70 text-xs font-medium uppercase">Activos</span>
                  </div>
                  <div className="px-1.5 py-0.5 bg-emerald-500/20 rounded-full border border-emerald-400/30 flex-shrink-0">
                    <span className="text-emerald-200 text-xs font-bold">{estadisticas.porcentajeActivos}%</span>
                  </div>
                </div>

                {/* Inactivos */}
                <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                  <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-red-400 flex-shrink-0"></div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-white/90 font-semibold text-sm">{estadisticas.usuariosInactivos}</span>
                    <span className="text-white/70 text-xs font-medium uppercase">Inactivos</span>
                  </div>
                  <div className="px-1.5 py-0.5 bg-red-500/20 rounded-full border border-red-400/30 flex-shrink-0">
                    <span className="text-red-200 text-xs font-bold">{estadisticas.porcentajeInactivos}%</span>
                  </div>
                </div>

                {/* Total */}
                <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                  <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-blue-400 flex-shrink-0"></div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-white/90 font-semibold text-sm">{estadisticas.totalUsuarios}</span>
                    <span className="text-white/70 text-xs font-medium uppercase">Total</span>
                  </div>
                </div>

                {/* Indicador de resultados de búsqueda */}
                {filtroTexto && (
                  <div className="flex items-center gap-2 bg-white/15 px-3 py-2 rounded-lg border border-white/30 h-10 sm:h-12">
                    <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-yellow-400 flex-shrink-0"></div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-white/90 font-semibold text-sm">{usuariosFiltrados.length}</span>
                      <span className="text-white/70 text-xs font-medium uppercase">Resultados</span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

export default HeaderGestionUsuarios;
