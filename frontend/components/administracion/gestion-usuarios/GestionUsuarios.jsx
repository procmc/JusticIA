import React, { useState, useEffect } from 'react';
import TablaUsuarios from './TablaUsuarios';
import DetalleUsuario from './DetalleUsuario';
import FormularioUsuario from './FormularioUsuario';
import HeaderGestionUsuarios from './HeaderGestionUsuarios';
import ConfirmModal from '../../ui/ConfirmModal';
import { obtenerUsuariosService, crearUsuarioService, editarUsuarioService, resetearContrasenaService } from '../../../services/usuarioService';
import { Toast } from '../../ui/CustomAlert';

const GestionUsuarios = () => {
  const [usuarios, setUsuarios] = useState([]);
  const [usuariosFiltrados, setUsuariosFiltrados] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingResetPassword, setLoadingResetPassword] = useState(false); // Loading para el modal
  const [estadisticas, setEstadisticas] = useState(null);
  const [usuarioSeleccionado, setUsuarioSeleccionado] = useState(null);
  const [modalDetalleAbierto, setModalDetalleAbierto] = useState(false);
  const [modalFormularioAbierto, setModalFormularioAbierto] = useState(false);
  const [modalConfirmResetAbierto, setModalConfirmResetAbierto] = useState(false); // Modal de confirmación
  const [usuarioParaReset, setUsuarioParaReset] = useState(null); // Usuario a resetear
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
          setModalFormularioAbierto(false);
          setUsuarioSeleccionado(null);
          await cargarUsuarios(); // Recargar lista después de cerrar el modal
        } else {
          Toast.error('Error', resultado.message || 'Error al crear usuario');
          throw new Error(resultado.message); // Lanzar error para que el formulario no se cierre
        }
      } else if (modoFormulario === 'editar') {
        // Editar usuario
        resultado = await editarUsuarioService(usuarioSeleccionado.CN_Id_usuario, datosUsuario);
        if (resultado.success) {
          Toast.success('Éxito', 'Usuario actualizado exitosamente');
          setModalFormularioAbierto(false);
          setUsuarioSeleccionado(null);
          await cargarUsuarios(); // Recargar lista después de cerrar el modal
        } else {
          Toast.error('Error', resultado.message || 'Error al actualizar usuario');
          throw new Error(resultado.message); // Lanzar error para que el formulario no se cierre
        }
      }
      
    } catch (error) {
      console.error('Error al guardar usuario:', error);
      // No cerramos el modal si hay error para que el usuario pueda corregir
      throw error; // Re-lanzar el error para que FormularioUsuario lo maneje
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
    // Abrir modal de confirmación en lugar de ejecutar directamente
    setUsuarioParaReset(usuario);
    setModalConfirmResetAbierto(true);
  };

  const confirmarResetearContrasena = async () => {
    setLoadingResetPassword(true);
    try {
      const resultado = await resetearContrasenaService(usuarioParaReset.CN_Id_usuario);
      if (resultado.success) {
        Toast.success('Éxito', resultado.message || 'Contraseña reseteada exitosamente');
        // Cerrar modal después del éxito
        setTimeout(() => {
          setModalConfirmResetAbierto(false);
          setUsuarioParaReset(null);
        }, 1000);
      } else {
        Toast.error('Error', resultado.message || 'Error al resetear contraseña');
      }
    } catch (error) {
      console.error('Error al resetear contraseña:', error);
      Toast.error('Error', 'Error al resetear contraseña del usuario');
    } finally {
      setLoadingResetPassword(false);
    }
  };

  const cerrarModalConfirmReset = () => {
    if (!loadingResetPassword) {
      setModalConfirmResetAbierto(false);
      setUsuarioParaReset(null);
    }
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
        cargando={loading}
        onVerDetalle={handleVerDetalle}
        onEditarUsuario={handleEditarUsuario}
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

      {/* Modal de confirmación para resetear contraseña */}
      <ConfirmModal
        isOpen={modalConfirmResetAbierto}
        onClose={cerrarModalConfirmReset}
        title="Resetear Contraseña"
        description={`¿Estás seguro de que deseas resetear la contraseña del usuario ${usuarioParaReset?.CN_Nombre || ''} ${usuarioParaReset?.CN_Apellido1 || ''} ${usuarioParaReset?.CN_Apellido2 || ''}?\n\nSe enviará un correo electrónico a ${usuarioParaReset?.CT_Correo || ''} con las instrucciones para establecer una nueva contraseña.`}
        confirmText={loadingResetPassword ? "Enviando..." : "Sí, Resetear"}
        cancelText="Cancelar"
        confirmColor="danger"
        onConfirm={confirmarResetearContrasena}
        isLoading={loadingResetPassword}
        disableBackdropClose={loadingResetPassword}
      />
    </div>
  );
};

export default GestionUsuarios;