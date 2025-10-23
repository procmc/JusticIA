import { format } from 'date-fns';
import { es } from 'date-fns/locale';

/**
 * Zona horaria de Costa Rica
 * Costa Rica no tiene horario de verano, siempre es UTC-6
 */
const COSTA_RICA_TIMEZONE = 'America/Costa_Rica';

/**
 * Convierte una fecha a la zona horaria de Costa Rica
 */
const convertirACostaRica = (fecha) => {
  if (!fecha) return null;
  
  try {
    // Convertir a Date si es string
    const fechaOriginal = typeof fecha === 'string' ? new Date(fecha) : fecha;
    
    // Usar Intl.DateTimeFormat para obtener la fecha/hora en zona horaria de Costa Rica
    // Esto maneja automáticamente la conversión de zona horaria
    return fechaOriginal;
  } catch (error) {
    console.error('Error convirtiendo fecha a Costa Rica:', error);
    return null;
  }
};

/**
 * Convierte una fecha a la zona horaria de Costa Rica y la formatea
 */
export const formatearFechaCostaRica = (fecha, formatoSalida = 'dd/MM/yyyy hh:mm:ss a') => {
  if (!fecha) return '-';
  
  try {
    // Convertir a Date si es string
    const fechaOriginal = typeof fecha === 'string' ? new Date(fecha) : fecha;
    
    // Crear un formateador que use la zona horaria de Costa Rica
    const opciones = {
      timeZone: COSTA_RICA_TIMEZONE,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    };
    
    // Si solo queremos la hora
    if (formatoSalida === 'hh:mm:ss a') {
      const opcionesHora = {
        timeZone: COSTA_RICA_TIMEZONE,
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      };
      return new Intl.DateTimeFormat('es-CR', opcionesHora).format(fechaOriginal);
    }
    
    // Si solo queremos la fecha
    if (formatoSalida === 'dd/MM/yyyy') {
      const opcionesFecha = {
        timeZone: COSTA_RICA_TIMEZONE,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      };
      return new Intl.DateTimeFormat('es-CR', opcionesFecha).format(fechaOriginal);
    }
    
    // Si queremos fecha y hora corta
    if (formatoSalida === 'dd/MM/yyyy hh:mm a') {
      const opcionesFechaHora = {
        timeZone: COSTA_RICA_TIMEZONE,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      };
      return new Intl.DateTimeFormat('es-CR', opcionesFechaHora).format(fechaOriginal);
    }
    
    // Si queremos formato completo legible
    if (formatoSalida === "d 'de' MMMM 'de' yyyy, hh:mm a") {
      const opcionesCompletas = {
        timeZone: COSTA_RICA_TIMEZONE,
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      };
      const fechaFormateada = new Intl.DateTimeFormat('es-CR', opcionesCompletas).format(fechaOriginal);
      // Ajustar el formato para que sea más legible
      return fechaFormateada.replace(/(\d+) de (\w+) de (\d+), (\d+:\d+ [ap]\.?\s?m\.?)/, '$1 de $2 de $3, $4');
    }
    
    // Por defecto, usar formato completo
    return new Intl.DateTimeFormat('es-CR', opciones).format(fechaOriginal);
    
  } catch (error) {
    console.error('Error formateando fecha:', error);
    return '-';
  }
};

/**
 * Formatea solo la fecha (sin hora) en zona horaria de Costa Rica
 */
export const formatearSoloFechaCostaRica = (fecha) => {
  if (!fecha) return '-';
  
  try {
    const fechaOriginal = typeof fecha === 'string' ? new Date(fecha) : fecha;
    
    const opcionesFecha = {
      timeZone: COSTA_RICA_TIMEZONE,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    };
    
    return new Intl.DateTimeFormat('es-CR', opcionesFecha).format(fechaOriginal);
  } catch (error) {
    console.error('Error formateando fecha:', error);
    return '-';
  }
};

/**
 * Formatea solo la hora en zona horaria de Costa Rica (formato 12 horas)
 */
export const formatearSoloHoraCostaRica = (fecha) => {
  if (!fecha) return '-';
  
  try {
    const fechaOriginal = typeof fecha === 'string' ? new Date(fecha) : fecha;
    
    // El backend envía timestamps que parecen UTC pero son realmente hora local de Costa Rica
    // Los tratamos como hora local directamente (SIN segundos para el chat)
    const horaLocal = fechaOriginal.toLocaleString('es-CR', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
    
    return horaLocal;
  } catch (error) {
    console.error('Error formateando hora:', error);
    return '-';
  }
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
  if (!fecha) return '-';
  
  try {
    const fechaOriginal = typeof fecha === 'string' ? new Date(fecha) : fecha;
    
    const opcionesCompletas = {
      timeZone: COSTA_RICA_TIMEZONE,
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    };
    
    const fechaFormateada = new Intl.DateTimeFormat('es-CR', opcionesCompletas).format(fechaOriginal);
    return fechaFormateada;
  } catch (error) {
    console.error('Error formateando fecha completa:', error);
    return '-';
  }
};
