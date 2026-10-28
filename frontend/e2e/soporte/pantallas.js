// Acciones de pantalla de los flujos de la 005b (spec 005b, T2). Usan `pulsar` y `escribir`, que a 616 px exigen que el
// control sea alcanzable (RA-02.46). Cada acción espera un estado visible, nunca un tiempo. Las de Ingesta y del chat del
// notebook se agregan en las tareas que las usan por primera vez (T3 a T5).
const { expect } = require('@playwright/test');
const { pulsar, escribir } = require('./sesion.js');

// El menú cerrado conserva solo los íconos (sin «Cerrar sesión»), así que se identifica por su contenedor.
const barraLateral = (page) => page.locator('div.bg-primary.h-screen').first();

// A menos de 768 px la página carga con el menú lateral abierto y tapando el contenido: se cierra con el botón del
// encabezado y se espera a que salga de la ventana (sin tiempos fijos). A 1366 px no hace nada.
async function ocultarMenuSiTapa(page) {
  if (page.viewportSize().width >= 768) return;
  const barra = barraLateral(page);
  const afuera = async () => {
    const derecha = await barra.evaluate((e) => e.getBoundingClientRect().right);
    return derecha <= 1;
  };
  if (await afuera()) return;
  await pulsar(page.locator('div.fixed.top-0 button:has(svg)').first());
  await expect.poll(afuera).toBe(true);
}

// Abre NotebookServIA con la sesión ya iniciada y espera a que la pantalla esté lista para crear un notebook.
async function abrirNotebooks(page) {
  await page.goto('/notebooks');
  await expect(page.getByPlaceholder('Nombre del notebook')).toBeVisible();
  await ocultarMenuSiTapa(page);
}

// Crea un notebook desde la pantalla (botón «Crear notebook») y espera a verlo en la lista.
async function crearNotebookEnPantalla(page, nombre) {
  await escribir(page.getByPlaceholder('Nombre del notebook'), nombre);
  await pulsar(page.getByRole('button', { name: 'Crear notebook' }));
  await expect(page.getByText(nombre).first()).toBeVisible();
}

// Los notebooks de la lista lateral, en el orden en que se muestran (el primero es el más reciente).
const listaDeNotebooks = (page) => page.locator('div.overflow-y-auto.space-y-1 > button');

// Crea un notebook escribiendo el nombre y pulsando Enter en el campo (sin el botón) y espera a verlo en la lista.
async function crearNotebookConEnter(page, nombre) {
  const campo = page.getByPlaceholder('Nombre del notebook');
  await escribir(campo, nombre);
  await campo.press('Enter');
  await expect(listaDeNotebooks(page).filter({ hasText: nombre })).toHaveCount(1);
}

// Abre un notebook de la lista por su nombre y espera a que su área de trabajo (título y «Subir documentos») esté lista.
async function abrirNotebookDeLaLista(page, nombre) {
  await pulsar(listaDeNotebooks(page).filter({ hasText: nombre }));
  await expect(page.getByRole('heading', { name: nombre })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Subir documentos' })).toBeVisible();
}

// Elige archivos (`{ nombre, contenido, tipo }`) en el notebook abierto y espera a la revisión previa a la subida.
async function elegirArchivosEnNotebook(page, archivos) {
  await page.locator('input[type="file"]').setInputFiles(
    archivos.map((a) => ({ name: a.nombre, mimeType: a.tipo || 'text/plain', buffer: a.contenido })),
  );
  await expect(page.getByText(`${archivos.length} archivo(s) seleccionado(s)`)).toBeVisible();
}

// Confirma la subida de lo elegido en el notebook abierto.
const confirmarSubidaEnNotebook = (page, nombreDelNotebook) => pulsar(
  page.getByRole('button', { name: `Confirmar y subir a "${nombreDelNotebook}"` }),
);

// La ficha (chip) de un documento del notebook abierto, por su nombre. Mientras se abre su vista previa muestra «Abriendo…».
const fichaDeDocumento = (page, nombre) => page.locator('div.flex-wrap.gap-2 > div').filter({ hasText: nombre });

// Abre el notebook por la pantalla y espera a que su lista de documentos muestre los nombres dados (la lista carga tras abrirlo).
async function abrirNotebookConDocumentos(page, notebook, nombres) {
  await abrirNotebooks(page);
  await abrirNotebookDeLaLista(page, notebook.nombre);
  for (const nombre of nombres) await expect(fichaDeDocumento(page, nombre)).toHaveCount(1);
}

// Pulsa la «x» de un documento. Si el sistema pide confirmar (RF-19.40), acepta; si no, la petición de quitar sale sola. Espera
// lo primero que ocurra: el cuadro o la petición, sin tiempos fijos.
async function quitarDocumentoEnPantalla(page, nombre) {
  const peticion = page.waitForRequest((r) => r.method() === 'DELETE' && /\/documentos\/\d+$/.test(new URL(r.url()).pathname));
  peticion.catch(() => {}); // si el cuadro gana la carrera y la prueba termina, no queda un rechazo sin atender
  await pulsar(fichaDeDocumento(page, nombre).locator('[aria-label="close chip"]'));
  const dialogo = page.getByRole('dialog');
  const primero = await Promise.race([peticion.then(() => 'peticion'), dialogo.waitFor({ state: 'visible' }).then(() => 'dialogo')]);
  if (primero === 'dialogo') {
    await pulsar(dialogo.getByRole('button').filter({ hasNotText: /cancel|cerrar|close/i }).last());
    await peticion;
  }
}

// El campo se identifica por su rótulo «Tema» (RF-06.54): ya no lleva el ejemplo del formato heredado como placeholder.
const campoDelTema = (page) => page.getByRole('textbox', { name: 'Tema' });

// Abre Ingesta de Datos con la sesión ya iniciada y espera a que el campo del tema esté listo.
async function abrirIngesta(page) {
  await page.goto('/ingesta-datos');
  await expect(campoDelTema(page)).toBeVisible();
  await ocultarMenuSiTapa(page);
}

// Escribe el tema y elige los archivos (`{ nombre, contenido, tipo }`) con el selector de la zona de carga. El tema va
// primero: los archivos toman el tema vigente en el momento de elegirlos.
async function elegirArchivosEnIngesta(page, tema, archivos) {
  await escribir(campoDelTema(page), tema);
  await agregarArchivosEnIngesta(page, archivos);
  await expect(page.getByRole('button', { name: `Guardar ${archivos.length}` })).toBeVisible();
}

// Agrega archivos con el selector de la zona de carga SIN tocar el campo del tema: cada uno toma el texto que tenga el campo
// en ese momento (RF-06.50).
const agregarArchivosEnIngesta = (page, archivos) => page.locator('input[type="file"]').setInputFiles(
  archivos.map((a) => ({ name: a.nombre, mimeType: a.tipo || 'text/plain', buffer: a.contenido })),
);

// «Guardar N» abre el cuadro de confirmación; «Sí, Guardar Archivos» envía la carga.
async function guardarEnIngesta(page, cantidad) {
  await pulsar(page.getByRole('button', { name: `Guardar ${cantidad}` }));
  await pulsar(page.getByRole('button', { name: 'Sí, Guardar Archivos' }));
}

// La fila de la lista de Ingesta de un archivo, por su nombre.
const filaDeIngesta = (page, nombre) => page.locator('[data-files-list] div.border-b').filter({ hasText: nombre });

// Los avisos de la pantalla (toast y avisos de carga) llevan `role="alert"`; se excluye el anunciador de rutas de Next.
const avisosDeLaPantalla = (page) => page.locator('[role="alert"]:not(#__next-route-announcer__)');

// Abre el chat general (sin acotar a un tema) y envía la pregunta con Enter; cada prueba espera lo que debe aparecer.
async function preguntarEnElChat(page, pregunta) {
  await page.goto('/consulta-datos/chat');
  const campo = page.getByPlaceholder('¿En qué puedo ayudarte hoy?...');
  await expect(campo).toBeVisible();
  await ocultarMenuSiTapa(page);
  await escribir(campo, pregunta);
  await campo.press('Enter');
}

module.exports = {
  abrirNotebooks, crearNotebookEnPantalla, abrirIngesta, elegirArchivosEnIngesta, guardarEnIngesta, filaDeIngesta,
  campoDelTema, agregarArchivosEnIngesta,
  avisosDeLaPantalla, preguntarEnElChat, listaDeNotebooks, crearNotebookConEnter, abrirNotebookDeLaLista,
  elegirArchivosEnNotebook, confirmarSubidaEnNotebook, fichaDeDocumento, abrirNotebookConDocumentos, quitarDocumentoEnPantalla,
};
