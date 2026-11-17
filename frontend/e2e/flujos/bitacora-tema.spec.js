// Vocabulario «tema» en la Bitácora del Administrador (spec 011, T1): RF-22.130, RF-22.131, RF-22.132, RF-22.134, RF-23.130 y
// RNF-04.130. El ERS ya pide «tema» (RF-22, RF-23); la pantalla todavía decía «expediente». Corre en `escritorio` (1366) y `pequena`
// (616). Los registros los produce la API de la instancia con datos inventados; el navegador solo los consulta como Administrador.
const { test, expect, iniciarSesion, pulsar, escribir } = require('../soporte/fixtures.js');
const { iniciarSesion: iniciarSesionPorApi, subirYProcesar, documentoDePrueba, nuevoTema, preguntar } = require('../soporte/datos.js');

const RUTA = '/administracion/bitacora';

async function abrirHistorial(page) {
  await page.goto(RUTA);
  await expect(page.getByText('Registros de Bitácora')).toBeVisible();
  await page.waitForFunction(() => Boolean(window.next && window.next.router && window.next.router.isReady));
}

const sinBarraHorizontal = (page) => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);
const sinExpediente = (page) => expect(page.locator('body')).not.toContainText(/expediente/i);

test.describe('Bitácora del Administrador: vocabulario «tema»', () => {
  test('RF-22.130 · RF-22.131 · el filtro y la columna dicen «Tema»', async ({ page, crearUsuario }) => {
    const administrador = await crearUsuario('administrador');
    await iniciarSesion(page, administrador.correo, administrador.contrasena);
    await abrirHistorial(page);

    // El filtro: rótulo «Tema» y ayuda «Nombre del tema» (antes «Expediente» y «Número de expediente»).
    await expect(page.getByPlaceholder('Nombre del tema')).toBeVisible();
    await expect(page.getByPlaceholder('Número de expediente')).toHaveCount(0);
    await expect(page.getByText('Tema', { exact: true }).first()).toBeVisible();
    // La columna de la tabla.
    await expect(page.getByText('TEMA', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('EXPEDIENTE', { exact: true })).toHaveCount(0);
    // Ningún texto de la pantalla dice «expediente».
    await sinExpediente(page);
    expect(await sinBarraHorizontal(page), 'sin desborde horizontal de la página').toBe(true);
  });

  test('RF-22.130 · filtrar solo por un tema que no existe muestra 0 registros y ningún error', async ({ page, crearUsuario }) => {
    const administrador = await crearUsuario('administrador');
    await iniciarSesion(page, administrador.correo, administrador.contrasena);
    await abrirHistorial(page);

    await escribir(page.getByPlaceholder('Nombre del tema'), 'PRUEBA tema que no existe');
    const [respuesta] = await Promise.all([
      page.waitForResponse((r) => new URL(r.url()).pathname.includes('/bitacora/registros') && r.request().method() === 'GET'),
      pulsar(page.getByRole('button', { name: 'Buscar' })),
    ]);
    expect(respuesta.status()).toBe(200);
    await expect(page.getByText('No se encontraron registros')).toBeVisible();
    await expect(page.getByText(/Unhandled Runtime Error|Error interno del servidor/)).toHaveCount(0);
  });

  test('RF-23.130 · Estadísticas habla de temas', async ({ page, crearUsuario }) => {
    const administrador = await crearUsuario('administrador');
    await iniciarSesion(page, administrador.correo, administrador.contrasena);
    await abrirHistorial(page);
    await pulsar(page.getByRole('tab', { name: /Estadísticas/ }));

    await expect(page.getByText('Temas más Consultados', { exact: true })).toBeVisible();
    await expect(page.getByText('Top 5 de temas con más actividad')).toBeVisible();
    await expect(page.getByText('Temas', { exact: true }).first()).toBeVisible();
    await sinExpediente(page);
    expect(await sinBarraHorizontal(page), 'sin desborde horizontal de la página').toBe(true);
  });

  test('RF-22.132 · el detalle de una consulta a un tema etiqueta «Tema»', async ({ page, crearUsuario, control }) => {
    // Un usuario consulta un tema (con un documento procesado) y el Administrador abre el detalle de ese registro.
    const administrador = await crearUsuario('administrador');
    const usuario = await crearUsuario('usuario');
    const tema = nuevoTema();
    const token = await iniciarSesionPorApi(control, usuario);
    await subirYProcesar(control, token, tema, documentoDePrueba());
    await control.motor({ modo: 'texto', texto: 'PRUEBA respuesta simulada' });
    await preguntar(control, token, usuario, '¿Qué dice el documento inventado?', { tema });

    await iniciarSesion(page, administrador.correo, administrador.contrasena);
    await abrirHistorial(page);
    await escribir(page.getByPlaceholder('Nombre, apellido o correo'), usuario.correo);
    await Promise.all([
      page.waitForResponse((r) => new URL(r.url()).pathname.includes('/bitacora/registros') && r.request().method() === 'GET'),
      pulsar(page.getByRole('button', { name: 'Buscar' })),
    ]);
    const fila = page.getByRole('grid', { name: 'Tabla de registros de bitácora' }).getByRole('row').filter({ hasText: 'Consulta' });
    await expect(fila.first()).toBeVisible();
    await pulsar(fila.first().getByRole('button'));
    const panel = page.getByRole('dialog');
    await expect(panel.getByText(/Detalle del Evento #/)).toBeVisible();

    await expect(panel.getByText('Tema', { exact: true }).first()).toBeVisible();
    await expect(panel).toContainText(tema);
    await expect(panel).not.toContainText(/expediente/i);
    expect(await sinBarraHorizontal(page), 'sin desborde horizontal de la página').toBe(true);
  });

  // ---- T2: el PDF y el inicio ----------------------------------------------------------------------------------------------
  test('RF-22.133 · exportar el PDF funciona y no menciona «expediente»', async ({ page, crearUsuario }) => {
    const administrador = await crearUsuario('administrador');
    await iniciarSesion(page, administrador.correo, administrador.contrasena);
    await abrirHistorial(page);

    const [descarga] = await Promise.all([page.waitForEvent('download'), pulsar(page.getByRole('button', { name: /Exportar PDF/ }))]);
    expect(descarga.suggestedFilename()).toMatch(/^bitacora_.*\.pdf$/);
    const ruta = await descarga.path();
    const contenido = require('node:fs').readFileSync(ruta).toString('latin1');
    expect(contenido.length).toBeGreaterThan(500);
    // El texto del PDF va sin comprimir en el flujo de jsPDF: «Tema» sí aparece y «expediente» no. (Con otra compresión esta
    // comprobación no vería nada, por eso el contenido también se revisa a mano.)
    expect(contenido).not.toMatch(/expediente/i);
  });

  test('RT-06.130 · el inicio del Administrador no dice «expediente»', async ({ page, crearUsuario }) => {
    const administrador = await crearUsuario('administrador');
    await iniciarSesion(page, administrador.correo, administrador.contrasena);
    await page.goto('/');
    await expect(page.getByRole('heading').first()).toBeVisible();
    await sinExpediente(page);
  });

  test('RT-06.130 · el inicio del Usuario Gubernamental no dice «expediente»', async ({ page, crearUsuario }) => {
    const usuario = await crearUsuario('usuario');
    await iniciarSesion(page, usuario.correo, usuario.contrasena);
    await page.goto('/');
    await expect(page.getByRole('heading').first()).toBeVisible();
    await sinExpediente(page);
  });
});
