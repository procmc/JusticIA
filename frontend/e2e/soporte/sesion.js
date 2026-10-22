// Accesibilidad a 616 px (RA-02.46, RNF-04): los controles que un flujo usa deben poder alcanzarse.
// `exigirAccesible` desplaza el control a la vista y comprueba que su caja cae dentro de la ventana y que nada lo tapa;
// `pulsar` y `escribir` lo aplican antes de actuar cuando la prueba corre en el proyecto `pequena`.
const { expect, test } = require('@playwright/test');

const PROYECTO_PEQUENO = 'pequena';

// Devuelve 'ok' o el motivo (en español) por el que el control no es accesible.
async function evaluarAccesibilidad(locator) {
  await locator.scrollIntoViewIfNeeded();
  const resultado = await locator.evaluate((elemento) => {
    const caja = elemento.getBoundingClientRect();
    const ancho = window.innerWidth;
    const alto = window.innerHeight;
    if (caja.width === 0 || caja.height === 0) return { motivo: 'no tiene tamaño' };
    if (caja.left < -1 || caja.top < -1 || caja.right > ancho + 1 || caja.bottom > alto + 1) {
      return { motivo: `queda fuera de la ventana (${Math.round(caja.left)},${Math.round(caja.top)} a ${Math.round(caja.right)},${Math.round(caja.bottom)} en ${ancho}×${alto})` };
    }
    const encima = document.elementFromPoint(caja.left + caja.width / 2, caja.top + caja.height / 2);
    if (!encima || (encima !== elemento && !elemento.contains(encima))) {
      const etiqueta = encima ? `<${encima.tagName.toLowerCase()}${encima.id ? ` id="${encima.id}"` : ''}>` : 'nada';
      return { motivo: `está tapado por ${etiqueta}` };
    }
    return { motivo: 'ok' };
  });
  return resultado.motivo;
}

async function exigirAccesible(locator, { timeout = 10_000 } = {}) {
  // Sondeo con plazo (sin pausas fijas): una animación o un panel que termina de abrirse no cuenta como fallo.
  let ultimoMotivo = 'no se pudo evaluar';
  try {
    await expect.poll(async () => {
      ultimoMotivo = await evaluarAccesibilidad(locator);
      return ultimoMotivo;
    }, { timeout }).toBe('ok');
  } catch (error) {
    throw new Error(`Control no accesible: ${locator} ${ultimoMotivo}`);
  }
}

function esPantallaPequena() {
  return test.info().project.name === PROYECTO_PEQUENO;
}

async function pulsar(locator, opciones) {
  if (esPantallaPequena()) await exigirAccesible(locator);
  await locator.click(opciones);
}

async function escribir(locator, texto, opciones) {
  if (esPantallaPequena()) await exigirAccesible(locator);
  await locator.fill(texto, opciones);
}

// Inicia sesión por la pantalla y espera la página de inicio (cuenta con último acceso: sin panel de cambio obligatorio).
// Espera a que React hidrate: si se enviara antes, el formulario viajaría por GET con la contraseña en la dirección.
async function iniciarSesion(page, correo, contrasena) {
  await page.goto('/auth/login');
  await expect(page.getByRole('heading', { name: 'Inicio de sesión' })).toBeVisible();
  await page.waitForFunction(() => Boolean(window.next && window.next.router && window.next.router.isReady));
  await escribir(page.getByLabel('Correo electrónico'), correo);
  await escribir(page.getByLabel('Contraseña', { exact: true }), contrasena);
  await pulsar(page.getByRole('button', { name: 'Iniciar sesión' }));
  await page.waitForURL((url) => url.pathname === '/', { timeout: 10_000 });
  await expect(page.getByText('Bienvenid@')).toBeVisible();
}

module.exports = { exigirAccesible, pulsar, escribir, iniciarSesion };
