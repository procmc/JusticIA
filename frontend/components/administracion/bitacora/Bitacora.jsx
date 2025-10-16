import React, { useState, useEffect } from 'react';
import { Button, Card, CardBody, Tabs, Tab, Spinner } from '@heroui/react';
import { IoDocumentText, IoStatsChart, IoCalendar, IoShield } from 'react-icons/io5';
import { Toast } from '../../ui/CustomAlert';
import HeaderBitacora from './HeaderBitacora';
import FiltrosBitacora from './FiltrosBitacora';
import TablaBitacora from './TablaBitacora';
import DetalleEvento from './DetalleEvento';
import DashboardEstadisticas from './DashboardEstadisticas';
import bitacoraService from '../../../services/bitacoraService';

const Bitacora = () => {
  const [vistaActual, setVistaActual] = useState('registros'); // 'registros' o 'estadisticas'
  const [registrosFiltrados, setRegistrosFiltrados] = useState([]);
  const [estadisticas, setEstadisticas] = useState(null);
  const [registroSeleccionado, setRegistroSeleccionado] = useState(null);
  const [modalAbierto, setModalAbierto] = useState(false);
  const [cargandoRegistros, setCargandoRegistros] = useState(false);
  const [cargandoEstadisticas, setCargandoEstadisticas] = useState(false);
  const [filtros, setFiltros] = useState({
    usuario: '',
    tipoAccion: '',
    expediente: '',
    fechaInicio: '',
    fechaFin: '',
    limite: 200
  });

  // Cargar registros y estadísticas al inicializar
  useEffect(() => {
    cargarDatosIniciales();
  }, []);

  // Cargar datos al cambiar de vista
  useEffect(() => {
    if (vistaActual === 'estadisticas' && !estadisticas) {
      cargarEstadisticas();
    }
  }, [vistaActual]);

  /**
   * Cargar datos iniciales (registros sin filtros)
   */
  const cargarDatosIniciales = async () => {
    await Promise.all([
      cargarRegistros(),
      cargarEstadisticas()
    ]);
  };

  /**
   * Cargar registros con filtros aplicados
   */
  const cargarRegistros = async (filtrosPersonalizados = null) => {
    setCargandoRegistros(true);
    try {
      const filtrosAplicar = filtrosPersonalizados || filtros;
      
      // Limpiar filtros vacíos
      const filtrosLimpios = Object.entries(filtrosAplicar).reduce((acc, [key, value]) => {
        if (value !== '' && value !== null && value !== undefined) {
          acc[key] = value;
        }
        return acc;
      }, {});

      const registros = await bitacoraService.obtenerRegistros(filtrosLimpios);
      setRegistrosFiltrados(registros);
      
    } catch (error) {
      console.error('Error cargando registros:', error);
      Toast.error('Error al cargar registros de bitácora');
      setRegistrosFiltrados([]);
    } finally {
      setCargandoRegistros(false);
    }
  };

  /**
   * Cargar estadísticas
   */
  const cargarEstadisticas = async () => {
    setCargandoEstadisticas(true);
    try {
      const stats = await bitacoraService.obtenerEstadisticas(30);
      setEstadisticas(stats);
    } catch (error) {
      console.error('Error cargando estadísticas:', error);
      Toast.error('Error al cargar estadísticas');
    } finally {
      setCargandoEstadisticas(false);
    }
  };

  /**
   * Aplicar filtros (callback del componente FiltrosBitacora)
   */
  const aplicarFiltros = () => {
    cargarRegistros();
  };

  /**
   * Limpiar filtros y recargar
   */
  const limpiarFiltros = () => {
    const filtrosVacios = {
      usuario: '',
      tipoAccion: '',
      expediente: '',
      fechaInicio: '',
      fechaFin: '',
      limite: 200
    };
    setFiltros(filtrosVacios);
    cargarRegistros(filtrosVacios);
  };

  /**
   * Ver detalle de un registro
   */
  const verDetalle = (registro) => {
    setRegistroSeleccionado(registro);
    setModalAbierto(true);
  };

  /**
   * Cerrar modal de detalle
   */
  const cerrarModal = () => {
    setModalAbierto(false);
    setRegistroSeleccionado(null);
  };

  // Verificar si hay filtros activos
  const filtrosActivos = Object.entries(filtros).some(
    ([key, valor]) => key !== 'limite' && valor !== '' && valor !== null
  );

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
        onRefresh={vistaActual === 'registros' ? cargarRegistros : cargarEstadisticas}
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
            disabled={cargandoRegistros}
          />

          {/* Tabla de Registros */}
          <TablaBitacora
            registros={registrosFiltrados}
            onVerDetalle={verDetalle}
            cargando={cargandoRegistros}
          />
        </div>
      ) : (
        <div>
          {/* Dashboard de Estadísticas */}
          {cargandoEstadisticas ? (
            <div className="flex justify-center items-center py-12">
              <Spinner size="lg" label="Cargando estadísticas..." />
            </div>
          ) : estadisticas ? (
            <DashboardEstadisticas
              estadisticas={estadisticas}
              onRefresh={cargarEstadisticas}
            />
          ) : (
            <Card>
              <CardBody className="text-center py-12">
                <p className="text-gray-500">No hay estadísticas disponibles</p>
              </CardBody>
            </Card>
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
