import React from 'react';
import { Card, CardBody, Button } from '@heroui/react';
import { 
  IoPeople, 
  IoCheckmarkCircle, 
  IoCloseCircle, 
  IoAdd,
  IoTrendingUp
} from 'react-icons/io5';

const DashboardEstadisticasUsuarios = ({ estadisticas, onAgregarUsuario }) => {
  // Datos por defecto para demostración
  const stats = estadisticas || {
    usuariosActivos: 245,
    usuariosInactivos: 38,
    accionesUltimoMes: 1247
  };

  return (
    <div className="space-y-6">
      {/* Cabecera Principal con fondo primary */}
      <Card className="bg-gradient-to-r from-primary to-primary-600 text-white shadow-xl">
        <CardBody className="p-8">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            {/* Título y descripción */}
            <div className="flex items-center gap-4">
              <div className="p-3 bg-white/20 rounded-full">
                <IoPeople className="text-3xl text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white mb-2">
                  Gestión de Usuarios
                </h1>
                <p className="text-white/90 text-lg">
                  Administra usuarios del sistema JusticIA
                </p>
              </div>
            </div>

            {/* Botón Agregar */}
            <Button
              color="secondary"
              size="lg"
              startContent={<IoAdd className="text-xl" />}
              className="bg-white text-primary font-semibold hover:bg-gray-100 px-8 py-3 text-lg shadow-lg"
              onPress={onAgregarUsuario}
            >
              Agregar Usuario
            </Button>
          </div>

          {/* Estadísticas en la cabecera */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
            {/* Usuarios Activos */}
            <div className="bg-white/15 backdrop-blur-sm rounded-xl p-6 border border-white/20">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white/80 text-sm font-medium mb-1">
                    Usuarios Activos
                  </p>
                  <p className="text-4xl font-bold text-white">
                    {stats.usuariosActivos}
                  </p>
                </div>
                <div className="p-3 bg-green-500/30 rounded-full">
                  <IoCheckmarkCircle className="text-2xl text-green-200" />
                </div>
              </div>
            </div>

            {/* Usuarios Inactivos */}
            <div className="bg-white/15 backdrop-blur-sm rounded-xl p-6 border border-white/20">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white/80 text-sm font-medium mb-1">
                    Usuarios Inactivos
                  </p>
                  <p className="text-4xl font-bold text-white">
                    {stats.usuariosInactivos}
                  </p>
                </div>
                <div className="p-3 bg-red-500/30 rounded-full">
                  <IoCloseCircle className="text-2xl text-red-200" />
                </div>
              </div>
            </div>

            {/* Acciones del Último Mes */}
            <div className="bg-white/15 backdrop-blur-sm rounded-xl p-6 border border-white/20">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white/80 text-sm font-medium mb-1">
                    Acciones Último Mes
                  </p>
                  <p className="text-4xl font-bold text-white">
                    {stats.accionesUltimoMes?.toLocaleString() || '0'}
                  </p>
                </div>
                <div className="p-3 bg-blue-500/30 rounded-full">
                  <IoTrendingUp className="text-2xl text-blue-200" />
                </div>
              </div>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
};

export default DashboardEstadisticasUsuarios;
