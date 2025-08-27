import React, { useState, useEffect } from 'react';
import { Button, Card, CardBody, Tabs, Tab } from '@heroui/react';
import { IoDocumentText, IoStatsChart, IoCalendar, IoShield } from 'react-icons/io5';
import HeaderBitacora from './HeaderBitacora';
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

  // Verificar si hay filtros activos
  const filtrosActivos = Object.values(filtros).some(valor => valor !== '');

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
      {/* Header estandarizado */}
      <HeaderBitacora 
        vistaActual={vistaActual}
        onVistaChange={setVistaActual}
        estadisticas={estadisticas}
        registrosFiltrados={registrosFiltrados}
        filtrosActivos={filtrosActivos}
      />

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
