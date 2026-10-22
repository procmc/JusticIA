// Contraseñas de prueba (spec 005a, RA-02.43).
// Se derivan de una semilla que vive solo en la memoria del orquestador y llega a los trabajadores por una variable de
// entorno del proceso: ninguna contraseña se escribe en un archivo ni en la salida. El orquestador recalcula todas las
// posibles para buscarlas en los artefactos al final de la corrida.
const crypto = require('node:crypto');

// Largo del núcleo derivado: es lo que el orquestador busca en los artefactos.
const LARGO_NUCLEO = 24;
// Sufijo fijo que cumple la política de contraseñas (mayúscula, minúscula, dígito, símbolo, ≥ 8 caracteres).
const SUFIJO = '-Ab9';
// Rango de trabajadores y de contraseñas por trabajador que el orquestador recalcula.
const MAX_TRABAJADORES = 200;
const MAX_POR_TRABAJADOR = 200;

function nucleo(semilla, trabajador, n) {
  return crypto.createHmac('sha256', semilla).update(`${trabajador}:${n}`).digest('base64url').slice(0, LARGO_NUCLEO);
}

function generar(semilla, trabajador, n) {
  return nucleo(semilla, trabajador, n) + SUFIJO;
}

// Todos los núcleos posibles de la corrida.
function nucleosPosibles(semilla) {
  const todos = new Set();
  for (let trabajador = 0; trabajador < MAX_TRABAJADORES; trabajador += 1) {
    for (let n = 0; n < MAX_POR_TRABAJADOR; n += 1) todos.add(nucleo(semilla, trabajador, n));
  }
  return todos;
}

// La semilla de la corrida (hexadecimal en E2E_SEMILLA) como Buffer.
function semillaDelEntorno() {
  const hexadecimal = process.env.E2E_SEMILLA;
  if (!hexadecimal) throw new Error('Falta E2E_SEMILLA: las pruebas se ejecutan con `npm run e2e`.');
  return Buffer.from(hexadecimal, 'hex');
}

// Generador de un trabajador: cada llamada entrega una contraseña nueva e irrepetible.
function crearGenerador(semilla = semillaDelEntorno(), trabajador = Number(process.env.TEST_PARALLEL_INDEX || 0)) {
  let n = 0;
  return { siguiente: () => generar(semilla, trabajador, n++) };
}

module.exports = {
  LARGO_NUCLEO, SUFIJO, MAX_TRABAJADORES, MAX_POR_TRABAJADOR, nucleo, generar, nucleosPosibles, semillaDelEntorno, crearGenerador,
};
