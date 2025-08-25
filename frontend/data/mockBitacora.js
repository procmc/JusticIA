// Datos mock para el módulo de bitácora
import { subDays, format } from 'date-fns';

// Tipos de acciones
export const tiposAccion = [
  { id: 1, nombre: 'Consulta' },
  { id: 2, nombre: 'Carga' },
  { id: 3, nombre: 'Búsqueda similares' }
];

// Estados de procesamiento
export const estadosProcesamiento = [
  { id: 1, nombre: 'Pendiente' },
  { id: 2, nombre: 'Procesado' },
  { id: 3, nombre: 'Error' }
];

// Roles
export const roles = [
  { id: 1, nombre: 'Administrador' },
  { id: 2, nombre: 'Usuario Judicial' }
];

// Usuarios mock
export const usuarios = [
  { id: 1, nombre: 'María González', correo: 'maria.gonzalez@justicia.gov', rol: 'Administrador' },
  { id: 2, nombre: 'Carlos Rodríguez', correo: 'carlos.rodriguez@justicia.gov', rol: 'Usuario Judicial' },
  { id: 3, nombre: 'Ana Martínez', correo: 'ana.martinez@justicia.gov', rol: 'Usuario Judicial' },
  { id: 4, nombre: 'Luis Fernández', correo: 'luis.fernandez@justicia.gov', rol: 'Usuario Judicial' },
  { id: 5, nombre: 'Carmen Silva', correo: 'carmen.silva@justicia.gov', rol: 'Administrador' },
  { id: 6, nombre: 'Diego Morales', correo: 'diego.morales@justicia.gov', rol: 'Usuario Judicial' },
  { id: 7, nombre: 'Patricia Ruiz', correo: 'patricia.ruiz@justicia.gov', rol: 'Usuario Judicial' },
  { id: 8, nombre: 'Roberto Jiménez', correo: 'roberto.jimenez@justicia.gov', rol: 'Usuario Judicial' }
];

// Expedientes mock
export const expedientes = [
  '2024-000001-1234-CI',
  '2024-000002-1234-PE',
  '2024-000003-1235-CI',
  '2024-000004-1236-FA',
  '2024-000005-1234-LA',
  '2024-000006-1237-CI',
  '2024-000007-1234-PE',
  '2024-000008-1238-CI',
  '2024-000009-1234-FA',
  '2024-000010-1239-LA'
];

// Registros de bitácora con fechas fijas (sin Math.random)
export const registrosBitacora = [
  {
    id: 1,
    fechaHora: new Date('2024-08-25T09:15:30'),
    texto: 'Consulta de expediente 2024-000001-1234-CI',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 1250ms',
    expediente: '2024-000001-1234-CI',
    tipoAccion: 'Consulta',
    usuario: 'María González',
    correoUsuario: 'maria.gonzalez@justicia.gov',
    rolUsuario: 'Administrador',
    estado: 'Procesado',
    ip: '192.168.1.15',
    navegador: 'Chrome',
    duracion: 1250
  },
  {
    id: 2,
    fechaHora: new Date('2024-08-25T10:30:45'),
    texto: 'Carga de documento en expediente 2024-000002-1234-PE',
    informacionAdicional: 'Archivo: documento_567.pdf. Tamaño: 15MB',
    expediente: '2024-000002-1234-PE',
    tipoAccion: 'Carga',
    usuario: 'Carlos Rodríguez',
    correoUsuario: 'carlos.rodriguez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.45',
    navegador: 'Firefox',
    duracion: 3200
  },
  {
    id: 3,
    fechaHora: new Date('2024-08-25T11:20:15'),
    texto: 'Búsqueda de casos similares para expediente 2024-000003-1235-CI',
    informacionAdicional: '12 casos similares encontrados. Threshold: 0.85',
    expediente: '2024-000003-1235-CI',
    tipoAccion: 'Búsqueda similares',
    usuario: 'Ana Martínez',
    correoUsuario: 'ana.martinez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.78',
    navegador: 'Edge',
    duracion: 4500
  },
  {
    id: 4,
    fechaHora: new Date('2024-08-25T14:45:22'),
    texto: 'Consulta de expediente 2024-000004-1236-FA',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 850ms',
    expediente: '2024-000004-1236-FA',
    tipoAccion: 'Consulta',
    usuario: 'Luis Fernández',
    correoUsuario: 'luis.fernandez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Error',
    ip: '192.168.1.92',
    navegador: 'Chrome',
    duracion: 850
  },
  {
    id: 5,
    fechaHora: new Date('2024-08-24T16:12:33'),
    texto: 'Carga de documento en expediente 2024-000005-1234-LA',
    informacionAdicional: 'Archivo: documento_234.pdf. Tamaño: 8MB',
    expediente: '2024-000005-1234-LA',
    tipoAccion: 'Carga',
    usuario: 'Carmen Silva',
    correoUsuario: 'carmen.silva@justicia.gov',
    rolUsuario: 'Administrador',
    estado: 'Procesado',
    ip: '192.168.1.123',
    navegador: 'Safari',
    duracion: 2100
  },
  {
    id: 6,
    fechaHora: new Date('2024-08-24T08:30:45'),
    texto: 'Búsqueda de casos similares para expediente 2024-000006-1237-CI',
    informacionAdicional: '8 casos similares encontrados. Threshold: 0.78',
    expediente: '2024-000006-1237-CI',
    tipoAccion: 'Búsqueda similares',
    usuario: 'Diego Morales',
    correoUsuario: 'diego.morales@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.156',
    navegador: 'Chrome',
    duracion: 3800
  },
  {
    id: 7,
    fechaHora: new Date('2024-08-23T13:22:11'),
    texto: 'Consulta de expediente 2024-000007-1234-PE',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 1150ms',
    expediente: '2024-000007-1234-PE',
    tipoAccion: 'Consulta',
    usuario: 'Patricia Ruiz',
    correoUsuario: 'patricia.ruiz@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Pendiente',
    ip: '192.168.1.189',
    navegador: 'Firefox',
    duracion: 1150
  },
  {
    id: 8,
    fechaHora: new Date('2024-08-23T15:45:30'),
    texto: 'Carga de documento en expediente 2024-000008-1238-CI',
    informacionAdicional: 'Archivo: documento_890.pdf. Tamaño: 22MB',
    expediente: '2024-000008-1238-CI',
    tipoAccion: 'Carga',
    usuario: 'Roberto Jiménez',
    correoUsuario: 'roberto.jimenez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Error',
    ip: '192.168.1.201',
    navegador: 'Edge',
    duracion: 5200
  },
  {
    id: 9,
    fechaHora: new Date('2024-08-22T09:15:30'),
    texto: 'Consulta de expediente 2024-000009-1234-FA',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 950ms',
    expediente: '2024-000009-1234-FA',
    tipoAccion: 'Consulta',
    usuario: 'María González',
    correoUsuario: 'maria.gonzalez@justicia.gov',
    rolUsuario: 'Administrador',
    estado: 'Procesado',
    ip: '192.168.1.15',
    navegador: 'Chrome',
    duracion: 950
  },
  {
    id: 10,
    fechaHora: new Date('2024-08-22T11:30:45'),
    texto: 'Búsqueda de casos similares para expediente 2024-000010-1239-LA',
    informacionAdicional: '15 casos similares encontrados. Threshold: 0.82',
    expediente: '2024-000010-1239-LA',
    tipoAccion: 'Búsqueda similares',
    usuario: 'Carlos Rodríguez',
    correoUsuario: 'carlos.rodriguez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.45',
    navegador: 'Firefox',
    duracion: 4200
  },
  {
    id: 11,
    fechaHora: new Date('2024-08-22T11:30:45'),
    texto: 'Búsqueda de casos similares para expediente 2024-000010-1239-LA',
    informacionAdicional: '15 casos similares encontrados. Threshold: 0.82',
    expediente: '2024-000010-1239-LA',
    tipoAccion: 'Búsqueda similares',
    usuario: 'Carlos Rodríguez',
    correoUsuario: 'carlos.rodriguez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.45',
    navegador: 'Firefox',
    duracion: 4200
  }
];

// Función para obtener estadísticas
export const obtenerEstadisticas = () => {
  const hoy = new Date();
  const hace7Dias = subDays(hoy, 7);
  const hace30Dias = subDays(hoy, 30);

  const registrosHoy = registrosBitacora.filter(r => 
    format(r.fechaHora, 'yyyy-MM-dd') === format(hoy, 'yyyy-MM-dd')
  ).length;

  const registros7Dias = registrosBitacora.filter(r => r.fechaHora >= hace7Dias).length;
  const registros30Dias = registrosBitacora.filter(r => r.fechaHora >= hace30Dias).length;

  // Conteo por tipo de acción
  const accionesPorTipo = tiposAccion.map(tipo => ({
    tipo: tipo.nombre,
    cantidad: registrosBitacora.filter(r => r.tipoAccion === tipo.nombre).length
  }));

  // Usuarios más activos
  const usuariosActivos = usuarios.map(usuario => ({
    nombre: usuario.nombre,
    cantidad: registrosBitacora.filter(r => r.usuario === usuario.nombre).length
  })).sort((a, b) => b.cantidad - a.cantidad);

  // Expedientes más consultados
  const expedientesActivos = expedientes.map(exp => ({
    expediente: exp,
    cantidad: registrosBitacora.filter(r => r.expediente === exp).length
  })).sort((a, b) => b.cantidad - a.cantidad);

  // Distribución por horas
  const distribucionHoras = Array.from({ length: 24 }, (_, hora) => ({
    hora,
    cantidad: registrosBitacora.filter(r => r.fechaHora.getHours() === hora).length
  }));

  // Actividad por días de la semana
  const diasSemana = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
  const actividadSemanal = diasSemana.map((dia, index) => ({
    dia,
    cantidad: registrosBitacora.filter(r => r.fechaHora.getDay() === index).length
  }));

  // Errores recientes
  const erroresRecientes = registrosBitacora
    .filter(r => r.estado === 'Error')
    .slice(0, 10);

  return {
    registrosHoy,
    registros7Dias,
    registros30Dias,
    totalRegistros: registrosBitacora.length,
    usuariosUnicos: new Set(registrosBitacora.map(r => r.usuario)).size,
    expedientesUnicos: new Set(registrosBitacora.map(r => r.expediente)).size,
    accionesPorTipo,
    usuariosActivos: usuariosActivos.slice(0, 10),
    expedientesActivos: expedientesActivos.slice(0, 10),
    distribucionHoras,
    actividadSemanal,
    erroresRecientes
  };
};

// Función para filtrar registros
export const filtrarRegistros = (filtros) => {
  return registrosBitacora.filter(registro => {
    if (filtros.usuario && !registro.usuario.toLowerCase().includes(filtros.usuario.toLowerCase())) {
      return false;
    }
    if (filtros.tipoAccion && registro.tipoAccion !== filtros.tipoAccion) {
      return false;
    }
    if (filtros.expediente && !registro.expediente.includes(filtros.expediente)) {
      return false;
    }
    if (filtros.fechaInicio && registro.fechaHora < new Date(filtros.fechaInicio)) {
      return false;
    }
    if (filtros.fechaFin && registro.fechaHora > new Date(filtros.fechaFin + 'T23:59:59')) {
      return false;
    }
    if (filtros.estado && registro.estado !== filtros.estado) {
      return false;
    }
    return true;
  });
};
