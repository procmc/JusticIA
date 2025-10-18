import { format } from 'date-fns';
import { es } from 'date-fns/locale';

/**
 * Offset de Costa Rica (UTC-6)
 * Costa Rica no tiene horario de verano, siempre es UTC-6
 */
const COSTA_RICA_OFFSET_HOURS = -6;

/**
 * Convierte una fecha UTC a la zona horaria de Costa Rica
 */
const convertirACostaRica = (fecha) => {
  if (!fecha) return null;
  
  try {
    // Convertir a Date si es string
    const fechaUTC = typeof fecha === 'string' ? new Date(fecha) : fecha;
    
    // Crear una nueva fecha ajustada al offset de Costa Rica
    // Como la fecha viene en UTC, le restamos 6 horas para obtener hora de Costa Rica
    const fechaCostaRica = new Date(fechaUTC.getTime() + (COSTA_RICA_OFFSET_HOURS * 60 * 60 * 1000));
    
    return fechaCostaRica;
  } catch (error) {
    console.error('Error convirtiendo fecha a Costa Rica:', error);
    return null;
  }
};

/**
 * Convierte una fecha UTC a la zona horaria de Costa Rica y la formatea
 */
export const formatearFechaCostaRica = (fecha, formatoSalida = 'dd/MM/yyyy hh:mm:ss a') => {
  if (!fecha) return '-';
  
  try {
    const fechaCostaRica = convertirACostaRica(fecha);
    if (!fechaCostaRica) return '-';
    
    // Formatear con date-fns
    return format(fechaCostaRica, formatoSalida, { locale: es });
  } catch (error) {
    console.error('Error formateando fecha:', error);
    return '-';
  }
};

/**
 * Formatea solo la fecha (sin hora) en zona horaria de Costa Rica
 */
export const formatearSoloFechaCostaRica = (fecha) => {
  return formatearFechaCostaRica(fecha, 'dd/MM/yyyy');
};

/**
 * Formatea solo la hora en zona horaria de Costa Rica (formato 12 horas)
 */
export const formatearSoloHoraCostaRica = (fecha) => {
  return formatearFechaCostaRica(fecha, 'hh:mm:ss a');
};

/**
 * Formatea fecha y hora en formato corto
 */
export const formatearFechaHoraCorta = (fecha) => {
  return formatearFechaCostaRica(fecha, 'dd/MM/yyyy hh:mm a');
};

/**
 * Formatea fecha y hora en formato completo legible
 */
export const formatearFechaHoraCompleta = (fecha) => {
  return formatearFechaCostaRica(fecha, "d 'de' MMMM 'de' yyyy, hh:mm a");
};
