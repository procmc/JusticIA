import React from 'react';
import { Button, Card, CardBody, Tabs, Tab } from '@heroui/react';
import { 
  IoShield, 
  IoDocumentText, 
  IoStatsChart,
  IoFunnel
} from 'react-icons/io5';

const HeaderBitacora = ({ 
  vistaActual, 
  onVistaChange, 
  estadisticas, 
  registrosFiltrados,
  filtrosActivos = false
}) => {
  return (
    <Card className="bg-primary text-white shadow-lg border-none">
      <CardBody className="p-4 sm:p-6 lg:p-8">
        <div className="space-y-6">
          {/* Fila superior: Título y navegación */}
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 lg:gap-6">
            {/* Título y descripción */}
            <div className="flex items-center gap-3 sm:gap-4 flex-1">
              <div className="p-2 sm:p-3 bg-white/15 rounded-xl border border-white/20 flex-shrink-0">
                <IoShield className="text-2xl sm:text-3xl lg:text-4xl text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-white mb-1 sm:mb-2 truncate">
                  Bitácora del Sistema
                </h1>
                <p className="text-white/80 text-sm sm:text-base">
                  Monitoreo y registro de actividades del sistema
                </p>
              </div>
            </div>

            {/* Navegación de pestañas */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 sm:gap-4">
              <Tabs
                selectedKey={vistaActual}
                onSelectionChange={onVistaChange}
                variant="underlined"
                classNames={{
                  tabList: "bg-white/10 p-1 rounded-lg border border-white/20",
                  tab: "text-white/70 data-[selected=true]:text-white px-3 sm:px-4 py-2",
                  cursor: "bg-white/20 rounded-md",
                  panel: "p-0"
                }}
              >
                <Tab
                  key="registros"
                  title={
                    <div className="flex items-center gap-2">
                      <IoDocumentText className="text-base sm:text-lg" />
                      <span className="hidden sm:inline">Registros</span>
                    </div>
                  }
                />
                <Tab
                  key="estadisticas"
                  title={
                    <div className="flex items-center gap-2">
                      <IoStatsChart className="text-base sm:text-lg" />
                      <span className="hidden sm:inline">Estadísticas</span>
                    </div>
                  }
                />
              </Tabs>
            </div>
          </div>

          {/* Estadísticas - Solo mostrar en vista de registros */}
          {vistaActual === 'registros' && estadisticas && (
            <div className="pt-2">
              <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                {/* Total de registros */}
                <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                  <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-blue-400 flex-shrink-0"></div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-white/90 font-semibold text-sm">{estadisticas.totalRegistros}</span>
                    <span className="text-white/70 text-xs font-medium uppercase">Total</span>
                  </div>
                </div>

                {/* Procesados */}
                <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                  <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-emerald-400 flex-shrink-0"></div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-white/90 font-semibold text-sm">{estadisticas.procesados}</span>
                    <span className="text-white/70 text-xs font-medium uppercase">Procesados</span>
                  </div>
                  <div className="px-1.5 py-0.5 bg-emerald-500/20 rounded-full border border-emerald-400/30 flex-shrink-0">
                    <span className="text-emerald-200 text-xs font-bold">{estadisticas.porcentajeProcesados}%</span>
                  </div>
                </div>

                {/* Errores */}
                <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                  <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-red-400 flex-shrink-0"></div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-white/90 font-semibold text-sm">{estadisticas.errores}</span>
                    <span className="text-white/70 text-xs font-medium uppercase">Errores</span>
                  </div>
                  <div className="px-1.5 py-0.5 bg-red-500/20 rounded-full border border-red-400/30 flex-shrink-0">
                    <span className="text-red-200 text-xs font-bold">{estadisticas.porcentajeErrores}%</span>
                  </div>
                </div>

                {/* Pendientes */}
                <div className="flex items-center gap-2 bg-white/10 hover:bg-white/15 px-3 py-2 rounded-lg border border-white/20 h-10 sm:h-12">
                  <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-yellow-400 flex-shrink-0"></div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-white/90 font-semibold text-sm">{estadisticas.pendientes}</span>
                    <span className="text-white/70 text-xs font-medium uppercase">Pendientes</span>
                  </div>
                  <div className="px-1.5 py-0.5 bg-yellow-500/20 rounded-full border border-yellow-400/30 flex-shrink-0">
                    <span className="text-yellow-200 text-xs font-bold">{estadisticas.porcentajePendientes}%</span>
                  </div>
                </div>

                {/* Indicador de filtros activos */}
                {filtrosActivos && (
                  <div className="flex items-center gap-2 bg-white/15 px-3 py-2 rounded-lg border border-white/30 h-10 sm:h-12">
                    <IoFunnel className="text-white/90 text-sm" />
                    <div className="flex items-center gap-1.5">
                      <span className="text-white/90 font-semibold text-sm">{registrosFiltrados.length}</span>
                      <span className="text-white/70 text-xs font-medium uppercase">Filtrados</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </CardBody>
    </Card>
  );
};

export default HeaderBitacora;
