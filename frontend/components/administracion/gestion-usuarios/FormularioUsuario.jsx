import React, { useState, useEffect } from 'react';
import {
  Button,
  Input,
  Select,
  SelectItem
} from '@heroui/react';
import { 
  IoPerson, 
  IoMail,
  IoShield,
  IoCheckmarkCircle
} from 'react-icons/io5';
import { roles, estadosUsuario } from '../../../data/mockUsuarios';
import DrawerGeneral from '../../ui/DrawerGeneral';

const FormularioUsuario = ({ 
  usuario, 
  modo, 
  isOpen, 
  onClose, 
  onGuardar 
}) => {
  const [formData, setFormData] = useState({
    CT_Nombre_usuario: '',
    CT_Correo: '',
    CN_Id_rol: '',
    rolNombre: '',
    CN_Id_estado: 1,
    estadoNombre: 'Activo'
  });

  const [errores, setErrores] = useState({});
  const [cargando, setCargando] = useState(false);

  // Inicializar formulario cuando cambie el usuario o modo
  useEffect(() => {
    if (modo === 'editar' && usuario) {
      setFormData({
        CT_Nombre_usuario: usuario.CT_Nombre_usuario || '',
        CT_Correo: usuario.CT_Correo || '',
        CN_Id_rol: usuario.CN_Id_rol || '',
        rolNombre: usuario.rolNombre || '',
        CN_Id_estado: usuario.CN_Id_estado || 1,
        estadoNombre: usuario.estadoNombre || 'Activo'
      });
    } else {
      // Resetear formulario para nuevo usuario
      setFormData({
        CT_Nombre_usuario: '',
        CT_Correo: '',
        CN_Id_rol: '',
        rolNombre: '',
        CN_Id_estado: 1,
        estadoNombre: 'Activo'
      });
    }
    setErrores({});
  }, [usuario, modo, isOpen]);

  const handleInputChange = (campo, valor) => {
    setFormData(prev => ({
      ...prev,
      [campo]: valor
    }));

    // Limpiar error del campo cuando el usuario empiece a escribir
    if (errores[campo]) {
      setErrores(prev => ({
        ...prev,
        [campo]: null
      }));
    }
  };

  const handleRolChange = (keys) => {
    const rolId = Array.from(keys)[0];
    const rol = roles.find(r => r.id.toString() === rolId);
    
    if (rol) {
      setFormData(prev => ({
        ...prev,
        CN_Id_rol: rol.id,
        rolNombre: rol.nombre
      }));
    }
  };

  const handleEstadoChange = (keys) => {
    const estadoId = Array.from(keys)[0];
    const estado = estadosUsuario.find(e => e.id.toString() === estadoId);
    
    if (estado) {
      setFormData(prev => ({
        ...prev,
        CN_Id_estado: estado.id,
        estadoNombre: estado.nombre
      }));
    }
  };

  const validarFormulario = () => {
    const nuevosErrores = {};

    // Validaciones requeridas
    if (!formData.CT_Nombre_usuario.trim()) {
      nuevosErrores.CT_Nombre_usuario = 'El nombre de usuario es requerido';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.CT_Nombre_usuario)) {
      nuevosErrores.CT_Nombre_usuario = 'Debe ser un correo electrónico válido';
    }

    if (!formData.CT_Correo.trim()) {
      nuevosErrores.CT_Correo = 'El correo es requerido';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.CT_Correo)) {
      nuevosErrores.CT_Correo = 'El formato del correo no es válido';
    }

    if (!formData.CN_Id_rol) {
      nuevosErrores.CN_Id_rol = 'El rol es requerido';
    }

    setErrores(nuevosErrores);
    return Object.keys(nuevosErrores).length === 0;
  };

  const handleSubmit = async () => {
    if (!validarFormulario()) {
      return;
    }

    setCargando(true);
    
    try {
      // Preparar datos para enviar
      const datosUsuario = {
        CT_Nombre_usuario: formData.CT_Nombre_usuario.trim(),
        CT_Correo: formData.CT_Correo.trim(),
        CN_Id_rol: formData.CN_Id_rol,
        rolNombre: formData.rolNombre,
        CN_Id_estado: formData.CN_Id_estado,
        estadoNombre: formData.estadoNombre
      };

      await onGuardar(datosUsuario);
      
    } catch (error) {
      console.error('Error al guardar usuario:', error);
      // Aquí podrías mostrar un mensaje de error al usuario
    } finally {
      setCargando(false);
    }
  };

  const handleClose = () => {
    setFormData({
      CT_Nombre_usuario: '',
      CT_Correo: '',
      CN_Id_rol: '',
      rolNombre: '',
      CN_Id_estado: 1,
      estadoNombre: 'Activo'
    });
    setErrores({});
    onClose();
  };

  return (
    <DrawerGeneral
      isOpen={isOpen}
      onOpenChange={(open) => !open && handleClose()}
      titulo={modo === 'crear' ? 'Crear Nuevo Usuario' : 'Editar Usuario'}
      size="lg"
      disableClose={cargando}
      botonCerrar={{
        mostrar: true,
        texto: "Cancelar",
        onPress: handleClose
      }}
      botonAccion={{
        texto: modo === 'crear' ? 'Crear Usuario' : 'Guardar Cambios',
        onPress: handleSubmit,
        loading: cargando,
        color: "primary"
      }}
    >
      <div className="space-y-6">
        {/* Descripción con mejor estilo */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-sm text-blue-700 dark:text-blue-300 flex items-center gap-2">
            <IoPerson className="text-blue-600 dark:text-blue-400" />
            {modo === 'crear' 
              ? 'Complete los datos para crear un nuevo usuario en el sistema'
              : 'Modifique los datos del usuario seleccionado'
            }
          </p>
        </div>

        {/* Campos del formulario con mejor espaciado */}
        <div className="space-y-5">
          <Input
            label="Nombre de Usuario"
            placeholder="usuario@justicia.gov.co"
            type="email"
            value={formData.CT_Nombre_usuario}
            onValueChange={(valor) => handleInputChange('CT_Nombre_usuario', valor)}
            isInvalid={!!errores.CT_Nombre_usuario}
            errorMessage={errores.CT_Nombre_usuario}
            isRequired
            variant="bordered"
            classNames={{
              input: "text-sm",
              label: "text-sm font-medium"
            }}
          />

          <Input
            label="Correo Electrónico"
            placeholder="correo@justicia.gov.co"
            type="email"
            value={formData.CT_Correo}
            onValueChange={(valor) => handleInputChange('CT_Correo', valor)}
            isInvalid={!!errores.CT_Correo}
            errorMessage={errores.CT_Correo}
            isRequired
            variant="bordered"
            classNames={{
              input: "text-sm",
              label: "text-sm font-medium"
            }}
          />

          <Select
            label="Rol del Usuario"
            placeholder="Seleccionar rol"
            selectedKeys={formData.CN_Id_rol ? [formData.CN_Id_rol.toString()] : []}
            onSelectionChange={handleRolChange}
            isInvalid={!!errores.CN_Id_rol}
            errorMessage={errores.CN_Id_rol}
            isRequired
            variant="bordered"
            classNames={{
              label: "text-sm font-medium"
            }}
          >
            {roles.map((rol) => (
              <SelectItem key={rol.id.toString()} value={rol.id.toString()}>
                {rol.nombre}
              </SelectItem>
            ))}
          </Select>

          <Select
            label="Estado del Usuario"
            placeholder="Seleccionar estado"
            selectedKeys={formData.CN_Id_estado ? [formData.CN_Id_estado.toString()] : []}
            onSelectionChange={handleEstadoChange}
            variant="bordered"
            classNames={{
              label: "text-sm font-medium"
            }}
          >
            {estadosUsuario.map((estado) => (
              <SelectItem key={estado.id.toString()} value={estado.id.toString()}>
                {estado.nombre}
              </SelectItem>
            ))}
          </Select>
        </div>
      </div>
    </DrawerGeneral>
  );
};

export default FormularioUsuario;
