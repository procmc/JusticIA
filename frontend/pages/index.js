import Image from 'next/image';
import {
  IoShield,
  IoDocument,
  IoSearch,
  IoAnalytics,
  IoChatbubble,
  IoSettings
} from 'react-icons/io5';

export default function Home() {

  return (
    <div className="min-h-screen bg-white relative overflow-hidden">
      {/* Hero Section */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-[calc(100vh-120px)] px-6 text-center pt-24">
        <div className="max-w-5xl mx-auto">

          {/* Main Title */}
          <h1 className="text-4xl md:text-4xl lg:text-7xl font-extrabold mb-3 leading-tight">
            <span className="text-primary">
              JusticIA
            </span>
            <br />
          </h1>

          {/* Subtitle */}
          <p className="text-xl md:text-xl text-gray-600 mb-16 max-w-4xl mx-auto leading-relaxed">
            Plataforma tecnológica para la gestión y consulta de información jurídica en Costa Rica.
          </p>

          {/* Features Grid */}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-5xl mx-auto mb-16">

            {/* Consultas */}
            <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-lg hover:shadow-xl transition-all duration-300">
              <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center mb-6 mx-auto">
                <IoChatbubble className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-3">Consultas Jurídicas</h3>
              <p className="text-gray-600">Acceso rápido a información legal y normativa costarricense.</p>
            </div>

            {/* Búsqueda */}
            <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-lg hover:shadow-xl transition-all duration-300">
              <div className="w-14 h-14 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-xl flex items-center justify-center mb-6 mx-auto">
                <IoSearch className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-3">Búsqueda Especializada</h3>
              <p className="text-gray-600">Herramientas de búsqueda en documentos y precedentes legales.</p>
            </div>

            {/* Gestión */}
            <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-lg hover:shadow-xl transition-all duration-300">
              <div className="w-14 h-14 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center mb-6 mx-auto">
                <IoDocument className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-3">Gestión Documental</h3>
              <p className="text-gray-600">Organización y administración de documentos jurídicos.</p>
            </div>

            {/* Administración */}
            <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-lg hover:shadow-xl transition-all duration-300">
              <div className="w-14 h-14 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center mb-6 mx-auto">
                <IoSettings className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-3">Administración</h3>
              <p className="text-gray-600">Panel de control para usuarios y configuraciones del sistema.</p>
            </div>

            {/* Reportes */}
            <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-lg hover:shadow-xl transition-all duration-300">
              <div className="w-14 h-14 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl flex items-center justify-center mb-6 mx-auto">
                <IoAnalytics className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-3">Reportes</h3>
              <p className="text-gray-600">Generación de informes y análisis estadísticos.</p>
            </div>

            {/* Seguridad */}
            <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-lg hover:shadow-xl transition-all duration-300">
              <div className="w-14 h-14 bg-gradient-to-br from-teal-500 to-teal-600 rounded-xl flex items-center justify-center mb-6 mx-auto">
                <IoShield className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-3">Seguridad</h3>
              <p className="text-gray-600">Protección de datos y control de acceso seguro.</p>
            </div>
          </div>

          {/* Info Section */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-3xl p-12 mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-center text-primary mb-6">
              Plataforma Confiable
            </h2>
            <p className="text-lg text-gray-600 text-center max-w-3xl mx-auto">
              JusticIA está diseñado para facilitar el acceso a información jurídica
              y optimizar los procesos administrativos en el ámbito legal costarricense.
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="relative z-10 bg-white border-t border-gray-200 w-full">
        <div className="w-full px-6 py-4">
          <div className="max-w-7xl mx-auto">

            {/* Contenido principal */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-center">

              {/* Logo y Nombre Poder Judicial */}
              <div className="flex items-center justify-center md:justify-start gap-3">
                <Image
                  src="/PJ.png"
                  alt="Poder Judicial de Costa Rica"
                  width={60}
                  height={40}
                  className="w-auto"
                />
                <div>
                  <h3 className="text-sm font-semibold text-gray-800">Poder Judicial</h3>
                  <p className="text-xs text-gray-600">Costa Rica</p>
                </div>
              </div>

              {/* Información del Sistema */}
              <div className="md:col-span-2 text-center">
                <h2 className="text-base font-bold text-gray-800 mb-1">
                  JusticIA
                </h2>
                <p className="text-sm text-gray-600">
                  Sistema de Información Jurídica
                </p>
              </div>

              {/* Logo y Nombre TI */}
              <div className="flex items-center justify-center md:justify-end gap-3">
                <div className="text-right">
                  <h3 className="text-sm font-semibold text-gray-800">Dirección de TI</h3>
                  <p className="text-xs text-gray-600">Tecnologías de la Información</p>
                </div>
                <Image
                  src="/InteligenciaInformacion.png"
                  alt="Tecnologías de la Información"
                  width={140}
                  height={60}
                  className=""
                />
              </div>

            </div>

            {/* Información inferior */}
            <div className="flex justify-center items-center gap-2 mt-3 pt-3 border-t border-gray-100">
              <div className="flex items-center gap-4 text-sm text-gray-500">
                <span>&copy; 2025 Poder Judicial de Costa Rica</span>
              </div>
            </div>

          </div>
        </div>
      </footer>
    </div>
  );
}
