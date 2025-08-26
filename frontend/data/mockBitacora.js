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

// Registros de bitácora con fechas distribuidas en los últimos 14 días
export const registrosBitacora = [
  // Registros del 25 de agosto (hoy)
  {
    id: 1,
    fechaHora: new Date('2025-08-25T09:15:30'),
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
    fechaHora: new Date('2025-08-25T10:30:45'),
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
    fechaHora: new Date('2025-08-25T11:20:15'),
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
    fechaHora: new Date('2025-08-25T14:45:22'),
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
    fechaHora: new Date('2025-08-25T16:20:10'),
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

  // Registros del 24 de agosto
  {
    id: 6,
    fechaHora: new Date('2025-08-24T08:30:45'),
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
    fechaHora: new Date('2025-08-24T10:15:20'),
    texto: 'Consulta de expediente 2024-000007-1234-PE',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 1150ms',
    expediente: '2024-000007-1234-PE',
    tipoAccion: 'Consulta',
    usuario: 'Patricia Ruiz',
    correoUsuario: 'patricia.ruiz@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.189',
    navegador: 'Firefox',
    duracion: 1150
  },
  {
    id: 8,
    fechaHora: new Date('2025-08-24T13:45:30'),
    texto: 'Carga de documento en expediente 2024-000008-1238-CI',
    informacionAdicional: 'Archivo: documento_890.pdf. Tamaño: 22MB',
    expediente: '2024-000008-1238-CI',
    tipoAccion: 'Carga',
    usuario: 'Roberto Jiménez',
    correoUsuario: 'roberto.jimenez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.201',
    navegador: 'Edge',
    duracion: 5200
  },
  {
    id: 9,
    fechaHora: new Date('2025-08-24T15:20:45'),
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

  // Registros del 23 de agosto
  {
    id: 10,
    fechaHora: new Date('2025-08-23T09:30:45'),
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
    fechaHora: new Date('2025-08-23T11:15:20'),
    texto: 'Consulta de expediente 2024-000011-1240-CI',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 1320ms',
    expediente: '2024-000011-1240-CI',
    tipoAccion: 'Consulta',
    usuario: 'Ana Martínez',
    correoUsuario: 'ana.martinez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.78',
    navegador: 'Edge',
    duracion: 1320
  },
  {
    id: 12,
    fechaHora: new Date('2025-08-23T14:40:10'),
    texto: 'Carga de documento en expediente 2024-000012-1241-PE',
    informacionAdicional: 'Archivo: documento_455.pdf. Tamaño: 12MB',
    expediente: '2024-000012-1241-PE',
    tipoAccion: 'Carga',
    usuario: 'Luis Fernández',
    correoUsuario: 'luis.fernandez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.92',
    navegador: 'Chrome',
    duracion: 2800
  },

  // Registros del 22 de agosto
  {
    id: 13,
    fechaHora: new Date('2025-08-22T08:45:15'),
    texto: 'Consulta de expediente 2024-000013-1242-FA',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 980ms',
    expediente: '2024-000013-1242-FA',
    tipoAccion: 'Consulta',
    usuario: 'Carmen Silva',
    correoUsuario: 'carmen.silva@justicia.gov',
    rolUsuario: 'Administrador',
    estado: 'Procesado',
    ip: '192.168.1.123',
    navegador: 'Safari',
    duracion: 980
  },
  {
    id: 14,
    fechaHora: new Date('2025-08-22T10:20:30'),
    texto: 'Búsqueda de casos similares para expediente 2024-000014-1243-LA',
    informacionAdicional: '9 casos similares encontrados. Threshold: 0.76',
    expediente: '2024-000014-1243-LA',
    tipoAccion: 'Búsqueda similares',
    usuario: 'Diego Morales',
    correoUsuario: 'diego.morales@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.156',
    navegador: 'Chrome',
    duracion: 3600
  },
  {
    id: 15,
    fechaHora: new Date('2025-08-22T12:35:45'),
    texto: 'Carga de documento en expediente 2024-000015-1244-CI',
    informacionAdicional: 'Archivo: documento_678.pdf. Tamaño: 18MB',
    expediente: '2024-000015-1244-CI',
    tipoAccion: 'Carga',
    usuario: 'Patricia Ruiz',
    correoUsuario: 'patricia.ruiz@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.189',
    navegador: 'Firefox',
    duracion: 4100
  },
  {
    id: 16,
    fechaHora: new Date('2025-08-22T15:10:20'),
    texto: 'Consulta de expediente 2024-000016-1245-PE',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 1100ms',
    expediente: '2024-000016-1245-PE',
    tipoAccion: 'Consulta',
    usuario: 'Roberto Jiménez',
    correoUsuario: 'roberto.jimenez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.201',
    navegador: 'Edge',
    duracion: 1100
  },

  // Registros del 21 de agosto
  {
    id: 17,
    fechaHora: new Date('2025-08-21T09:25:10'),
    texto: 'Búsqueda de casos similares para expediente 2024-000017-1246-FA',
    informacionAdicional: '11 casos similares encontrados. Threshold: 0.80',
    expediente: '2024-000017-1246-FA',
    tipoAccion: 'Búsqueda similares',
    usuario: 'María González',
    correoUsuario: 'maria.gonzalez@justicia.gov',
    rolUsuario: 'Administrador',
    estado: 'Procesado',
    ip: '192.168.1.15',
    navegador: 'Chrome',
    duracion: 3900
  },
  {
    id: 18,
    fechaHora: new Date('2025-08-21T11:40:35'),
    texto: 'Consulta de expediente 2024-000018-1247-LA',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 1250ms',
    expediente: '2024-000018-1247-LA',
    tipoAccion: 'Consulta',
    usuario: 'Carlos Rodríguez',
    correoUsuario: 'carlos.rodriguez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.45',
    navegador: 'Firefox',
    duracion: 1250
  },
  {
    id: 19,
    fechaHora: new Date('2025-08-21T14:15:50'),
    texto: 'Carga de documento en expediente 2024-000019-1248-CI',
    informacionAdicional: 'Archivo: documento_789.pdf. Tamaño: 14MB',
    expediente: '2024-000019-1248-CI',
    tipoAccion: 'Carga',
    usuario: 'Ana Martínez',
    correoUsuario: 'ana.martinez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.78',
    navegador: 'Edge',
    duracion: 3200
  },

  // Registros del 20 de agosto
  {
    id: 20,
    fechaHora: new Date('2025-08-20T08:50:25'),
    texto: 'Consulta de expediente 2024-000020-1249-PE',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 890ms',
    expediente: '2024-000020-1249-PE',
    tipoAccion: 'Consulta',
    usuario: 'Luis Fernández',
    correoUsuario: 'luis.fernandez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.92',
    navegador: 'Chrome',
    duracion: 890
  },
  {
    id: 21,
    fechaHora: new Date('2025-08-20T10:30:40'),
    texto: 'Búsqueda de casos similares para expediente 2024-000021-1250-FA',
    informacionAdicional: '7 casos similares encontrados. Threshold: 0.75',
    expediente: '2024-000021-1250-FA',
    tipoAccion: 'Búsqueda similares',
    usuario: 'Carmen Silva',
    correoUsuario: 'carmen.silva@justicia.gov',
    rolUsuario: 'Administrador',
    estado: 'Procesado',
    ip: '192.168.1.123',
    navegador: 'Safari',
    duracion: 3400
  },
  {
    id: 22,
    fechaHora: new Date('2025-08-20T13:20:15'),
    texto: 'Carga de documento en expediente 2024-000022-1251-LA',
    informacionAdicional: 'Archivo: documento_901.pdf. Tamaño: 9MB',
    expediente: '2024-000022-1251-LA',
    tipoAccion: 'Carga',
    usuario: 'Diego Morales',
    correoUsuario: 'diego.morales@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.156',
    navegador: 'Chrome',
    duracion: 2400
  },
  {
    id: 23,
    fechaHora: new Date('2025-08-20T15:45:30'),
    texto: 'Consulta de expediente 2024-000023-1252-CI',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 1180ms',
    expediente: '2024-000023-1252-CI',
    tipoAccion: 'Consulta',
    usuario: 'Patricia Ruiz',
    correoUsuario: 'patricia.ruiz@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.189',
    navegador: 'Firefox',
    duracion: 1180
  },

  // Registros del 19 de agosto
  {
    id: 24,
    fechaHora: new Date('2025-08-19T09:10:45'),
    texto: 'Búsqueda de casos similares para expediente 2024-000024-1253-PE',
    informacionAdicional: '13 casos similares encontrados. Threshold: 0.83',
    expediente: '2024-000024-1253-PE',
    tipoAccion: 'Búsqueda similares',
    usuario: 'Roberto Jiménez',
    correoUsuario: 'roberto.jimenez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.201',
    navegador: 'Edge',
    duracion: 4300
  },
  {
    id: 25,
    fechaHora: new Date('2025-08-19T11:35:20'),
    texto: 'Consulta de expediente 2024-000025-1254-FA',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 1050ms',
    expediente: '2024-000025-1254-FA',
    tipoAccion: 'Consulta',
    usuario: 'María González',
    correoUsuario: 'maria.gonzalez@justicia.gov',
    rolUsuario: 'Administrador',
    estado: 'Procesado',
    ip: '192.168.1.15',
    navegador: 'Chrome',
    duracion: 1050
  },
  {
    id: 26,
    fechaHora: new Date('2025-08-19T14:20:35'),
    texto: 'Carga de documento en expediente 2024-000026-1255-LA',
    informacionAdicional: 'Archivo: documento_112.pdf. Tamaño: 16MB',
    expediente: '2024-000026-1255-LA',
    tipoAccion: 'Carga',
    usuario: 'Carlos Rodríguez',
    correoUsuario: 'carlos.rodriguez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.45',
    navegador: 'Firefox',
    duracion: 3700
  },

  // Registros del 18 de agosto
  {
    id: 27,
    fechaHora: new Date('2025-08-18T08:40:15'),
    texto: 'Consulta de expediente 2024-000027-1256-CI',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 920ms',
    expediente: '2024-000027-1256-CI',
    tipoAccion: 'Consulta',
    usuario: 'Ana Martínez',
    correoUsuario: 'ana.martinez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.78',
    navegador: 'Edge',
    duracion: 920
  },
  {
    id: 28,
    fechaHora: new Date('2025-08-18T12:25:50'),
    texto: 'Búsqueda de casos similares para expediente 2024-000028-1257-PE',
    informacionAdicional: '6 casos similares encontrados. Threshold: 0.72',
    expediente: '2024-000028-1257-PE',
    tipoAccion: 'Búsqueda similares',
    usuario: 'Luis Fernández',
    correoUsuario: 'luis.fernandez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.92',
    navegador: 'Chrome',
    duracion: 3100
  },

  // Registros del 17 de agosto  
  {
    id: 29,
    fechaHora: new Date('2025-08-17T10:15:30'),
    texto: 'Carga de documento en expediente 2024-000029-1258-FA',
    informacionAdicional: 'Archivo: documento_223.pdf. Tamaño: 11MB',
    expediente: '2024-000029-1258-FA',
    tipoAccion: 'Carga',
    usuario: 'Carmen Silva',
    correoUsuario: 'carmen.silva@justicia.gov',
    rolUsuario: 'Administrador',
    estado: 'Procesado',
    ip: '192.168.1.123',
    navegador: 'Safari',
    duracion: 2700
  },
  {
    id: 30,
    fechaHora: new Date('2025-08-17T13:50:45'),
    texto: 'Consulta de expediente 2024-000030-1259-LA',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 1380ms',
    expediente: '2024-000030-1259-LA',
    tipoAccion: 'Consulta',
    usuario: 'Diego Morales',
    correoUsuario: 'diego.morales@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.156',
    navegador: 'Chrome',
    duracion: 1380
  },

  // Registros del 16 de agosto
  {
    id: 31,
    fechaHora: new Date('2025-08-16T09:30:20'),
    texto: 'Búsqueda de casos similares para expediente 2024-000031-1260-CI',
    informacionAdicional: '10 casos similares encontrados. Threshold: 0.79',
    expediente: '2024-000031-1260-CI',
    tipoAccion: 'Búsqueda similares',
    usuario: 'Patricia Ruiz',
    correoUsuario: 'patricia.ruiz@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.189',
    navegador: 'Firefox',
    duracion: 3800
  },
  {
    id: 32,
    fechaHora: new Date('2025-08-16T11:45:15'),
    texto: 'Consulta de expediente 2024-000032-1261-PE',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 1150ms',
    expediente: '2024-000032-1261-PE',
    tipoAccion: 'Consulta',
    usuario: 'Roberto Jiménez',
    correoUsuario: 'roberto.jimenez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.201',
    navegador: 'Edge',
    duracion: 1150
  },
  {
    id: 33,
    fechaHora: new Date('2025-08-16T14:20:40'),
    texto: 'Carga de documento en expediente 2024-000033-1262-FA',
    informacionAdicional: 'Archivo: documento_334.pdf. Tamaño: 13MB',
    expediente: '2024-000033-1262-FA',
    tipoAccion: 'Carga',
    usuario: 'María González',
    correoUsuario: 'maria.gonzalez@justicia.gov',
    rolUsuario: 'Administrador',
    estado: 'Procesado',
    ip: '192.168.1.15',
    navegador: 'Chrome',
    duracion: 3000
  },

  // Registros del 15 de agosto
  {
    id: 34,
    fechaHora: new Date('2025-08-15T08:55:25'),
    texto: 'Consulta de expediente 2024-000034-1263-LA',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 870ms',
    expediente: '2024-000034-1263-LA',
    tipoAccion: 'Consulta',
    usuario: 'Carlos Rodríguez',
    correoUsuario: 'carlos.rodriguez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.45',
    navegador: 'Firefox',
    duracion: 870
  },
  {
    id: 35,
    fechaHora: new Date('2025-08-15T12:10:50'),
    texto: 'Búsqueda de casos similares para expediente 2024-000035-1264-CI',
    informacionAdicional: '8 casos similares encontrados. Threshold: 0.77',
    expediente: '2024-000035-1264-CI',
    tipoAccion: 'Búsqueda similares',
    usuario: 'Ana Martínez',
    correoUsuario: 'ana.martinez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.78',
    navegador: 'Edge',
    duracion: 3500
  },

  // Registros del 14 de agosto
  {
    id: 36,
    fechaHora: new Date('2025-08-14T10:25:35'),
    texto: 'Carga de documento en expediente 2024-000036-1265-PE',
    informacionAdicional: 'Archivo: documento_445.pdf. Tamaño: 17MB',
    expediente: '2024-000036-1265-PE',
    tipoAccion: 'Carga',
    usuario: 'Luis Fernández',
    correoUsuario: 'luis.fernandez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.92',
    navegador: 'Chrome',
    duracion: 3900
  },

  // Registros del 13 de agosto
  {
    id: 37,
    fechaHora: new Date('2025-08-13T09:40:20'),
    texto: 'Consulta de expediente 2024-000037-1266-FA',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 1200ms',
    expediente: '2024-000037-1266-FA',
    tipoAccion: 'Consulta',
    usuario: 'Carmen Silva',
    correoUsuario: 'carmen.silva@justicia.gov',
    rolUsuario: 'Administrador',
    estado: 'Procesado',
    ip: '192.168.1.123',
    navegador: 'Safari',
    duracion: 1200
  },
  {
    id: 38,
    fechaHora: new Date('2025-08-13T15:15:45'),
    texto: 'Búsqueda de casos similares para expediente 2024-000038-1267-LA',
    informacionAdicional: '14 casos similares encontrados. Threshold: 0.84',
    expediente: '2024-000038-1267-LA',
    tipoAccion: 'Búsqueda similares',
    usuario: 'Diego Morales',
    correoUsuario: 'diego.morales@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.156',
    navegador: 'Chrome',
    duracion: 4200
  },

  // Registros del 12 de agosto
  {
    id: 39,
    fechaHora: new Date('2025-08-12T11:30:15'),
    texto: 'Consulta de expediente 2024-000039-1268-CI',
    informacionAdicional: 'Búsqueda realizada en documentos relacionados. Tiempo de respuesta: 960ms',
    expediente: '2024-000039-1268-CI',
    tipoAccion: 'Consulta',
    usuario: 'Patricia Ruiz',
    correoUsuario: 'patricia.ruiz@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.189',
    navegador: 'Firefox',
    duracion: 960
  },
  {
    id: 40,
    fechaHora: new Date('2025-08-12T14:45:30'),
    texto: 'Carga de documento en expediente 2024-000040-1269-PE',
    informacionAdicional: 'Archivo: documento_556.pdf. Tamaño: 10MB',
    expediente: '2024-000040-1269-PE',
    tipoAccion: 'Carga',
    usuario: 'Roberto Jiménez',
    correoUsuario: 'roberto.jimenez@justicia.gov',
    rolUsuario: 'Usuario Judicial',
    estado: 'Procesado',
    ip: '192.168.1.201',
    navegador: 'Edge',
    duracion: 2600
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

  // Usuarios más activos (solo para el gráfico de pastel)
  const usuariosActivos = usuarios.map(usuario => ({
    nombre: usuario.nombre,
    cantidad: registrosBitacora.filter(r => r.usuario === usuario.nombre).length
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

  return {
    registrosHoy,
    registros7Dias,
    registros30Dias,
    totalRegistros: registrosBitacora.length,
    usuariosUnicos: new Set(registrosBitacora.map(r => r.usuario)).size,
    expedientesUnicos: new Set(registrosBitacora.map(r => r.expediente)).size,
    accionesPorTipo,
    usuariosActivos: usuariosActivos.slice(0, 10),
    distribucionHoras,
    actividadSemanal
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
