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
          {/* Fila superior: Título y filtros */}
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 sm:gap-4">
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

            {/* Indicador de filtros activos - Arriba derecha */}
            {vistaActual === 'registros' && filtrosActivos && (
              <div className="flex items-center gap-2 bg-white/15 px-4 py-2 rounded-lg border border-white/30">
                <IoFunnel className="text-white/90 text-sm" />
                <div className="flex items-center gap-1.5">
                  <span className="text-white/90 font-semibold text-sm">{registrosFiltrados.length}</span>
                  <span className="text-white/70 text-xs font-medium uppercase">Registros Filtrados</span>
                </div>
              </div>
            )}
          </div>

          {/* Navegación de pestañas */}
          <div className="flex items-center justify-center sm:justify-start">
            <Tabs
              selectedKey={vistaActual}
              onSelectionChange={onVistaChange}
              variant="light"
              size="lg"
              classNames={{
                tabList: "bg-white/10 p-1 rounded-lg border border-white/20",
                tab: "px-4 py-2 font-medium",
                cursor: "bg-white/20 rounded-md shadow-sm",
                panel: "p-0"
              }}
            >
              <Tab
                key="registros"
                title={
                  <div className={`flex items-center gap-2 ${vistaActual === 'registros' ? 'text-white' : 'text-white/70'}`}>
                    <IoDocumentText className="text-lg" />
                    <span>Registros</span>
                  </div>
                }
              />
              <Tab
                key="estadisticas"
                title={
                  <div className={`flex items-center gap-2 ${vistaActual === 'estadisticas' ? 'text-white' : 'text-white/70'}`}>
                    <IoStatsChart className="text-lg" />
                    <span>Estadísticas</span>
                  </div>
                }
              />
            </Tabs>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

export default HeaderBitacora;
