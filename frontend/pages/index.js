import { 
  IoScale, 
  IoShield, 
  IoFlash, 
  IoDocument, 
  IoSearch, 
  IoAnalytics,
  IoCloudUpload,
  IoChatbubble,
  IoPeople,
  IoTime,
  IoDocuments,
  IoSettings
} from 'react-icons/io5';

export default function Home() {
  
  return (
    <div className="min-h-screen bg-white relative overflow-hidden py-24">
      {/* Hero Section */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-[calc(100vh-120px)] px-6 text-center">
        <div className="max-w-5xl mx-auto">

          {/* Main Title */}
          <h1 className="text-4xl md:text-4xl lg:text-7xl font-extrabold mb-3 leading-tight">
            <span className="text-tituloSeccion">
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
            <h2 className="text-3xl md:text-4xl font-bold text-center text-tituloSeccion mb-6">
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
      <footer className="relative z-10 text-center py-12 text-gray-500 text-sm border-t border-gray-100">
        <p>&copy; 2025 JusticIA. Sistema de Información Jurídica.</p>
      </footer>
    </div>
  );
}
