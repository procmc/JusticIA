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
      const count = registros.filter(r => 
        format(r.fechaHora, 'yyyy-MM-dd') === diaStr
      ).length;
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
    <div className="space-y-6">
      {/* Tarjetas de Resumen */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardBody>
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-medium mr-4">
                <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <h3 className="text-2xl font-bold text-default-900">{estadisticas.totalRegistros.toLocaleString()}</h3>
                <p className="text-small text-default-600">Total Registros</p>
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-medium mr-4">
                <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                </svg>
              </div>
              <div>
                <h3 className="text-2xl font-bold text-default-900">{estadisticas.usuariosUnicos}</h3>
                <p className="text-small text-default-600">Usuarios Únicos</p>
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <div className="flex items-center">
              <div className="p-2 bg-purple-100 rounded-medium mr-4">
                <svg className="h-6 w-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <div>
                <h3 className="text-2xl font-bold text-default-900">{estadisticas.expedientesUnicos}</h3>
                <p className="text-small text-default-600">Expedientes Únicos</p>
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <div className="flex items-center">
              <div className="p-2 bg-yellow-100 rounded-medium mr-4">
                <svg className="h-6 w-6 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h3 className="text-2xl font-bold text-default-900">{estadisticas.registrosHoy}</h3>
                <p className="text-small text-default-600">Registros Hoy</p>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Gráficos Principales */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Línea de Tiempo de Actividad */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold">Actividad de los Últimos 14 Días</h3>
          </CardHeader>
          <CardBody>
            <div className="h-64">
              <Line data={prepararDatosLineaTiempo()} options={opcionesGraficos} />
            </div>
          </CardBody>
        </Card>

        {/* Acciones por Tipo */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold">Distribución por Tipo de Acción</h3>
          </CardHeader>
          <CardBody>
            <div className="h-64">
              <Bar data={prepararDatosAcciones()} options={opcionesGraficos} />
            </div>
          </CardBody>
        </Card>

        {/* Distribución por Usuarios */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold">Top 5 Usuarios Más Activos</h3>
          </CardHeader>
          <CardBody>
            <div className="h-64">
              <Doughnut data={prepararDatosUsuarios()} options={opcionesCircular} />
            </div>
          </CardBody>
        </Card>

        {/* Horarios Pico */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold">Horarios Pico de Uso (8:00 - 18:00)</h3>
          </CardHeader>
          <CardBody>
            <div className="h-64">
              <Bar data={prepararDatosHoras()} options={opcionesGraficos} />
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Tablas de Reportes Específicos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Usuarios Más Activos */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold">Top 10 Usuarios Más Activos</h3>
          </CardHeader>
          <CardBody className="p-0">
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-default-100">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-default-600 uppercase">#</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-default-600 uppercase">Usuario</th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-default-600 uppercase">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-default-200">
                  {estadisticas.usuariosActivos.slice(0, 10).map((usuario, index) => (
                    <tr key={usuario.nombre} className="hover:bg-default-50">
                      <td className="px-4 py-2 text-sm font-medium text-default-900">{index + 1}</td>
                      <td className="px-4 py-2 text-sm text-default-900">{usuario.nombre}</td>
                      <td className="px-4 py-2 text-sm text-default-900 text-right">{usuario.cantidad}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardBody>
        </Card>

        {/* Top Expedientes */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold">Expedientes con Mayor Actividad</h3>
          </CardHeader>
          <CardBody className="p-0">
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-default-100">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-default-600 uppercase">#</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-default-600 uppercase">Expediente</th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-default-600 uppercase">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-default-200">
                  {estadisticas.expedientesActivos.slice(0, 10).map((expediente, index) => (
                    <tr key={expediente.expediente} className="hover:bg-default-50">
                      <td className="px-4 py-2 text-sm font-medium text-default-900">{index + 1}</td>
                      <td className="px-4 py-2 text-sm font-mono text-default-900">{expediente.expediente}</td>
                      <td className="px-4 py-2 text-sm text-default-900 text-right">{expediente.cantidad}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Análisis de Errores */}
      {estadisticas.erroresRecientes.length > 0 && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold">Análisis de Errores Recientes</h3>
          </CardHeader>
          <CardBody className="p-0">
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-danger-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-danger-600 uppercase">Fecha</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-danger-600 uppercase">Usuario</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-danger-600 uppercase">Acción</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-danger-600 uppercase">Expediente</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-danger-600 uppercase">Descripción</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-default-200">
                  {estadisticas.erroresRecientes.map((error) => (
                    <tr key={error.id} className="hover:bg-default-50">
                      <td className="px-4 py-2 text-sm text-default-900">
                        {format(error.fechaHora, 'dd/MM/yyyy HH:mm')}
                      </td>
                      <td className="px-4 py-2 text-sm text-default-900">{error.usuario}</td>
                      <td className="px-4 py-2 text-sm">
                        <Chip color="danger" size="sm" variant="flat">
                          {error.tipoAccion}
                        </Chip>
                      </td>
                      <td className="px-4 py-2 text-sm font-mono text-default-900">{error.expediente}</td>
                      <td className="px-4 py-2 text-sm text-default-900 max-w-xs truncate" title={error.texto}>
                        {error.texto}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
};

export default DashboardEstadisticas;
