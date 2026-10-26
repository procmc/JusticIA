// Fixtures de la red de seguridad de extremo a extremo (spec 005a). Todas las pruebas importan `test` y `expect` de aquí.
// T3 (RA-02.42, RA-02.43): el cliente del control, las contraseñas de la suite, la creación de usuarios PRUEBA y la limpieza
// automática tras cada prueba. T4 (RA-02.41, RA-02.44, RA-02.45, RA-02.46): la red, la consola, los 616 px y el fallo esperado.
const base = require('@playwright/test');
const { crearControl } = require('./control.js');
const { crearGenerador } = require('./contrasenas.js');
const { esDeclarado } = require('./consola_declarada.js');
const { exigirAccesible, pulsar, escribir, iniciarSesion } = require('./sesion.js');

// Fallo esperado estricto (RA-02.44): «<requisito> · <módulo>», p. ej. «RF-19.40 · notebooks».
const FORMATO_ANOTACION = /^(RF|RNF|RA)-\d+(\.\d+)? · \S/;

function validarAnotacion(anotacion) {
  if (typeof anotacion !== 'string' || !FORMATO_ANOTACION.test(anotacion)) {
    throw new Error(`Anotación de fallo esperado inválida («${anotacion}»): debe ser «<requisito> · <módulo>», p. ej. «RF-19.40 · notebooks».`);
  }
}

// Se llama dentro de la prueba, solo después de verla fallar por el motivo del requisito. Si luego pasa, Playwright
// la marca como inesperada y la corrida falla nombrándola.
function fallaEsperada(test, anotacion) {
  validarAnotacion(anotacion);
  test.fail(true, anotacion);
}

// El navegador solo puede hablar con el frontend y la instancia de pruebas (RA-02.41, RNF-09.40).
function origenesPermitidos() {
  return new Set([
    new URL(process.env.E2E_URL_WEB || 'http://127.0.0.1:3100').origin,
    new URL(process.env.E2E_URL_API || 'http://127.0.0.1:8100').origin,
  ]);
}

// El visor de PDF integrado de Chrome (vista previa de RF-18.40) carga recursos propios que no salen a ninguna red
// (RNF-09.40 sigue intacto). Solo se aceptan esos dos orígenes, completos; cualquier otra extensión o página `chrome:` cuenta
// como externa. El identificador es el de la extensión «Chrome PDF Viewer», comprobado en lo que el navegador pide.
const VISOR_PDF_CHROME = 'chrome-extension://mhjfbmdgcfjbbpaeojofohoefgiehjai/';
const RECURSOS_CHROME = 'chrome://resources/';
function esLocalDelNavegador(url) {
  return url.startsWith(VISOR_PDF_CHROME) || url.startsWith(RECURSOS_CHROME);
}

// Bloquea antes de que salga cualquier petición a otro origen y la registra para nombrarla al terminar.
async function vigilarRed(context) {
  const permitidos = origenesPermitidos();
  const externas = [];
  await context.route('**/*', (route) => {
    const peticion = route.request();
    const direccion = new URL(peticion.url());
    if (permitidos.has(direccion.origin) || esLocalDelNavegador(peticion.url())) return route.continue();
    externas.push(`${peticion.method()} ${peticion.url()}`);
    return route.abort('blockedbyclient');
  });
  return {
    externas: () => [...externas],
    descartar: () => { externas.length = 0; },
    verificar: () => {
      if (externas.length) {
        throw new Error(`El navegador pidió direcciones fuera de la instancia de pruebas (RA-02.41, RNF-09.40): ${externas.join(', ')}`);
      }
    },
  };
}

// Next.js 15.2.4 normaliza todo loopback a `localhost` en `NextURL`, así que el middleware (que redirige con
// `new URL(..., req.url)`) contesta con `Location: http://localhost:3100/...` aunque el servidor de pruebas escuche en
// 127.0.0.1. Ese origen no lleva la cookie de la sesión y la red de la suite lo bloquea (RA-02.41). Solo se reescriben las
// redirecciones de página hacia `localhost:<puerto de pruebas>`; todo lo demás sigue su curso. Se puede quitar cuando el
// centinela de `flujos/red.spec.js` falle diciendo que Next ya no normaliza.
async function reescribirRedirecciones(page) {
  const web = new URL(process.env.E2E_URL_WEB || 'http://127.0.0.1:3100');
  await page.route(`${web.origin}/**`, async (route) => {
    if (!route.request().isNavigationRequest()) return route.fallback();
    const respuesta = await route.fetch({ maxRedirects: 0 });
    const destino = respuesta.headers().location;
    const url = destino ? new URL(destino, web.origin) : null;
    if (url && url.hostname === 'localhost' && url.port === web.port) {
      return route.fulfill({
        status: respuesta.status(),
        headers: { location: `${web.origin}${url.pathname}${url.search}${url.hash}` },
      });
    }
    // Sin redirección a localhost: el pedido sigue su curso real (servir la página con `fulfill` haría que Chrome le
    // niegue los pedidos a la API).
    return route.fallback();
  });
}

// Errores de consola y excepciones sin capturar (RA-02.45); las advertencias no cuentan. Se filtran al consultar, así que
// una prueba puede declarar `provocado(/401/)` antes o después de la acción.
function vigilarConsola(context) {
  const registrados = [];
  const provocados = [];
  context.on('console', (mensaje) => {
    if (mensaje.type() !== 'error') return;
    const url = mensaje.location().url;
    registrados.push({ texto: `[consola] ${mensaje.text()}${url ? ` (${url})` : ''}`, comparar: `${mensaje.text()} ${url || ''}` });
  });
  context.on('weberror', (errorWeb) => {
    const error = errorWeb.error();
    const texto = String(error?.message || error);
    registrados.push({ texto: `[excepción sin capturar] ${texto}`, comparar: texto });
  });
  const pendientesObjetos = () => registrados.filter(
    (r) => !provocados.some((patron) => patron.test(r.comparar)) && !esDeclarado(r.comparar),
  );
  return {
    pendientes: () => pendientesObjetos().map((r) => r.texto),
    provocado: (patron) => { provocados.push(patron); },
    descartar: () => { registrados.length = 0; },
    verificar: () => {
      const pendientes = pendientesObjetos();
      if (pendientes.length) {
        throw new Error(`Errores de consola no declarados (RA-02.45):\n${pendientes.map((r) => `  - ${r.texto}`).join('\n')}`);
      }
    },
  };
}

const test = base.test.extend({
  // Red y consola se instalan al pedir `page` (abajo); las pruebas de infraestructura, sin navegador, no las usan.
  red: async ({ context }, use) => {
    await use(await vigilarRed(context));
  },

  consola: async ({ context }, use) => {
    await use(vigilarConsola(context));
  },

  // Toda prueba con navegador pasa por aquí: al terminar falla si salió una petición externa o hubo un error de consola
  // no declarado.
  page: async ({ page, red, consola }, use) => {
    await reescribirRedirecciones(page);
    await use(page);
    red.verificar();
    consola.verificar();
  },

  // Otra pestaña del mismo contexto (005b, RNF-07.40): comparte sesión, red y consola vigiladas, y las redirecciones reescritas.
  otraPestana: async ({ page }, use) => {
    const pestana = await page.context().newPage();
    await reescribirRedirecciones(pestana);
    await use(pestana);
    await pestana.close();
  },

  // Otro usuario Gubernamental en un contexto nuevo (005b, RF-17.40), con sesión iniciada y su propia red y consola vigiladas;
  // al terminar exige lo mismo que `page`. Devuelve `{ page, usuario, red, consola }`.
  otroUsuario: async ({ browser, baseURL, viewport, crearUsuario }, use) => {
    const usuario = await crearUsuario('usuario');
    const contexto = await browser.newContext({ baseURL, viewport });
    const red = await vigilarRed(contexto);
    const consola = vigilarConsola(contexto);
    const pagina = await contexto.newPage();
    await reescribirRedirecciones(pagina);
    await iniciarSesion(pagina, usuario.correo, usuario.contrasena);
    try {
      await use({ page: pagina, usuario, red, consola });
      red.verificar();
      consola.verificar();
    } finally {
      await contexto.close();
    }
  },

  // Un generador por trabajador: cada contraseña es nueva, derivada de la semilla de la corrida y nunca se escribe.
  generadorContrasenas: [async ({}, use, workerInfo) => {
    await use(crearGenerador(undefined, workerInfo.parallelIndex));
  }, { scope: 'worker' }],

  control: async ({}, use) => {
    await use(crearControl());
  },

  // `crearUsuario(rol, { temporal, inactivo })` devuelve el usuario con su contraseña (solo en memoria de la prueba).
  crearUsuario: async ({ control, generadorContrasenas }, use) => {
    await use(async (rol, opciones = {}) => {
      const contrasena = generadorContrasenas.siguiente();
      const usuario = await control.crearUsuario(rol, contrasena, opciones);
      return { ...usuario, contrasena };
    });
  },

  // Automática: tras CADA prueba (pase o falle) limpia todo el entorno aislado y exige residuos en cero, nombrando la tabla.
  limpiezaPorPrueba: [async ({ control }, use) => {
    await use();
    await control.limpiar();
    const residuos = await control.residuos();
    if (residuos.total !== 0) {
      throw new Error(`Quedaron residuos de datos de prueba tras limpiar: ${residuos.texto}`);
    }
  }, { auto: true }],
});

module.exports = {
  test, expect: base.expect, esLocalDelNavegador, fallaEsperada, validarAnotacion, exigirAccesible, pulsar, escribir, iniciarSesion,
};
