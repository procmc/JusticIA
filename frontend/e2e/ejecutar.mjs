// Orquestador de la red de seguridad de extremo a extremo (spec 005a, RA-02.40, RA-02.41, RA-02.43 y RA-02.47).
//
//   npm run e2e [-- <argumentos de Playwright>]   prepara, corre Playwright, apaga todo y resume
//   npm run e2e:apagar                            apaga una instancia o un frontend de pruebas que quedaron vivos
//
// Prepara la instancia del backend (puerto 8100, base y colección `servia_pruebas_e2e`) y el frontend de pruebas
// (`next start` en 127.0.0.1:3100, compilado en `.next-e2e`, sin tocar `.next`), corre Playwright con el Chrome
// instalado y, pase lo que pase, apaga ambos. Al final busca contraseñas en los artefactos. Las funciones puras se
// exportan para probarlas (e2e/infraestructura/orquestador.spec.js); el flujo solo corre al ejecutar este archivo.
import { spawn } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
const { nucleosPosibles, LARGO_NUCLEO, SUFIJO } =require('./soporte/contrasenas.js');

const CARPETA_FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const RAIZ_PROYECTO = path.resolve(CARPETA_FRONTEND, '..');
const CARPETA_DIST = '.next-e2e';
const CARPETA_RESULTADOS = path.join(CARPETA_FRONTEND, 'test-results');
const INFORME_JSON = path.join(CARPETA_RESULTADOS, 'informe.json');
const ARCHIVO_HUELLA = path.join(CARPETA_FRONTEND, CARPETA_DIST, 'huella-servia');
const ARCHIVO_PID_WEB = path.join(CARPETA_FRONTEND, CARPETA_DIST, 'servidor.pid');

const HOST = '127.0.0.1';
const PUERTO_WEB = 3100;
const PUERTO_API = 8100;
const URL_WEB = `http://${HOST}:${PUERTO_WEB}`;
const URL_API = `http://${HOST}:${PUERTO_API}`;
const URL_DESARROLLO = process.env.E2E_URL_DESARROLLO || 'http://localhost:8000';
const NOMBRE_E2E = 'servia_pruebas_e2e';
const LIMITE_PREPARACION_MS = 5 * 60_000;

// --- Funciones puras (se prueban en orquestador.spec.js) -------------------------------------------------------

// Resuelve si nadie escucha en host:puerto; si algo responde, falla nombrando el puerto y cómo liberarlo.
export function comprobarPuertoLibre(host, puerto, quien) {
  return new Promise((resolver, rechazar) => {
    const conexion = net.connect({ host, port: puerto });
    conexion.setTimeout(2000);
    conexion.once('connect', () => {
      conexion.destroy();
      rechazar(new Error(
        `El puerto ${puerto} de ${host} ya está en uso (${quien}). Si es una corrida anterior, libérelo con \`npm run e2e:apagar\`.`,
      ));
    });
    conexion.once('timeout', () => { conexion.destroy(); resolver(); });
    conexion.once('error', () => resolver());
  });
}

// Recorre el informe JSON de Playwright y cuenta cada prueba. Un fallo esperado (`test.fail`) que pasa es un XPASS.
export function analizarInforme(informe) {
  const cuentas = { recolectadas: 0, pasan: 0, fallan: 0, esperados: 0, omitidas: 0, xpass: [], fallidas: [] };
  const recorrer = (suite, ruta) => {
    const titulos = suite.title ? [...ruta, suite.title] : ruta;
    for (const especificacion of suite.specs || []) {
      for (const prueba of especificacion.tests || []) {
        cuentas.recolectadas += 1;
        const nombre = [...titulos, especificacion.title].join(' › ');
        const ultimo = (prueba.results || []).at(-1);
        if (prueba.status === 'skipped') cuentas.omitidas += 1;
        else if (prueba.expectedStatus === 'failed') {
          if (ultimo && ultimo.status === 'passed') cuentas.xpass.push(nombre);
          else cuentas.esperados += 1;
        } else if (prueba.status === 'expected') cuentas.pasan += 1;
        else {
          cuentas.fallan += 1;
          cuentas.fallidas.push(nombre);
        }
      }
    }
    for (const hija of suite.suites || []) recorrer(hija, titulos);
  };
  for (const suite of (informe && informe.suites) || []) recorrer(suite, []);
  return cuentas;
}

// Borra los resultados de la corrida anterior al empezar: si la preparación aborta antes de Playwright, no debe quedar un
// informe viejo que el resumen confunda con el de esta corrida.
export function prepararResultados(carpeta) {
  fs.rmSync(carpeta, { recursive: true, force: true });
}

// Lee el informe de esta corrida. `sinInforme` distingue «Playwright no escribió informe» de «informe con 0 pruebas».
export function resumirInforme(ruta) {
  let informe = null;
  try {
    informe = JSON.parse(fs.readFileSync(ruta, 'utf8'));
  } catch { /* sin informe */ }
  return { ...analizarInforme(informe), sinInforme: informe === null };
}

// Código de salida y motivos. Solo es 0 con pruebas recolectadas, ninguna fallida ni XPASS, residuos y contraseñas en 0
// y el backend de desarrollo respondiendo antes y después.
export function veredicto(datos) {
  const motivos = [];
  if (datos.sinInforme) motivos.push('no hubo informe de esta corrida');
  if (!datos.recolectadas) motivos.push('no se recolectó ninguna prueba');
  if (datos.fallan) motivos.push(`${datos.fallan} prueba(s) fallan`);
  if (datos.xpass && datos.xpass.length) motivos.push(`${datos.xpass.length} fallo(s) esperado(s) pasan (XPASS): quitar su marca`);
  if (datos.residuos) motivos.push(`quedaron ${datos.residuos} residuo(s) de datos de prueba`);
  if (datos.residuosAlEmpezar) motivos.push(`la instancia empezó con ${datos.residuosAlEmpezar} residuo(s) de datos de prueba`);
  if (datos.contrasenas) motivos.push(`${datos.contrasenas} contraseña(s) en los artefactos`);
  if (datos.coincidenciasRegistro) motivos.push(`${datos.coincidenciasRegistro} contraseña(s) en el registro de la instancia`);
  if (datos.desarrolloAntes !== 200) motivos.push('el backend de desarrollo no respondía antes de la corrida');
  if (datos.desarrolloDespues !== 200) motivos.push('el backend de desarrollo no respondía después de la corrida');
  if (!motivos.length && datos.codigoPlaywright) motivos.push(`Playwright terminó con el código ${datos.codigoPlaywright}`);
  return { codigo: motivos.length ? 1 : 0, motivos };
}

// Lo que hay en el entorno aislado según el control (T3); null si no se pudo leer.
async function leerResiduos(token) {
  try {
    const respuesta = await fetch(`${URL_API}/pruebas-e2e/residuos`, {
      headers: { 'X-Control-Pruebas': token }, signal: AbortSignal.timeout(30_000),
    });
    return respuesta.ok ? await respuesta.json() : null;
  } catch {
    return null;
  }
}

const segundos = (ms) => `${(ms / 1000).toFixed(1)} s`;

export function textoResumen(d) {
  const cifras = d.sinInforme
    ? ['Sin informe de esta corrida: Playwright no llegó a escribirlo, por eso no hay cifras de pruebas.']
    : [
      `Recolectadas: ${d.recolectadas}`,
      `Pasan: ${d.pasan}`,
      `Fallan: ${d.fallan}`,
      `Fallos esperados: ${d.esperados}`,
      `XPASS (fallos esperados que pasan): ${d.xpass.length}`,
      ...d.xpass.map((nombre) => `  - ${nombre}`),
      ...(d.fallidas || []).map((nombre) => `  x ${nombre}`),
      `Omitidas: ${d.omitidas ?? 0}`,
    ];
  const lineas = [
    '',
    '=== Resumen de extremo a extremo ===',
    ...cifras,
    `Preparación: ${segundos(d.preparacionMs)} (límite ${segundos(LIMITE_PREPARACION_MS)})`,
    `Suite: ${segundos(d.suiteMs)} (límite 600.0 s)`,
    `Residuos de datos de prueba: ${d.residuos ?? 'no se pudo leer'}${d.textoResiduos && d.residuos ? ` (${d.textoResiduos})` : ''} (al empezar: ${d.residuosAlEmpezar ?? 'n/d'})`,
    `Contraseñas en artefactos: ${d.contrasenas} (en el registro de la instancia: ${d.coincidenciasRegistro ?? 'n/d'})`,
    `Backend de desarrollo: antes ${d.desarrolloAntes}, después ${d.desarrolloDespues}`,
    `Resultado: ${d.codigo === 0 ? 'CORRECTO' : `FALLA: ${d.motivos.join('; ')}`}`,
  ];
  return lineas.join('\n');
}

function archivosDe(carpeta) {
  const archivos = [];
  if (!fs.existsSync(carpeta)) return archivos;
  for (const entrada of fs.readdirSync(carpeta, { withFileTypes: true })) {
    const ruta = path.join(carpeta, entrada.name);
    if (entrada.isDirectory()) archivos.push(...archivosDe(ruta));
    else archivos.push(ruta);
  }
  return archivos;
}

// Cuenta cuántas veces aparece en `contenido` (texto o binario, leído como latin-1) el núcleo de alguna contraseña posible.
function contarNucleos(contenido, nucleos) {
  let total = 0;
  for (const tramo of contenido.matchAll(/[A-Za-z0-9_-]{24,}/g)) {
    for (let i = 0; i + LARGO_NUCLEO <= tramo[0].length; i += 1) {
      if (nucleos.has(tramo[0].slice(i, i + LARGO_NUCLEO))) total += 1;
    }
  }
  return total;
}

// Busca contraseñas de la corrida en carpetas de artefactos y en textos (la salida capturada). Devuelve solo cuántas hay y
// dónde (nombres de archivo), nunca los valores.
export function buscarContrasenas({ semilla, carpetas = [], textos = [] }) {
  const nucleos = nucleosPosibles(semilla);
  const donde = [];
  let total = 0;
  for (const archivo of carpetas.flatMap(archivosDe)) {
    const cantidad = contarNucleos(fs.readFileSync(archivo).toString('latin1'), nucleos);
    if (cantidad) { total += cantidad; donde.push(archivo); }
  }
  for (const texto of textos) {
    const cantidad = contarNucleos(Buffer.from(texto, 'utf8').toString('latin1'), nucleos);
    if (cantidad) { total += cantidad; donde.push('salida'); }
  }
  return { total, donde };
}

// Marcador que sustituye a cada contraseña generada en los artefactos de texto.
export const MARCADOR_CONTRASENA = '[CONTRASEÑA OCULTA]';
const EXTENSIONES_TEXTO = /\.(md|json|txt|log|html?|xml|ya?ml|csv)$/i;

// Reemplaza cada contraseña de la corrida (núcleo + sufijo fijo) por el marcador en los artefactos de texto de las carpetas,
// para conservarlos en el diagnóstico (p. ej. el error-context.md que Playwright guarda al fallar con el valor de los campos).
// Los binarios (capturas) no se tocan: la búsqueda posterior los revisa. Devuelve cuántas ocultó, nunca los valores.
export function ocultarContrasenas({ semilla, carpetas = [] }) {
  const nucleos = nucleosPosibles(semilla);
  let total = 0;
  for (const archivo of carpetas.flatMap(archivosDe).filter((a) => EXTENSIONES_TEXTO.test(a))) {
    const texto = fs.readFileSync(archivo, 'utf8');
    let cantidad = 0;
    const nuevo = texto.replace(/[A-Za-z0-9_-]{24,}/g, (tramo) => {
      let salida = '';
      let i = 0;
      while (i < tramo.length) {
        if (i + LARGO_NUCLEO <= tramo.length && nucleos.has(tramo.slice(i, i + LARGO_NUCLEO))) {
          i += LARGO_NUCLEO;
          if (tramo.startsWith(SUFIJO, i)) i += SUFIJO.length;
          salida += MARCADOR_CONTRASENA;
          cantidad += 1;
        } else {
          salida += tramo[i];
          i += 1;
        }
      }
      return salida;
    });
    if (cantidad) { fs.writeFileSync(archivo, nuevo, 'utf8'); total += cantidad; }
  }
  return total;
}

// Pausas fijas (`waitForTimeout`, `setTimeout(`) en los archivos de una carpeta (RA-02.47).
export function buscarPausasFijas(carpeta) {
  const halladas = [];
  for (const archivo of archivosDe(carpeta).filter((a) => /\.(m?js|jsx)$/.test(a))) {
    fs.readFileSync(archivo, 'utf8').split(/\r?\n/).forEach((texto, indice) => {
      if (/waitForTimeout|setTimeout\s*\(/.test(texto)) halladas.push({ archivo, linea: indice + 1 });
    });
  }
  return halladas;
}

// --- Flujo (solo al ejecutar este archivo) ----------------------------------------------------------------------

const dormir = (ms) => new Promise((resolver) => { setTimeout(resolver, ms); });

// Sondeo con plazo absoluto: repite `comprobar` hasta que devuelva algo verdadero; sin pausas fijas fuera del intervalo.
async function esperar(comprobar, { hasta, intervalo = 500, nombre }) {
  for (;;) {
    try {
      const resultado = await comprobar();
      if (resultado) return resultado;
    } catch { /* todavía no está listo */ }
    if (Date.now() >= hasta) throw new Error(`Se agotó el plazo esperando ${nombre}.`);
    await dormir(intervalo);
  }
}

async function estadoHttp(url) {
  try {
    return (await fetch(url, { signal: AbortSignal.timeout(5000) })).status;
  } catch {
    return 0;
  }
}

// Ejecuta un comando y devuelve su código y su salida. `eco` imprime y conserva la salida (la de Playwright se vigila).
function ejecutar(comando, argumentos, { cwd = RAIZ_PROYECTO, env = process.env, eco = false, limiteMs } = {}) {
  return new Promise((resolver) => {
    const hijo = spawn(comando, argumentos, { cwd, env, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
    let salida = '';
    const alRecibir = (flujo, destino) => flujo.on('data', (trozo) => {
      salida += trozo.toString('utf8');
      if (eco) destino.write(trozo);
    });
    alRecibir(hijo.stdout, process.stdout);
    alRecibir(hijo.stderr, process.stderr);
    const reloj = limiteMs ? setTimeout(() => matarArbol(hijo.pid), limiteMs) : null;
    hijo.on('error', (error) => { clearTimeout(reloj); resolver({ codigo: 127, salida: `${salida}${error.message}` }); });
    hijo.on('close', (codigo) => { clearTimeout(reloj); resolver({ codigo: codigo ?? 1, salida }); });
  });
}

function matarArbol(pid) {
  if (!pid) return;
  try {
    if (process.platform === 'win32') spawn('taskkill', ['/PID', String(pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true });
    else process.kill(pid, 'SIGTERM');
  } catch { /* ya terminó */ }
}

const docker = (...argumentos) => ejecutar('docker', ['compose', ...argumentos]);

// Huella de lo que entra en la compilación: si no cambia, no se vuelve a compilar.
function calcularHuella(urlApi) {
  const hash = crypto.createHash('sha256');
  const raices = ['pages', 'components', 'common', 'config', 'constants', 'contexts', 'data', 'hooks', 'public', 'services', 'styles', 'utils'];
  const sueltos = ['middleware.js', 'next.config.mjs', 'tailwind.config.js', 'postcss.config.mjs', 'jsconfig.json', 'package-lock.json', '.env.local'];
  const archivos = [
    ...raices.flatMap((r) => archivosDe(path.join(CARPETA_FRONTEND, r))),
    ...sueltos.map((s) => path.join(CARPETA_FRONTEND, s)).filter((s) => fs.existsSync(s)),
  ].sort();
  for (const archivo of archivos) {
    hash.update(path.relative(CARPETA_FRONTEND, archivo));
    hash.update(fs.readFileSync(archivo));
  }
  hash.update(urlApi);
  return hash.digest('hex');
}

function entornoDelFrontend(secreto) {
  const entorno = { ...process.env };
  delete entorno.NODE_ENV;
  return {
    ...entorno,
    NEXT_DIST_DIR: CARPETA_DIST,
    NEXT_TELEMETRY_DISABLED: '1',
    NEXT_PUBLIC_API_URL: URL_API,
    NEXTAUTH_URL: URL_WEB,
    NEXTAUTH_SECRET: secreto,
  };
}

export function validarEstado(estado) {
  if (!estado || estado.listo !== true) return 'la instancia no se declara lista';
  if (estado.nombre_activo !== NOMBRE_E2E || estado.base !== NOMBRE_E2E || estado.coleccion !== NOMBRE_E2E) {
    return `la instancia no usa ${NOMBRE_E2E} (base ${estado.base}, colección ${estado.coleccion})`;
  }
  if (!estado.todos_simulados || !estado.redis_simulado) {
    const faltan = Object.entries(estado.simulados || {}).filter(([, activo]) => !activo).map(([nombre]) => nombre);
    return `faltan simulados activos: ${[...faltan, ...(estado.redis_simulado ? [] : ['redis'])].join(', ')}`;
  }
  return null;
}

async function leerEstado() {
  const respuesta = await fetch(`${URL_API}/pruebas-e2e/estado`, { signal: AbortSignal.timeout(5000) });
  return respuesta.ok ? respuesta.json() : null;
}

async function apagarServidorWeb() {
  try {
    const pid = Number(fs.readFileSync(ARCHIVO_PID_WEB, 'utf8'));
    if (pid) matarArbol(pid);
  } catch { /* no había servidor */ }
  fs.rmSync(ARCHIVO_PID_WEB, { force: true });
}

// Apaga la instancia y espera a que termine de eliminar su base, su colección y su carpeta.
async function apagarInstancia() {
  const resultado = await docker('exec', '-T', 'backend', 'python', '-m', 'tests.instancia_e2e', '--apagar');
  return resultado;
}

async function apagarTodo() {
  await apagarServidorWeb();
  const instancia = await apagarInstancia();
  console.log(instancia.salida.trim());
  const web = await estadoHttp(`${URL_WEB}/auth/login`);
  const api = await estadoHttp(`${URL_API}/pruebas-e2e/estado`);
  console.log(`Frontend de pruebas (${PUERTO_WEB}): ${web ? 'sigue respondiendo' : 'apagado'} · instancia (${PUERTO_API}): ${api ? 'sigue respondiendo' : 'apagada'}`);
  return !web && !api;
}

async function correr(argumentosPlaywright) {
  const t0 = Date.now();
  const limite = t0 + LIMITE_PREPARACION_MS;
  const estado = { semilla: crypto.randomBytes(32), secreto: crypto.randomBytes(32).toString('hex'), token: null };
  let servidorWeb = null;
  let instanciaLanzada = false;
  let resultado = { codigo: 1, motivos: [] };
  let salidaPlaywright = '';
  let datos = { ...analizarInforme(null), contrasenas: 0, coincidenciasRegistro: null, residuos: null };
  let preparacionMs = 0;
  let suiteMs = 0;
  let desarrolloAntes = 0;
  let desarrolloDespues = 0;
  let codigoPlaywright = 1;

  // Antes de cualquier otra cosa, para que un informe anterior nunca se lea como el de esta corrida.
  prepararResultados(CARPETA_RESULTADOS);

  try {
    desarrolloAntes = await estadoHttp(`${URL_DESARROLLO}/`);
    console.log(`Backend de desarrollo antes de la corrida: ${desarrolloAntes}`);
    if (desarrolloAntes !== 200) throw new Error('El backend de desarrollo no responde; no se prepara nada.');

    await comprobarPuertoLibre(HOST, PUERTO_WEB, 'frontend de pruebas');
    if (await estadoHttp(`${URL_API}/pruebas-e2e/estado`)) {
      throw new Error(`El puerto ${PUERTO_API} de ${HOST} ya responde como instancia de pruebas. Libérelo con \`npm run e2e:apagar\`.`);
    }

    // Compilación del frontend de pruebas (solo si cambió algo).
    const huella = calcularHuella(URL_API);
    const huellaActual = fs.existsSync(ARCHIVO_HUELLA) ? fs.readFileSync(ARCHIVO_HUELLA, 'utf8') : '';
    if (huella !== huellaActual) {
      console.log('Compilando el frontend de pruebas (.next-e2e)...');
      const tb = Date.now();
      const nextBin = require.resolve('next/dist/bin/next');
      const compilacion = await ejecutar(process.execPath, [nextBin, 'build'], {
        cwd: CARPETA_FRONTEND, env: entornoDelFrontend(estado.secreto), limiteMs: Math.max(1000, limite - Date.now()),
      });
      if (compilacion.codigo !== 0) throw new Error(`La compilación del frontend de pruebas falló:\n${compilacion.salida.slice(-3000)}`);
      fs.writeFileSync(ARCHIVO_HUELLA, huella);
      console.log(`Compilación lista en ${segundos(Date.now() - tb)}.`);
    } else {
      console.log('Frontend de pruebas ya compilado (la huella no cambió).');
    }

    // Instancia del backend.
    console.log('Arrancando la instancia del backend de pruebas...');
    instanciaLanzada = true;
    const lanzamiento = await docker('exec', '-d', 'backend', 'python', '-m', 'tests.instancia_e2e');
    if (lanzamiento.codigo !== 0) throw new Error(`No se pudo lanzar la instancia: ${lanzamiento.salida.trim()}`);
    const estadoInstancia = await esperar(leerEstado, { hasta: limite, nombre: 'la instancia del backend de pruebas' });
    const problema = validarEstado(estadoInstancia);
    if (problema) throw new Error(`Se aborta antes de abrir el navegador: ${problema}.`);
    const token = await esperar(async () => {
      const lectura = await docker('exec', '-T', 'backend', 'cat', '/tmp/servia_e2e/control.token');
      return lectura.codigo === 0 && lectura.salida.trim() ? lectura.salida.trim() : null;
    }, { hasta: limite, nombre: 'el token del control' });
    estado.token = token;
    // Una corrida cortada deja su base atrás, pero la instancia nueva la reemplaza: debe empezar sin residuos.
    const alEmpezar = await leerResiduos(token);
    datos.residuosAlEmpezar = alEmpezar ? alEmpezar.total : null;
    if (!alEmpezar || alEmpezar.total !== 0) {
      throw new Error(`Se aborta antes de abrir el navegador: la instancia no empezó sin residuos (${alEmpezar ? alEmpezar.texto : 'no se pudieron leer'}).`);
    }

    // Frontend de pruebas.
    console.log('Arrancando el frontend de pruebas...');
    const nextBin = require.resolve('next/dist/bin/next');
    servidorWeb = spawn(process.execPath, [nextBin, 'start', '-H', HOST, '-p', String(PUERTO_WEB)], {
      cwd: CARPETA_FRONTEND, env: entornoDelFrontend(estado.secreto), stdio: 'ignore', windowsHide: true,
    });
    fs.mkdirSync(path.dirname(ARCHIVO_PID_WEB), { recursive: true });
    fs.writeFileSync(ARCHIVO_PID_WEB, String(servidorWeb.pid));
    await esperar(async () => (await estadoHttp(`${URL_WEB}/auth/login`)) === 200, { hasta: limite, nombre: 'el frontend de pruebas' });

    const t1 = Date.now();
    preparacionMs = t1 - t0;
    console.log(`Preparación lista en ${segundos(preparacionMs)}.`);

    // Playwright.
    const ejecucion = await ejecutar(process.execPath, [require.resolve('@playwright/test/cli'), 'test', ...argumentosPlaywright], {
      cwd: CARPETA_FRONTEND,
      eco: true,
      env: {
        ...process.env,
        E2E_SEMILLA: estado.semilla.toString('hex'),
        E2E_TOKEN: estado.token,
        E2E_URL_API: URL_API,
        E2E_URL_WEB: URL_WEB,
        E2E_URL_DESARROLLO: URL_DESARROLLO,
        NEXT_TELEMETRY_DISABLED: '1',
      },
    });
    suiteMs = Date.now() - t1;
    codigoPlaywright = ejecucion.codigo;
    salidaPlaywright = ejecucion.salida;
  } catch (error) {
    console.error(`\n${error.message}`);
    datos.motivoPreparacion = error.message;
  } finally {
    // Apagado: primero los residuos finales, luego el control (devuelve la cuenta de contraseñas en el registro) y la espera del cierre.
    if (instanciaLanzada && estado.token) {
      const finales = await leerResiduos(estado.token);
      datos.residuos = finales ? finales.total : null;
      datos.textoResiduos = finales ? finales.texto : null;
      try {
        const respuesta = await fetch(`${URL_API}/pruebas-e2e/apagar`, {
          method: 'POST', headers: { 'X-Control-Pruebas': estado.token }, signal: AbortSignal.timeout(30_000),
        });
        if (respuesta.ok) datos.coincidenciasRegistro = (await respuesta.json()).coincidencias_en_registro;
      } catch { /* se apaga igual con --apagar */ }
    }
    if (servidorWeb) matarArbol(servidorWeb.pid);
    await apagarTodo();
  }

  desarrolloDespues = await estadoHttp(`${URL_DESARROLLO}/`);
  const cuentas = resumirInforme(INFORME_JSON);
  // Primero se ocultan las contraseñas de los artefactos de texto; la búsqueda final comprueba que no quedó ninguna.
  const ocultas = ocultarContrasenas({ semilla: estado.semilla, carpetas: [CARPETA_RESULTADOS] });
  if (ocultas) console.log(`Contraseñas ocultas en los artefactos de texto: ${ocultas}`);
  const busqueda = buscarContrasenas({ semilla: estado.semilla, carpetas: [CARPETA_RESULTADOS], textos: [salidaPlaywright] });
  datos = {
    ...datos, ...cuentas, contrasenas: busqueda.total, desarrolloAntes, desarrolloDespues, codigoPlaywright, preparacionMs, suiteMs,
  };
  if (busqueda.donde.length) console.error(`Contraseñas halladas en: ${busqueda.donde.join(', ')}`);
  resultado = veredicto(datos);
  if (datos.motivoPreparacion) resultado.motivos.unshift(datos.motivoPreparacion.split('\n')[0]);
  if (datos.motivoPreparacion) resultado.codigo = 1;
  console.log(textoResumen({ ...datos, ...resultado }));
  return resultado.codigo;
}

async function principal(argumentos) {
  if (argumentos.includes('--apagar')) {
    const apagado = await apagarTodo();
    return apagado ? 0 : 1;
  }
  const alInterrumpir = async () => {
    console.error('\nInterrumpido: apagando lo que se levantó...');
    await apagarTodo();
    process.exit(130);
  };
  process.once('SIGINT', alInterrumpir);
  process.once('SIGTERM', alInterrumpir);
  return correr(argumentos);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  principal(process.argv.slice(2)).then((codigo) => process.exit(codigo), (error) => {
    console.error(error);
    process.exit(2);
  });
}
