import React, { useState, useEffect } from 'react';
import { Button, Card, CardBody, Tabs, Tab } from '@heroui/react';
import { IoDocumentText, IoStatsChart, IoCalendar, IoShield } from 'react-icons/io5';
import FiltrosBitacora from './FiltrosBitacora';
import TablaBitacora from './TablaBitacora';
import DetalleEvento from './DetalleEvento';
import DashboardEstadisticas from './DashboardEstadisticas';
import { 
  registrosBitacora, 
  obtenerEstadisticas, 
  filtrarRegistros 
} from '../../../data/mockBitacora';

const Bitacora = () => {
  const [vistaActual, setVistaActual] = useState('registros'); // 'registros' o 'estadisticas'
  const [registrosFiltrados, setRegistrosFiltrados] = useState(registrosBitacora);
  const [estadisticas, setEstadisticas] = useState(null);
  const [registroSeleccionado, setRegistroSeleccionado] = useState(null);
  const [modalAbierto, setModalAbierto] = useState(false);
  const [filtros, setFiltros] = useState({
    usuario: '',
    tipoAccion: '',
    expediente: '',
    fechaInicio: '',
    fechaFin: '',
    estado: ''
  });

  // Cargar estadísticas al inicializar
  useEffect(() => {
    setEstadisticas(obtenerEstadisticas());
  }, []);

  // Aplicar filtros cuando cambien
  const aplicarFiltros = () => {
    const registrosFiltrados = filtrarRegistros(filtros);
    setRegistrosFiltrados(registrosFiltrados);
  };

  const limpiarFiltros = () => {
    const filtrosVacios = {
      usuario: '',
      tipoAccion: '',
      expediente: '',
      fechaInicio: '',
      fechaFin: '',
      estado: ''
    };
    setFiltros(filtrosVacios);
    setRegistrosFiltrados(registrosBitacora);
  };

  const verDetalle = (registro) => {
    setRegistroSeleccionado(registro);
    setModalAbierto(true);
  };

  const cerrarModal = () => {
    setModalAbierto(false);
    setRegistroSeleccionado(null);
  };

  return (
    <div 
      className="p-6 space-y-6"
      style={{
        transform: 'none',
        transition: 'none',
        position: 'static',
        willChange: 'auto'
      }}
    >
      {/* Header simplificado y elegante */}
      <div 
        className="bg-white rounded-2xl border border-gray-200 shadow-sm"
        style={{
          transform: 'none',
          transition: 'none',
          position: 'static',
          willChange: 'auto',
          backfaceVisibility: 'hidden'
        }}
      >
        <div 
          className="p-6"
          style={{
            transform: 'none',
            transition: 'none',
            position: 'static'
          }}
        >
          <div className="flex items-center gap-4 mb-6">
            <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center shadow-sm">
              <IoShield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Bitácora del Sistema
              </h1>
              <p className="text-gray-600">
                Registro completo de actividades y auditoría del sistema
              </p>
            </div>
          </div>

          {/* Tabs simplificados */}
          <Tabs
            selectedKey={vistaActual}
            onSelectionChange={setVistaActual}
            variant="underlined"
            style={{
              transform: 'none',
              transition: 'none',
              willChange: 'auto'
            }}
            classNames={{
              tabList: "gap-6 w-full relative rounded-none p-0 border-b border-gray-200",
              cursor: "w-full bg-blue-600 h-0.5",
              tab: "max-w-fit px-0 h-10",
              tabContent: "group-data-[selected=true]:text-blue-600 text-gray-600 font-medium"
            }}
          >
            <Tab
              key="registros"
              title={
                <div className="flex items-center gap-3">
                  <IoDocumentText className="w-5 h-5" />
                  <span>Registros ({registrosBitacora.length})</span>
                </div>
              }
            />
            <Tab
              key="estadisticas"
              title={
                <div className="flex items-center gap-3">
                  <IoStatsChart className="w-5 h-5" />
                  <span>Estadísticas</span>
                </div>
              }
            />
          </Tabs>
        </div>
      </div>

      {/* Contenido según la vista seleccionada */}
      {vistaActual === 'registros' ? (
        <div className="space-y-6">
          {/* Filtros */}
          <FiltrosBitacora
            filtros={filtros}
            onFiltroChange={setFiltros}
            onLimpiarFiltros={limpiarFiltros}
            onBuscar={aplicarFiltros}
          />

          {/* Tabla de Registros */}
          <TablaBitacora
            registros={registrosFiltrados}
            onVerDetalle={verDetalle}
          />
        </div>
      ) : (
        <div>
          {/* Dashboard de Estadísticas */}
          {estadisticas && (
            <DashboardEstadisticas
              estadisticas={estadisticas}
              registros={registrosBitacora}
            />
          )}
        </div>
      )}

      {/* Modal de Detalle */}
      <DetalleEvento
        registro={registroSeleccionado}
        isOpen={modalAbierto}
        onClose={cerrarModal}
      />
    </div>
  );
};

export default Bitacora;
