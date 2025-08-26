import React, { useState, useEffect } from 'react';
import { Button, Card, CardBody, Input } from '@heroui/react';
import { 
  IoPeople, 
  IoAdd, 
  IoSearch,
  IoCheckmarkCircle, 
  IoCloseCircle, 
  IoPersonAdd, 
  IoStatsChart
} from 'react-icons/io5';
import TablaUsuarios from './TablaUsuarios';
import DetalleUsuario from './DetalleUsuario';
import FormularioUsuario from './FormularioUsuario';
import { 
  usuariosMock, 
  obtenerEstadisticasUsuarios,
  crearUsuario,
  actualizarUsuario,
  desactivarUsuario,
  activarUsuario
} from '../../../data/mockUsuarios';
import '../../../styles/gestion-usuarios-animations.css';

const GestionUsuarios = () => {
  const [usuariosFiltrados, setUsuariosFiltrados] = useState(usuariosMock);
  const [estadisticas, setEstadisticas] = useState(null);
  const [usuarioSeleccionado, setUsuarioSeleccionado] = useState(null);
  const [modalDetalleAbierto, setModalDetalleAbierto] = useState(false);
  const [modalFormularioAbierto, setModalFormularioAbierto] = useState(false);
  const [modoFormulario, setModoFormulario] = useState('crear'); // 'crear' o 'editar'
  const [filtroTexto, setFiltroTexto] = useState('');

  // Cargar estadísticas al inicializar
  useEffect(() => {
    setEstadisticas(obtenerEstadisticasUsuarios());
  }, []);

  // Filtrar usuarios cuando cambie el texto de filtro
  useEffect(() => {
    if (!filtroTexto.trim()) {
      setUsuariosFiltrados(usuariosMock);
    } else {
      const usuariosFiltradosTexto = usuariosMock.filter(usuario => 
        usuario.nombre.toLowerCase().includes(filtroTexto.toLowerCase()) ||
        usuario.nombreUsuario.toLowerCase().includes(filtroTexto.toLowerCase()) ||
        usuario.correo.toLowerCase().includes(filtroTexto.toLowerCase()) ||
        usuario.rolNombre.toLowerCase().includes(filtroTexto.toLowerCase()) ||
        usuario.estadoNombre.toLowerCase().includes(filtroTexto.toLowerCase()) ||
        (usuario.telefono && usuario.telefono.toLowerCase().includes(filtroTexto.toLowerCase())) ||
        (usuario.cedula && usuario.cedula.toLowerCase().includes(filtroTexto.toLowerCase())) ||
        (usuario.cargo && usuario.cargo.toLowerCase().includes(filtroTexto.toLowerCase()))
      );
      setUsuariosFiltrados(usuariosFiltradosTexto);
    }
  }, [filtroTexto]);

  const handleFiltroChange = (value) => {
    setFiltroTexto(value);
  };

  const handleVerDetalle = (usuario) => {
    setUsuarioSeleccionado(usuario);
    setModalDetalleAbierto(true);
  };

  const handleCrearUsuario = () => {
    setModoFormulario('crear');
    setUsuarioSeleccionado(null);
    setModalFormularioAbierto(true);
  };

  const handleEditarUsuario = (usuario) => {
    setModoFormulario('editar');
    setUsuarioSeleccionado(usuario);
    setModalFormularioAbierto(true);
  };

  const handleGuardarUsuario = (datosUsuario) => {
    try {
      if (modoFormulario === 'crear') {
        const nuevoUsuario = crearUsuario(datosUsuario);
        setUsuariosFiltrados([...usuariosFiltrados, nuevoUsuario]);
      } else {
        const usuarioActualizado = actualizarUsuario(usuarioSeleccionado.id, datosUsuario);
        setUsuariosFiltrados(usuariosFiltrados.map(u => 
          u.id === usuarioActualizado.id ? usuarioActualizado : u
        ));
      }
      
      // Actualizar estadísticas
      setEstadisticas(obtenerEstadisticasUsuarios());
      setModalFormularioAbierto(false);
      setUsuarioSeleccionado(null);
      
      // Mostrar mensaje de éxito (aquí podrías agregar un toast)
      console.log(`Usuario ${modoFormulario === 'crear' ? 'creado' : 'actualizado'} exitosamente`);
    } catch (error) {
      console.error('Error al guardar usuario:', error);
      // Mostrar mensaje de error
    }
  };

  const handleCambiarEstadoUsuario = (usuario, nuevoEstado) => {
    try {
      let usuarioActualizado;
      if (nuevoEstado === 'Activo') {
        usuarioActualizado = activarUsuario(usuario.id);
      } else {
        usuarioActualizado = desactivarUsuario(usuario.id);
      }
      
      setUsuariosFiltrados(usuariosFiltrados.map(u => 
        u.id === usuarioActualizado.id ? usuarioActualizado : u
      ));
      
      // Actualizar estadísticas
      setEstadisticas(obtenerEstadisticasUsuarios());
      
      console.log(`Usuario ${nuevoEstado === 'Activo' ? 'activado' : 'desactivado'} exitosamente`);
    } catch (error) {
      console.error('Error al cambiar estado del usuario:', error);
    }
  };

  const handleResetearContrasena = (usuario) => {
    // Aquí implementarías la lógica para resetear la contraseña
    console.log('Resetear contraseña para:', usuario.correo);
    // Mostrar mensaje de confirmación
  };

  return (
    <div className="p-6 space-y-6">
      {/* Cabecera Principal con fondo primary */}
      <Card className="bg-gradient-to-br from-primary via-primary-600 to-primary-700 text-white shadow-2xl border-none overflow-hidden relative">
        {/* Efectos de fondo creativos */}
        <div className="absolute inset-0 bg-gradient-to-r from-white/5 via-transparent to-transparent"></div>
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -translate-y-32 translate-x-32 blur-3xl"></div>
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/5 rounded-full translate-y-24 -translate-x-24 blur-2xl"></div>
        
        <CardBody className="p-8 relative z-10">
          <div className="space-y-6">
            {/* Fila superior: Título, Input de búsqueda y botón */}
            <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-6">
              {/* Título y descripción */}
              <div className="flex items-center gap-4 flex-1">
                <div className="relative group">
                  <div className="p-3 bg-gradient-to-br from-white/20 via-white/15 to-white/10 rounded-3xl backdrop-blur-xl shadow-2xl border border-white/30 hover:border-white/50 transition-all duration-500 hover:scale-105">
                    <IoPeople className="text-4xl text-white drop-shadow-lg filter brightness-110" />
                  </div>
                  {/* Badge con total de usuarios en la esquina superior derecha */}
                  {estadisticas && (
                    <div className="absolute -top-3 -right-3 bg-gradient-to-br from-green-400 via-green-500 to-green-600 text-white font-bold text-sm rounded-full w-9 h-9 flex items-center justify-center shadow-xl border-3 border-white/40 hover:scale-110 transition-transform duration-300 cursor-pointer">
                      {estadisticas.totalUsuarios}
                    </div>
                  )}
                  {/* Efecto de resplandor sutil al hover */}
                  <div className="absolute inset-0 rounded-3xl bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-xl -z-10"></div>
                </div>
                <div className="flex-1">
                  <h1 className="text-3xl font-bold text-white mb-2 tracking-tight bg-gradient-to-r from-white to-white/90 bg-clip-text">
                    Gestión de Usuarios
                  </h1>
                  <p className="text-white/80 text-base font-medium">
                    Administra usuarios del sistema JusticIA
                  </p>
                </div>
              </div>

              {/* Input de búsqueda y Botón Agregar */}
              <div className="flex items-center gap-4">
                {/* Input de búsqueda moderno */}
                <div className="relative group">
                  <Input
                    placeholder="Buscar usuarios..."
                    value={filtroTexto}
                    onValueChange={handleFiltroChange}
                    startContent={<IoSearch className="text-white/70 text-lg group-hover:text-white transition-colors" />}
                    classNames={{
                      base: "w-80 h-12",
                      mainWrapper: "h-full",
                      input: "text-white placeholder:text-white/50 font-medium",
                      inputWrapper: "h-full bg-white/10 backdrop-blur-xl border-2 border-white/20 hover:border-white/40 focus-within:border-white/60 focus-within:bg-white/20 transition-all duration-500 rounded-2xl shadow-lg group-hover:shadow-xl",
                    }}
                    size="lg"
                  />
                  {/* Efecto de brillo en focus */}
                  <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-white/10 via-white/5 to-transparent opacity-0 group-focus-within:opacity-100 transition-opacity duration-500 pointer-events-none"></div>
                </div>

                {/* Botón Agregar mejorado */}
                <div className="relative group">
                  <Button
                    color="secondary"
                    size="lg"
                    startContent={<IoAdd className="text-xl group-hover:rotate-90 transition-transform duration-300" />}
                    className="bg-white text-primary font-bold hover:bg-white/95 px-8 py-3 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105 border-none rounded-2xl"
                    onPress={handleCrearUsuario}
                  >
                    Agregar Usuario
                  </Button>
                  {/* Efecto de resplandor */}
                  <div className="absolute inset-0 rounded-2xl bg-white/20 opacity-0 group-hover:opacity-100 blur-xl transition-opacity duration-300 -z-10"></div>
                </div>
              </div>
            </div>

            {/* Estadísticas elegantes debajo del texto */}
            <div className="pt-2">
              {estadisticas && (
                <div className="flex items-center gap-4 flex-wrap animate-fade-in">
                  {/* Activos */}
                  <div className="group relative overflow-hidden">
                    <div className="flex items-center gap-3 bg-white/8 hover:bg-white/15 px-4 py-2 rounded-xl backdrop-blur-md transition-all duration-500 hover:scale-105 cursor-pointer border border-white/10 hover:border-white/20">
                      <div className="relative">
                        <div className="w-3 h-3 rounded-full bg-gradient-to-br from-emerald-300 to-emerald-500 shadow-lg"></div>
                        <div className="absolute inset-0 w-3 h-3 rounded-full bg-emerald-400 animate-pulse opacity-60"></div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-white/90 font-semibold text-sm">{estadisticas.usuariosActivos}</span>
                        <span className="text-white/70 text-xs font-medium uppercase tracking-wider">Activos</span>
                      </div>
                      <div className="ml-1 px-2 py-0.5 bg-emerald-500/20 rounded-full border border-emerald-400/30">
                        <span className="text-emerald-200 text-xs font-bold">{estadisticas.porcentajeActivos}%</span>
                      </div>
                    </div>
                    <div className="absolute inset-0 bg-gradient-to-r from-emerald-400/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl"></div>
                  </div>

                  {/* Inactivos */}
                  <div className="group relative overflow-hidden">
                    <div className="flex items-center gap-3 bg-white/8 hover:bg-white/15 px-4 py-2 rounded-xl backdrop-blur-md transition-all duration-500 hover:scale-105 cursor-pointer border border-white/10 hover:border-white/20">
                      <div className="relative">
                        <div className="w-3 h-3 rounded-full bg-gradient-to-br from-red-300 to-red-500 shadow-lg"></div>
                        <div className="absolute inset-0 w-3 h-3 rounded-full bg-red-400 animate-pulse opacity-60"></div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-white/90 font-semibold text-sm">{estadisticas.usuariosInactivos}</span>
                        <span className="text-white/70 text-xs font-medium uppercase tracking-wider">Inactivos</span>
                      </div>
                      <div className="ml-1 px-2 py-0.5 bg-red-500/20 rounded-full border border-red-400/30">
                        <span className="text-red-200 text-xs font-bold">{estadisticas.porcentajeInactivos}%</span>
                      </div>
                    </div>
                    <div className="absolute inset-0 bg-gradient-to-r from-red-400/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl"></div>
                  </div>

                  {/* Nuevos */}
                  <div className="group relative overflow-hidden">
                    <div className="flex items-center gap-3 bg-white/8 hover:bg-white/15 px-4 py-2 rounded-xl backdrop-blur-md transition-all duration-500 hover:scale-105 cursor-pointer border border-white/10 hover:border-white/20">
                      <div className="relative">
                        <div className="w-3 h-3 rounded-full bg-gradient-to-br from-blue-300 to-blue-500 shadow-lg"></div>
                        <div className="absolute inset-0 w-3 h-3 rounded-full bg-blue-400 animate-pulse opacity-60"></div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-white/90 font-semibold text-sm">{estadisticas.usuariosRecientes}</span>
                        <span className="text-white/70 text-xs font-medium uppercase tracking-wider">Nuevos</span>
                      </div>
                      <div className="ml-1 px-2 py-0.5 bg-blue-500/20 rounded-full border border-blue-400/30">
                        <span className="text-blue-200 text-xs font-bold">30d</span>
                      </div>
                    </div>
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-400/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl"></div>
                  </div>

                  {/* Indicador de resultados de búsqueda */}
                  {filtroTexto && (
                    <div className="group relative overflow-hidden animate-slide-in">
                      <div className="flex items-center gap-3 bg-white/12 px-4 py-2 rounded-xl backdrop-blur-md border border-white/20">
                        <div className="w-3 h-3 rounded-full bg-gradient-to-br from-yellow-300 to-yellow-500 shadow-lg animate-pulse"></div>
                        <div className="flex items-center gap-2">
                          <span className="text-white/90 font-semibold text-sm">{usuariosFiltrados.length}</span>
                          <span className="text-white/70 text-xs font-medium uppercase tracking-wider">Resultados</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Tabla de usuarios */}
      <TablaUsuarios
        usuarios={usuariosFiltrados}
        onVerDetalle={handleVerDetalle}
        onEditarUsuario={handleEditarUsuario}
        onCambiarEstado={handleCambiarEstadoUsuario}
        onResetearContrasena={handleResetearContrasena}
      />

      {/* Modales */}
      <DetalleUsuario
        usuario={usuarioSeleccionado}
        isOpen={modalDetalleAbierto}
        onClose={() => {
          setModalDetalleAbierto(false);
          setUsuarioSeleccionado(null);
        }}
        onEditar={handleEditarUsuario}
        onCambiarEstado={handleCambiarEstadoUsuario}
      />

      <FormularioUsuario
        usuario={usuarioSeleccionado}
        modo={modoFormulario}
        isOpen={modalFormularioAbierto}
        onClose={() => {
          setModalFormularioAbierto(false);
          setUsuarioSeleccionado(null);
        }}
        onGuardar={handleGuardarUsuario}
      />
    </div>
  );
};

export default GestionUsuarios;
