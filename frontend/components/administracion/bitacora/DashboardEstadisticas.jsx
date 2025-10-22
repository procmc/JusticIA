import React, { useState, useEffect } from 'react';
import { Card, CardBody, CardHeader, Chip, Button } from '@heroui/react';
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
import { IoDocumentText, IoPersonAdd, IoFolderOpen, IoToday, IoRefresh, IoPeople, IoCalendarOutline, IoStatsChart, IoChatbubbleEllipses, IoPieChart } from 'react-icons/io5';
import bitacoraService from '../../../services/bitacoraService';

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

const DashboardEstadisticas = ({ estadisticas, onRefresh }) => {
  // Las estadísticas RAG ahora vienen incluidas en las estadísticas principales
  const estadisticasRAG = estadisticas?.rag;
  const cargandoRAG = false; // Ya no cargamos por separado

  // Función para refrescar todas las estadísticas
  const refreshTodasLasEstadisticas = async () => {
    // Ahora solo necesitamos refrescar una vez ya que se cargan juntas
    if (onRefresh) {
      await onRefresh();
    }
  };
  // Función para formatear números grandes de manera elegante
  const formatearNumeroGrande = (numero) => {
    if (numero >= 1000000000) {
      return `${(numero / 1000000000).toFixed(1)}B`; // Billones
    } else if (numero >= 1000000) {
      return `${(numero / 1000000).toFixed(1)}M`; // Millones
    } else if (numero >= 1000) {
      return `${(numero / 1000).toFixed(1)}K`; // Miles
    }
    return numero.toLocaleString('es-ES');
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

    return {
      labels: estadisticas.usuariosMasActivos.map(u => u.nombre || 'Usuario desconocido'),
      datasets: [
        {
          label: 'Acciones realizadas',
          data: estadisticas.usuariosMasActivos.map(u => u.cantidad || 0),
          backgroundColor: [
            'rgba(59, 130, 246, 0.8)',
            'rgba(147, 51, 234, 0.8)',
            'rgba(34, 197, 94, 0.8)',
            'rgba(249, 115, 22, 0.8)',
            'rgba(239, 68, 68, 0.8)',
          ],
          borderColor: [
            'rgb(59, 130, 246)',
            'rgb(147, 51, 234)',
            'rgb(34, 197, 94)',
            'rgb(249, 115, 22)',
            'rgb(239, 68, 68)',
          ],
          borderWidth: 2,
        },
      ],
    };
  };

  // Preparar datos para expedientes más consultados (Top 5)
  const prepararDatosExpedientes = () => {
    if (!estadisticas?.expedientesMasConsultados || estadisticas.expedientesMasConsultados.length === 0) return null;

    return {
      labels: estadisticas.expedientesMasConsultados.map(e => e.numero || 'Sin número'),
      datasets: [
        {
          label: 'Consultas',
          data: estadisticas.expedientesMasConsultados.map(e => e.cantidad || 0),
          backgroundColor: 'rgba(34, 197, 94, 0.8)',
          borderColor: 'rgb(34, 197, 94)',
          borderWidth: 1,
        },
      ],
    };
  };

  // Preparar datos para actividad por día (últimos 7 días)
  const prepararDatosActividadDiaria = () => {
    if (!estadisticas?.actividadPorDia || estadisticas.actividadPorDia.length === 0) return null;

    return {
      labels: estadisticas.actividadPorDia.map(d => {
        const fecha = new Date(d.fecha);
        return fecha.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
      }),
      datasets: [
        {
          label: 'Registros por día',
          data: estadisticas.actividadPorDia.map(d => d.cantidad || 0),
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true,
          tension: 0.4,
        },
      ],
    };
  };

  const datosUsuarios = prepararDatosUsuarios();
  const datosExpedientes = prepararDatosExpedientes();
  const datosActividad = prepararDatosActividadDiaria();

  // Preparar datos para gráfico de distribución RAG
  const prepararDatosRAG = () => {
    if (!estadisticasRAG) return null;
    
    // Obtener valores, usar 0 si son undefined
    const generales = estadisticasRAG.consultasGenerales || 0;
    const expedientes = estadisticasRAG.consultasExpediente || 0;
    const total = generales + expedientes;
    
    // Si no hay consultas RAG, mostrar gráfico con mensaje
    if (total === 0) {
      return {
        labels: ['Sin consultas RAG'],
        datasets: [
          {
            data: [1],
            backgroundColor: ['rgba(156, 163, 175, 0.5)'], // Gris claro
            borderColor: ['rgb(156, 163, 175)'],
            borderWidth: 1,
          },
        ],
      };
    }

    return {
      labels: ['Consultas Generales', 'Consultas por Expediente'],
      datasets: [
        {
          data: [generales, expedientes],
          backgroundColor: [
            'rgba(59, 130, 246, 0.8)',    // Azul para generales
            'rgba(34, 197, 94, 0.8)',     // Verde para expedientes
          ],
          borderColor: [
            'rgb(59, 130, 246)',
            'rgb(34, 197, 94)',
          ],
          borderWidth: 2,
        },
      ],
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
            onPress={refreshTodasLasEstadisticas}
            size="sm"
            isDisabled={cargandoRAG}
          >
            {cargandoRAG ? 'Actualizando...' : 'Actualizar'}
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
                    {cargandoRAG ? (
                      <div className="animate-pulse bg-indigo-200 h-8 w-16 rounded"></div>
                    ) : (
                      estadisticasRAG?.totalConsultasRAG?.toLocaleString() || 0
                    )}
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

      {/* Grid con gráficos secundarios */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Gráfico de actividad por día */}
        {datosActividad && datosActividad.labels.length > 0 && (
          <Card className="border-none shadow-lg">
            <CardHeader className="bg-white px-6 pt-5 pb-3 border-b">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                  <IoCalendarOutline className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900">Actividad Diaria</h3>
                  <p className="text-xs text-gray-600 mt-0.5">Últimos 7 días</p>
                </div>
              </div>
            </CardHeader>
            <CardBody className="p-6">
              <div style={{ height: '300px' }}>
                <Line 
                  data={datosActividad} 
                  options={{
                    ...opcionesGraficos,
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

        {/* Gráfico de usuarios más activos */}
        {datosUsuarios && datosUsuarios.labels.length > 0 && (
          <Card className="border-none shadow-lg">
            <CardHeader className="bg-white px-6 pt-5 pb-3 border-b">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <IoPeople className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900">Usuarios Más Activos</h3>
                  <p className="text-xs text-gray-600 mt-0.5">Top 5 del período</p>
                </div>
              </div>
            </CardHeader>
            <CardBody className="p-6">
              <div style={{ height: '300px' }}>
                <Doughnut 
                  data={datosUsuarios} 
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        position: 'right',
                      },
                    },
                  }} 
                />
              </div>
            </CardBody>
          </Card>
        )}

        {/* Gráfico de distribución RAG */}
        <Card className="border-none shadow-lg">
          <CardHeader className="bg-white px-6 pt-5 pb-3 border-b">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
                  <IoPieChart className="w-5 h-5 text-indigo-600" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900">Consultas RAG</h3>
                  <p className="text-xs text-gray-600 mt-0.5">General vs. Expedientes</p>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardBody className="p-6">
            {cargandoRAG ? (
              <div className="flex items-center justify-center" style={{ height: '300px' }}>
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-2"></div>
                  <p className="text-sm text-gray-600">Cargando estadísticas RAG...</p>
                </div>
              </div>
            ) : datosRAG ? (
              <div style={{ height: '300px' }}>
                <Doughnut 
                  data={datosRAG} 
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        position: 'bottom',
                      },
                      tooltip: {
                        callbacks: {
                          label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = estadisticasRAG?.totalConsultasRAG || 0;
                            
                            // Si es el mensaje de "Sin consultas RAG", no mostrar porcentaje
                            if (label === 'Sin consultas RAG') {
                              return 'No hay consultas RAG en este período';
                            }
                            
                            const percentage = total > 0 
                              ? ((value / total) * 100).toFixed(1)
                              : 0;
                            return `${label}: ${value} (${percentage}%)`;
                          }
                        }
                      }
                    },
                  }} 
                />
              </div>
            ) : (
              <div className="flex items-center justify-center" style={{ height: '300px' }}>
                <div className="text-center">
                  <IoPieChart className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">No hay datos RAG disponibles</p>
                </div>
              </div>
            )}
            
            {/* Estadísticas adicionales RAG */}
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="grid grid-cols-2 gap-4 text-center">
                <div>
                  <p className="text-xs text-gray-500">Usuarios RAG</p>
                  <p className="text-lg font-semibold text-indigo-600">
                    {estadisticasRAG?.usuariosActivosRAG || 0}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Expedientes</p>
                  <p className="text-lg font-semibold text-indigo-600">
                    {estadisticasRAG?.expedientesConsultadosRAG || 0}
                  </p>
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Mensaje si no hay datos RAG */}
        {(!estadisticasRAG || estadisticasRAG.totalConsultasRAG === 0) && (
          <Card className="border-dashed border-2 border-gray-300">
            <CardBody className="p-6 text-center">
              <IoChatbubbleEllipses className="w-8 h-8 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-500">
                No hay consultas RAG en este período
              </p>
            </CardBody>
          </Card>
        )}
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
            <div style={{ height: '300px' }}>
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
