import React, { useState, useEffect } from 'react';
import { Button, Card, CardBody } from '@heroui/react';
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
    <div className="p-6 space-y-6">
      {/* Header */}
      <Card>
        <CardBody>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h1 className="text-3xl font-bold text-default-900">
                Bitácora del Sistema
              </h1>
              <p className="text-default-600 mt-1">
                Registro completo de actividades y auditoría del sistema
              </p>
            </div>

            {/* Navegación entre vistas */}
            <div className="flex bg-default-100 rounded-large p-1">
              <Button
                size="sm"
                variant={vistaActual === 'registros' ? 'solid' : 'light'}
                color={vistaActual === 'registros' ? 'primary' : 'default'}
                onPress={() => setVistaActual('registros')}
                className="px-4"
              >
                📋 Registros
              </Button>
              <Button
                size="sm"
                variant={vistaActual === 'estadisticas' ? 'solid' : 'light'}
                color={vistaActual === 'estadisticas' ? 'primary' : 'default'}
                onPress={() => setVistaActual('estadisticas')}
                className="px-4"
              >
                📊 Estadísticas
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>

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
