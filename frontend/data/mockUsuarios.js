// Datos mock para el módulo de gestión de usuarios
import { subDays, format } from 'date-fns';

// Roles disponibles
export const roles = [
  { id: 1, nombre: 'Administrador' },
  { id: 2, nombre: 'Usuario Judicial' }
];

// Estados de usuario
export const estadosUsuario = [
  { id: 1, nombre: 'Activo' },
  { id: 2, nombre: 'Inactivo' }
];

// Usuarios mock con todos los campos necesarios
export const usuariosMock = [
  {
    id: 1,
    nombreUsuario: 'maria.gonzalez',
    correo: 'maria.gonzalez@justicia.gov',
    nombre: 'María González Pérez',
    idRol: 1,
    rolNombre: 'Administrador',
    idEstado: 1,
    estadoNombre: 'Activo',
    fechaCreacion: subDays(new Date(), 180).toISOString(),
    ultimoAcceso: subDays(new Date(), 1).toISOString(),
    telefono: '+57 310 123 4567',
    cedula: '12345678',
    cargo: 'Administrador del Sistema'
  },
  {
    id: 2,
    nombreUsuario: 'carlos.rodriguez',
    correo: 'carlos.rodriguez@justicia.gov',
    nombre: 'Carlos Rodríguez López',
    idRol: 2,
    rolNombre: 'Usuario Judicial',
    idEstado: 1,
    estadoNombre: 'Activo',
    fechaCreacion: subDays(new Date(), 150).toISOString(),
    ultimoAcceso: subDays(new Date(), 2).toISOString(),
    telefono: '+57 315 987 6543',
    cedula: '23456789',
    cargo: 'Juez Civil'
  },
  {
    id: 3,
    nombreUsuario: 'ana.martinez',
    correo: 'ana.martinez@justicia.gov',
    nombre: 'Ana María Martínez Silva',
    idRol: 2,
    rolNombre: 'Usuario Judicial',
    idEstado: 1,
    estadoNombre: 'Activo',
    fechaCreacion: subDays(new Date(), 120).toISOString(),
    ultimoAcceso: subDays(new Date(), 5).toISOString(),
    telefono: '+57 320 456 7890',
    cedula: '34567890',
    cargo: 'Secretaria Judicial'
  },
  {
    id: 4,
    nombreUsuario: 'luis.fernandez',
    correo: 'luis.fernandez@justicia.gov',
    nombre: 'Luis Fernando Fernández Castro',
    idRol: 2,
    rolNombre: 'Usuario Judicial',
    idEstado: 2,
    estadoNombre: 'Inactivo',
    fechaCreacion: subDays(new Date(), 90).toISOString(),
    ultimoAcceso: subDays(new Date(), 30).toISOString(),
    telefono: '+57 318 234 5678',
    cedula: '45678901',
    cargo: 'Auxiliar Judicial'
  },
  {
    id: 5,
    nombreUsuario: 'carmen.silva',
    correo: 'carmen.silva@justicia.gov',
    nombre: 'Carmen Elena Silva Vargas',
    idRol: 1,
    rolNombre: 'Administrador',
    idEstado: 1,
    estadoNombre: 'Activo',
    fechaCreacion: subDays(new Date(), 200).toISOString(),
    ultimoAcceso: subDays(new Date(), 1).toISOString(),
    telefono: '+57 312 345 6789',
    cedula: '56789012',
    cargo: 'Administrador General'
  },
  {
    id: 6,
    nombreUsuario: 'diego.morales',
    correo: 'diego.morales@justicia.gov',
    nombre: 'Diego Alejandro Morales Ruiz',
    idRol: 2,
    rolNombre: 'Usuario Judicial',
    idEstado: 1,
    estadoNombre: 'Activo',
    fechaCreacion: subDays(new Date(), 75).toISOString(),
    ultimoAcceso: subDays(new Date(), 3).toISOString(),
    telefono: '+57 317 890 1234',
    cedula: '67890123',
    cargo: 'Juez Penal'
  },
  {
    id: 7,
    nombreUsuario: 'patricia.ruiz',
    correo: 'patricia.ruiz@justicia.gov',
    nombre: 'Patricia Andrea Ruiz Gómez',
    idRol: 2,
    rolNombre: 'Usuario Judicial',
    idEstado: 1,
    estadoNombre: 'Activo',
    fechaCreacion: subDays(new Date(), 60).toISOString(),
    ultimoAcceso: subDays(new Date(), 7).toISOString(),
    telefono: '+57 314 567 8901',
    cedula: '78901234',
    cargo: 'Secretaria de Despacho'
  },
  {
    id: 8,
    nombreUsuario: 'roberto.jimenez',
    correo: 'roberto.jimenez@justicia.gov',
    nombre: 'Roberto Carlos Jiménez Torres',
    idRol: 2,
    rolNombre: 'Usuario Judicial',
    idEstado: 2,
    estadoNombre: 'Inactivo',
    fechaCreacion: subDays(new Date(), 45).toISOString(),
    ultimoAcceso: subDays(new Date(), 15).toISOString(),
    telefono: '+57 319 678 9012',
    cedula: '89012345',
    cargo: 'Oficial Mayor'
  }
];

// Función para obtener estadísticas de usuarios
export const obtenerEstadisticasUsuarios = () => {
  const totalUsuarios = usuariosMock.length;
  const usuariosActivos = usuariosMock.filter(u => u.estadoNombre === 'Activo').length;
  const usuariosInactivos = usuariosMock.filter(u => u.estadoNombre === 'Inactivo').length;
  const administradores = usuariosMock.filter(u => u.rolNombre === 'Administrador').length;
  const usuariosJudiciales = usuariosMock.filter(u => u.rolNombre === 'Usuario Judicial').length;

  // Usuarios creados en los últimos 30 días
  const hace30Dias = subDays(new Date(), 30);
  const usuariosRecientes = usuariosMock.filter(u => 
    new Date(u.fechaCreacion) >= hace30Dias
  ).length;

  // Usuarios con acceso reciente (últimos 7 días)
  const hace7Dias = subDays(new Date(), 7);
  const usuariosConAccesoReciente = usuariosMock.filter(u => 
    u.estadoNombre === 'Activo' && new Date(u.ultimoAcceso) >= hace7Dias
  ).length;

  return {
    totalUsuarios,
    usuariosActivos,
    usuariosInactivos,
    administradores,
    usuariosJudiciales,
    usuariosRecientes,
    usuariosConAccesoReciente,
    porcentajeActivos: Math.round((usuariosActivos / totalUsuarios) * 100),
    porcentajeInactivos: Math.round((usuariosInactivos / totalUsuarios) * 100)
  };
};

// Función para filtrar usuarios
export const filtrarUsuarios = (filtros) => {
  return usuariosMock.filter(usuario => {
    const cumpleNombre = !filtros.nombre || 
      usuario.nombre.toLowerCase().includes(filtros.nombre.toLowerCase()) ||
      usuario.nombreUsuario.toLowerCase().includes(filtros.nombre.toLowerCase());
    
    const cumpleCorreo = !filtros.correo || 
      usuario.correo.toLowerCase().includes(filtros.correo.toLowerCase());
    
    const cumpleRol = !filtros.rol || usuario.rolNombre === filtros.rol;
    
    const cumpleEstado = !filtros.estado || usuario.estadoNombre === filtros.estado;
    
    const cumpleCargo = !filtros.cargo || 
      usuario.cargo.toLowerCase().includes(filtros.cargo.toLowerCase());

    return cumpleNombre && cumpleCorreo && cumpleRol && cumpleEstado && cumpleCargo;
  });
};

// Función para crear un nuevo usuario
export const crearUsuario = (datosUsuario) => {
  const nuevoId = Math.max(...usuariosMock.map(u => u.id)) + 1;
  const nuevoUsuario = {
    id: nuevoId,
    ...datosUsuario,
    fechaCreacion: new Date().toISOString(),
    ultimoAcceso: null
  };
  
  usuariosMock.push(nuevoUsuario);
  return nuevoUsuario;
};

// Función para actualizar un usuario
export const actualizarUsuario = (id, datosActualizados) => {
  const indice = usuariosMock.findIndex(u => u.id === id);
  if (indice !== -1) {
    usuariosMock[indice] = { ...usuariosMock[indice], ...datosActualizados };
    return usuariosMock[indice];
  }
  return null;
};

// Función para eliminar lógicamente un usuario (cambiar estado a inactivo)
export const desactivarUsuario = (id) => {
  const indice = usuariosMock.findIndex(u => u.id === id);
  if (indice !== -1) {
    usuariosMock[indice].idEstado = 2;
    usuariosMock[indice].estadoNombre = 'Inactivo';
    return usuariosMock[indice];
  }
  return null;
};

// Función para activar un usuario
export const activarUsuario = (id) => {
  const indice = usuariosMock.findIndex(u => u.id === id);
  if (indice !== -1) {
    usuariosMock[indice].idEstado = 1;
    usuariosMock[indice].estadoNombre = 'Activo';
    return usuariosMock[indice];
  }
  return null;
};
