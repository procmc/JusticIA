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
  filtrosActivos = false,
  paginacion = { total: 0 },
  onExportarPDF,
  exportando = false,
  cargandoRegistros = false
}) => {
  // Función para formatear números grandes
  const formatearNumeroGrande = (numero) => {
    if (!numero) return '0';
    if (numero >= 1000000000) {
      return `${(numero / 1000000000).toFixed(1)}B`;
    } else if (numero >= 1000000) {
      return `${(numero / 1000000).toFixed(1)}M`;
    } else if (numero >= 1000) {
      return `${(numero / 1000).toFixed(1)}K`;
    }
    return numero.toLocaleString('es-ES');
  };

  return (
    <Card className="bg-primary text-white shadow-lg border-none">
      <CardBody className="p-4 sm:p-6 lg:p-8">
        <div className="space-y-6">
          {/* Fila superior: Título y métricas */}
          <div className="flex items-center justify-between gap-4 flex-wrap">
            {/* Título */}
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

            {/* Total Histórico - Siempre visible */}
            {estadisticas && (
              <div className="bg-white/10 backdrop-blur-sm rounded-lg border border-white/30 px-3 py-2 shadow-lg">
                <div className="flex items-center gap-2.5">
                  <IoStatsChart className="text-lg text-white/90" />
                  <div>
                    <p className="text-white/70 text-[10px] font-medium uppercase tracking-wider leading-tight">
                      Eventos del Sistema
                    </p>
                    <p className="text-white text-lg font-black tracking-tight leading-tight">
                      {formatearNumeroGrande(estadisticas.totalRegistros)}
                    </p>
                    <p className="text-white/60 text-[9px] font-medium leading-tight">
                      Desde el inicio
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Fila inferior: Tabs y controles */}
          <div className="flex items-center justify-between gap-4 flex-wrap">
            {/* Navegación de pestañas */}
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

            {/* Indicador de registros y botón de exportación */}
            {/* Indicador de registros y botón de exportación */}
            {vistaActual === 'registros' && (
              <div className="flex items-center gap-3">
                {/* Contador de registros */}
                {filtrosActivos && (
                  <div className="flex items-center gap-2 bg-white/15 px-4 py-2 rounded-lg border border-white/30">
                    <IoFunnel className="text-white/90 text-sm" />
                    <div className="flex items-center gap-1.5">
                      <span className="text-white/90 font-semibold text-sm">{paginacion.total}</span>
                      <span className="text-white/70 text-xs font-medium uppercase">
                        {paginacion.total === 1 ? 'Registro' : 'Registros'}
                      </span>
                    </div>
                  </div>
                )}
                
                {/* Botón de exportar PDF */}
                <Button
                  color="default"
                  variant="flat"
                  size="md"
                  onPress={onExportarPDF}
                  isLoading={exportando}
                  isDisabled={paginacion.total === 0 || cargandoRegistros}
                  className="bg-white/15 text-white border-white/30 hover:bg-white/25"
                  startContent={!exportando && <IoDocumentText className="w-5 h-5" />}
                >
                  Exportar PDF
                </Button>
              </div>
            )}
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

export default HeaderBitacora;
