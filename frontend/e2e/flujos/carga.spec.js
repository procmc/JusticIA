// Carga en Ingesta de Datos y la cita en el chat general (spec 005b, T3): RF-05.40 (cierra RF-05.23), RNF-04.40 y RF-11.40
// (solo la cita, decisión 21). Spec retroactiva: sigue al ERS, no a lo que hoy hace el código. Corre en `escritorio` (1366) y
// `pequena` (616). Los datos son inventados (prefijo PRUEBA); el motor de lenguaje es el simulado de la instancia.
const { test, expect, iniciarSesion, exigirAccesible } = require('../soporte/fixtures.js');
const { nuevoTema, documentoDePrueba, cargaMixta } = require('../soporte/datos.js');
const {
  abrirIngesta, elegirArchivosEnIngesta, guardarEnIngesta, filaDeIngesta, avisosDeLaPantalla, preguntarEnElChat,
} = require('../soporte/pantallas.js');

const MOTIVO_VACIO = 'archivo vacío';
const MOTIVO_NOMBRE = 'nombre de archivo no válido';
const TODOS_RECHAZADOS = 'No se aceptó ningún archivo. Revise el motivo de cada uno.';

const esCargaDeArchivos = (r) => r.url().endsWith('/ingesta/archivos') && r.request().method() === 'POST';

async function iniciarComoUsuario(page, crearUsuario) {
  const usuario = await crearUsuario('usuario');
  await iniciarSesion(page, usuario.correo, usuario.contrasena);
  return usuario;
}

const avisoDelTema = (page, tema) => avisosDeLaPantalla(page).filter({ hasText: `Tema ${tema}:` });

// Desplaza la página hasta el final del texto del elemento y comprueba que ahí se ve: dentro de la ventana y, en ese punto,
// el elemento mismo (si un contenedor lo recortara con `overflow`, el punto lo ocuparía otro elemento). Devuelve 'ok' o el motivo.
function finDelTextoAlcanzable(locator) {
  return locator.evaluate((elemento) => {
    elemento.scrollIntoView({ block: 'center', inline: 'start' });
    const rango = document.createRange();
    rango.selectNodeContents(elemento);
    const cajas = [...rango.getClientRects()].filter((c) => c.width > 0);
    const ultima = cajas[cajas.length - 1];
    if (!ultima) return 'sin texto';
    if (ultima.right > window.innerWidth) window.scrollBy(ultima.right - window.innerWidth + 8, 0);
    const despues = [...rango.getClientRects()].filter((c) => c.width > 0).pop();
    if (despues.right > window.innerWidth + 1) return `el final del texto queda fuera de la ventana (${Math.round(despues.right)} px de ${window.innerWidth})`;
    const encima = document.elementFromPoint(despues.right - 2, despues.top + despues.height / 2);
    if (!encima || (encima !== elemento && !elemento.contains(encima))) return 'el final del texto está recortado o tapado';
    return 'ok';
  });
}

test.describe('carga en Ingesta de Datos', () => {
  test('RF-05.40 · Ingesta: carga mixta', async ({ page, crearUsuario }) => {
    await iniciarComoUsuario(page, crearUsuario);
    const { valido, vacio, largo } = cargaMixta();
    const tema = nuevoTema();
    await abrirIngesta(page);
    await elegirArchivosEnIngesta(page, tema, [valido, vacio, largo]);

    const respuestaEsperada = page.waitForResponse(esCargaDeArchivos);
    await guardarEnIngesta(page, 3);
    const respuesta = await respuestaEsperada;
    const cuerpo = await respuesta.json();

    // La API: un aceptado y dos rechazados con su motivo, y ningún nombre en lo que entrega el sistema (RNF-07.24).
    expect(cuerpo.aceptados.cantidad).toBe(1);
    expect(cuerpo.rechazados.archivos.map((r) => r.motivo)).toEqual([MOTIVO_VACIO, MOTIVO_NOMBRE]);
    expect(JSON.stringify(cuerpo)).not.toContain(largo.nombre);

    // El aviso: la confirmación cuenta solo al aceptado y cada rechazado muestra el motivo tal cual lo entregó la API.
    const aviso = avisoDelTema(page, tema);
    await expect(aviso).toBeVisible();
    await expect(aviso).toContainText('1 archivo enviado a procesamiento');
    await expect(aviso).not.toContainText(/3 archivos/);
    const motivos = aviso.locator('li');
    await expect(motivos).toHaveCount(2);
    await expect(motivos.nth(0)).toHaveText(`${vacio.nombre}: ${cuerpo.rechazados.archivos[0].motivo}`);
    await expect(motivos.nth(1)).toHaveText(new RegExp(`: ${cuerpo.rechazados.archivos[1].motivo}$`));

    // Los rechazados quedan «Rechazado», nunca «Procesando», y el aceptado llega a Procesado (Completado).
    const filaValida = filaDeIngesta(page, valido.nombre);
    await expect(filaValida).toContainText('Completado', { timeout: 30_000 });
    for (const rechazado of [vacio, largo]) {
      const fila = filaDeIngesta(page, rechazado.nombre);
      await expect(fila).toContainText('Rechazado');
      await expect(fila).not.toContainText('Procesando');
      await expect(fila.getByRole('progressbar')).toHaveCount(0);
    }
    await expect(filaDeIngesta(page, vacio.nombre)).toContainText(MOTIVO_VACIO);
    await expect(filaDeIngesta(page, largo.nombre)).toContainText(MOTIVO_NOMBRE);
  });

  test('RF-05.40 · Ingesta: todos rechazados sin aviso de éxito', async ({ page, crearUsuario }) => {
    await iniciarComoUsuario(page, crearUsuario);
    const { vacio, largo } = cargaMixta();
    const tema = nuevoTema();
    await abrirIngesta(page);
    await elegirArchivosEnIngesta(page, tema, [vacio, largo]);

    const respuestaEsperada = page.waitForResponse(esCargaDeArchivos);
    await guardarEnIngesta(page, 2);
    const cuerpo = await (await respuestaEsperada).json();
    expect(cuerpo.aceptados.cantidad).toBe(0);
    expect(cuerpo.message).toBe(TODOS_RECHAZADOS);

    // Solo el aviso con los motivos: ningún texto dice que algo se envió, se guardó o se procesó.
    const aviso = avisoDelTema(page, tema);
    await expect(aviso).toBeVisible();
    await expect(aviso).toContainText(TODOS_RECHAZADOS);
    await expect(aviso.locator('li')).toHaveCount(2);
    await expect(avisosDeLaPantalla(page)).toHaveCount(1);
    await expect(page.locator('body')).not.toContainText(/enviados? a procesamiento|Subida iniciada|se ha guardado|¡Archivo procesado!/);
    for (const rechazado of [vacio, largo]) {
      const fila = filaDeIngesta(page, rechazado.nombre);
      await expect(fila).toContainText('Rechazado');
      await expect(fila).not.toContainText('Procesando');
    }
    // Sigue así tras el tiempo en que se consultaría el progreso de un archivo en proceso (cada 2 s).
    await expect.poll(async () => (await avisosDeLaPantalla(page).count()), { timeout: 4_000, intervals: [500] }).toBe(1);
  });

  test('RF-05.40 · Ingesta: ningún aviso antes de la respuesta', async ({ page, crearUsuario }) => {
    await iniciarComoUsuario(page, crearUsuario);
    const { valido, vacio } = cargaMixta();
    const tema = nuevoTema();
    await abrirIngesta(page);
    await elegirArchivosEnIngesta(page, tema, [valido, vacio]);

    // La respuesta de la carga se retiene hasta comprobar que la pantalla no anunció nada.
    let soltar;
    const liberada = new Promise((resolver) => { soltar = resolver; });
    let pedidoRetenido;
    const retenido = new Promise((resolver) => { pedidoRetenido = resolver; });
    await page.route('**/ingesta/archivos', async (ruta) => {
      pedidoRetenido();
      await liberada;
      await ruta.continue();
    });

    await guardarEnIngesta(page, 2);
    await retenido;
    await expect(page.getByText('Subiendo...').first()).toBeVisible(); // la subida está en curso
    await expect(avisosDeLaPantalla(page)).toHaveCount(0);
    await expect(page.locator('body')).not.toContainText(/enviados? a procesamiento|Subida iniciada|se ha guardado/);

    soltar();
    const aviso = avisoDelTema(page, tema);
    await expect(aviso).toBeVisible();
    await expect(aviso).toContainText('1 archivo enviado a procesamiento');
    await expect(filaDeIngesta(page, vacio.nombre)).toContainText('Rechazado');
    await expect(filaDeIngesta(page, valido.nombre)).toContainText('Completado', { timeout: 30_000 });
  });

  // RNF-04.40 corre en las dos pantallas; en `pequena` (616 px) es la medida que importa.
  test('RNF-04.40 · aviso accesible y completo', async ({ page, crearUsuario }) => {
    await iniciarComoUsuario(page, crearUsuario);
    const { valido, vacio, largo } = cargaMixta();
    const tema = nuevoTema();
    await abrirIngesta(page);
    await elegirArchivosEnIngesta(page, tema, [valido, vacio, largo]);
    await guardarEnIngesta(page, 3);

    const aviso = avisoDelTema(page, tema);
    await expect(aviso).toBeVisible();
    await expect(aviso.locator('li')).toHaveCount(2);
    await exigirAccesible(aviso);
    // El texto completo se ve al desplazarse (criterio de RNF-04.1): el final de cada línea del aviso se alcanza con el
    // desplazamiento de la página y nada lo recorta ni lo tapa.
    const lineas = [aviso.getByText('1 archivo enviado a procesamiento'), ...(await aviso.locator('li').all())];
    for (const linea of lineas) {
      let motivo = 'sin evaluar';
      try {
        await expect.poll(async () => { motivo = await finDelTextoAlcanzable(linea); return motivo; }, { timeout: 5_000 }).toBe('ok');
      } catch (error) {
        throw new Error(`Texto del aviso de la carga no alcanzable (${linea}): ${motivo}`);
      }
    }
    const textoVisible = await aviso.innerText();
    expect(textoVisible).toContain(`${vacio.nombre}: ${MOTIVO_VACIO}`);
    expect(textoVisible).toContain(largo.nombre); // el nombre largo se muestra entero, no abreviado
    expect(textoVisible).toContain(MOTIVO_NOMBRE);
    await expect(filaDeIngesta(page, valido.nombre)).toContainText('Completado', { timeout: 30_000 });
  });

  test('RF-11.40 · Ingesta: Procesado y el chat general lo cita', async ({ page, crearUsuario }) => {
    await iniciarComoUsuario(page, crearUsuario);
    const documento = documentoDePrueba();
    const tema = nuevoTema();
    await abrirIngesta(page);
    await elegirArchivosEnIngesta(page, tema, [documento]);
    await guardarEnIngesta(page, 1);
    await expect(filaDeIngesta(page, documento.nombre)).toContainText('Completado', { timeout: 30_000 });

    // Con el motor simulado (cita el archivo recibido), basta con que el nombre del archivo aparezca en la respuesta.
    await preguntarEnElChat(page, `¿Qué dice el documento sobre ${documento.frase}?`);
    await expect(page.getByText(documento.nombre).first()).toBeVisible({ timeout: 30_000 });
  });
});
