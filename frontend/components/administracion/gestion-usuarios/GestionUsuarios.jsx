import React, { useState, useEffect } from 'react';
import TablaUsuarios from './TablaUsuarios';
import DetalleUsuario from './DetalleUsuario';
import FormularioUsuario from './FormularioUsuario';
import HeaderGestionUsuarios from './HeaderGestionUsuarios';
import { 
  usuariosMock, 
  obtenerEstadisticasUsuarios,
  crearUsuario,
  actualizarUsuario,
  desactivarUsuario,
  activarUsuario
} from '../../../data/mockUsuarios';

const GestionUsuarios = () => {
  const [usuariosFiltrados, setUsuariosFiltrados] = useState(usuariosMock);
  const [estadisticas, setEstadisticas] = useState(null);
  const [usuarioSeleccionado, setUsuarioSeleccionado] = useState(null);
  const [modalDetalleAbierto, setModalDetalleAbierto] = useState(false);
  const [modalFormularioAbierto, setModalFormularioAbierto] = useState(false);
  const [modoFormulario, setModoFormulario] = useState('crear');
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
      
      setEstadisticas(obtenerEstadisticasUsuarios());
      setModalFormularioAbierto(false);
      setUsuarioSeleccionado(null);
      
      console.log(`Usuario ${modoFormulario === 'crear' ? 'creado' : 'actualizado'} exitosamente`);
    } catch (error) {
      console.error('Error al guardar usuario:', error);
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
      
      setEstadisticas(obtenerEstadisticasUsuarios());
      
      console.log(`Usuario ${nuevoEstado === 'Activo' ? 'activado' : 'desactivado'} exitosamente`);
    } catch (error) {
      console.error('Error al cambiar estado del usuario:', error);
    }
  };

  const handleResetearContrasena = (usuario) => {
    console.log('Resetear contraseña para:', usuario.correo);
  };

  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Header Component */}
      <HeaderGestionUsuarios
        filtroTexto={filtroTexto}
        onFiltroChange={handleFiltroChange}
        onCrearUsuario={handleCrearUsuario}
        estadisticas={estadisticas}
        usuariosFiltrados={usuariosFiltrados}
      />

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