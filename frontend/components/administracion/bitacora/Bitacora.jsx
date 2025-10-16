import React, { useState, useEffect } from 'react';
import { Button, Card, CardBody, Tabs, Tab } from '@heroui/react';
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
  const [paginacion, setPaginacion] = useState({ total: 0, page: 1, pages: 1 });
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
    page: 1,
    limit: 10
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

      const resultado = await bitacoraService.obtenerRegistros(filtrosLimpios);
      setRegistrosFiltrados(resultado.registros);
      setPaginacion({
        total: resultado.total,
        page: resultado.page,
        pages: resultado.pages
      });
      
    } catch (error) {
      console.error('Error cargando registros:', error);
      Toast.error('Error al cargar registros de bitácora');
      setRegistrosFiltrados([]);
      setPaginacion({ total: 0, page: 1, pages: 1 });
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
    // Resetear a página 1 cuando se aplican filtros
    const nuevosFiltros = { ...filtros, page: 1 };
    setFiltros(nuevosFiltros);
    cargarRegistros(nuevosFiltros);
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
      page: 1,
      limit: 10
    };
    setFiltros(filtrosVacios);
    cargarRegistros(filtrosVacios);
  };

  /**
   * Cambiar de página en la paginación
   */
  const cambiarPagina = (nuevaPagina) => {
    const nuevosFiltros = { ...filtros, page: nuevaPagina };
    setFiltros(nuevosFiltros);
    cargarRegistros(nuevosFiltros);
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
            paginacion={paginacion}
            onCambiarPagina={cambiarPagina}
          />
        </div>
      ) : (
        <div>
          {/* Dashboard de Estadísticas */}
          {cargandoEstadisticas ? (
            <Card>
              <CardBody>
                <div className="flex flex-col items-center justify-center py-16">
                  <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary mb-4"></div>
                  <p className="text-gray-600 font-medium">Cargando estadísticas...</p>
                  <p className="text-sm text-gray-500 mt-2">Procesando datos del sistema</p>
                </div>
              </CardBody>
            </Card>
          ) : estadisticas ? (
            <DashboardEstadisticas
              estadisticas={estadisticas}
              onRefresh={cargarEstadisticas}
            />
          ) : (
            <Card>
              <CardBody>
                <div className="flex flex-col items-center justify-center py-16">
                  <div className="bg-gray-100 rounded-full p-6 mb-4">
                    <IoStatsChart className="w-14 h-14 text-gray-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-700 mb-2">No hay estadísticas disponibles</h3>
                  <p className="text-sm text-gray-500 text-center max-w-sm">
                    Aún no se han generado estadísticas para este período
                  </p>
                </div>
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
