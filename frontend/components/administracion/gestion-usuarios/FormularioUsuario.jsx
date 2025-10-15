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
    cedula: '',
    CT_Nombre: '',
    CT_Apellido_uno: '',
    CT_Apellido_dos: '',
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
        cedula: usuario.CN_Id_usuario || '',
        CT_Nombre: usuario.CT_Nombre || '',
        CT_Apellido_uno: usuario.CT_Apellido_uno || '',
        CT_Apellido_dos: usuario.CT_Apellido_dos || '',
        CT_Correo: usuario.CT_Correo || '',
        CN_Id_rol: (usuario.CN_Id_rol && usuario.CN_Id_rol > 0) ? usuario.CN_Id_rol : '',
        rolNombre: usuario.rol?.nombre || '',
        CN_Id_estado: (usuario.CN_Id_estado && usuario.CN_Id_estado > 0) ? usuario.CN_Id_estado : 1,
        estadoNombre: usuario.estado?.nombre || 'Activo'
      });
    } else {
      // Resetear formulario para nuevo usuario
      setFormData({
        cedula: '',
        CT_Nombre: '',
        CT_Apellido_uno: '',
        CT_Apellido_dos: '',
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
    if (!formData.cedula.trim()) {
      nuevosErrores.cedula = 'La cédula es requerida';
    } else if (!/^\d{8,15}$/.test(formData.cedula.trim())) {
      nuevosErrores.cedula = 'La cédula debe contener solo números (8-15 dígitos)';
    }

    if (!formData.CT_Nombre.trim()) {
      nuevosErrores.CT_Nombre = 'El nombre es requerido';
    }

    if (!formData.CT_Apellido_uno.trim()) {
      nuevosErrores.CT_Apellido_uno = 'El primer apellido es requerido';
    }

    if (!formData.CT_Apellido_dos.trim()) {
      nuevosErrores.CT_Apellido_dos = 'El segundo apellido es requerido';
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
        cedula: formData.cedula.trim(),
        nombre_usuario: formData.CT_Correo.trim().split('@')[0], // Usar solo la parte antes del @ como nombre de usuario
        nombre: formData.CT_Nombre.trim(),
        apellido_uno: formData.CT_Apellido_uno.trim(),
        apellido_dos: formData.CT_Apellido_dos.trim(), // Ahora requerido
        correo: formData.CT_Correo.trim(),
        id_rol: formData.CN_Id_rol,
        id_estado: formData.CN_Id_estado || 1
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
      cedula: '',
      CT_Nombre: '',
      CT_Apellido_uno: '',
      CT_Apellido_dos: '',
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
      size="md"
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
            label="Cédula"
            placeholder="123456789"
            type="text"
            value={formData.cedula}
            onValueChange={(valor) => handleInputChange('cedula', valor)}
            isInvalid={!!errores.cedula}
            errorMessage={errores.cedula}
            isRequired
            variant="bordered"
            isDisabled={modo === 'editar'}
            classNames={{
              input: modo === 'editar' ? "text-sm bg-gray-100 text-gray-700" : "text-sm",
              label: modo === 'editar' ? "text-sm font-medium text-gray-700" : "text-sm font-medium",
              inputWrapper: modo === 'editar' ? "bg-gray-100 border-gray-300" : ""
            }}
            color='primary'
          />

          <Input
            label="Nombre"
            placeholder="Juan"
            type="text"
            value={formData.CT_Nombre}
            onValueChange={(valor) => handleInputChange('CT_Nombre', valor)}
            isInvalid={!!errores.CT_Nombre}
            errorMessage={errores.CT_Nombre}
            isRequired
            variant="bordered"
            color='primary'
          />

          <Input
            label="Primer Apellido"
            placeholder="Pérez"
            type="text"
            value={formData.CT_Apellido_uno}
            onValueChange={(valor) => handleInputChange('CT_Apellido_uno', valor)}
            isInvalid={!!errores.CT_Apellido_uno}
            errorMessage={errores.CT_Apellido_uno}
            isRequired
            variant="bordered"
            color='primary'
          />

          <Input
            label="Segundo Apellido"
            placeholder="López"
            type="text"
            value={formData.CT_Apellido_dos}
            onValueChange={(valor) => handleInputChange('CT_Apellido_dos', valor)}
            isInvalid={!!errores.CT_Apellido_dos}
            errorMessage={errores.CT_Apellido_dos}
            isRequired
            variant="bordered"
            color='primary'
          />

          <Input
            label="Correo Electrónico"
            placeholder="correo@ejemplo.com"
            type="email"
            value={formData.CT_Correo}
            onValueChange={(valor) => handleInputChange('CT_Correo', valor)}
            isInvalid={!!errores.CT_Correo}
            errorMessage={errores.CT_Correo}
            isRequired
            variant="bordered"
            color='primary'
          />

          <Select
            label="Rol del Usuario"
            placeholder="Seleccionar rol"
            selectedKeys={formData.CN_Id_rol && formData.CN_Id_rol > 0 ? [formData.CN_Id_rol.toString()] : []}
            onSelectionChange={handleRolChange}
            isInvalid={!!errores.CN_Id_rol}
            errorMessage={errores.CN_Id_rol}
            isRequired
            variant="bordered"
            isDisabled={modo === 'editar'}
            classNames={{
              label: modo === 'editar' ? "text-sm font-medium text-gray-700" : "text-sm font-medium",
              trigger: modo === 'editar' ? "bg-gray-100 border-gray-300" : "",
              value: modo === 'editar' ? "text-gray-700" : ""
            }}
            color='primary'
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
            selectedKeys={formData.CN_Id_estado && formData.CN_Id_estado > 0 ? [formData.CN_Id_estado.toString()] : []}
            onSelectionChange={handleEstadoChange}
            variant="bordered"
            color='primary'
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
