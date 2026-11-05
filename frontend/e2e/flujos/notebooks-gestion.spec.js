// NotebookServIA: renombrar y eliminar (spec 009, T5): RF-17.80 a RF-17.90. Corre en `escritorio` (1366) y `pequena` (616).
// Datos inventados (prefijo PRUEBA). La T6 añade los casos límite: doble clic, respuesta retenida, otra pestaña y 150 caracteres.
const { test, expect, iniciarSesion, pulsar, escribir } = require('../soporte/fixtures.js');
const { aleatorio, iniciarSesion: iniciarSesionPorApi, crearNotebook, notebookConDocumento } = require('../soporte/datos.js');
const {
  abrirNotebooks, crearNotebookEnPantalla, listaDeNotebooks, abrirNotebookDeLaLista, avisosDeLaPantalla, exigirSinVoseo,
  abrirNotebookConDocumentos,
} = require('../soporte/pantallas.js');

const esRuta = (url, metodo, esperado) => /\/notebooks\/\d+$/.test(new URL(url).pathname) && metodo === esperado;
const esRenombrado = (r) => esRuta(r.url(), r.request().method(), 'PUT');
const esEliminacion = (r) => esRuta(r.url(), r.request().method(), 'DELETE');
const esCreacion = (r) => new URL(r.url()).pathname.replace(/\/$/, '').endsWith('/notebooks') && r.request().method() === 'POST';

const filas = (page) => page.locator('div.overflow-y-auto.space-y-1 > div');
const campoDeNombre = (page) => page.getByRole('textbox', { name: 'Nuevo nombre del notebook' });

// Un usuario con la sesión iniciada en el navegador y su token de API, para preparar notebooks sin pasar por la pantalla.
async function prepararUsuario(page, crearUsuario, control) {
  const usuario = await crearUsuario('usuario');
  await iniciarSesion(page, usuario.correo, usuario.contrasena);
  return { usuario, token: await iniciarSesionPorApi(control, usuario) };
}

async function empezarRenombrar(page, nombre) {
  await pulsar(filas(page).filter({ hasText: nombre }).getByRole('button', { name: 'Renombrar notebook' }));
  await expect(campoDeNombre(page)).toBeVisible();
}

test.describe('NotebookServIA: renombrar y eliminar', () => {
  test('RF-17.80 · renombrar, cancelar y Escape', async ({ page, crearUsuario, control }) => {
    const { token } = await prepararUsuario(page, crearUsuario, control);
    const original = `PRUEBA gestión original ${aleatorio()}`;
    const nuevo = `PRUEBA gestión nuevo ${aleatorio()}`;
    await crearNotebook(control, token, original);
    await abrirNotebooks(page);
    await abrirNotebookDeLaLista(page, original);
    const llamadas = [];
    page.on('request', (r) => { if (esRuta(r.url(), r.method(), 'PUT')) llamadas.push(r.url()); });

    // Cancelar y Escape no llaman al servidor y dejan el nombre como estaba.
    await empezarRenombrar(page, original);
    await campoDeNombre(page).fill('PRUEBA descartado');
    await pulsar(page.getByRole('button', { name: 'Cancelar', exact: true }));
    await expect(campoDeNombre(page)).toHaveCount(0);
    await expect(listaDeNotebooks(page)).toHaveText([original]);
    await empezarRenombrar(page, original);
    await campoDeNombre(page).fill('PRUEBA descartado');
    await campoDeNombre(page).press('Escape');
    await expect(campoDeNombre(page)).toHaveCount(0);
    await expect(listaDeNotebooks(page)).toHaveText([original]);
    expect(llamadas).toHaveLength(0);

    // Guardar con Enter: la fila y el encabezado (el notebook está abierto) muestran el nombre nuevo, y persiste al recargar.
    await empezarRenombrar(page, original);
    await campoDeNombre(page).fill(nuevo);
    const respuesta = page.waitForResponse(esRenombrado);
    await campoDeNombre(page).press('Enter');
    expect((await respuesta).status()).toBe(200);
    await expect(listaDeNotebooks(page)).toHaveText([nuevo]);
    await expect(page.getByRole('heading', { name: nuevo })).toBeVisible();
    await exigirSinVoseo(page);
    await abrirNotebooks(page);
    await expect(listaDeNotebooks(page)).toHaveText([nuevo]);
  });

  test('RF-17.81 · RF-17.82 · RF-17.84 · rechazos al renombrar', async ({ page, crearUsuario, control, consola }) => {
    consola.provocado(/400/); // los rechazos de validación que provoca la prueba
    const { token } = await prepararUsuario(page, crearUsuario, control);
    const uno = `PRUEBA gestión uno ${aleatorio()}`;
    const dos = `PRUEBA gestión dos ${aleatorio()}`;
    await crearNotebook(control, token, uno);
    await crearNotebook(control, token, dos);
    await abrirNotebooks(page);
    await empezarRenombrar(page, uno);

    const intentar = async (texto, mensaje) => {
      await campoDeNombre(page).fill(texto);
      const respuesta = page.waitForResponse(esRenombrado);
      await campoDeNombre(page).press('Enter');
      expect((await respuesta).status()).toBe(400);
      await expect(page.getByText(mensaje, { exact: true })).toBeVisible();
      await expect(campoDeNombre(page)).toBeVisible(); // sigue en edición
    };
    await intentar('   ', 'El nombre del notebook no puede estar vacío');
    await intentar('A'.repeat(151), 'El nombre no puede superar 150 caracteres.');
    await intentar(dos.toUpperCase(), 'Ya tiene un notebook con ese nombre.');

    // Ninguno cambió.
    await pulsar(page.getByRole('button', { name: 'Cancelar', exact: true }));
    await expect(listaDeNotebooks(page)).toHaveText([dos, uno]);
  });

  test('RF-17.85 · crear con nombre duplicado', async ({ page, crearUsuario, control, consola }) => {
    consola.provocado(/400/);
    const { token } = await prepararUsuario(page, crearUsuario, control);
    const nombre = `PRUEBA gestión duplicado ${aleatorio()}`;
    await crearNotebook(control, token, nombre);
    await abrirNotebooks(page);
    const respuesta = page.waitForResponse(esCreacion);
    await escribir(page.getByPlaceholder('Nombre del notebook'), nombre.toUpperCase());
    await pulsar(page.getByRole('button', { name: 'Crear notebook' }));
    expect((await respuesta).status()).toBe(400);
    await expect(page.getByText('Ya tiene un notebook con ese nombre.', { exact: true })).toBeVisible();
    await expect(listaDeNotebooks(page)).toHaveText([nombre]);
  });

  test('RF-17.86 · RF-17.87 · eliminar: cancelar y confirmar', async ({ page, crearUsuario, control }) => {
    const { token } = await prepararUsuario(page, crearUsuario, control);
    const queda = `PRUEBA gestión queda ${aleatorio()}`;
    const sale = `PRUEBA gestión sale ${aleatorio()}`;
    await crearNotebook(control, token, queda);
    await crearNotebook(control, token, sale);
    await abrirNotebooks(page);
    const llamadas = [];
    page.on('request', (r) => { if (esRuta(r.url(), r.method(), 'DELETE')) llamadas.push(r.url()); });

    // Cancelar: el cuadro nombra el notebook, no se llama al servidor y la fila sigue.
    await pulsar(filas(page).filter({ hasText: sale }).getByRole('button', { name: 'Eliminar notebook' }));
    const dialogo = page.getByRole('dialog');
    await expect(dialogo).toContainText('Eliminar notebook');
    await expect(dialogo).toContainText(sale);
    await exigirSinVoseo(page);
    await pulsar(dialogo.getByRole('button', { name: 'Cancelar', exact: true }));
    await expect(dialogo).toHaveCount(0);
    expect(llamadas).toHaveLength(0);
    await expect(listaDeNotebooks(page)).toHaveText([sale, queda]);

    // Confirmar: sale de la lista y no vuelve al recargar.
    await pulsar(filas(page).filter({ hasText: sale }).getByRole('button', { name: 'Eliminar notebook' }));
    const respuesta = page.waitForResponse(esEliminacion);
    await pulsar(page.getByRole('dialog').getByRole('button', { name: 'Eliminar', exact: true }));
    expect((await respuesta).status()).toBe(200);
    await expect(listaDeNotebooks(page)).toHaveText([queda]);
    expect(llamadas).toHaveLength(1);
    await abrirNotebooks(page);
    await expect(listaDeNotebooks(page)).toHaveText([queda]);
  });

  test('RF-17.89 · el abierto se cierra', async ({ page, crearUsuario, control }) => {
    await prepararUsuario(page, crearUsuario, control);
    await abrirNotebooks(page);
    const nombre = `PRUEBA gestión abierto ${aleatorio()}`;
    await crearNotebookEnPantalla(page, nombre);
    await abrirNotebookDeLaLista(page, nombre);

    await pulsar(filas(page).filter({ hasText: nombre }).getByRole('button', { name: 'Eliminar notebook' }));
    const respuesta = page.waitForResponse(esEliminacion);
    await pulsar(page.getByRole('dialog').getByRole('button', { name: 'Eliminar', exact: true }));
    expect((await respuesta).status()).toBe(200);

    await expect(page.getByRole('heading', { name: nombre })).toHaveCount(0);
    await expect(page.getByText('Elija o cree un notebook para empezar')).toBeVisible();
    await expect(avisosDeLaPantalla(page).filter({ hasText: 'Notebook eliminado.' })).toBeVisible();
    await expect(listaDeNotebooks(page)).toHaveCount(0);
  });

  // T6 · casos límite (spec 009, §9 diferibles).
  test('RF-17.86 · doble clic en Eliminar envía una sola solicitud', async ({ page, crearUsuario, control }) => {
    const { token } = await prepararUsuario(page, crearUsuario, control);
    const queda = `PRUEBA gestión queda ${aleatorio()}`;
    const sale = `PRUEBA gestión doble ${aleatorio()}`;
    await crearNotebook(control, token, queda);
    await crearNotebook(control, token, sale);
    await abrirNotebooks(page);
    const llamadas = [];
    page.on('request', (r) => { if (esRuta(r.url(), r.method(), 'DELETE')) llamadas.push(r.url()); });

    await pulsar(filas(page).filter({ hasText: sale }).getByRole('button', { name: 'Eliminar notebook' }));
    const respuesta = page.waitForResponse(esEliminacion);
    await page.getByRole('dialog').getByRole('button', { name: 'Eliminar', exact: true }).dblclick();
    expect((await respuesta).status()).toBe(200);
    await expect(listaDeNotebooks(page)).toHaveText([queda]);
    await expect(page.getByRole('dialog')).toHaveCount(0);
    expect(llamadas, 'RF-17.86 · una sola solicitud DELETE').toHaveLength(1);
  });

  test('RF-17.89 · eliminar con una respuesta en curso no la guarda', async ({ page, crearUsuario, control }) => {
    const { token } = await prepararUsuario(page, crearUsuario, control);
    const { notebook, documento } = await notebookConDocumento(control, token);
    // La señal de vida de 1 s hace que el servidor note la desconexión de una respuesta retenida en un segundo.
    await control.chat({ senal_de_vida_segundos: 1 });
    await control.motor({ modo: 'texto', texto: 'PRUEBA parcial uno dos tres', retener_tras: 2 });
    await abrirNotebookConDocumentos(page, notebook, [documento.nombre]);

    const campo = page.getByPlaceholder(`Pregúntele algo a "${notebook.nombre}"...`, { exact: false });
    await escribir(campo, '¿Qué dice el documento de PRUEBA?');
    await campo.press('Enter');
    const burbujas = page.locator('div.space-y-4 > div');
    await expect(burbujas.nth(1)).toContainText('PRUEBA parcial');
    await expect(burbujas.nth(1)).not.toContainText('tres');

    await pulsar(filas(page).filter({ hasText: notebook.nombre }).getByRole('button', { name: 'Eliminar notebook' }));
    const respuesta = page.waitForResponse(esEliminacion);
    await pulsar(page.getByRole('dialog').getByRole('button', { name: 'Eliminar', exact: true }));
    expect((await respuesta).status()).toBe(200);
    await expect(page.getByText('Elija o cree un notebook para empezar')).toBeVisible();
    await expect.poll(async () => (await control.chatEstado()).abandonados, { message: 'el servidor registra el abandono' }).toBe(1);

    // Liberada la respuesta, nada de ella vuelve a la pantalla ni se guarda en el navegador.
    await control.motorLiberar();
    const guardado = () => page.evaluate((id) => Object.keys(sessionStorage).filter((k) => k.endsWith(`_${id}`)), notebook.id);
    await expect.poll(guardado, { message: 'RF-17.89 · no queda conversación guardada' }).toEqual([]);
    await expect(burbujas).toHaveCount(0);
    await expect(page.getByRole('heading', { name: notebook.nombre })).toHaveCount(0);
    await expect(listaDeNotebooks(page)).toHaveCount(0);
  });

  test('RF-17.92 · notebook eliminado en otra pestaña', async ({ page, otraPestana, crearUsuario, control, consola }) => {
    consola.provocado(/404/); // el 404 uniforme que provoca la prueba
    const { token } = await prepararUsuario(page, crearUsuario, control);
    const aRenombrar = `PRUEBA gestión renombrar ${aleatorio()}`;
    const aEliminar = `PRUEBA gestión eliminar ${aleatorio()}`;
    const queda = `PRUEBA gestión queda ${aleatorio()}`;
    await crearNotebook(control, token, queda);
    await crearNotebook(control, token, aEliminar);
    await crearNotebook(control, token, aRenombrar);
    await abrirNotebooks(page); // la lista de esta pestaña queda con los tres

    // En la otra pestaña (misma sesión) se eliminan dos.
    await abrirNotebooks(otraPestana);
    for (const nombre of [aRenombrar, aEliminar]) {
      await pulsar(filas(otraPestana).filter({ hasText: nombre }).getByRole('button', { name: 'Eliminar notebook' }));
      const respuesta = otraPestana.waitForResponse(esEliminacion);
      await pulsar(otraPestana.getByRole('dialog').getByRole('button', { name: 'Eliminar', exact: true }));
      expect((await respuesta).status()).toBe(200);
    }
    await expect(listaDeNotebooks(otraPestana)).toHaveText([queda]);
    await page.bringToFront();
    await expect(listaDeNotebooks(page)).toHaveText([aRenombrar, aEliminar, queda]); // la lista antigua no cambió sola

    // Renombrar el ya eliminado: 404 uniforme, aviso y la fila se quita.
    await empezarRenombrar(page, aRenombrar);
    await campoDeNombre(page).fill('PRUEBA gestión nombre nuevo');
    const respuestaRenombrar = page.waitForResponse(esRenombrado);
    await campoDeNombre(page).press('Enter');
    expect((await respuestaRenombrar).status()).toBe(404);
    await expect(avisosDeLaPantalla(page).filter({ hasText: 'El notebook ya no está disponible.' })).toBeVisible();
    await expect(listaDeNotebooks(page)).toHaveText([aEliminar, queda]);
    await exigirSinVoseo(page);

    // Eliminar el otro ya eliminado: 404 uniforme, aviso y la fila se quita.
    await pulsar(filas(page).filter({ hasText: aEliminar }).getByRole('button', { name: 'Eliminar notebook' }));
    const respuestaEliminar = page.waitForResponse(esEliminacion);
    await pulsar(page.getByRole('dialog').getByRole('button', { name: 'Eliminar', exact: true }));
    expect((await respuestaEliminar).status()).toBe(404);
    await expect(listaDeNotebooks(page)).toHaveText([queda]);
  });

  test('RNF-04.80 · un nombre de 150 caracteres no desborda la lista', async ({ page, crearUsuario, control }) => {
    const { token } = await prepararUsuario(page, crearUsuario, control);
    const nombre = `PRUEBA${'A'.repeat(144)}`; // 150 caracteres sin espacios: el peor caso para el desborde
    expect(nombre).toHaveLength(150);
    await crearNotebook(control, token, nombre);
    await abrirNotebooks(page);
    await expect(filas(page)).toHaveCount(1);

    // La lista es el padre de las filas (en escritorio hay otros contenedores con las mismas clases).
    const medir = () => filas(page).first().evaluate((fila) => {
      const lista = fila.parentElement;
      const caja = lista.getBoundingClientRect();
      const botones = [...lista.querySelectorAll('button')].map((b) => b.getBoundingClientRect());
      return {
        desborde: lista.scrollWidth - lista.clientWidth,
        botones: botones.length,
        fuera: botones.filter((b) => b.right > caja.right + 0.5 || b.left < caja.left - 0.5 || b.width === 0).length,
      };
    });
    // La lista se vuelve a pintar al terminar de cargar: se mide cuando la fila ya es estable.
    await expect.poll(async () => (await medir().catch(() => null))?.botones).toBe(3);
    const reposo = await medir();
    expect(reposo.desborde, 'la lista no se desplaza a los lados').toBeLessThanOrEqual(0);
    expect(reposo.botones, 'nombre, Renombrar y Eliminar').toBe(3);
    expect(reposo.fuera, 'Renombrar y Eliminar quedan dentro de la lista').toBe(0);

    // También con el campo de edición abierto.
    await empezarRenombrar(page, 'PRUEBA');
    await expect(page.getByRole('button', { name: 'Guardar', exact: true })).toBeVisible();
    expect((await medir()).desborde).toBeLessThanOrEqual(0);
  });
});
