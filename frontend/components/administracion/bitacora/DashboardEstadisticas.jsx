import React from 'react';
import { Card, CardBody, CardHeader, Button } from '@heroui/react';
import { formatearSoloFechaCostaRica } from '../../../utils/dateUtils';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler,
} from 'chart.js';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import { IoDocumentText, IoPersonAdd, IoFolderOpen, IoToday, IoRefresh, IoChatbubbleEllipses, IoPieChart, IoCalendarOutline, IoPeople } from 'react-icons/io5';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler
);

// Configuraciones de colores reutilizables
const COLORES = {
  azul: { bg: 'rgba(59, 130, 246, 0.8)', border: 'rgb(59, 130, 246)' },
  purpura: { bg: 'rgba(147, 51, 234, 0.8)', border: 'rgb(147, 51, 234)' },
  naranja: { bg: 'rgba(249, 115, 22, 0.8)', border: 'rgb(249, 115, 22)' },
  verde: { bg: 'rgba(34, 197, 94, 0.8)', border: 'rgb(34, 197, 94)' },
  rojo: { bg: 'rgba(239, 68, 68, 0.8)', border: 'rgb(239, 68, 68)' },
  indigo: { bg: 'rgba(147, 51, 234, 0.8)', border: 'rgb(147, 51, 234)' },
  gris: { bg: 'rgba(156, 163, 175, 0.5)', border: 'rgb(156, 163, 175)' }
};

const DashboardEstadisticas = ({ estadisticas, onRefresh }) => {
  // Las estadísticas RAG vienen incluidas en las estadísticas principales
  const estadisticasRAG = estadisticas?.rag;
  
  // Función utilitaria para formatear números
  const formatearNumero = (numero) => {
    if (!numero) return '0';
    if (numero >= 1000000000) return `${(numero / 1000000000).toFixed(1)}B`;
    if (numero >= 1000000) return `${(numero / 1000000).toFixed(1)}M`;
    if (numero >= 1000) return `${(numero / 1000).toFixed(1)}K`;
    return numero.toLocaleString('es-ES');
  };

  // Función utilitaria para crear datasets
  const crearDataset = (label, data, colores, tipo = 'bar') => ({
    label,
    data,
    backgroundColor: Array.isArray(colores) ? colores.map(c => c.bg) : colores.bg,
    borderColor: Array.isArray(colores) ? colores.map(c => c.border) : colores.border,
    borderWidth: tipo === 'doughnut' ? 2 : 1,
    ...(tipo === 'line' && { fill: true, tension: 0.4 })
  });

  // Función genérica para preparar datos de gráficos
  const prepararDatosGrafico = (datos, config) => {
    const { labelKey, valueKey, etiquetas, colores, limite } = config;
    
    if (!datos || datos.length === 0) return null;
    
    let datosOrdenados = datos;
    if (limite) {
      datosOrdenados = datos.sort((a, b) => b[valueKey] - a[valueKey]).slice(0, limite);
    }
    
    const labels = etiquetas || datosOrdenados.map(item => item[labelKey]);
    const values = datosOrdenados.map(item => item[valueKey]);
    
    return {
      labels,
      datasets: [crearDataset('Cantidad', values, colores)]
    };
  };

  // Preparar datos para el gráfico de barras por tipo de acción
  const prepararDatosAcciones = () => {
    if (!estadisticas?.accionesPorTipo) return null;

    return {
      labels: estadisticas.accionesPorTipo.map(a => a.tipo || `Tipo ${a.id}`),
      datasets: [
        {
          label: 'Cantidad de Acciones',
          data: estadisticas.accionesPorTipo.map(a => a.cantidad || 0),
          backgroundColor: [
            'rgba(59, 130, 246, 0.8)',    // Azul
            'rgba(147, 51, 234, 0.8)',    // Púrpura
            'rgba(249, 115, 22, 0.8)',    // Naranja
            'rgba(34, 197, 94, 0.8)',     // Verde
            'rgba(239, 68, 68, 0.8)',     // Rojo
            'rgba(236, 72, 153, 0.8)',    // Rosa
            'rgba(14, 165, 233, 0.8)',    // Celeste
            'rgba(168, 85, 247, 0.8)',    // Violeta
          ],
          borderColor: [
            'rgb(59, 130, 246)',
            'rgb(147, 51, 234)',
            'rgb(249, 115, 22)',
            'rgb(34, 197, 94)',
            'rgb(239, 68, 68)',
            'rgb(236, 72, 153)',
            'rgb(14, 165, 233)',
            'rgb(168, 85, 247)',
          ],
          borderWidth: 1,
        },
      ],
    };
  };

  const opcionesGraficos = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          stepSize: 1,
        },
      },
    },
  };

  const datosAcciones = prepararDatosAcciones();

  // Preparar datos para usuarios más activos (Top 5)
  const prepararDatosUsuarios = () => {
    if (!estadisticas?.usuariosMasActivos || estadisticas.usuariosMasActivos.length === 0) return null;

    return prepararDatosGrafico(estadisticas.usuariosMasActivos, {
      labelKey: 'nombre',
      valueKey: 'cantidad',
      colores: [COLORES.azul, COLORES.purpura, COLORES.verde, COLORES.naranja, COLORES.rojo],
      limite: 5
    });
  };

  // Preparar datos para expedientes más consultados (Top 5)
  const prepararDatosExpedientes = () => {
    if (!estadisticas?.expedientesMasConsultados || estadisticas.expedientesMasConsultados.length === 0) return null;

    return prepararDatosGrafico(estadisticas.expedientesMasConsultados, {
      labelKey: 'numero',
      valueKey: 'cantidad',
      colores: COLORES.verde
    });
  };

  // Preparar datos para actividad por día (últimos 7 días)
  const prepararDatosActividadDiaria = () => {
    if (!estadisticas?.actividadPorDia || estadisticas.actividadPorDia.length === 0) return null;

    const etiquetas = estadisticas.actividadPorDia.map(d => {
      const fecha = new Date(d.fecha);
      return fecha.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
    });

    return {
      labels: etiquetas,
      datasets: [crearDataset('Registros por día', estadisticas.actividadPorDia.map(d => d.cantidad || 0), COLORES.azul, 'line')]
    };
  };

  const datosUsuarios = prepararDatosUsuarios();
  const datosExpedientes = prepararDatosExpedientes();
  const datosActividad = prepararDatosActividadDiaria();

  // Preparar datos para gráfico de distribución RAG
  const prepararDatosRAG = () => {
    if (!estadisticasRAG) return null;
    
    const generales = estadisticasRAG.consultasGenerales || 0;
    const expedientes = estadisticasRAG.consultasExpediente || 0;
    const total = generales + expedientes;
    
    if (total === 0) {
      return {
        labels: ['Sin consultas RAG'],
        datasets: [crearDataset('Sin datos', [1], COLORES.gris, 'doughnut')]
      };
    }

    return {
      labels: ['Consultas Generales', 'Consultas por Expediente'],
      datasets: [crearDataset('Distribución RAG', [generales, expedientes], [COLORES.azul, COLORES.verde], 'doughnut')]
    };
  };

  const datosRAG = prepararDatosRAG();

  return (
    <div 
      className="space-y-6" 
      style={{
        transform: 'none',
        transition: 'none',
        position: 'static',
        willChange: 'auto'
      }}
    >
      {/* Header con botón de refrescar */}
      {onRefresh && (
        <div className="flex justify-end mb-4">
          <Button
            color="primary"
            variant="flat"
            startContent={<IoRefresh className="w-4 h-4" />}
            onPress={onRefresh}
            size="sm"
          >
            Actualizar
          </Button>
        </div>
      )}

      {/* Tarjetas de métricas principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <Card className="border-none shadow-lg bg-gradient-to-br from-blue-50 to-blue-100">
          <CardBody className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-blue-600 rounded-2xl flex items-center justify-center shadow-lg">
                  <IoToday className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h3 className="text-3xl font-bold text-blue-900 mb-1">
                    {estadisticas.registrosHoy?.toLocaleString() || 0}
                  </h3>
                  <p className="text-sm font-medium text-blue-700">Registros Hoy</p>
                  <p className="text-xs text-blue-600 mt-1">Actividad del día</p>
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        <Card className="border-none shadow-lg bg-gradient-to-br from-purple-50 to-purple-100">
          <CardBody className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
                  <IoDocumentText className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h3 className="text-3xl font-bold text-purple-900 mb-1">
                    {estadisticas.registros30Dias?.toLocaleString() || 0}
                  </h3>
                  <p className="text-sm font-medium text-purple-700">Últimos 30 Días</p>
                  <p className="text-xs text-purple-600 mt-1">Actividad mensual</p>
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        <Card className="border-none shadow-lg bg-gradient-to-br from-green-50 to-green-100">
          <CardBody className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-green-600 rounded-2xl flex items-center justify-center shadow-lg">
                  <IoPersonAdd className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h3 className="text-3xl font-bold text-green-900 mb-1">
                    {estadisticas.usuariosUnicos || 0}
                  </h3>
                  <p className="text-sm font-medium text-green-700">Usuarios Activos</p>
                  <p className="text-xs text-green-600 mt-1">Usuarios diferentes</p>
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        <Card className="border-none shadow-lg bg-gradient-to-br from-orange-50 to-orange-100">
          <CardBody className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-orange-600 rounded-2xl flex items-center justify-center shadow-lg">
                  <IoFolderOpen className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h3 className="text-3xl font-bold text-orange-900 mb-1">
                    {estadisticas.expedientesUnicos || 0}
                  </h3>
                  <p className="text-sm font-medium text-orange-700">Expedientes</p>
                  <p className="text-xs text-orange-600 mt-1">Casos consultados</p>
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Nueva tarjeta para RAG */}
        <Card className="border-none shadow-lg bg-gradient-to-br from-indigo-50 to-indigo-100">
          <CardBody className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-indigo-600 rounded-2xl flex items-center justify-center shadow-lg">
                  <IoChatbubbleEllipses className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h3 className="text-3xl font-bold text-indigo-900 mb-1">
                    {estadisticasRAG?.totalConsultasRAG?.toLocaleString() || 0}
                  </h3>
                  <p className="text-sm font-medium text-indigo-700">Consultas RAG</p>
                  <p className="text-xs text-indigo-600 mt-1">Inteligencia artificial</p>
                </div>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Gráfico de acciones por tipo */}
      {datosAcciones && datosAcciones.labels.length > 0 && (
        <Card className="border-none shadow-lg">
          <CardHeader className="bg-white px-8 pt-6 pb-4 border-b">
            <div>
              <h3 className="text-xl font-bold text-gray-900">Distribución por Tipo de Acción</h3>
              <p className="text-sm text-gray-600 mt-1">
                Acciones registradas en los últimos 30 días
              </p>
            </div>
          </CardHeader>
          <CardBody className="p-8">
            <div style={{ height: '400px' }}>
              <Bar data={datosAcciones} options={opcionesGraficos} />
            </div>
          </CardBody>
        </Card>
      )}

      {/* Grid con 3 columnas para los gráficos restantes */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Actividad por día */}
        {datosActividad && (
          <Card className="border-none shadow-lg">
            <CardHeader className="bg-white px-6 pt-6 pb-4 border-b">
              <div className="flex items-center gap-3">
                <IoCalendarOutline className="w-6 h-6 text-blue-600" />
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Actividad Diaria</h3>
                  <p className="text-sm text-gray-600">Últimos 7 días</p>
                </div>
              </div>
            </CardHeader>
            <CardBody className="p-8">
              <div style={{ height: '350px' }}>
                <Line 
                  data={datosActividad} 
                  options={{
                    ...opcionesGraficos,
                    plugins: {
                      legend: {
                        display: false,
                      },
                    },
                    scales: {
                      y: {
                        beginAtZero: true,
                        ticks: {
                          stepSize: 1,
                        },
                        grid: {
                          color: 'rgba(59, 130, 246, 0.08)',
                        }
                      },
                      x: {
                        grid: {
                          display: false,
                        }
                      }
                    }
                  }} 
                />
              </div>
            </CardBody>
          </Card>
        )}

        {/* Usuarios más activos */}
        {datosUsuarios && (
          <Card className="border-none shadow-lg">
            <CardHeader className="bg-white px-6 pt-6 pb-4 border-b">
              <div className="flex items-center gap-3">
                <IoPeople className="w-6 h-6 text-purple-600" />
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Usuarios Activos</h3>
                  <p className="text-sm text-gray-600">Top 5 más activos</p>
                </div>
              </div>
            </CardHeader>
            <CardBody className="p-8">
              <div style={{ height: '350px' }}>
                <Doughnut 
                  data={datosUsuarios} 
                  options={{
                    ...opcionesGraficos,
                    cutout: '60%',
                    plugins: {
                      legend: {
                        position: 'right',
                        labels: {
                          padding: 12,
                          boxWidth: 12,
                          font: {
                            size: 11
                          }
                        }
                      },
                    },
                  }} 
                />
              </div>
            </CardBody>
          </Card>
        )}

        {/* Distribución RAG */}
        <Card className="border-none shadow-lg">
          <CardHeader className="bg-white px-6 pt-6 pb-4 border-b">
            <div className="flex items-center gap-3">
              <IoPieChart className="w-6 h-6 text-indigo-600" />
              <div>
                <h3 className="text-xl font-bold text-gray-900">Consultas RAG</h3>
                <p className="text-sm text-gray-600">Distribución por tipo</p>
              </div>
            </div>
          </CardHeader>
          <CardBody className="p-8">
            {datosRAG ? (
              <div className="relative" style={{ height: '350px' }}>
                <Doughnut 
                  data={datosRAG} 
                  options={{
                    ...opcionesGraficos,
                    cutout: '65%',
                    plugins: {
                      legend: {
                        position: 'bottom',
                      },
                    },
                  }} 
                />
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none" style={{ top: '15%' }}>
                  <p className="text-3xl font-bold text-gray-800">
                    {estadisticasRAG?.totalConsultasRAG?.toLocaleString() || 0}
                  </p>
                  <p className="text-sm text-gray-500">Total</p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-80 text-gray-500">
                <IoPieChart className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <p className="text-sm text-gray-500">No hay datos RAG disponibles</p>
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      {/* Gráfico de expedientes más consultados */}
      {datosExpedientes && datosExpedientes.labels.length > 0 && (
        <Card className="border-none shadow-lg">
          <CardHeader className="bg-white px-8 pt-6 pb-4 border-b">
            <div>
              <h3 className="text-xl font-bold text-gray-900">Expedientes Más Consultados</h3>
              <p className="text-sm text-gray-600 mt-1">
                Top 5 de expedientes con más actividad
              </p>
            </div>
          </CardHeader>
          <CardBody className="p-8">
            <div style={{ height: '400px' }}>
              <Bar 
                data={datosExpedientes} 
                options={{
                  ...opcionesGraficos,
                  indexAxis: 'y',
                  plugins: {
                    legend: {
                      display: false,
                    },
                  },
                }} 
              />
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
};

export default DashboardEstadisticas;