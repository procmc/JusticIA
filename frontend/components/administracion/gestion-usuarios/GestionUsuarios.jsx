import React, { useState, useEffect } from 'react';
import TablaUsuarios from './TablaUsuarios';
import DetalleUsuario from './DetalleUsuario';
import FormularioUsuario from './FormularioUsuario';
import HeaderGestionUsuarios from './HeaderGestionUsuarios';
import { obtenerUsuariosService } from '../../../services/usuarioService';
import { Toast } from '../../ui/CustomAlert';

const GestionUsuarios = () => {
  const [usuarios, setUsuarios] = useState([]);
  const [usuariosFiltrados, setUsuariosFiltrados] = useState([]);
  const [loading, setLoading] = useState(true);
  const [estadisticas, setEstadisticas] = useState(null);
  const [usuarioSeleccionado, setUsuarioSeleccionado] = useState(null);
  const [modalDetalleAbierto, setModalDetalleAbierto] = useState(false);
  const [modalFormularioAbierto, setModalFormularioAbierto] = useState(false);
  const [modoFormulario, setModoFormulario] = useState('crear');
  const [filtroTexto, setFiltroTexto] = useState('');

  // Cargar usuarios del backend
  const cargarUsuarios = async () => {
    setLoading(true);
    try {
      const resultado = await obtenerUsuariosService();
      if (resultado.success) {
        setUsuarios(resultado.usuarios);
        setUsuariosFiltrados(resultado.usuarios);
        // Calcular estadísticas
        const activos = resultado.usuarios.filter(u => u.estado?.nombre === 'Activo').length;
        const inactivos = resultado.usuarios.filter(u => u.estado?.nombre === 'Inactivo').length;
        setEstadisticas({
          totalUsuarios: resultado.usuarios.length,
          usuariosActivos: activos,
          usuariosInactivos: inactivos
        });
      } else {
        Toast.error('Error', resultado.message || 'Error al cargar usuarios');
      }
    } catch (error) {
      console.error('Error al cargar usuarios:', error);
      Toast.error('Error', 'Error al cargar usuarios');
    } finally {
      setLoading(false);
    }
  };

  // Cargar usuarios al inicializar
  useEffect(() => {
    cargarUsuarios();
  }, []);

  // Filtrar usuarios cuando cambie el texto de filtro
  useEffect(() => {
    if (!filtroTexto.trim()) {
      setUsuariosFiltrados(usuarios);
    } else {
      const usuariosFiltradosTexto = usuarios.filter(usuario => 
        usuario.CT_Nombre.toLowerCase().includes(filtroTexto.toLowerCase()) ||
        usuario.CT_Nombre_usuario.toLowerCase().includes(filtroTexto.toLowerCase()) ||
        usuario.CT_Correo.toLowerCase().includes(filtroTexto.toLowerCase()) ||
        usuario.rol?.nombre.toLowerCase().includes(filtroTexto.toLowerCase()) ||
        usuario.estado?.nombre.toLowerCase().includes(filtroTexto.toLowerCase()) ||
        usuario.CN_Id_usuario.toLowerCase().includes(filtroTexto.toLowerCase())
      );
      setUsuariosFiltrados(usuariosFiltradosTexto);
    }
  }, [filtroTexto, usuarios]);

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

  const handleGuardarUsuario = async (datosUsuario) => {
    try {
      let resultado;
      if (modoFormulario === 'crear') {
        // Crear usuario
        resultado = await crearUsuarioService(datosUsuario);
        if (resultado.success) {
          Toast.success('Éxito', 'Usuario creado exitosamente');
          await cargarUsuarios(); // Recargar lista
        } else {
          Toast.error('Error', resultado.message || 'Error al crear usuario');
          return;
        }
      } else {
        // Editar usuario - implementar cuando sea necesario
        Toast.info('Info', 'Función de editar en desarrollo');
        return;
      }
      
      setModalFormularioAbierto(false);
      setUsuarioSeleccionado(null);
      
    } catch (error) {
      console.error('Error al guardar usuario:', error);
      Toast.error('Error', 'Error al guardar usuario');
    }
  };

  const handleCambiarEstadoUsuario = async (usuario, nuevoEstado) => {
    try {
      // Implementar cambio de estado cuando sea necesario
      Toast.info('Info', 'Función de cambiar estado en desarrollo');
    } catch (error) {
      console.error('Error al cambiar estado:', error);
      Toast.error('Error', 'Error al cambiar estado del usuario');
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
      {loading ? (
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
        </div>
      ) : (
        <TablaUsuarios
          usuarios={usuariosFiltrados}
          onVerDetalle={handleVerDetalle}
          onEditarUsuario={handleEditarUsuario}
          onCambiarEstado={handleCambiarEstadoUsuario}
          onResetearContrasena={handleResetearContrasena}
        />
      )}

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