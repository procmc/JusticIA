import React, { useState, useEffect } from 'react';
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Input,
  Select,
  SelectItem,
  Card,
  CardBody
} from '@heroui/react';
import { 
  IoPerson, 
  IoMail, 
  IoCall, 
  IoCard, 
  IoBriefcase, 
  IoLockClosed, 
  IoEye, 
  IoEyeOff,
  IoSave,
  IoClose
} from 'react-icons/io5';
import { roles, estadosUsuario } from '../../../data/mockUsuarios';

const FormularioUsuario = ({ 
  usuario, 
  modo, 
  isOpen, 
  onClose, 
  onGuardar 
}) => {
  const [formData, setFormData] = useState({
    nombre: '',
    nombreUsuario: '',
    correo: '',
    telefono: '',
    cedula: '',
    cargo: '',
    idRol: '',
    rolNombre: '',
    idEstado: 1,
    estadoNombre: 'Activo',
    contrasena: '',
    confirmarContrasena: ''
  });

  const [errores, setErrores] = useState({});
  const [mostrarContrasena, setMostrarContrasena] = useState(false);
  const [mostrarConfirmarContrasena, setMostrarConfirmarContrasena] = useState(false);
  const [cargando, setCargando] = useState(false);

  // Inicializar formulario cuando cambie el usuario o modo
  useEffect(() => {
    if (modo === 'editar' && usuario) {
      setFormData({
        nombre: usuario.nombre || '',
        nombreUsuario: usuario.nombreUsuario || '',
        correo: usuario.correo || '',
        telefono: usuario.telefono || '',
        cedula: usuario.cedula || '',
        cargo: usuario.cargo || '',
        idRol: usuario.idRol || '',
        rolNombre: usuario.rolNombre || '',
        idEstado: usuario.idEstado || 1,
        estadoNombre: usuario.estadoNombre || 'Activo',
        contrasena: '',
        confirmarContrasena: ''
      });
    } else {
      // Resetear formulario para nuevo usuario
      setFormData({
        nombre: '',
        nombreUsuario: '',
        correo: '',
        telefono: '',
        cedula: '',
        cargo: '',
        idRol: '',
        rolNombre: '',
        idEstado: 1,
        estadoNombre: 'Activo',
        contrasena: '',
        confirmarContrasena: ''
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
        idRol: rol.id,
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
        idEstado: estado.id,
        estadoNombre: estado.nombre
      }));
    }
  };

  const validarFormulario = () => {
    const nuevosErrores = {};

    // Validaciones requeridas
    if (!formData.nombre.trim()) {
      nuevosErrores.nombre = 'El nombre es requerido';
    }

    if (!formData.nombreUsuario.trim()) {
      nuevosErrores.nombreUsuario = 'El nombre de usuario es requerido';
    } else if (!/^[a-zA-Z0-9._-]+$/.test(formData.nombreUsuario)) {
      nuevosErrores.nombreUsuario = 'El nombre de usuario solo puede contener letras, números, puntos, guiones y guiones bajos';
    }

    if (!formData.correo.trim()) {
      nuevosErrores.correo = 'El correo es requerido';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.correo)) {
      nuevosErrores.correo = 'El formato del correo no es válido';
    }

    if (!formData.telefono.trim()) {
      nuevosErrores.telefono = 'El teléfono es requerido';
    }

    if (!formData.cedula.trim()) {
      nuevosErrores.cedula = 'La cédula es requerida';
    } else if (!/^\d+$/.test(formData.cedula)) {
      nuevosErrores.cedula = 'La cédula debe contener solo números';
    }

    if (!formData.cargo.trim()) {
      nuevosErrores.cargo = 'El cargo es requerido';
    }

    if (!formData.idRol) {
      nuevosErrores.idRol = 'El rol es requerido';
    }

    // Validaciones de contraseña solo para nuevo usuario o si se está cambiando
    if (modo === 'crear' || formData.contrasena) {
      if (!formData.contrasena) {
        nuevosErrores.contrasena = 'La contraseña es requerida';
      } else if (formData.contrasena.length < 8) {
        nuevosErrores.contrasena = 'La contraseña debe tener al menos 8 caracteres';
      }

      if (!formData.confirmarContrasena) {
        nuevosErrores.confirmarContrasena = 'Confirmar la contraseña es requerido';
      } else if (formData.contrasena !== formData.confirmarContrasena) {
        nuevosErrores.confirmarContrasena = 'Las contraseñas no coinciden';
      }
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
        nombre: formData.nombre.trim(),
        nombreUsuario: formData.nombreUsuario.trim(),
        correo: formData.correo.trim(),
        telefono: formData.telefono.trim(),
        cedula: formData.cedula.trim(),
        cargo: formData.cargo.trim(),
        idRol: formData.idRol,
        rolNombre: formData.rolNombre,
        idEstado: formData.idEstado,
        estadoNombre: formData.estadoNombre
      };

      // Solo incluir contraseña si es un nuevo usuario o si se está cambiando
      if (modo === 'crear' || formData.contrasena) {
        datosUsuario.contrasena = formData.contrasena;
      }

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
      nombre: '',
      nombreUsuario: '',
      correo: '',
      telefono: '',
      cedula: '',
      cargo: '',
      idRol: '',
      rolNombre: '',
      idEstado: 1,
      estadoNombre: 'Activo',
      contrasena: '',
      confirmarContrasena: ''
    });
    setErrores({});
    onClose();
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={handleClose}
      size="3xl"
      scrollBehavior="inside"
      placement="center"
      isDismissable={!cargando}
    >
      <ModalContent>
        <ModalHeader className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <IoPerson className="text-primary text-xl" />
            <span>
              {modo === 'crear' ? 'Crear Nuevo Usuario' : 'Editar Usuario'}
            </span>
          </div>
          <p className="text-sm text-gray-500 font-normal">
            {modo === 'crear' 
              ? 'Complete los datos para crear un nuevo usuario en el sistema'
              : 'Modifique los datos del usuario seleccionado'
            }
          </p>
        </ModalHeader>
        
        <ModalBody>
          <div className="space-y-6">
            {/* Información Personal */}
            <Card>
              <CardBody className="space-y-4">
                <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Información Personal
                </h4>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Nombre Completo"
                    placeholder="Ej: María González Pérez"
                    value={formData.nombre}
                    onValueChange={(valor) => handleInputChange('nombre', valor)}
                    isInvalid={!!errores.nombre}
                    errorMessage={errores.nombre}
                    startContent={<IoPerson className="text-gray-400" />}
                    isRequired
                    variant="bordered"
                  />
                  
                  <Input
                    label="Nombre de Usuario"
                    placeholder="Ej: maria.gonzalez"
                    value={formData.nombreUsuario}
                    onValueChange={(valor) => handleInputChange('nombreUsuario', valor)}
                    isInvalid={!!errores.nombreUsuario}
                    errorMessage={errores.nombreUsuario}
                    startContent={<span className="text-gray-400">@</span>}
                    isRequired
                    variant="bordered"
                  />
                  
                  <Input
                    label="Correo Electrónico"
                    placeholder="Ej: maria.gonzalez@justicia.gov"
                    type="email"
                    value={formData.correo}
                    onValueChange={(valor) => handleInputChange('correo', valor)}
                    isInvalid={!!errores.correo}
                    errorMessage={errores.correo}
                    startContent={<IoMail className="text-gray-400" />}
                    isRequired
                    variant="bordered"
                  />
                  
                  <Input
                    label="Teléfono"
                    placeholder="Ej: +57 310 123 4567"
                    value={formData.telefono}
                    onValueChange={(valor) => handleInputChange('telefono', valor)}
                    isInvalid={!!errores.telefono}
                    errorMessage={errores.telefono}
                    startContent={<IoCall className="text-gray-400" />}
                    isRequired
                    variant="bordered"
                  />
                  
                  <Input
                    label="Cédula"
                    placeholder="Ej: 12345678"
                    value={formData.cedula}
                    onValueChange={(valor) => handleInputChange('cedula', valor)}
                    isInvalid={!!errores.cedula}
                    errorMessage={errores.cedula}
                    startContent={<IoCard className="text-gray-400" />}
                    isRequired
                    variant="bordered"
                  />
                  
                  <Input
                    label="Cargo"
                    placeholder="Ej: Juez Civil"
                    value={formData.cargo}
                    onValueChange={(valor) => handleInputChange('cargo', valor)}
                    isInvalid={!!errores.cargo}
                    errorMessage={errores.cargo}
                    startContent={<IoBriefcase className="text-gray-400" />}
                    isRequired
                    variant="bordered"
                  />
                </div>
              </CardBody>
            </Card>

            {/* Rol y Estado */}
            <Card>
              <CardBody className="space-y-4">
                <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Rol y Estado
                </h4>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Select
                    label="Rol"
                    placeholder="Seleccionar rol"
                    selectedKeys={formData.idRol ? [formData.idRol.toString()] : []}
                    onSelectionChange={handleRolChange}
                    isInvalid={!!errores.idRol}
                    errorMessage={errores.idRol}
                    isRequired
                    variant="bordered"
                  >
                    {roles.map((rol) => (
                      <SelectItem key={rol.id.toString()} value={rol.id.toString()}>
                        {rol.nombre}
                      </SelectItem>
                    ))}
                  </Select>
                  
                  {modo === 'editar' && (
                    <Select
                      label="Estado"
                      placeholder="Seleccionar estado"
                      selectedKeys={formData.idEstado ? [formData.idEstado.toString()] : []}
                      onSelectionChange={handleEstadoChange}
                      variant="bordered"
                    >
                      {estadosUsuario.map((estado) => (
                        <SelectItem key={estado.id.toString()} value={estado.id.toString()}>
                          {estado.nombre}
                        </SelectItem>
                      ))}
                    </Select>
                  )}
                </div>
              </CardBody>
            </Card>

            {/* Contraseña */}
            <Card>
              <CardBody className="space-y-4">
                <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {modo === 'crear' ? 'Contraseña' : 'Cambiar Contraseña (Opcional)'}
                </h4>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label={modo === 'crear' ? 'Contraseña' : 'Nueva Contraseña'}
                    placeholder="Mínimo 8 caracteres"
                    type={mostrarContrasena ? 'text' : 'password'}
                    value={formData.contrasena}
                    onValueChange={(valor) => handleInputChange('contrasena', valor)}
                    isInvalid={!!errores.contrasena}
                    errorMessage={errores.contrasena}
                    startContent={<IoLockClosed className="text-gray-400" />}
                    endContent={
                      <button
                        type="button"
                        onClick={() => setMostrarContrasena(!mostrarContrasena)}
                        className="focus:outline-none"
                      >
                        {mostrarContrasena ? (
                          <IoEyeOff className="text-gray-400" />
                        ) : (
                          <IoEye className="text-gray-400" />
                        )}
                      </button>
                    }
                    isRequired={modo === 'crear'}
                    variant="bordered"
                  />
                  
                  <Input
                    label="Confirmar Contraseña"
                    placeholder="Repita la contraseña"
                    type={mostrarConfirmarContrasena ? 'text' : 'password'}
                    value={formData.confirmarContrasena}
                    onValueChange={(valor) => handleInputChange('confirmarContrasena', valor)}
                    isInvalid={!!errores.confirmarContrasena}
                    errorMessage={errores.confirmarContrasena}
                    startContent={<IoLockClosed className="text-gray-400" />}
                    endContent={
                      <button
                        type="button"
                        onClick={() => setMostrarConfirmarContrasena(!mostrarConfirmarContrasena)}
                        className="focus:outline-none"
                      >
                        {mostrarConfirmarContrasena ? (
                          <IoEyeOff className="text-gray-400" />
                        ) : (
                          <IoEye className="text-gray-400" />
                        )}
                      </button>
                    }
                    isRequired={modo === 'crear' || !!formData.contrasena}
                    variant="bordered"
                  />
                </div>
              </CardBody>
            </Card>
          </div>
        </ModalBody>
        
        <ModalFooter>
          <Button
            color="danger"
            variant="flat"
            onPress={handleClose}
            isDisabled={cargando}
            startContent={<IoClose className="text-lg" />}
          >
            Cancelar
          </Button>
          
          <Button
            color="primary"
            onPress={handleSubmit}
            isLoading={cargando}
            startContent={!cargando && <IoSave className="text-lg" />}
          >
            {modo === 'crear' ? 'Crear Usuario' : 'Guardar Cambios'}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default FormularioUsuario;
