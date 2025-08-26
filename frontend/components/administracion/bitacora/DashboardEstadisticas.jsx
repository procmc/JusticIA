import React from 'react';
import { Card, CardBody, CardHeader, Chip } from '@heroui/react';
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
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import { format, eachDayOfInterval, subDays } from 'date-fns';
import { es } from 'date-fns/locale';
import { IoTrendingUp, IoStatsChart, IoPeople, IoTime, IoDocumentText, IoPersonAdd, IoFolderOpen, IoToday } from 'react-icons/io5';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

const DashboardEstadisticas = ({ estadisticas, registros }) => {
  // Preparar datos para el gráfico de línea de tiempo
  const prepararDatosLineaTiempo = () => {
    const ultimosDias = eachDayOfInterval({
      start: subDays(new Date(), 13),
      end: new Date()
    });

    const datos = ultimosDias.map(dia => {
      const diaStr = format(dia, 'yyyy-MM-dd');
      const count = registros.filter(r => {
        const fechaRegistro = new Date(r.fechaHora);
        const fechaRegistroStr = format(fechaRegistro, 'yyyy-MM-dd');
        return fechaRegistroStr === diaStr;
      }).length;
      
      return {
        fecha: format(dia, 'dd/MM', { locale: es }),
        cantidad: count
      };
    });

    return {
      labels: datos.map(d => d.fecha),
      datasets: [
        {
          label: 'Actividad Diaria',
          data: datos.map(d => d.cantidad),
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true,
          tension: 0.4,
        },
      ],
    };
  };

  // Preparar datos para el gráfico de barras por tipo de acción
  const prepararDatosAcciones = () => {
    return {
      labels: estadisticas.accionesPorTipo.map(a => a.tipo),
      datasets: [
        {
          label: 'Cantidad de Acciones',
          data: estadisticas.accionesPorTipo.map(a => a.cantidad),
          backgroundColor: [
            'rgba(59, 130, 246, 0.8)',
            'rgba(147, 51, 234, 0.8)',
            'rgba(249, 115, 22, 0.8)',
          ],
          borderColor: [
            'rgb(59, 130, 246)',
            'rgb(147, 51, 234)',
            'rgb(249, 115, 22)',
          ],
          borderWidth: 1,
        },
      ],
    };
  };

  // Preparar datos para el gráfico circular de usuarios
  const prepararDatosUsuarios = () => {
    const top5Usuarios = estadisticas.usuariosActivos.slice(0, 5);
    const otros = estadisticas.usuariosActivos.slice(5).reduce((sum, u) => sum + u.cantidad, 0);
    
    const labels = [...top5Usuarios.map(u => u.nombre.split(' ')[0]), ...(otros > 0 ? ['Otros'] : [])];
    const data = [...top5Usuarios.map(u => u.cantidad), ...(otros > 0 ? [otros] : [])];

    return {
      labels,
      datasets: [
        {
          data,
          backgroundColor: [
            'rgba(59, 130, 246, 0.8)',
            'rgba(147, 51, 234, 0.8)',
            'rgba(249, 115, 22, 0.8)',
            'rgba(34, 197, 94, 0.8)',
            'rgba(239, 68, 68, 0.8)',
            'rgba(156, 163, 175, 0.8)',
          ],
          borderColor: [
            'rgb(59, 130, 246)',
            'rgb(147, 51, 234)',
            'rgb(249, 115, 22)',
            'rgb(34, 197, 94)',
            'rgb(239, 68, 68)',
            'rgb(156, 163, 175)',
          ],
          borderWidth: 1,
        },
      ],
    };
  };

  // Preparar datos para el heatmap de actividad por horas
  const prepararDatosHoras = () => {
    const horasLaborales = estadisticas.distribucionHoras.filter(h => h.hora >= 8 && h.hora <= 18);
    
    return {
      labels: horasLaborales.map(h => `${h.hora}:00`),
      datasets: [
        {
          label: 'Actividad por Hora',
          data: horasLaborales.map(h => h.cantidad),
          backgroundColor: 'rgba(34, 197, 94, 0.8)',
          borderColor: 'rgb(34, 197, 94)',
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

  const opcionesCircular = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right',
      },
    },
  };

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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="border-none shadow-lg bg-gradient-to-br from-blue-50 to-blue-100">
          <CardBody className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-blue-600 rounded-2xl flex items-center justify-center shadow-lg">
                  <IoDocumentText className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h3 className="text-3xl font-bold text-blue-900 mb-1">
                    {estadisticas.totalRegistros.toLocaleString()}
                  </h3>
                  <p className="text-sm font-medium text-blue-700">Registros Históricos</p>
                  <p className="text-xs text-blue-600 mt-1">Desde el inicio del sistema</p>
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
                    {estadisticas.usuariosUnicos}
                  </h3>
                  <p className="text-sm font-medium text-green-700">Usuarios Diferentes</p>
                  <p className="text-xs text-green-600 mt-1">Personas que han usado el sistema</p>
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
                  <IoFolderOpen className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h3 className="text-3xl font-bold text-purple-900 mb-1">
                    {estadisticas.expedientesUnicos}
                  </h3>
                  <p className="text-sm font-medium text-purple-700">Expedientes Consultados</p>
                  <p className="text-xs text-purple-600 mt-1">Casos que han tenido actividad</p>
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
                  <IoToday className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h3 className="text-3xl font-bold text-orange-900 mb-1">
                    {estadisticas.registrosHoy}
                  </h3>
                  <p className="text-sm font-medium text-orange-700">Acciones de Hoy</p>
                  <p className="text-xs text-orange-600 mt-1">Actividad en las últimas 24 horas</p>
                </div>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Gráficos Principales */}
      <div 
        className="grid grid-cols-1 lg:grid-cols-2 gap-6"
        style={{
          transform: 'none',
          transition: 'none',
          position: 'static',
          willChange: 'auto',
          backfaceVisibility: 'hidden',
          perspective: 'none'
        }}
      >
        {/* Línea de Tiempo de Actividad */}
        <Card style={{ transform: 'none', transition: 'none', willChange: 'auto' }}>
          <CardHeader className="bg-white">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-md">
                <IoTrendingUp className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">Actividad de los Últimos 14 Días</h3>
                <p className="text-sm text-gray-600">Tendencia de actividad diaria</p>
              </div>
            </div>
          </CardHeader>
          <CardBody>
            <div className="h-64" style={{ transform: 'none', position: 'relative' }}>
              <Line data={prepararDatosLineaTiempo()} options={opcionesGraficos} />
            </div>
          </CardBody>
        </Card>

        {/* Acciones por Tipo */}
        <Card style={{ transform: 'none', transition: 'none', willChange: 'auto' }}>
          <CardHeader className="bg-white">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-600 rounded-xl flex items-center justify-center shadow-md">
                <IoStatsChart className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">Distribución por Tipo de Acción</h3>
                <p className="text-sm text-gray-600">Análisis de tipos de operaciones</p>
              </div>
            </div>
          </CardHeader>
          <CardBody>
            <div className="h-64" style={{ transform: 'none', position: 'relative' }}>
              <Bar data={prepararDatosAcciones()} options={opcionesGraficos} />
            </div>
          </CardBody>
        </Card>

        {/* Distribución por Usuarios */}
        <Card style={{ transform: 'none', transition: 'none', willChange: 'auto' }}>
          <CardHeader className="bg-white">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-600 rounded-xl flex items-center justify-center shadow-md">
                <IoPeople className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">Top 5 Usuarios Más Activos</h3>
                <p className="text-sm text-gray-600">Distribución de actividad por usuario</p>
              </div>
            </div>
          </CardHeader>
          <CardBody>
            <div className="h-64" style={{ transform: 'none', position: 'relative' }}>
              <Doughnut data={prepararDatosUsuarios()} options={opcionesCircular} />
            </div>
          </CardBody>
        </Card>

        {/* Horarios Pico */}
        <Card style={{ transform: 'none', transition: 'none', willChange: 'auto' }}>
          <CardHeader className="bg-white">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-orange-600 rounded-xl flex items-center justify-center shadow-md">
                <IoTime className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">Horarios Pico de Uso (8:00 - 18:00)</h3>
                <p className="text-sm text-gray-600">Patrón de uso durante horas laborales</p>
              </div>
            </div>
          </CardHeader>
          <CardBody>
            <div className="h-64" style={{ transform: 'none', position: 'relative' }}>
              <Bar data={prepararDatosHoras()} options={opcionesGraficos} />
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
};

export default DashboardEstadisticas;
