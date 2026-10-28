// NotebookServIA: crear y cargar (spec 005b, T4): RF-17.40 y RF-05.40 en un notebook propio. Spec retroactiva: sigue al ERS,
// no a lo que hoy hace el código. Corre en `escritorio` (1366) y `pequena` (616). Los datos son inventados (prefijo PRUEBA);
// el motor de lenguaje es el simulado de la instancia.
const { test, expect, iniciarSesion, pulsar, fallaEsperada } = require('../soporte/fixtures.js');
const {
  aleatorio, iniciarSesion: iniciarSesionPorApi, crearNotebook, listarDocumentos, cargaMixta, documentoDePrueba, pdfMinimo,
  PNG_MINIMO, cargar, esperarTarea, subirYProcesar, notebookConDocumento, preguntar, textoDeLosEventos,
} = require('../soporte/datos.js');
const {
  abrirNotebooks, crearNotebookEnPantalla, crearNotebookConEnter, listaDeNotebooks, abrirNotebookDeLaLista,
  elegirArchivosEnNotebook, confirmarSubidaEnNotebook, avisosDeLaPantalla, fichaDeDocumento, abrirNotebookConDocumentos,
  quitarDocumentoEnPantalla,
} = require('../soporte/pantallas.js');

const MOTIVO_VACIO = 'archivo vacío';
const MOTIVO_NOMBRE = 'nombre de archivo no válido';

const esCargaDeArchivos = (r) => r.url().endsWith('/ingesta/archivos') && r.request().method() === 'POST';
const esCreacion = (url, metodo) => new URL(url).pathname.replace(/\/$/, '').endsWith('/notebooks') && metodo === 'POST';
const esCreacionDeNotebook = (r) => esCreacion(r.url(), r.request().method());

async function iniciarComoUsuario(page, crearUsuario) {
  const usuario = await crearUsuario('usuario');
  await iniciarSesion(page, usuario.correo, usuario.contrasena);
  return usuario;
}

// Comprueba que el notebook recién creado quedó abierto: su título, «Subir documentos», su lista de documentos (vacía) y el chat.
async function exigirNotebookAbierto(page, nombre) {
  await expect(page.getByRole('heading', { name: nombre })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Subir documentos' })).toBeVisible();
  await expect(page.getByPlaceholder(`Preguntale algo a "${nombre}"...`, { exact: false })).toBeVisible();
  await expect(page.getByText('archivo(s) seleccionado(s)')).toHaveCount(0);
  await expect(page.locator('div.flex-wrap.gap-2 > div')).toHaveCount(0); // su lista de documentos, vacía
}

test.describe('NotebookServIA: crear y cargar', () => {
  test('RF-17.40 · crear con botón y con Enter', async ({ page, crearUsuario }) => {
    await iniciarComoUsuario(page, crearUsuario);
    await abrirNotebooks(page);
    const primero = `PRUEBA notebook botón ${aleatorio()}`;
    const segundo = `PRUEBA notebook enter ${aleatorio()}`;

    // Con el botón: aparece en la lista y se abre.
    const creado1 = page.waitForResponse(esCreacionDeNotebook);
    await crearNotebookEnPantalla(page, primero);
    expect((await creado1).status()).toBe(200);
    await expect(listaDeNotebooks(page)).toHaveCount(1);
    await expect(listaDeNotebooks(page).first()).toHaveText(primero);
    await exigirNotebookAbierto(page, primero);
    await expect(page.getByPlaceholder('Nombre del notebook')).toHaveValue(''); // el campo queda listo para otro

    // Con Enter: el nuevo aparece primero (antes que el anterior) y es el que queda abierto.
    const creado2 = page.waitForResponse(esCreacionDeNotebook);
    await crearNotebookConEnter(page, segundo);
    expect((await creado2).status()).toBe(200);
    await expect(listaDeNotebooks(page)).toHaveText([segundo, primero]);
    await exigirNotebookAbierto(page, segundo);

    // Y siguen ahí al volver a abrir la pantalla: se guardaron, no solo se dibujaron.
    await abrirNotebooks(page);
    await expect(listaDeNotebooks(page)).toHaveText([segundo, primero]);
  });

  test('RF-17.40 · nombre vacío', async ({ page, crearUsuario }) => {
    await iniciarComoUsuario(page, crearUsuario);
    await abrirNotebooks(page);
    await expect(page.getByText('Todavía no tenés notebooks')).toBeVisible();
    const peticiones = [];
    page.on('request', (r) => { if (esCreacion(r.url(), r.method())) peticiones.push(r.url()); });

    // Vacío y solo espacios, con el botón y con Enter: no se crea nada y la lista no cambia.
    const campo = page.getByPlaceholder('Nombre del notebook');
    for (const texto of ['', '   ']) {
      await campo.fill(texto);
      await page.getByRole('button', { name: 'Crear notebook' }).click();
      await campo.press('Enter');
    }
    await expect(page.getByText('Todavía no tenés notebooks')).toBeVisible();
    await expect(listaDeNotebooks(page)).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Subir documentos' })).toHaveCount(0); // no se abrió ninguno

    // Testigo: un nombre válido sí se crea, y es la única creación que llegó al sistema y el único notebook.
    const nombre = `PRUEBA notebook testigo ${aleatorio()}`;
    await crearNotebookEnPantalla(page, nombre);
    await expect(listaDeNotebooks(page)).toHaveText([nombre]);
    expect(peticiones).toHaveLength(1);
  });

  test('RF-17.40 · otro usuario no lo ve', async ({ page, crearUsuario, control, otroUsuario }) => {
    await iniciarComoUsuario(page, crearUsuario);
    await abrirNotebooks(page);
    const mio = `PRUEBA notebook propio ${aleatorio()}`;
    await crearNotebookEnPantalla(page, mio);

    // El otro usuario tiene el suyo: cuando se ve, la lista ya cargó y se puede afirmar que el ajeno no está.
    const tokenAjeno = await iniciarSesionPorApi(control, otroUsuario.usuario);
    const suyo = (await crearNotebook(control, tokenAjeno, `PRUEBA notebook ajeno ${aleatorio()}`)).nombre;
    await abrirNotebooks(otroUsuario.page);
    await expect(listaDeNotebooks(otroUsuario.page)).toHaveText([suyo]);
    await expect(otroUsuario.page.getByText(mio)).toHaveCount(0);

    // Y el primero sigue viendo solo el suyo.
    await abrirNotebooks(page);
    await expect(listaDeNotebooks(page)).toHaveText([mio]);
  });

  test('RF-05.40 · notebook: carga mixta', async ({ page, crearUsuario, control }) => {
    const usuario = await iniciarComoUsuario(page, crearUsuario);
    const token = await iniciarSesionPorApi(control, usuario);
    const notebook = await crearNotebook(control, token, `PRUEBA notebook carga ${aleatorio()}`);
    const { valido, vacio, largo } = cargaMixta();
    await abrirNotebooks(page);
    await abrirNotebookDeLaLista(page, notebook.nombre);
    // RF-10.50: la advertencia de manuscrito junto a «Subir documentos».
    await expect(page.getByText('Las imágenes deben contener texto impreso o tipeado: la escritura a mano no se reconoce de forma confiable.')).toBeVisible();
    await elegirArchivosEnNotebook(page, [valido, vacio, largo]);

    const respuestaEsperada = page.waitForResponse(esCargaDeArchivos);
    await confirmarSubidaEnNotebook(page, notebook.nombre);
    const cuerpo = await (await respuestaEsperada).json();

    // La API: un aceptado y dos rechazados con su motivo, y ningún nombre rechazado en lo que entrega el sistema (decisión 29).
    expect(cuerpo.aceptados.cantidad).toBe(1);
    expect(cuerpo.rechazados.archivos.map((r) => r.motivo)).toEqual([MOTIVO_VACIO, MOTIVO_NOMBRE]);
    expect(JSON.stringify(cuerpo)).not.toContain(largo.nombre);
    expect(JSON.stringify(cuerpo)).not.toContain(vacio.nombre);

    // El aviso: la confirmación cuenta solo al aceptado y cada rechazado muestra su motivo tal cual lo entregó la API.
    const aviso = avisosDeLaPantalla(page).filter({ hasText: `${notebook.nombre}:` });
    await expect(aviso).toBeVisible();
    await expect(aviso).toContainText('1 archivo enviado a procesamiento');
    await expect(aviso).not.toContainText(/3 archivos/);
    const motivos = aviso.locator('li');
    await expect(motivos).toHaveCount(2);
    await expect(motivos.nth(0)).toHaveText(`${vacio.nombre}: ${cuerpo.rechazados.archivos[0].motivo}`);
    await expect(motivos.nth(1)).toHaveText(new RegExp(`: ${cuerpo.rechazados.archivos[1].motivo}$`));

    // El aceptado llega a Procesado y se lista; los rechazados nunca aparecen como «procesando» ni se listan.
    await expect.poll(async () => (await listarDocumentos(control, token, notebook)).map((d) => [d.nombre_archivo, d.estado]), {
      timeout: 30_000, intervals: [100, 250, 500],
    }).toEqual([[valido.nombre, 'Procesado']]);
    await expect(page.getByText(valido.nombre)).toHaveCount(1);
    for (const rechazado of [vacio, largo]) {
      await expect(page.locator('body')).not.toContainText(`${rechazado.nombre} —`); // así se rotula una subida en curso
    }
    await expect(page.locator('body')).not.toContainText(/\d+%/);
  });
});

// ---------------------------------------------------------------------------------------------------------------------
// Previsualizar y quitar un documento (spec 005b, T5): RF-18.40, RF-19.40 a RF-19.42 y RNF-07.40.
// Los datos de base van por la API; la acción del requisito, por la pantalla.

const esArchivo = (r) => /\/notebooks\/\d+\/documentos\/\d+\/archivo$/.test(new URL(r.url()).pathname);
const esQuitar = (r) => r.request().method() === 'DELETE' && /\/notebooks\/\d+\/documentos\/\d+$/.test(new URL(r.url()).pathname);
const MENSAJE_FALLO_QUITAR = 'No se pudo quitar el documento. Intente de nuevo.';

// Deja pasar un par de fotogramas: para afirmar que algo NO ocurrió sin tiempos fijos (el estado ya se esperó antes).
const dejarPasarFotogramas = (page) => page.evaluate(() => new Promise((ok) => {
  requestAnimationFrame(() => requestAnimationFrame(ok));
}));

const estadoDelDocumento = async (control, token, notebook, documento) => (
  (await listarDocumentos(control, token, notebook)).find((d) => d.nombre_archivo === documento.nombre)?.estado
);

test.describe('NotebookServIA: previsualizar y quitar un documento', () => {
  test('RF-18.40 · vista previa de imagen y PDF', async ({ page, crearUsuario, control }) => {
    const usuario = await iniciarComoUsuario(page, crearUsuario);
    const token = await iniciarSesionPorApi(control, usuario);
    const sufijo = aleatorio();
    const imagen = { nombre: `PRUEBA_${sufijo}.png`, contenido: PNG_MINIMO, tipo: 'image/png' };
    const pdf = { nombre: `PRUEBA_${sufijo}.pdf`, contenido: pdfMinimo(`PRUEBA documento inventado ${sufijo}`), tipo: 'application/pdf' };
    const { notebook } = await notebookConDocumento(control, token, imagen);
    await subirYProcesar(control, token, notebook.clave_interna, pdf);
    await abrirNotebookConDocumentos(page, notebook, [imagen.nombre, pdf.nombre]);

    // Sin descargas ni pestañas nuevas: el contenido se muestra en línea.
    const descargas = [];
    page.on('download', (d) => descargas.push(d.suggestedFilename()));
    const dialogo = page.getByRole('dialog');

    for (const documento of [imagen, pdf]) {
      // Mientras se obtiene el archivo: «Abriendo…» sobre el documento y todavía ninguna ventana.
      await control.notebooks({ retener_vista_previa: true });
      await pulsar(fichaDeDocumento(page, documento.nombre));
      await expect(fichaDeDocumento(page, 'Abriendo…')).toHaveCount(1);
      await expect.poll(async () => (await control.notebooksEstado()).esperando_vista_previa, { timeout: 15_000 }).toBe(1);
      await expect(dialogo).toHaveCount(0);

      // Al llegar el archivo: una ventana con el nombre y el contenido en línea.
      await control.notebooksLiberar();
      await expect(dialogo).toBeVisible();
      await expect(dialogo.getByRole('banner')).toHaveText(documento.nombre);
      if (documento === imagen) {
        await expect(dialogo.locator('img')).toHaveAttribute('alt', documento.nombre);
        await expect.poll(() => dialogo.locator('img').evaluate((i) => i.complete && i.naturalWidth > 0)).toBe(true);
      } else {
        await expect(dialogo.locator('iframe')).toHaveAttribute('title', documento.nombre);
        await expect(dialogo.locator('iframe')).toHaveAttribute('src', /^blob:/);
      }
      await expect(fichaDeDocumento(page, documento.nombre)).toHaveCount(1); // «Abriendo…» ya terminó
      await page.keyboard.press('Escape');
      await expect(dialogo).toHaveCount(0);
    }
    expect(descargas).toEqual([]);
    expect(page.context().pages()).toHaveLength(1);
  });

  test('RF-18.40 · Pendiente y Error no se abren', async ({ page, crearUsuario, control }) => {
    const usuario = await iniciarComoUsuario(page, crearUsuario);
    const token = await iniciarSesionPorApi(control, usuario);
    const notebook = await crearNotebook(control, token, `PRUEBA notebook estados ${aleatorio()}`);
    const malo = documentoDePrueba();
    const pendiente = documentoDePrueba();

    // Un documento en Error (falla la vectorización, que ya lo registró) y otro Pendiente (retenido en esa etapa).
    await control.ingesta({ etapa: 'vectorizacion', fallar: [malo.nombre] });
    await esperarTarea(control, token, (await cargar(control, token, notebook.clave_interna, [malo]))[0], 'fallido');
    await control.ingesta({ etapa: 'vectorizacion', retener: [pendiente.nombre] });
    await cargar(control, token, notebook.clave_interna, [pendiente]);
    await expect.poll(async () => (await control.ingestaEstado()).esperando, { timeout: 15_000 }).toBe(1);
    expect(await estadoDelDocumento(control, token, notebook, malo)).toBe('Error');
    expect(await estadoDelDocumento(control, token, notebook, pendiente)).toBe('Pendiente');

    await abrirNotebookConDocumentos(page, notebook, [malo.nombre, pendiente.nombre]);
    const pedidos = [];
    page.on('request', (r) => { if (/\/documentos\/\d+\/archivo$/.test(new URL(r.url()).pathname)) pedidos.push(r.url()); });
    for (const documento of [malo, pendiente]) {
      await pulsar(fichaDeDocumento(page, documento.nombre));
      await dejarPasarFotogramas(page);
      await expect(fichaDeDocumento(page, 'Abriendo…')).toHaveCount(0);
      await expect(page.getByRole('dialog')).toHaveCount(0);
      await expect(fichaDeDocumento(page, documento.nombre)).toHaveCount(1);
    }
    expect(pedidos).toEqual([]); // ni siquiera se pidió el archivo
  });

  test('RF-18.40 · tipo sin vista previa', async ({ page, crearUsuario, control }) => {
    const usuario = await iniciarComoUsuario(page, crearUsuario);
    const token = await iniciarSesionPorApi(control, usuario);
    const { notebook, documento } = await notebookConDocumento(control, token);
    await abrirNotebookConDocumentos(page, notebook, [documento.nombre]);

    await pulsar(fichaDeDocumento(page, documento.nombre));
    const dialogo = page.getByRole('dialog');
    await expect(dialogo).toBeVisible();
    await expect(dialogo.getByRole('banner')).toHaveText(documento.nombre);
    await expect(dialogo).toContainText('Vista previa no disponible para este tipo de archivo.');
    await expect(dialogo.locator('img, iframe')).toHaveCount(0);
  });

  test('RF-19.40 · confirmación con nombre y advertencia; cancelar no cambia nada', async ({ page, crearUsuario, control }) => {
    // Hoy la «x» quita el documento sin pedir confirmar (visto en rojo: no aparece ningún cuadro). Estado actual del ERS (RF-19).
    fallaEsperada(test, 'RF-19.40 · notebooks');
    const usuario = await iniciarComoUsuario(page, crearUsuario);
    const token = await iniciarSesionPorApi(control, usuario);
    const { notebook, documento } = await notebookConDocumento(control, token);
    await abrirNotebookConDocumentos(page, notebook, [documento.nombre]);
    const borrados = [];
    page.on('request', (r) => { if (r.method() === 'DELETE') borrados.push(r.url()); });

    await pulsar(fichaDeDocumento(page, documento.nombre).locator('[aria-label="close chip"]'));
    const dialogo = page.getByRole('dialog');
    await expect(dialogo).toBeVisible();
    await expect(dialogo).toContainText(documento.nombre);
    await expect(dialogo).toContainText(/no (se )?puede(n)? deshacer/i);

    // Cancelar: el cuadro se cierra, el documento sigue en pantalla y en el sistema, y no salió ninguna petición de quitar.
    await pulsar(dialogo.getByRole('button', { name: /cancelar/i }));
    await expect(dialogo).toHaveCount(0);
    await dejarPasarFotogramas(page);
    await expect(fichaDeDocumento(page, documento.nombre)).toHaveCount(1);
    expect(borrados).toEqual([]);
    expect(await estadoDelDocumento(control, token, notebook, documento)).toBe('Procesado');
  });

  test('RF-19.41 · deshabilitado, luego fuera de la lista y del chat', async ({ page, crearUsuario, control }) => {
    const usuario = await iniciarComoUsuario(page, crearUsuario);
    const token = await iniciarSesionPorApi(control, usuario);
    const { notebook, documento } = await notebookConDocumento(control, token);
    const pregunta = `¿Qué dice el documento sobre ${documento.frase}?`;
    const citaEnElChat = async () => textoDeLosEventos(await preguntar(control, token, usuario, pregunta, { notebook: notebook.id }))
      .includes(documento.nombre);
    expect(await citaEnElChat()).toBe(true);
    await abrirNotebookConDocumentos(page, notebook, [documento.nombre]);

    // Mientras dura la operación (retenida): el documento sigue en la lista pero deshabilitado.
    await control.notebooks({ retener_quitar: true });
    await quitarDocumentoEnPantalla(page, documento.nombre);
    await expect.poll(async () => (await control.notebooksEstado()).esperando_quitar, { timeout: 15_000 }).toBe(1);
    const ficha = fichaDeDocumento(page, documento.nombre);
    await expect(ficha).toHaveCount(1);
    await expect.poll(() => ficha.evaluate((e) => (
      getComputedStyle(e).pointerEvents === 'none' || e.hasAttribute('data-disabled') || e.getAttribute('aria-disabled') === 'true'
    ))).toBe(true);

    // Al terminar: deja de listarse (en pantalla y en el sistema) y el chat del notebook ya no lo cita.
    const quitada = page.waitForResponse(esQuitar);
    await control.notebooksLiberar();
    expect((await quitada).status()).toBe(200);
    await expect(ficha).toHaveCount(0);
    expect(await listarDocumentos(control, token, notebook)).toEqual([]);
    expect(await citaEnElChat()).toBe(false);
  });

  test('RF-19.42 · fallo con aviso y reintento', async ({ page, crearUsuario, control, consola }) => {
    consola.provocado(/500/); // el fallo programado llega como 500 y el navegador lo registra
    const usuario = await iniciarComoUsuario(page, crearUsuario);
    const token = await iniciarSesionPorApi(control, usuario);
    const { notebook, documento } = await notebookConDocumento(control, token);
    await abrirNotebookConDocumentos(page, notebook, [documento.nombre]);

    await control.notebooks({ fallar_quitar: true });
    const fallida = page.waitForResponse(esQuitar);
    await quitarDocumentoEnPantalla(page, documento.nombre);
    expect((await fallida).status()).toBe(500);
    await expect(avisosDeLaPantalla(page).filter({ hasText: MENSAJE_FALLO_QUITAR })).toBeVisible();
    await expect(fichaDeDocumento(page, documento.nombre)).toHaveCount(1); // sigue listado y habilitado
    expect(await estadoDelDocumento(control, token, notebook, documento)).toBe('Procesado');

    // Un nuevo intento, sin el fallo, lo quita.
    await control.notebooks({});
    const quitada = page.waitForResponse(esQuitar);
    await quitarDocumentoEnPantalla(page, documento.nombre);
    expect((await quitada).status()).toBe(200);
    await expect(fichaDeDocumento(page, documento.nombre)).toHaveCount(0);
    expect(await listarDocumentos(control, token, notebook)).toEqual([]);
  });

  test('RNF-07.40 · documento quitado en otra pestaña: sesión y pantalla siguen', async ({
    page, otraPestana, crearUsuario, control, consola,
  }) => {
    consola.provocado(/404/);
    consola.provocado(/Error al obtener el archivo/); // el servicio de notebooks registra la vista previa fallida
    const usuario = await iniciarComoUsuario(page, crearUsuario);
    const token = await iniciarSesionPorApi(control, usuario);
    const { notebook, documento } = await notebookConDocumento(control, token);
    await abrirNotebookConDocumentos(page, notebook, [documento.nombre]);

    // En la otra pestaña (misma sesión) se quita el documento.
    await abrirNotebookConDocumentos(otraPestana, notebook, [documento.nombre]);
    await quitarDocumentoEnPantalla(otraPestana, documento.nombre);
    await expect(fichaDeDocumento(otraPestana, documento.nombre)).toHaveCount(0);

    // En la primera, que aún lo muestra: previsualizar y quitar reciben la respuesta uniforme de no disponible.
    const vistaPrevia = page.waitForResponse(esArchivo);
    await pulsar(fichaDeDocumento(page, documento.nombre));
    expect((await vistaPrevia).status()).toBe(404);
    await expect(fichaDeDocumento(page, 'Abriendo…')).toHaveCount(0);
    const quitada = page.waitForResponse(esQuitar);
    await quitarDocumentoEnPantalla(page, documento.nombre);
    expect((await quitada).status()).toBe(404);

    // La sesión sigue abierta y la pantalla es operable: se puede crear otro notebook y queda en la lista.
    expect(new URL(page.url()).pathname).toBe('/notebooks');
    const nuevo = `PRUEBA notebook después ${aleatorio()}`;
    await crearNotebookEnPantalla(page, nuevo);
    await expect(listaDeNotebooks(page).filter({ hasText: nuevo })).toHaveCount(1);
    await abrirNotebooks(page); // recargar sigue entrando: la sesión no se cerró
    await expect(listaDeNotebooks(page).filter({ hasText: nuevo })).toHaveCount(1);
  });
});
