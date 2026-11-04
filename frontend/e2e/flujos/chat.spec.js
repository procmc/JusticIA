// Señales del turno en la interfaz del chat (spec 007, T9): etapas, plazo con cualquier dato, errores y avisos.
// RF-11.64 (etapas), RF-11.67 (error y evento desconocido), RF-16.60 (señal de vida), RF-16.40 (servidor mudo),
// RF-16.62 (tope), RF-11.62 (pregunta larga), RF-16.61 (español neutro) y RNF-04.60 (matriz: 12 ejecuciones).
// General: escritorio (1366) y pantalla pequeña (616). Notebook: solo escritorio. El chat por tema usa la misma interfaz que
// el general (RNF-04.60). Los plazos de 30 s se recorren con el reloj controlado del navegador, nunca con esperas reales; el
// motor y el chat son los programables de la instancia (T8). Datos inventados (prefijo PRUEBA).
const { test, expect, iniciarSesion, escribir } = require('../soporte/fixtures.js');
const { iniciarSesion: iniciarSesionPorApi, notebookConDocumento } = require('../soporte/datos.js');
const { abrirChatGeneral, abrirNotebookConDocumentos } = require('../soporte/pantallas.js');

const ETAPAS = ['Procesando consulta', 'Analizando documentos', 'Generando respuesta'];
const AVISO_CONEXION = 'Se perdió la conexión con el servidor. Intente de nuevo.';
const AVISO_TOPE = 'La consulta tardó demasiado. Intente de nuevo.';
const AVISO_LARGA = 'La pregunta es demasiado larga. Acórtela e intente de nuevo.';
const PREGUNTA = '¿Qué dice el documento de PRUEBA?';
const RESPUESTA = 'PRUEBA respuesta completa del motor simulado';
const PREGUNTA_LARGA = 'palabra '.repeat(3750); // ~30.000 caracteres: no cabe en el presupuesto de entrada

const indicador = (page) => page.getByTestId('indicador-de-etapa');

async function iniciarComoUsuario(page, crearUsuario) {
  const usuario = await crearUsuario('usuario');
  await iniciarSesion(page, usuario.correo, usuario.contrasena);
  return usuario;
}

// Cada chat se maneja con lo mismo: enviar, y comprobar si el control de envío está bloqueado o libre.
async function prepararGeneral(page) {
  const campo = await abrirChatGeneral(page);
  const detener = page.getByRole('button', { name: 'Detener respuesta' });
  return {
    enviar: async (texto) => { await escribir(campo, texto); await campo.press('Enter'); },
    bloqueado: () => expect(detener).toHaveCount(1),
    libre: () => expect(detener).toHaveCount(0),
  };
}

async function prepararNotebook(page, control, usuario) {
  const token = await iniciarSesionPorApi(control, usuario);
  const { notebook, documento } = await notebookConDocumento(control, token);
  await abrirNotebookConDocumentos(page, notebook, [documento.nombre]);
  const campo = page.getByPlaceholder(`Pregúntele algo a "${notebook.nombre}"...`, { exact: false });
  const enviar = page.getByRole('button', { name: 'Enviar', exact: true });
  return {
    enviar: async (texto) => { await escribir(campo, texto); await campo.press('Enter'); },
    bloqueado: () => expect(enviar).toBeDisabled(),
    libre: () => expect(enviar).toBeEnabled(),
  };
}

// Anota, en orden y sin repetir, cada etapa que el indicador llega a mostrar (sin esperas: lo hace el propio navegador).
async function registrarEtapas(page) {
  await page.evaluate((etapas) => {
    window.__etapasVistas = [];
    const revisar = () => {
      const elemento = document.querySelector('[data-testid="indicador-de-etapa"]');
      if (!elemento) return;
      const etapa = etapas.find((e) => elemento.textContent.includes(e));
      const vistas = window.__etapasVistas;
      if (etapa && vistas[vistas.length - 1] !== etapa) vistas.push(etapa);
    };
    new MutationObserver(revisar).observe(document.body, { subtree: true, childList: true, characterData: true });
  }, ETAPAS);
}
const etapasVistas = (page) => page.evaluate(() => window.__etapasVistas);

// Deja pasar un par de fotogramas: lo que ya llegó a la página queda procesado antes de mover el reloj.
const dejarPasarFotogramas = (page) => page.evaluate(() => new Promise((ok) => {
  requestAnimationFrame(() => requestAnimationFrame(ok));
}));

const SUPERFICIES = [
  { nombre: 'chat general', preparar: (page) => prepararGeneral(page), soloEscritorio: false },
  { nombre: 'notebook', preparar: (page, control, usuario) => prepararNotebook(page, control, usuario), soloEscritorio: true },
];

function omitirSiCorresponde(superficie) {
  test.skip(superficie.soloEscritorio && test.info().project.name === 'pequena', 'El notebook solo se prueba en escritorio (RNF-04.60)');
}

test.describe('Chat: etapas, plazo y errores', () => {
  for (const superficie of SUPERFICIES) {
    test(`RF-11.64 · ${superficie.nombre}: las tres etapas en orden${superficie.nombre === 'chat general' ? ' y un evento desconocido no rompe la respuesta' : ''}`, async ({
      page, crearUsuario, control,
    }) => {
      omitirSiCorresponde(superficie);
      const usuario = await iniciarComoUsuario(page, crearUsuario);
      // Pausa tras la primera etapa; en el general se inyecta además un evento de tipo desconocido (RF-11.67).
      const eventoDesconocido = superficie.nombre === 'chat general' ? 'prueba_inventado' : undefined;
      await control.chat({ pausa_entre_etapas: true, evento_desconocido: eventoDesconocido });
      await control.motor({ modo: 'texto', texto: RESPUESTA, retener_tras: 0 });
      const chat = await superficie.preparar(page, control, usuario);
      await registrarEtapas(page);
      await chat.enviar(PREGUNTA);

      // Primera etapa en pantalla; la segunda todavía no.
      await expect(indicador(page)).toContainText(ETAPAS[0]);
      await expect(indicador(page)).not.toContainText(ETAPAS[1]);
      await chat.bloqueado();

      // Se mueve la pausa a justo antes de la tercera etapa (reprogramar suelta la primera): se ve la segunda y la tercera no.
      await control.chat({ pausa_antes_de_generar: true, evento_desconocido: eventoDesconocido });
      await expect(indicador(page)).toContainText(ETAPAS[1]);
      await expect(indicador(page)).not.toContainText(ETAPAS[2]);
      await chat.bloqueado();

      // Al liberar, sigue la tercera; se queda mientras el motor está retenido.
      await control.chatLiberar();
      await expect(indicador(page)).toContainText(ETAPAS[2]);
      await chat.bloqueado();

      // Con el primer texto, el indicador desaparece y la respuesta se completa (aun con el evento desconocido).
      await control.motorLiberar();
      await expect(page.getByText(RESPUESTA)).toBeVisible();
      await expect(indicador(page)).toHaveCount(0);
      await chat.libre();
      // Las tres etapas se vieron, en orden y sin repetirse.
      expect(await etapasVistas(page)).toEqual(ETAPAS);
      await expect(page.locator('body')).not.toContainText(AVISO_CONEXION);
    });
  }

  test('RF-16.60 · chat general: motor lento con señal de vida, sin aviso de conexión perdida', async ({
    page, crearUsuario, control,
  }) => {
    await iniciarComoUsuario(page, crearUsuario);
    await page.clock.install();
    await control.chat({ senal_de_vida_segundos: 1 });
    await control.motor({ modo: 'texto', texto: RESPUESTA, retener_tras: 0 });
    const chat = await prepararGeneral(page);

    // Cuenta los datos que llegan del flujo de la consulta (no hay otra forma de saber, sin esperar, que llegó una señal).
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('Network.enable');
    const flujos = new Set();
    let datos = 0;
    cdp.on('Network.requestWillBeSent', (e) => { if (e.request.url.includes('consulta-con-historial-stream')) flujos.add(e.requestId); });
    cdp.on('Network.dataReceived', (e) => { if (flujos.has(e.requestId)) datos += 1; });

    await chat.enviar(PREGUNTA);
    await expect(indicador(page)).toContainText(ETAPAS[2]);
    // Tras cada dato nuevo, el reloj del navegador avanza 8 s: en total, el doble del plazo de 30 s con el servidor sin texto.
    // El dato se cuenta en la red antes de que la página lo procese; pasos cortos toleran ese desfase sin disparar el plazo.
    let vistos = 0;
    for (let i = 0; i < 8; i += 1) {
      await expect.poll(() => datos, { timeout: 15_000 }).toBeGreaterThan(vistos);
      vistos = datos;
      await dejarPasarFotogramas(page);
      await page.clock.runFor(8_000);
    }
    await chat.bloqueado();
    await expect(page.locator('body')).not.toContainText(AVISO_CONEXION);

    // Al liberar el motor llega la respuesta, sin el aviso.
    await control.motorLiberar();
    await expect(page.getByText(RESPUESTA)).toBeVisible();
    await expect(page.locator('body')).not.toContainText(AVISO_CONEXION);
    await chat.libre();
  });

  test('RF-16.40 · chat general: servidor mudo, aviso a los 30 s y control libre', async ({ page, crearUsuario, control }) => {
    await iniciarComoUsuario(page, crearUsuario);
    await page.clock.install();
    await control.chat({ mudo: true });
    const chat = await prepararGeneral(page);
    await chat.enviar(PREGUNTA);
    await expect.poll(async () => (await control.chatEstado()).esperando, { timeout: 15_000 }).toBe(1);

    // Antes de los 30 s sin ningún dato, el control sigue bloqueado y no hay aviso.
    await chat.bloqueado();
    await page.clock.runFor(29_000);
    await chat.bloqueado();
    await expect(page.locator('body')).not.toContainText('Se perdió la conexión');

    // A los 30 s: el aviso exacto, en español neutro, y el control libre.
    await page.clock.runFor(2_000);
    await expect(page.getByText(AVISO_CONEXION, { exact: true })).toBeVisible();
    await expect(page.locator('body')).not.toContainText('Intentá');
    await chat.libre();
    await expect(indicador(page)).toHaveCount(0);
  });

  test('RF-16.62 · chat general: el tope detiene la consulta, conserva el texto y libera el control', async ({
    page, crearUsuario, control,
  }) => {
    await iniciarComoUsuario(page, crearUsuario);
    await control.chat({ senal_de_vida_segundos: 1, tiempo_maximo_segundos: 3 });
    await control.motor({ modo: 'texto', texto: 'PRUEBA primera parte y el resto nunca llega', retener_tras: 3 });
    const chat = await prepararGeneral(page);
    await registrarEtapas(page);
    await chat.enviar(PREGUNTA);
    await expect(page.getByText('PRUEBA primera parte', { exact: false })).toBeVisible();
    await chat.bloqueado();

    // RF-11.67: el aviso del servidor aparece en la conversación; el texto recibido se conserva; el indicador desaparece.
    await expect(page.getByText(AVISO_TOPE, { exact: true })).toBeVisible();
    await expect(page.getByText('PRUEBA primera parte', { exact: false })).toBeVisible();
    await expect(page.locator('body')).not.toContainText('el resto nunca llega');
    await expect(page.locator('body')).not.toContainText('Intentá');
    await expect(indicador(page)).toHaveCount(0);
    await chat.libre();
  });

  for (const superficie of SUPERFICIES) {
    test(`RF-11.62 · ${superficie.nombre}: pregunta demasiado larga, aviso sin etapas y control libre`, async ({
      page, crearUsuario, control,
    }) => {
      omitirSiCorresponde(superficie);
      const usuario = await iniciarComoUsuario(page, crearUsuario);
      const chat = await superficie.preparar(page, control, usuario);
      await registrarEtapas(page);
      await chat.enviar(PREGUNTA_LARGA);

      // RF-11.67: el texto del servidor, en español neutro; sin etapas ni indicador; el control libre.
      await expect(page.getByText(AVISO_LARGA, { exact: true })).toBeVisible();
      await expect(page.locator('body')).not.toContainText('Intentá');
      await expect(indicador(page)).toHaveCount(0);
      await chat.libre();
      expect(await etapasVistas(page)).toEqual([]);
    });
  }
});
