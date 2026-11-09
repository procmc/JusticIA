// Fuentes del notebook (spec 009b). T2: el menú ⋮ de cada fuente (RF-19.100). T3: la casilla y la selección enviada al chat
// (RF-11.100 a RF-11.106). El renombrado llega en la entrega 2. Corre en `escritorio` (1366) y `pequena` (616), salvo lo que
// diga la prueba. Datos inventados (prefijo PRUEBA); motor simulado.
const { test, expect, iniciarSesion, pulsar, escribir } = require('../soporte/fixtures.js');
const {
  iniciarSesion: iniciarSesionPorApi, notebookConDocumento, crearNotebook, subirYProcesar, listarDocumentos, documentoDePrueba, aleatorio, cargar, esperarTarea,
}= require('../soporte/datos.js');
const { fichaDeDocumento, abrirNotebookConDocumentos, abrirNotebookDeLaLista } = require('../soporte/pantallas.js');

// Selector CSS: con el menú ⋮ abierto el resto de la página queda oculto para los roles (como en `fichaDeDocumento`).
const casilla = (page, nombre) => page.locator(`ul[aria-label="Fuentes del notebook"] input[type="checkbox"][aria-label="Usar ${nombre} en el chat"]`);
// Se pulsa la etiqueta de la fila: el campo de la casilla de HeroUI está oculto visualmente.
const alternarCasilla = (page, nombre) => pulsar(fichaDeDocumento(page, nombre).locator('label'));
const rutaDelChat = (r) => r.method() === 'POST' && new URL(r.url()).pathname.endsWith('/rag/consulta-con-historial-stream');

// Un notebook con dos fuentes procesadas, abierto en pantalla, con el motor simulado respondiendo texto.
async function prepararConDosFuentes(page, crearUsuario, control) {
  const usuario = await crearUsuario('usuario');
  await iniciarSesion(page, usuario.correo, usuario.contrasena);
  const token = await iniciarSesionPorApi(control, usuario);
  const a = await notebookConDocumento(control, token);
  const otro = documentoDePrueba();
  await subirYProcesar(control, token, a.notebook.clave_interna, otro);
  const filas = await listarDocumentos(control, token, a.notebook);
  const idB = filas.find((d) => d.nombre_archivo === otro.nombre).id;
  await control.motor({ modo: 'texto', texto: 'PRUEBA respuesta simulada' });
  await abrirNotebookConDocumentos(page, a.notebook, [a.documento.nombre, otro.nombre]);
  const campo = page.getByPlaceholder(`Pregúntele algo a "${a.notebook.nombre}"...`, { exact: false });
  const enviar = page.getByRole('button', { name: 'Enviar', exact: true });
  return { usuario, token, notebook: a.notebook, docA: { ...a.documento, id: a.id }, docB: { ...otro, id: idB }, campo, enviar };
}

// Envía una pregunta con Enter y devuelve los `documentos` del cuerpo del pedido (undefined si no viajó el campo).
async function preguntarYLeerSeleccion(page, campo, enviar, pregunta) {
  const pedido = page.waitForRequest(rutaDelChat);
  await escribir(campo, pregunta);
  await campo.press('Enter');
  const cuerpo = JSON.parse((await pedido).postData());
  await expect(enviar).toBeEnabled({ timeout: 30_000 }); // la respuesta terminó
  return cuerpo.documentos;
}

test.describe('Fuentes del notebook', () => {
  test('RF-11.100 · RF-11.102 · casilla marcada y selección enviada', async ({ page, crearUsuario, control }) => {
    const { docA, docB, campo, enviar } = await prepararConDosFuentes(page, crearUsuario, control);
    // Cada fuente trae su casilla, marcada al cargarla (RF-11.100).
    await expect(casilla(page, docA.nombre)).toBeChecked();
    await expect(casilla(page, docB.nombre)).toBeChecked();
    expect((await preguntarYLeerSeleccion(page, campo, enviar, 'PRUEBA primera')).sort()).toEqual([docA.id, docB.id].sort());

    // Desmarcar una aplica a la siguiente pregunta (RF-11.102).
    await alternarCasilla(page, docB.nombre);
    await expect(casilla(page, docB.nombre)).not.toBeChecked();
    expect(await preguntarYLeerSeleccion(page, campo, enviar, 'PRUEBA segunda')).toEqual([docA.id]);

    // Volver a marcarla la devuelve a la selección.
    await alternarCasilla(page, docB.nombre);
    await expect(casilla(page, docB.nombre)).toBeChecked();
    expect((await preguntarYLeerSeleccion(page, campo, enviar, 'PRUEBA tercera')).sort()).toEqual([docA.id, docB.id].sort());
  });

  test('RF-11.104 · RF-11.106 · sin fuentes Procesado marcadas no se envía', async ({ page, crearUsuario, control }) => {
    const { docA, docB, campo, enviar } = await prepararConDosFuentes(page, crearUsuario, control);
    const aviso = page.getByText('Marque al menos una fuente para consultar.', { exact: true });
    await expect(aviso).toHaveCount(0);

    await alternarCasilla(page, docA.nombre);
    await expect(aviso).toHaveCount(0); // queda una marcada
    await alternarCasilla(page, docB.nombre);
    await expect(aviso).toBeVisible();
    await expect(enviar).toBeDisabled();

    // Enter tampoco envía y el texto escrito se conserva.
    const pedidos = [];
    page.on('request', (r) => { if (rutaDelChat(r)) pedidos.push(r.url()); });
    await escribir(campo, 'PRUEBA sin fuentes');
    await campo.press('Enter');
    await expect(campo).toHaveValue('PRUEBA sin fuentes');
    expect(pedidos).toEqual([]);

    // Marcar una fuente Procesado vuelve a habilitar el envío y quita el aviso.
    await alternarCasilla(page, docA.nombre);
    await expect(aviso).toHaveCount(0);
    await expect(enviar).toBeEnabled();
  });

  test('RF-11.103 · al volver al notebook todas marcadas', async ({ page, crearUsuario, control }) => {
    const usuario = await crearUsuario('usuario');
    await iniciarSesion(page, usuario.correo, usuario.contrasena);
    const token = await iniciarSesionPorApi(control, usuario);
    const { notebook, documento } = await notebookConDocumento(control, token);
    const otro = await crearNotebook(control, token);
    await abrirNotebookConDocumentos(page, notebook, [documento.nombre]);

    await alternarCasilla(page, documento.nombre);
    await expect(casilla(page, documento.nombre)).not.toBeChecked();

    // Cambiar de notebook y volver (la lista lateral solo se alcanza en escritorio: RNF-04.60).
    if (test.info().project.name !== 'pequena') {
      await abrirNotebookDeLaLista(page, otro.nombre);
      await expect(fichaDeDocumento(page, documento.nombre)).toHaveCount(0);
      await abrirNotebookDeLaLista(page, notebook.nombre);
      await expect(fichaDeDocumento(page, documento.nombre)).toHaveCount(1);
      await expect(casilla(page, documento.nombre)).toBeChecked();
    }

    // Recargar la página tampoco guarda la selección (solo vive en la página abierta).
    await alternarCasilla(page, documento.nombre);
    await page.reload();
    await abrirNotebookConDocumentos(page, notebook, [documento.nombre]);
    await expect(casilla(page, documento.nombre)).toBeChecked();
  });

  test('RNF-04.100 · nombre de 150 sin desborde', async ({ page, crearUsuario, control }) => {
    test.skip(test.info().project.name !== 'pequena', 'Solo se mide a 616 px (presupuesto de la suite)');
    const usuario = await crearUsuario('usuario');
    await iniciarSesion(page, usuario.correo, usuario.contrasena);
    const token = await iniciarSesionPorApi(control, usuario);
    const largo = documentoDePrueba();
    const sufijo = aleatorio();
    largo.nombre = `PRUEBA_${'n'.repeat(150 - 'PRUEBA_'.length - 1 - String(sufijo).length - '.txt'.length)}_${sufijo}.txt`;
    expect(largo.nombre.length).toBe(150);
    const notebook = await crearNotebook(control, token);
    await subirYProcesar(control, token, notebook.clave_interna, largo);
    await abrirNotebookConDocumentos(page, notebook, [largo.nombre]);

    const medidas = await page.evaluate(() => {
      const lista = document.querySelector('ul[aria-label="Fuentes del notebook"]');
      const fila = lista.querySelector('li');
      const caja = (e) => e.getBoundingClientRect();
      const etiqueta = fila.querySelector('label');
      const opciones = fila.querySelector('button[aria-label^="Opciones de"]');
      return {
        desborde: lista.scrollWidth - lista.clientWidth,
        filaDerecha: caja(fila).right, filaIzquierda: caja(fila).left,
        casilla: [caja(etiqueta).left, caja(etiqueta).right], opciones: [caja(opciones).left, caja(opciones).right],
        ventana: window.innerWidth,
      };
    });
    expect(medidas.desborde).toBeLessThanOrEqual(0);
    expect(medidas.casilla[0]).toBeGreaterThanOrEqual(medidas.filaIzquierda);
    expect(medidas.opciones[1]).toBeLessThanOrEqual(medidas.filaDerecha + 0.5);
    expect(medidas.opciones[1]).toBeLessThanOrEqual(medidas.ventana);
    // Ni la casilla ni el ⋮ quedan tapados: se pueden pulsar.
    await alternarCasilla(page, largo.nombre);
    await expect(casilla(page, largo.nombre)).not.toBeChecked();
    await pulsar(page.getByRole('button', { name: `Opciones de ${largo.nombre}`, exact: true }));
    await expect(page.getByRole('menuitem', { name: 'Quitar fuente' })).toBeVisible();
  });

  test('RF-19.100 · el menú no abre la vista previa ni cambia la casilla', async ({ page, crearUsuario, control }) => {
    const usuario = await crearUsuario('usuario');
    await iniciarSesion(page, usuario.correo, usuario.contrasena);
    const token = await iniciarSesionPorApi(control, usuario);
    const { notebook, documento } = await notebookConDocumento(control, token);
    await abrirNotebookConDocumentos(page, notebook, [documento.nombre]);

    // El propio menú es un «dialog» de HeroUI: la vista previa se reconoce por su encabezado (banner) con el nombre.
    const vistaPrevia = page.getByRole('dialog').getByRole('banner').filter({ hasText: documento.nombre });
    const pedidos = [];
    page.on('request', (r) => { if (/\/documentos\/\d+\/archivo$/.test(new URL(r.url()).pathname)) pedidos.push(r.url()); });

    // La fuente es un elemento de la lista «Fuentes del notebook» con su botón de opciones (texto accesible con el nombre).
    const lista = page.getByRole('list', { name: 'Fuentes del notebook' });
    await expect(lista.getByRole('listitem')).toHaveCount(1);
    const opciones = lista.getByRole('button', { name: `Opciones de ${documento.nombre}` });
    await expect(opciones).toHaveCount(1);
    await expect(fichaDeDocumento(page, documento.nombre).locator('[aria-label="close chip"]')).toHaveCount(0); // ya no hay «x»

    // Abrir el menú ofrece «Quitar fuente» y no abre la vista previa ni pide el archivo.
    await pulsar(opciones);
    await expect(page.getByRole('menuitem', { name: 'Quitar fuente' })).toBeVisible();
    await expect(vistaPrevia).toHaveCount(0);
    expect(pedidos).toEqual([]);
    await expect(casilla(page, documento.nombre)).toBeChecked(); // abrir el menú no cambia la casilla

    // Cerrar el menú sin elegir nada deja la fuente como estaba.
    await page.keyboard.press('Escape');
    await expect(page.getByRole('menuitem', { name: 'Quitar fuente' })).toHaveCount(0);
    await expect(vistaPrevia).toHaveCount(0);
    await expect(fichaDeDocumento(page, documento.nombre)).toHaveCount(1);
    expect(pedidos).toEqual([]);

    // Elegir «Quitar fuente» abre la confirmación existente, no la vista previa.
    await pulsar(opciones);
    await pulsar(page.getByRole('menuitem', { name: 'Quitar fuente' }));
    const dialogo = page.getByRole('dialog').filter({ hasText: 'Quitar documento' });
    await expect(dialogo.getByRole('heading', { name: 'Quitar documento', exact: true })).toBeVisible();
    await expect(vistaPrevia).toHaveCount(0);
    expect(pedidos).toEqual([]);
    await expect(casilla(page, documento.nombre)).toBeChecked(); // elegir «Quitar fuente» tampoco
    await pulsar(dialogo.getByRole('button', { name: 'Cancelar', exact: true }));
    await expect(dialogo).toHaveCount(0);
    await expect(fichaDeDocumento(page, documento.nombre)).toHaveCount(1);
  });

  // Entrega 2 (T7): cambiar el nombre de la fuente. Solo a 1366 px (presupuesto de la suite); el ancho pequeño lo cubre la
  // verificación manual de la entrega 2.
  const soloEscritorio = () => test.skip(test.info().project.name === 'pequena', 'Solo en escritorio (presupuesto de la suite)');
  const OPCION = 'Cambiar el nombre de la fuente';
  const campoDelNombre = (page) => page.getByRole('textbox', { name: 'Nuevo nombre de la fuente' });
  const abrirEdicion = async (page, nombre) => {
    await pulsar(page.getByRole('button', { name: `Opciones de ${nombre}`, exact: true }));
    await pulsar(page.getByRole('menuitem', { name: OPCION }));
    await expect(campoDelNombre(page)).toBeVisible();
  };

  test('RF-19.102 · RF-19.103 · renombrar, cancelar y Escape', async ({ page, crearUsuario, control }) => {
    soloEscritorio();
    const usuario = await crearUsuario('usuario');
    await iniciarSesion(page, usuario.correo, usuario.contrasena);
    const token = await iniciarSesionPorApi(control, usuario);
    const { notebook, documento } = await notebookConDocumento(control, token);
    await abrirNotebookConDocumentos(page, notebook, [documento.nombre]);
    const base = documento.nombre.replace(/\.txt$/, '');
    const nuevo = `PRUEBA renombrada ${aleatorio()}`;

    // El campo trae solo la base; la extensión va fija a su lado y no se edita (RF-19.102).
    await abrirEdicion(page, documento.nombre);
    await expect(campoDelNombre(page)).toHaveValue(base);
    await expect(fichaDeDocumento(page, '.txt').getByText('.txt', { exact: true })).toBeVisible();

    // Cancelar con el botón y con Escape deja el nombre como estaba y no llama al servidor.
    const llamadas = [];
    page.on('request', (r) => { if (r.method() === 'PUT' && /\/documentos\/\d+$/.test(new URL(r.url()).pathname)) llamadas.push(r.url()); });
    await escribir(campoDelNombre(page), 'PRUEBA descartado');
    await pulsar(page.getByRole('button', { name: 'Cancelar', exact: true }));
    await expect(campoDelNombre(page)).toHaveCount(0);
    await expect(fichaDeDocumento(page, documento.nombre)).toHaveCount(1);
    await abrirEdicion(page, documento.nombre);
    await escribir(campoDelNombre(page), 'PRUEBA descartado');
    await campoDelNombre(page).press('Escape');
    await expect(campoDelNombre(page)).toHaveCount(0);
    await expect(fichaDeDocumento(page, documento.nombre)).toHaveCount(1);
    expect(llamadas).toEqual([]);

    // Guardar con Enter: la lista muestra el nombre nuevo con la misma extensión (RF-19.102) y el servidor lo guarda.
    await abrirEdicion(page, documento.nombre);
    await escribir(campoDelNombre(page), nuevo);
    await campoDelNombre(page).press('Enter');
    await expect(campoDelNombre(page)).toHaveCount(0);
    await expect(fichaDeDocumento(page, `${nuevo}.txt`)).toHaveCount(1);
    await expect(fichaDeDocumento(page, documento.nombre)).toHaveCount(0);
    expect(llamadas).toHaveLength(1);
    expect((await listarDocumentos(control, token, notebook)).map((d) => d.nombre_archivo)).toEqual([`${nuevo}.txt`]);

    // La vista previa lleva el nombre nuevo (RF-19.103).
    await pulsar(fichaDeDocumento(page, `${nuevo}.txt`).getByRole('button', { name: `${nuevo}.txt`, exact: true }));
    await expect(page.getByRole('dialog').getByRole('banner')).toHaveText(`${nuevo}.txt`);
    await page.keyboard.press('Escape');

    // El mismo nombre no es un error: se cierra sin cambios.
    await abrirEdicion(page, `${nuevo}.txt`);
    await campoDelNombre(page).press('Enter');
    await expect(campoDelNombre(page)).toHaveCount(0);
    await expect(fichaDeDocumento(page, `${nuevo}.txt`)).toHaveCount(1);
  });

  test('RF-19.102 · RF-19.106 · rechazos del servidor bajo el campo', async ({ page, crearUsuario, control, consola }) => {
    soloEscritorio();
    consola.provocado(/400/); // cada rechazo llega como 400 y el navegador lo registra
    const usuario = await crearUsuario('usuario');
    await iniciarSesion(page, usuario.correo, usuario.contrasena);
    const token = await iniciarSesionPorApi(control, usuario);
    const a = await notebookConDocumento(control, token);
    const otro = documentoDePrueba();
    await subirYProcesar(control, token, a.notebook.clave_interna, otro);
    await abrirNotebookConDocumentos(page, a.notebook, [a.documento.nombre, otro.nombre]);
    const baseA = a.documento.nombre.replace(/\.txt$/, '');

    await abrirEdicion(page, otro.nombre);
    // Vacío: se envía igual y el mensaje es del servidor, sin punto final.
    await escribir(campoDelNombre(page), '   ');
    await campoDelNombre(page).press('Enter');
    await expect(page.getByText('El nombre de la fuente no puede estar vacío', { exact: true })).toBeVisible();
    // Duplicado sin distinguir mayúsculas de otra fuente del notebook.
    await escribir(campoDelNombre(page), baseA.toUpperCase());
    await campoDelNombre(page).press('Enter');
    await expect(page.getByText('Ya hay una fuente con ese nombre en este notebook.', { exact: true })).toBeVisible();
    // Demasiado largo: la base de 151 caracteres.
    await escribir(campoDelNombre(page), 'n'.repeat(151));
    await campoDelNombre(page).press('Enter');
    await expect(page.getByText('El nombre no puede superar 150 caracteres.', { exact: true })).toBeVisible();
    // Sigue en edición con lo escrito, y ninguna fuente cambió.
    await expect(campoDelNombre(page)).toHaveValue('n'.repeat(151));
    expect((await listarDocumentos(control, token, a.notebook)).map((d) => d.nombre_archivo).sort())
      .toEqual([a.documento.nombre, otro.nombre].sort());
    await campoDelNombre(page).press('Escape');
    await expect(campoDelNombre(page)).toHaveCount(0);
  });

  test('RF-19.107 · en proceso desactivado, en Error permitido', async ({ page, crearUsuario, control }) => {
    soloEscritorio();
    const usuario = await crearUsuario('usuario');
    await iniciarSesion(page, usuario.correo, usuario.contrasena);
    const token = await iniciarSesionPorApi(control, usuario);
    const notebook = await crearNotebook(control, token);
    const malo = documentoDePrueba();
    const pendiente = documentoDePrueba();
    await control.ingesta({ etapa: 'vectorizacion', fallar: [malo.nombre] });
    await esperarTarea(control, token, (await cargar(control, token, notebook.clave_interna, [malo]))[0], 'fallido');
    await control.ingesta({ etapa: 'vectorizacion', retener: [pendiente.nombre] });
    await cargar(control, token, notebook.clave_interna, [pendiente]);
    await expect.poll(async () => (await control.ingestaEstado()).esperando, { timeout: 15_000 }).toBe(1);
    await abrirNotebookConDocumentos(page, notebook, [malo.nombre, pendiente.nombre]);

    // Pendiente: la opción se ve desactivada con su explicación y no abre la edición.
    await pulsar(page.getByRole('button', { name: `Opciones de ${pendiente.nombre}`, exact: true }));
    const opcion = page.getByRole('menuitem', { name: OPCION });
    await expect(opcion).toHaveAttribute('aria-disabled', 'true');
    await expect(opcion).toContainText('Espere a que termine de procesarse.');
    await opcion.click({ force: true });
    await expect(campoDelNombre(page)).toHaveCount(0);
    await page.keyboard.press('Escape');

    // Error: sí se puede cambiar el nombre.
    const nuevo = `PRUEBA error ${aleatorio()}`;
    await abrirEdicion(page, malo.nombre);
    await escribir(campoDelNombre(page), nuevo);
    await campoDelNombre(page).press('Enter');
    await expect(fichaDeDocumento(page, `${nuevo}.txt`)).toHaveCount(1);
  });
});
