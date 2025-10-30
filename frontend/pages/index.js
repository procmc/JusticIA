import Image from 'next/image';
import { useRouter } from 'next/router';
import { useEffect } from 'react';
import {
  IoShield,
  IoDocument,
  IoSearch,
  IoAnalytics,
  IoChatbubble,
  IoSettings,
  IoCloudUpload,
  IoPeople,
  IoTime,
  IoStatsChart,
  IoDocuments,
  IoFolderOpen
} from 'react-icons/io5';
import Toast from '@/components/ui/CustomAlert';
import { useAuthSession } from '@/hooks/auth/useAuthSession';
import { ROLES } from '@/common/roles';

export default function Home() {
  const router = useRouter();
  const { query, replace } = router;
  const { user, isLoading, isAuthenticated } = useAuthSession();

  useEffect(() => {
    // Verificar si hay error de autorización en la URL
    if (query.error === 'unauthorized') {
      const requiredRoles = query.required ? query.required.split(',') : [];
      
      Toast.error(
        'Acceso Denegado',
        requiredRoles.length > 0
          ? `No tienes permisos para acceder a esa página. Roles requeridos: ${requiredRoles.join(', ')}`
          : 'No tienes permisos para acceder a esa página.'
      );

      // Limpiar la URL
      replace('/', undefined, { shallow: true });
    }
  }, [query.error, query.required, replace]);

  // Función para navegar a las rutas
  const navigateTo = (path) => {
    router.push(path);
  };

  // Configuración de tarjetas para Usuario Judicial
  const userJudicialCards = [
    {
      title: 'Consultas Generales',
      description: 'Realice consultas generales sobre expedientes del sistema',
      icon: IoChatbubble,
      gradient: 'from-blue-500 to-blue-600',
      onClick: () => navigateTo('/consulta-datos/chat')
    },
    {
      title: 'Consulta por Expediente',
      description: 'Busque información específica de un expediente',
      icon: IoDocument,
      gradient: 'from-indigo-500 to-indigo-600',
      onClick: () => navigateTo('/consulta-datos/chat?mode=expediente')
    },
    {
      title: 'Casos Similares por Descripción',
      description: 'Encuentre casos similares usando descripción de texto',
      icon: IoSearch,
      gradient: 'from-purple-500 to-purple-600',
      onClick: () => navigateTo('/consulta-datos/busqueda-similares?mode=descripcion')
    },
    {
      title: 'Casos Similares por Expediente',
      description: 'Encuentre casos similares basados en un expediente específico',
      icon: IoDocuments,
      gradient: 'from-green-500 to-green-600',
      onClick: () => navigateTo('/consulta-datos/busqueda-similares?mode=expediente')
    },
    {
      title: 'Ingesta de Datos',
      description: 'Cargue nuevos documentos y expedientes al sistema',
      icon: IoCloudUpload,
      gradient: 'from-orange-500 to-orange-600',
      onClick: () => navigateTo('/ingesta-datos')
    }
  ];

  // Configuración de tarjetas para Administrador
  const adminCards = [
    {
      title: 'Gestión de Usuarios',
      description: 'Administre usuarios del sistema, agregue nuevos y gestione permisos',
      icon: IoPeople,
      gradient: 'from-blue-500 to-blue-600',
      onClick: () => navigateTo('/administracion/gestion-usuarios')
    },
    {
      title: 'Bitácora de Actividades',
      description: 'Revise el historial de actividades y genere reportes',
      icon: IoTime,
      gradient: 'from-indigo-500 to-indigo-600',
      onClick: () => navigateTo('/administracion/bitacora')
    },
    {
      title: 'Estadísticas y Registros',
      description: 'Registros diarios, usuarios activos y métricas del sistema',
      icon: IoAnalytics,
      gradient: 'from-purple-500 to-purple-600',
      onClick: () => navigateTo('/administracion/bitacora?tab=estadisticas')
    },
    {
      title: 'Análisis de Usuarios',
      description: 'Top usuarios más activos y distribución de actividad',
      icon: IoStatsChart,
      gradient: 'from-green-500 to-green-600',
      onClick: () => navigateTo('/administracion/bitacora?tab=usuarios')
    },
    {
      title: 'Métricas de Consultas',
      description: 'Distribución de consultas chat y análisis de uso',
      icon: IoChatbubble,
      gradient: 'from-orange-500 to-orange-600',
      onClick: () => navigateTo('/administracion/bitacora?tab=consultas')
    },
    {
      title: 'Reportes de Expedientes',
      description: 'Top expedientes consultados y métricas documentales',
      icon: IoFolderOpen,
      gradient: 'from-teal-500 to-teal-600',
      onClick: () => navigateTo('/administracion/bitacora?tab=expedientes')
    }
  ];

  // Renderizar componente de tarjeta
  const renderCard = (card, index, isFullWidth = false) => (
    <div
      key={index}
      className={`bg-white rounded-2xl p-6 border border-gray-200 shadow-lg hover:shadow-xl transition-all duration-300 cursor-pointer transform hover:-translate-y-1 ${
        isFullWidth ? 'col-span-2' : ''
      }`}
      onClick={card.onClick}
    >
      <div className={`w-14 h-14 bg-gradient-to-br ${card.gradient} rounded-xl flex items-center justify-center mb-4 mx-auto`}>
        <card.icon className="w-7 h-7 text-white" />
      </div>
      <h3 className="text-lg font-bold text-gray-800 mb-2 text-center">{card.title}</h3>
      <p className="text-gray-600 text-sm text-center">{card.description}</p>
    </div>
  );

  if (isLoading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Cargando...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full bg-white relative overflow-hidden flex flex-col">
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-2 text-center py-8">
        <div className="max-w-6xl mx-auto">
          {/* Main Title */}
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold mb-3 leading-tight">
            <span className="text-secondary-900">JusticIA</span>
          </h1>

          {/* Saludo personalizado */}
          {isAuthenticated && (
            <div className="mb-8">
              <p className="text-lg text-gray-700">
                Bienvenid@ <span className="font-semibold">{user.name}</span> a JusticIA, donde puedes realizar las siguientes funcionalidades:
              </p>
            </div>
          )}

          {/* Grid de funcionalidades según rol */}
          {isAuthenticated ? (
            <div className="mb-8">
              {user.role === ROLES.USER && (
                <>
                  {/* Primera fila: 3 columnas */}
                  <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto mb-6">
                    {userJudicialCards.slice(0, 3).map((card, index) => renderCard(card, index))}
                  </div>
                  {/* Segunda fila: 2 tarjetas del mismo tamaño */}
                  <div className="grid md:grid-cols-2 gap-6 max-w-5xl mx-auto">
                    {renderCard(userJudicialCards[3], 3)}
                    {renderCard(userJudicialCards[4], 4)}
                  </div>
                </>
              )}

              {user.role === ROLES.ADMIN && (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
                  {adminCards.map((card, index) => renderCard(card, index))}
                </div>
              )}
            </div>
          ) : (
            /* Vista por defecto para usuarios no autenticados */
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-5xl mx-auto mb-8">
              <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-lg">
                <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center mb-6 mx-auto">
                  <IoChatbubble className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-800 mb-3">Consultas Jurídicas</h3>
                <p className="text-gray-600">Acceso rápido a información legal y normativa costarricense.</p>
              </div>

              <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-lg">
                <div className="w-14 h-14 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-xl flex items-center justify-center mb-6 mx-auto">
                  <IoSearch className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-800 mb-3">Búsqueda Especializada</h3>
                <p className="text-gray-600">Herramientas de búsqueda en documentos y precedentes legales.</p>
              </div>

              <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-lg">
                <div className="w-14 h-14 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center mb-6 mx-auto">
                  <IoDocument className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-800 mb-3">Gestión Documental</h3>
                <p className="text-gray-600">Organización y administración de documentos jurídicos.</p>
              </div>

              <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-lg">
                <div className="w-14 h-14 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center mb-6 mx-auto">
                  <IoSettings className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-800 mb-3">Administración</h3>
                <p className="text-gray-600">Panel de control para usuarios y configuraciones del sistema.</p>
              </div>

              <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-lg">
                <div className="w-14 h-14 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl flex items-center justify-center mb-6 mx-auto">
                  <IoAnalytics className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-800 mb-3">Reportes</h3>
                <p className="text-gray-600">Generación de informes y análisis estadísticos.</p>
              </div>

              <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-lg">
                <div className="w-14 h-14 bg-gradient-to-br from-teal-500 to-teal-600 rounded-xl flex items-center justify-center mb-6 mx-auto">
                  <IoShield className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-800 mb-3">Seguridad</h3>
                <p className="text-gray-600">Protección de datos y control de acceso seguro.</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="relative z-10 bg-white border-t border-gray-200 w-full">
        <div className="w-full">
          <div className="max-w-4xl mx-auto">

            {/* Contenido principal */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-2 items-center">

              {/* Logo y Nombre Poder Judicial */}
              <div className="flex items-center justify-center md:justify-start gap-2">
                <Image
                  src="/PJ.png"
                  alt="Poder Judicial de Costa Rica"
                  width={40}
                  height={30}
                  className="w-auto"
                />
                <div>
                  <h3 className="text-xs font-semibold text-gray-800">Poder Judicial</h3>
                  <p className="text-[10px] text-gray-600">Costa Rica</p>
                </div>
              </div>

              {/* Información del Sistema */}
              <div className="md:col-span-2 text-center">
                <h2 className="text-sm font-bold text-gray-800">
                  JusticIA
                </h2>
                <p className="text-xs text-gray-600">
                  Sistema de Información Jurídica
                </p>
              </div>

              {/* Logo y Nombre TI */}
              <div className="flex items-center justify-center md:justify-end gap-2">
                <div className="text-right">
                  <h3 className="text-xs font-semibold text-gray-800">Dirección de TI</h3>
                  <p className="text-[10px] text-gray-600">Tecnologías de la Información</p>
                </div>
                <Image
                  src="/InteligenciaInformacion.png"
                  alt="Tecnologías de la Información"
                  width={100}
                  height={40}
                  className=""
                />
              </div>

            </div>

            {/* Información inferior */}
            <div className="flex justify-center items-center gap-2 border-t border-gray-100">
              <div className="flex items-center gap-4 text-xs text-gray-500">
                <span>&copy; 2025 Poder Judicial de Costa Rica</span>
              </div>
            </div>

          </div>
        </div>
      </footer>
    </div>
  );
}
