// Estudio del notebook (spec 010): el panel de tres paneles (RF-17.120, RF-17.121, RNF-04.120), generar un Resumen y un Mapa
// mental con las fuentes marcadas (RF-11.120, RF-11.122, RF-14.120, RF-14.121), quitarlos (RF-14.124) y guardar una respuesta
// del chat como nota (RF-14.126, RF-14.127). Corre en `escritorio` (1366) y `pequena` (616). Datos inventados (prefijo
// PRUEBA); motor simulado.
const { test, expect, iniciarSesion, pulsar } = require('../soporte/fixtures.js');
const { iniciarSesion: iniciarSesionPorApi, notebookConDocumento } = require('../soporte/datos.js');
const { abrirNotebookConDocumentos, irAlPanel, abrirNotebooks, listaDeNotebooks, abrirNotebookDeLaLista } = require('../soporte/pantallas.js');

const MAPA = '{"titulo": "Quebrada ficticia", "ramas": [{"titulo": "Laguna", "ramas": [{"titulo": "Patos azules", "ramas": []}]}, {"titulo": "Caudal", "ramas": []}]}';

// Un notebook con una fuente procesada, abierto en pantalla (con la pestaña «Estudio» a la vista si la pantalla es pequeña).
async function prepararNotebook(page, crearUsuario, control) {
  const usuario = await crearUsuario('usuario');
  await iniciarSesion(page, usuario.correo, usuario.contrasena);
  const token = await iniciarSesionPorApi(control, usuario);
  const a = await notebookConDocumento(control, token);
  await abrirNotebookConDocumentos(page, a.notebook, [a.documento.nombre]);
  return { notebook: a.notebook, documento: a.documento };
}

const listaDeResultados = (page) => page.getByRole('list', { name: 'Resultados guardados' });

test.describe('Estudio del notebook', () => {
  test('RF-17.120 · RNF-04.120 · tres paneles a 1366 px y pestañas a 616 px', async ({ page, crearUsuario, control }) => {
    await prepararNotebook(page, crearUsuario, control);
    const pestanas = page.getByRole('tablist', { name: 'Paneles del notebook' });
    if (page.viewportSize().width >= 1024) {
      await expect(pestanas).toBeHidden();
      await expect(page.getByRole('complementary', { name: 'Fuentes' })).toBeVisible();
      await expect(page.getByRole('region', { name: 'Chat' })).toBeVisible();
      await expect(page.getByRole('complementary', { name: 'Panel Estudio' })).toBeVisible();
    } else {
      await expect(pestanas.getByRole('tab')).toHaveText([/Fuentes/, /Chat/, /Estudio/]);
      await expect(page.getByRole('button', { name: 'Subir documentos' })).toBeVisible();
      await expect(page.getByRole('region', { name: 'Estudio' })).toBeHidden();
      await irAlPanel(page, 'Estudio');
      await expect(page.getByRole('region', { name: 'Estudio' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Subir documentos' })).toBeHidden();
    }
    await irAlPanel(page, 'Estudio');
    await expect(page.getByText('Todavía no hay resultados. Genere uno con las fuentes marcadas.')).toBeVisible();
    for (const nombre of ['Resumen', 'Informe', 'Mapa mental']) {
      await expect(page.getByRole('button', { name: nombre, exact: true })).toBeEnabled();
    }
  });

  test('RF-11.120 · RF-14.120 · RF-14.121 · RF-14.124 · generar un resumen, abrirlo tras recargar y quitarlo', async ({ page, crearUsuario, control }) => {
    const { notebook, documento } = await prepararNotebook(page, crearUsuario, control);
    await control.motor({ modo: 'texto', texto: `PRUEBA resumen generado según [${documento.nombre}] sobre la quebrada ficticia.` });
    await irAlPanel(page, 'Estudio');

    await pulsar(page.getByRole('button', { name: 'Resumen', exact: true }));
    // Al terminar, el resultado queda guardado, abierto y en la lista
    await expect(page.getByText('PRUEBA resumen generado según', { exact: false })).toBeVisible();
    await expect(page.getByText(documento.nombre).first()).toBeVisible(); // «Fuentes con que se generó»
    await pulsar(page.getByRole('button', { name: 'Volver a la lista' }));
    await expect(listaDeResultados(page).getByRole('listitem')).toHaveCount(1);
    await expect(listaDeResultados(page)).toContainText('Resumen · ');

    // Persiste: al recargar y abrir de nuevo el notebook, sigue en la lista y se abre sin llamar al modelo
    await abrirNotebookConDocumentos(page, notebook, [documento.nombre]);
    await irAlPanel(page, 'Estudio');
    await expect(listaDeResultados(page).getByRole('listitem')).toHaveCount(1);
    await pulsar(listaDeResultados(page).getByRole('button', { name: /^Abrir Resumen · / }));
    await expect(page.getByText('PRUEBA resumen generado según', { exact: false })).toBeVisible();
    await pulsar(page.getByRole('button', { name: 'Volver a la lista' }));

    // Quitar: confirmación, baja y la lista vuelve a quedar vacía
    await pulsar(listaDeResultados(page).getByRole('button', { name: /^Opciones de Resumen · / }));
    await pulsar(page.getByRole('menuitem', { name: 'Quitar resultado' }));
    await pulsar(page.getByRole('dialog').getByRole('button', { name: 'Quitar', exact: true }));
    await expect(page.getByText('Todavía no hay resultados. Genere uno con las fuentes marcadas.')).toBeVisible();
  });

  test('RF-11.122 · RF-14.121 · generar un mapa mental y verlo dibujado', async ({ page, crearUsuario, control }) => {
    await prepararNotebook(page, crearUsuario, control);
    await control.motor({ modo: 'texto', texto: MAPA });
    await irAlPanel(page, 'Estudio');

    await pulsar(page.getByRole('button', { name: 'Mapa mental', exact: true }));
    const mapa = page.getByRole('group', { name: 'Mapa mental: Quebrada ficticia' });
    await expect(mapa).toBeVisible();
    for (const idea of ['Quebrada ficticia', 'Laguna', 'Patos azules', 'Caudal']) {
      await expect(mapa.getByText(idea, { exact: true })).toBeVisible();
    }
    // El mapa no desplaza la página (RNF-04.121)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);

    // Pedido de Andrés (10/11/2026): las líneas salen del borde derecho de cada caja con hijos y llegan al borde izquierdo de cada
    // hija, en tramos rectos (horizontales y verticales). Uno de salida por caja con ramas (2) y uno de llegada por rama (3).
    await expect(mapa.locator('[data-conector="salida"]')).toHaveCount(2);
    await expect(mapa.locator('[data-conector="entrada"]')).toHaveCount(3);
    const desajustes = await mapa.evaluate((raiz) => {
      const problemas = [];
      const centro = (r) => r.top + r.height / 2;
      raiz.querySelectorAll('[data-conector="salida"]').forEach((c) => {
        const caja = c.previousElementSibling.getBoundingClientRect(); const l = c.getBoundingClientRect();
        if (Math.abs(l.left - caja.right) > 1.5 || Math.abs(centro(l) - centro(caja)) > 2) problemas.push('salida');
      });
      raiz.querySelectorAll('[data-conector="entrada"]').forEach((c) => {
        const caja = c.nextElementSibling.firstElementChild.getBoundingClientRect(); const l = c.getBoundingClientRect();
        if (Math.abs(l.right - caja.left) > 1.5 || Math.abs(centro(l) - centro(caja)) > 2) problemas.push('entrada');
      });
      return problemas;
    });
    expect(desajustes).toEqual([]);
  });

  test('RF-14.126 · RF-14.127 · RF-14.128 · guardar una respuesta del chat como nota', async ({ page, crearUsuario, control }) => {
    const { notebook } = await prepararNotebook(page, crearUsuario, control);
    await control.motor({ modo: 'texto', texto: 'PRUEBA respuesta simulada para guardar' });
    await irAlPanel(page, 'Chat');
    const campo = page.getByPlaceholder(`Pregúntele algo a "${notebook.nombre}"...`, { exact: false });
    await campo.fill('PRUEBA pregunta que se guarda');
    await campo.press('Enter');
    const guardar = page.getByRole('button', { name: 'Guardar en notas', exact: true });
    await expect(guardar).toBeVisible({ timeout: 30_000 });

    await pulsar(guardar);
    await expect(page.getByRole('button', { name: 'Guardada', exact: true })).toBeDisabled();

    await irAlPanel(page, 'Estudio');
    await expect(listaDeResultados(page).getByRole('listitem')).toHaveCount(1);
    await pulsar(listaDeResultados(page).getByRole('button', { name: /^Abrir Nota · / }));
    await expect(page.getByText('PRUEBA pregunta que se guarda')).toBeVisible();
    await expect(page.getByText('PRUEBA respuesta simulada para guardar')).toBeVisible();
  });

  // Pedido de Andrés (10/11/2026), sin requisito en el ERS todavía: a 1366 px los tres paneles laterales se pliegan para dar
  // todo el ancho al chat, y el plegado se recuerda al recargar.
  test('RNF-04 [NUEVO] · Notebooks: plegar la lista, las fuentes y el Estudio da el ancho al chat', async ({ page, crearUsuario, control }) => {
    test.skip(test.info().project.name === 'pequena', 'Solo en escritorio: a 616 px los paneles ya son pestañas');
    const { notebook, documento } = await prepararNotebook(page, crearUsuario, control);
    const chat = page.getByRole('region', { name: 'Chat' });
    const ancho = async () => (await chat.boundingBox()).width;
    const anchoInicial = await ancho();

    await pulsar(page.getByRole('button', { name: 'Plegar lista de notebooks' }));
    await pulsar(page.getByRole('button', { name: 'Plegar Fuentes' }));
    await pulsar(page.getByRole('button', { name: 'Plegar Estudio' }));
    await expect(page.getByRole('button', { name: 'Subir documentos' })).toBeHidden();
    await expect(page.getByRole('button', { name: 'Resumen', exact: true })).toBeHidden();
    await expect.poll(ancho).toBeGreaterThan(anchoInicial + 400);

    // El plegado se recuerda al recargar. La lista se despliega antes para elegir el notebook; las fuentes y el Estudio siguen
    // plegados y se vuelven a mostrar con su botón (el ayudante que abre el notebook espera las fuentes a la vista y aquí no sirve).
    await pulsar(page.getByRole('button', { name: 'Mostrar lista de notebooks' }));
    await abrirNotebooks(page);
    await pulsar(listaDeNotebooks(page).filter({ hasText: notebook.nombre }));
    await expect(page.getByRole('button', { name: 'Mostrar Fuentes' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Mostrar Estudio' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Subir documentos' })).toBeHidden();
    await pulsar(page.getByRole('button', { name: 'Mostrar Fuentes' }));
    await pulsar(page.getByRole('button', { name: 'Mostrar Estudio' }));
    await expect(page.getByRole('button', { name: 'Subir documentos' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Resumen', exact: true })).toBeVisible();
    await expect(page.getByText(documento.nombre).first()).toBeVisible();
    await expect.poll(ancho).toBeLessThan(anchoInicial + 5);
  });

  // ---- Ancho de las columnas (spec 010, cambio JJ1): RNF-04.124 a RNF-04.130 -----------------------------------------------
  const COLUMNAS = {
    lista: { nombre: 'Cambiar el ancho de la lista de notebooks', fabrica: 224, minimo: 180, maximo: 400 },
    fuentes: { nombre: 'Cambiar el ancho de Fuentes', fabrica: 240, minimo: 200, maximo: 480 },
    estudio: { nombre: 'Cambiar el ancho de Estudio', fabrica: 256, minimo: 220, maximo: 560 },
  };
  const CLAVE_ANCHOS = 'notebooks_anchos_columnas';
  const CHAT_MINIMO = 280; // RNF-04.125
  const columna = (page, id) => page.getByTestId(`columna-${id}`);
  const anchoDe = async (page, id) => Math.round((await columna(page, id).boundingBox()).width);
  const divisor = (page, id) => page.getByRole('separator', { name: COLUMNAS[id].nombre });
  const sinBarraHorizontalDeLaPagina = (page) => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);

  // Arrastra la línea `dx` px con el mouse (positivo = a la derecha), en varios pasos como lo haría una persona.
  async function arrastrar(page, id, dx) {
    const caja = await divisor(page, id).boundingBox();
    const x = caja.x + caja.width / 2;
    const y = caja.y + caja.height / 2;
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x + dx, y, { steps: 10 });
    await page.mouse.up();
  }

  test('RNF-04.124 · RNF-04.125 · arrastrar cada línea cambia el ancho de su columna y el chat toma el resto', async ({ page, crearUsuario, control }) => {
    test.skip(test.info().project.name === 'pequena', 'Solo en escritorio: a 616 px no hay líneas divisorias');
    await prepararNotebook(page, crearUsuario, control);
    // De fábrica.
    for (const id of ['lista', 'fuentes', 'estudio']) expect(await anchoDe(page, id)).toBe(COLUMNAS[id].fabrica);
    const chat0 = await anchoDe(page, 'chat');
    const paso = Math.floor((chat0 - CHAT_MINIMO) / 3); // lo que sobra sobre el mínimo del chat, repartido en tres
    expect(paso).toBeGreaterThan(15);

    // La lista y Fuentes crecen hacia la derecha; el Estudio, hacia la izquierda (su línea está en su borde izquierdo).
    await arrastrar(page, 'lista', paso);
    expect(Math.abs((await anchoDe(page, 'lista')) - (COLUMNAS.lista.fabrica + paso))).toBeLessThanOrEqual(2);
    await arrastrar(page, 'fuentes', paso);
    expect(Math.abs((await anchoDe(page, 'fuentes')) - (COLUMNAS.fuentes.fabrica + paso))).toBeLessThanOrEqual(2);
    await arrastrar(page, 'estudio', -paso);
    expect(Math.abs((await anchoDe(page, 'estudio')) - (COLUMNAS.estudio.fabrica + paso))).toBeLessThanOrEqual(2);
    // El chat tomó lo que quedó: 3 pasos menos.
    expect(Math.abs((await anchoDe(page, 'chat')) - (chat0 - 3 * paso))).toBeLessThanOrEqual(4);
    expect(await sinBarraHorizontalDeLaPagina(page)).toBe(true);

    // Límites: hacia la izquierda se detiene en el mínimo; hacia la derecha, en el máximo o donde el chat conserva 360 px.
    await arrastrar(page, 'lista', -1000);
    expect(await anchoDe(page, 'lista')).toBe(COLUMNAS.lista.minimo);
    await arrastrar(page, 'fuentes', 2000);
    const fuentes = await anchoDe(page, 'fuentes');
    expect(fuentes).toBeLessThanOrEqual(COLUMNAS.fuentes.maximo);
    expect(await anchoDe(page, 'chat')).toBeGreaterThanOrEqual(CHAT_MINIMO - 2);
    if (fuentes < COLUMNAS.fuentes.maximo) expect(Math.abs((await anchoDe(page, 'chat')) - CHAT_MINIMO)).toBeLessThanOrEqual(3);
    expect(await sinBarraHorizontalDeLaPagina(page)).toBe(true);
  });

  test('RNF-04.126 · el ancho elegido se recuerda al recargar', async ({ page, crearUsuario, control }) => {
    test.skip(test.info().project.name === 'pequena', 'Solo en escritorio');
    const { notebook } = await prepararNotebook(page, crearUsuario, control);
    await arrastrar(page, 'lista', 25);
    await arrastrar(page, 'fuentes', 25);
    const antes = { lista: await anchoDe(page, 'lista'), fuentes: await anchoDe(page, 'fuentes') };

    await page.reload();
    await abrirNotebookDeLaLista(page, notebook.nombre);
    expect(await anchoDe(page, 'lista')).toBe(antes.lista);
    expect(await anchoDe(page, 'fuentes')).toBe(antes.fuentes);
    expect(await anchoDe(page, 'estudio')).toBe(COLUMNAS.estudio.fabrica); // la que no se tocó sigue de fábrica
  });

  test('RNF-04.126 · un valor dañado en el almacenamiento se corrige y la pantalla funciona sin errores', async ({ page, crearUsuario, control }) => {
    test.skip(test.info().project.name === 'pequena', 'Solo en escritorio');
    await page.addInitScript(([clave]) => {
      localStorage.setItem(clave, '{"lista":"ancho","fuentes":99999,"estudio":-5}');
    }, [CLAVE_ANCHOS]);
    await prepararNotebook(page, crearUsuario, control);

    // No numérico: de fábrica; fuera de límites: el más cercano. Con la pantalla de 1366 px el área no alcanza para guardar los tres
    // y dejar al chat su mínimo, así que lo que se muestra puede ser menor que lo guardado (RNF-04.129), nunca fuera de [mínimo, máximo].
    for (const id of ['lista', 'fuentes', 'estudio']) {
      const ancho = await anchoDe(page, id);
      expect(ancho).toBeGreaterThanOrEqual(COLUMNAS[id].minimo - 1);
      expect(ancho).toBeLessThanOrEqual(COLUMNAS[id].maximo);
    }
    expect(await anchoDe(page, 'lista')).toBeLessThanOrEqual(COLUMNAS.lista.fabrica);
    expect(await anchoDe(page, 'chat')).toBeGreaterThanOrEqual(CHAT_MINIMO - 2);
  });

  test('RNF-04.127 · doble clic en la línea devuelve la columna a su ancho de fábrica', async ({ page, crearUsuario, control }) => {
    test.skip(test.info().project.name === 'pequena', 'Solo en escritorio');
    await prepararNotebook(page, crearUsuario, control);
    await arrastrar(page, 'estudio', -60);
    expect(await anchoDe(page, 'estudio')).toBeGreaterThan(COLUMNAS.estudio.fabrica + 45);

    await divisor(page, 'estudio').dblclick();
    expect(await anchoDe(page, 'estudio')).toBe(COLUMNAS.estudio.fabrica);
  });

  test('RNF-04.128 · la línea se maneja con el teclado y es accesible', async ({ page, crearUsuario, control }) => {
    test.skip(test.info().project.name === 'pequena', 'Solo en escritorio');
    await prepararNotebook(page, crearUsuario, control);
    const linea = divisor(page, 'fuentes');
    await expect(linea).toHaveAttribute('aria-orientation', 'vertical');
    await expect(linea).toHaveAttribute('aria-valuemin', String(COLUMNAS.fuentes.minimo));
    await expect(linea).toHaveAttribute('aria-valuenow', String(COLUMNAS.fuentes.fabrica));

    await linea.focus();
    await page.keyboard.press('ArrowRight');
    expect(await anchoDe(page, 'fuentes')).toBe(COLUMNAS.fuentes.fabrica + 16);
    await page.keyboard.press('ArrowLeft');
    expect(await anchoDe(page, 'fuentes')).toBe(COLUMNAS.fuentes.fabrica);
    await page.keyboard.press('Shift+ArrowRight'); // paso mayor: 64 px (cabe en lo que sobra sobre el mínimo del chat)
    expect(await anchoDe(page, 'fuentes')).toBe(COLUMNAS.fuentes.fabrica + 64);
    await expect(linea).toHaveAttribute('aria-valuenow', String(COLUMNAS.fuentes.fabrica + 64));
    await page.keyboard.press('Home');
    expect(await anchoDe(page, 'fuentes')).toBe(COLUMNAS.fuentes.fabrica);
  });

  test('RNF-04.129 · una columna plegada no tiene línea y, al mostrarla, vuelve a su último ancho', async ({ page, crearUsuario, control }) => {
    test.skip(test.info().project.name === 'pequena', 'Solo en escritorio');
    await prepararNotebook(page, crearUsuario, control);
    await arrastrar(page, 'fuentes', 40);
    const elegido = await anchoDe(page, 'fuentes');

    await pulsar(page.getByRole('button', { name: 'Plegar Fuentes' }));
    await expect(divisor(page, 'fuentes')).toHaveCount(0);
    await pulsar(page.getByRole('button', { name: 'Mostrar Fuentes' }));
    await expect(divisor(page, 'fuentes')).toHaveCount(1);
    expect(await anchoDe(page, 'fuentes')).toBe(elegido);
  });

  test('RNF-04.129 · a 616 px no hay líneas divisorias y los anchos guardados no cambian la vista', async ({ page, crearUsuario, control }) => {
    test.skip(test.info().project.name !== 'pequena', 'Solo en pantalla pequeña');
    await page.addInitScript(([clave]) => {
      localStorage.setItem(clave, '{"lista":400,"fuentes":480,"estudio":560}');
    }, [CLAVE_ANCHOS]);
    await prepararNotebook(page, crearUsuario, control);

    await expect(page.getByRole('separator')).toHaveCount(0);
    expect(await sinBarraHorizontalDeLaPagina(page)).toBe(true);
  });
});
