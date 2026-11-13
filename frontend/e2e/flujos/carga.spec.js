// Carga en Ingesta de Datos y la cita en el chat general (spec 005b, T3): RF-05.40 (cierra RF-05.23), RNF-04.40 y RF-11.40
// (solo la cita, decisión 21). Spec retroactiva: sigue al ERS, no a lo que hoy hace el código. Corre en `escritorio` (1366) y
// `pequena` (616). Los datos son inventados (prefijo PRUEBA); el motor de lenguaje es el simulado de la instancia.
const { test, expect, iniciarSesion, exigirAccesible } = require('../soporte/fixtures.js');
const {
  nuevoTema, documentoDePrueba, PNG_MINIMO, cargaMixta, crearNotebook, listarDocumentos, aleatorio, iniciarSesion: iniciarSesionPorApi,
} = require('../soporte/datos.js');
const {
  abrirIngesta, elegirArchivosEnIngesta, guardarEnIngesta, filaDeIngesta, avisosDeLaPantalla, preguntarEnElChat,
  campoDelTema, agregarArchivosEnIngesta,
} = require('../soporte/pantallas.js');
const { pulsar, escribir } = require('../soporte/sesion.js');

const MOTIVO_VACIO = 'archivo vacío';
const MOTIVO_NOMBRE = 'nombre de archivo no válido';
const ADVERTENCIA_MANUSCRITO = 'Las imágenes deben contener texto impreso o tipeado: la escritura a mano no se reconoce de forma confiable.';
const TODOS_RECHAZADOS ='No se aceptó ningún archivo. Revise el motivo de cada uno.';

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

    // RF-06.54: rótulo «Tema», sin «expediente» ni formato heredado; un tema de 3 caracteres habilita Guardar.
    await expect(campoDelTema(page)).toBeVisible();
    await expect(page.locator('body')).not.toContainText(/expediente|YY-NNNNNN|Formato requerido/i);
    await escribir(campoDelTema(page), 'abc');
    await agregarArchivosEnIngesta(page, [{ nombre: `PRUEBA_tres_${aleatorio()}.txt`, contenido: Buffer.from('PRUEBA'), tipo: 'text/plain' }]);
    await expect(page.getByRole('button', { name: 'Guardar 1' })).toBeEnabled();
    await pulsar(page.getByRole('button', { name: 'Limpiar' }));
    await expect(page.locator('[data-files-list]')).toHaveCount(0);

    await elegirArchivosEnIngesta(page, tema, [valido, vacio, largo]);

    const respuestaEsperada = page.waitForResponse(esCargaDeArchivos);
    // La confirmación también dice «tema» (RF-06.54) y no «expediente».
    await pulsar(page.getByRole('button', { name: 'Guardar 3' }));
    const confirmacion = page.getByRole('dialog');
    await expect(confirmacion).toContainText('Tema');
    await expect(confirmacion).not.toContainText(/expediente/i);
    await pulsar(page.getByRole('button', { name: 'Sí, Guardar Archivos' }));
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

  // RF-06.50 a RF-06.52 (cambio FF1, 10/11/2026) y la regresión de RF-17.4: al guardar, los pendientes toman el tema ACTUAL del
  // campo. Una sola prueba, solo en escritorio.
  test('RF-06.50 · Ingesta: los pendientes toman el tema actual del campo al guardar', async ({ page, crearUsuario, control, consola }) => {
    test.skip(test.info().project.name === 'pequena', 'Solo en escritorio (plan, decisión 7)');
    consola.provocado(/400|404/); // los temas no válidos y la clave de notebook inexistente
    const usuario = await iniciarComoUsuario(page, crearUsuario);
    const token = await iniciarSesionPorApi(control, usuario);
    const notebook = await crearNotebook(control, token, `PRUEBA notebook tema ${aleatorio()}`);
    const [a, b, c, d, e] = Array.from({ length: 5 }, () => documentoDePrueba());
    const tema1 = nuevoTema();
    const tema2 = nuevoTema();
    const temaLargo = `PRUEBA ${'t'.repeat(60)}`; // 67 caracteres: el servidor admite hasta 60
    const claveInexistente = 'NB-987654321';
    // Lo que la pantalla envía en cada carga: el tema del formulario y los nombres de los archivos.
    const envios = [];
    page.on('request', (r) => {
      if (!esCargaDeArchivos({ url: () => r.url(), request: () => r })) return;
      const cuerpo = (r.postDataBuffer() || Buffer.alloc(0)).toString('utf-8');
      const tema = /name="CT_Num_expediente"\r\n\r\n([^\r]*)\r\n/.exec(cuerpo)?.[1];
      envios.push({ tema, nombres: [...cuerpo.matchAll(/filename="([^"]*)"/g)].map((m) => m[1]) });
    });
    const guardar = page.getByRole('button', { name: /^Guardar/ });
    const indicacion = page.getByText('Indique el tema antes de guardar los archivos.');

    await abrirIngesta(page);

    // Con el campo vacío o solo con espacios, Guardar queda deshabilitado con su indicación (sin alerta del navegador).
    await agregarArchivosEnIngesta(page, [a]);
    await expect(filaDeIngesta(page, a.nombre)).toBeVisible();
    await expect(guardar).toBeDisabled();
    await expect(indicacion).toBeVisible();
    await escribir(campoDelTema(page), '   ');
    await expect(guardar).toBeDisabled();

    // El tema escrito se ve de inmediato en el pendiente, sin Enter. B se agrega con el campo en tema 1.
    await escribir(campoDelTema(page), tema1);
    await expect(filaDeIngesta(page, a.nombre)).toContainText(tema1);
    await expect(indicacion).toHaveCount(0);
    await expect(guardar).toBeEnabled();
    await agregarArchivosEnIngesta(page, [b]);
    await expect(filaDeIngesta(page, b.nombre)).toContainText(tema1);

    // Cambiar el campo cambia el tema de los dos pendientes (era el error: se quedaban con el tema anterior).
    await escribir(campoDelTema(page), tema2);
    for (const doc of [a, b]) {
      await expect(filaDeIngesta(page, doc.nombre)).toContainText(tema2);
      await expect(filaDeIngesta(page, doc.nombre)).not.toContainText(tema1);
    }

    // La confirmación muestra un solo tema (el actual) con los dos archivos y la advertencia de asociación permanente.
    await pulsar(page.getByRole('button', { name: 'Guardar 2' }));
    const confirmacion = page.getByRole('dialog');
    await expect(confirmacion).toContainText('asociará permanentemente los archivos a su tema');
    await expect(confirmacion.locator('[data-tema-grupo]')).toHaveCount(1);
    await expect(confirmacion.locator(`[data-tema-grupo="${tema2}"]`)).toContainText(a.nombre);
    await expect(confirmacion.locator(`[data-tema-grupo="${tema2}"]`)).toContainText(b.nombre);
    await expect(confirmacion).not.toContainText(tema1);
    await pulsar(page.getByRole('button', { name: 'Sí, Guardar Archivos' }));
    for (const doc of [a, b]) {
      await expect(filaDeIngesta(page, doc.nombre)).toContainText('Completado', { timeout: 30_000 });
    }

    // Lo ya enviado conserva su tema aunque el campo cambie después.
    await escribir(campoDelTema(page), `${tema2} otro`);
    for (const doc of [a, b]) {
      await expect(filaDeIngesta(page, doc.nombre)).toContainText(tema2);
      await expect(filaDeIngesta(page, doc.nombre)).not.toContainText(`${tema2} otro`);
    }

    // Segundo Guardar, con la clave del notebook propio (RF-17.4, U1): el archivo carga en ese notebook.
    await escribir(campoDelTema(page), notebook.clave_interna);
    await agregarArchivosEnIngesta(page, [c]);
    await guardarEnIngesta(page, 1);
    await expect(filaDeIngesta(page, c.nombre)).toContainText('Completado', { timeout: 30_000 });

    // Un tema de más de 60 caracteres y una clave de notebook inexistente: el servidor los rechaza (RF-06.52) y el archivo queda
    // «Rechazado», sin afectar lo ya procesado.
    await escribir(campoDelTema(page), temaLargo);
    await agregarArchivosEnIngesta(page, [d]);
    await guardarEnIngesta(page, 1);
    await escribir(campoDelTema(page), claveInexistente);
    await agregarArchivosEnIngesta(page, [e]);
    await guardarEnIngesta(page, 1);
    for (const rechazado of [d, e]) {
      const fila = filaDeIngesta(page, rechazado.nombre);
      await expect(fila).toContainText('Rechazado', { timeout: 30_000 });
      await expect(fila).toContainText('El tema indicado no es válido');
    }

    // Lo que la pantalla envió decide el tema de cada documento: un solo tema por Guardar y nada en el tema que se descartó.
    expect(envios).toHaveLength(4);
    const nombresEnTema = (tema) => (envios.find((x) => x.tema === tema)?.nombres || []).sort();
    expect(nombresEnTema(tema2)).toEqual([a.nombre, b.nombre].sort());
    expect(nombresEnTema(tema1)).toEqual([]);
    expect(nombresEnTema(notebook.clave_interna)).toEqual([c.nombre]);
    expect(nombresEnTema(temaLargo)).toEqual([d.nombre]);
    expect(nombresEnTema(claveInexistente)).toEqual([e.nombre]);
    expect((await listarDocumentos(control, token, notebook)).map((x) => [x.nombre_archivo, x.estado])).toEqual([[c.nombre, 'Procesado']]);
  });

  // RF-07.50: el archivo cuyo procesamiento falla se ve en Error con el texto fijo y su causa, y los contadores lo cuentan.
  // Solo en escritorio (plan, decisión 7). El acompañante es una PNG (RF-05.50).
  test('RF-07.50 · Ingesta: fallo en Error con su causa e imagen Procesada', async ({ page, crearUsuario }) => {
    test.skip(test.info().project.name === 'pequena', 'Solo en escritorio (plan, decisión 7)');
    await iniciarComoUsuario(page, crearUsuario);
    const tema = nuevoTema();
    // RF-05.50: una PNG generada en memoria; el HTR simulado le devuelve su texto y debe quedar Procesada.
    const bueno = { nombre: `PRUEBA_${aleatorio()}.png`, contenido: PNG_MINIMO, tipo: 'image/png' };
    // Un PDF dañado inventado: tiene la firma de PDF pero no su estructura, así que no se puede leer.
    const danado = {
      nombre: `PRUEBA_danado_${aleatorio()}.pdf`,
      contenido: Buffer.from('%PDF-1.4\nPRUEBA contenido que no es un pdf válido \u0000\u0001\u0002 sin estructura ni fin', 'latin1'),
      tipo: 'application/pdf',
    };
    await abrirIngesta(page);
    // Las seis extensiones de imagen están en la lista de formatos y en el selector.
    await expect(page.getByText(/Formatos soportados:.*JPG, JPEG, PNG, TIF, TIFF, BMP/)).toBeVisible();
    await expect(page.locator('input[type="file"]')).toHaveAttribute('accept', /(?=.*\.jpg)(?=.*\.jpeg)(?=.*\.png)(?=.*\.tif,)(?=.*\.tiff)(?=.*\.bmp)/);
    await elegirArchivosEnIngesta(page, tema, [danado, bueno]);
    // Identificada como imagen en el cuadro de confirmación.
    await pulsar(page.getByRole('button', { name: 'Guardar 2' }));
    await expect(page.getByText('IMAGEN', { exact: true })).toBeVisible();
    await pulsar(page.getByRole('button', { name: 'Sí, Guardar Archivos' }));

    await expect(filaDeIngesta(page, bueno.nombre)).toContainText('Completado', { timeout: 30_000 });
    const fila = filaDeIngesta(page, danado.nombre);
    await expect(fila).toContainText('Error', { timeout: 30_000 });
    // El texto fijo y la causa de la lista cerrada; nunca texto técnico, rutas ni el nombre de una excepción.
    await expect(fila).toContainText('No se pudo procesar el archivo. Por favor, intente nuevamente.');
    await expect(fila).toContainText(/Causa: (no se pudo extraer el texto|servicio de procesamiento no disponible|formato o tamaño no permitido|error interno)\./);
    await expect(fila).not.toContainText(/Traceback|Exception|Tika|\/app\/|uploads/i);
    await expect(fila.getByRole('progressbar')).toHaveCount(0);

    // Los contadores: uno con error y uno completado.
    const contador = (rotulo) => page.getByText(rotulo, { exact: true }).locator('xpath=..');
    await expect(contador('Errores')).toHaveText(/^1Errores/);
    await expect(contador('Completados')).toHaveText(/^1Completados/);
  });

  test('RF-05.40 · Ingesta: todos rechazados sin aviso de éxito',async ({ page, crearUsuario }) => {
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
    // RNF-04.50: con el nombre largo sin espacios, ni el aviso ni sus líneas se desbordan (el nombre se parte en varias líneas).
    const desbordes = await aviso.evaluate((raiz) => [raiz, ...raiz.querySelectorAll('*')]
      .filter((e) => e.scrollWidth > e.clientWidth + 1 && e.clientWidth > 0 && getComputedStyle(e).display !== 'inline')
      .map((e) => `${e.tagName} ${e.scrollWidth}>${e.clientWidth}`));
    expect(desbordes, 'RNF-04.50 · elementos del aviso desbordados').toEqual([]);
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
    await expect(page.getByText(ADVERTENCIA_MANUSCRITO)).toBeVisible(); // RF-10.50
    await elegirArchivosEnIngesta(page, tema, [documento]);
    await guardarEnIngesta(page, 1);
    await expect(filaDeIngesta(page, documento.nombre)).toContainText('Completado', { timeout: 30_000 });

    // Con el motor simulado (cita el archivo recibido), basta con que el nombre del archivo aparezca en la respuesta.
    await preguntarEnElChat(page, `¿Qué dice el documento sobre ${documento.frase}?`);
    await expect(page.getByText(documento.nombre).first()).toBeVisible({ timeout: 30_000 });
  });

  // Pedido de Andrés (10/11/2026), sin requisito en el ERS todavía: un archivo con error se reintenta sin volver a elegirlo.
  test('RF-07 [NUEVO] · Ingesta: reintentar un archivo con error', async ({ page, crearUsuario, consola }) => {
    consola.provocado(/ingesta\/archivos|Failed to fetch|Error subiendo|Error de subida/);
    await iniciarComoUsuario(page, crearUsuario);
    const documento = documentoDePrueba();
    const tema = nuevoTema();
    await abrirIngesta(page);
    await elegirArchivosEnIngesta(page, tema, [documento]);

    // La carga se corta en sus 3 intentos automáticos (como cuando el servidor se recarga a mitad de la subida); la siguiente pasa tal cual.
    let cortes = 0;
    await page.route(/\/ingesta\/archivos$/, (ruta) => {
      if (ruta.request().method() === 'POST' && cortes < 3) { cortes += 1; return ruta.abort('failed'); }
      return ruta.continue();
    });
    await guardarEnIngesta(page, 1);
    const fila = filaDeIngesta(page, documento.nombre);
    await expect(fila).toContainText('Error', { timeout: 30_000 });

    // Un archivo con error ofrece «Reintentar»; el reintento lo envía de nuevo y llega a Procesado sin volver a elegirlo.
    await pulsar(fila.getByRole('button', { name: 'Reintentar' }));
    await expect(fila).toContainText('Completado', { timeout: 30_000 });
    expect(cortes).toBe(3);
  });

  test('RF-05.52 · Ingesta: un .rtf no se agrega a la lista y los formatos soportados no lo mencionan', async ({ page, crearUsuario }) => {
    // Spec 006, cambio FFF1: el RTF dejó de ser un formato permitido (el extractor de texto del despliegue no lo lee). La pantalla
    // filtra por extensión y descarta en silencio lo no permitido, como con cualquier otro formato.
    await iniciarComoUsuario(page, crearUsuario);
    const rtf = { nombre: `PRUEBA_formato_${aleatorio()}.rtf`, contenido: Buffer.from('PRUEBA texto inventado'), tipo: 'application/rtf' };
    const texto = { nombre: `PRUEBA_formato_${aleatorio()}.txt`, contenido: Buffer.from('PRUEBA texto inventado'), tipo: 'text/plain' };
    await abrirIngesta(page);
    const formatos = page.getByText(/Formatos soportados:/);
    await expect(formatos).toBeVisible();
    await expect(formatos).not.toContainText('RTF');
    await expect(page.locator('input[type="file"]')).not.toHaveAttribute('accept', /\.rtf/);

    await agregarArchivosEnIngesta(page, [rtf, texto]);
    await expect(filaDeIngesta(page, texto.nombre)).toHaveCount(1); // el permitido sí se agrega
    await expect(filaDeIngesta(page, rtf.nombre)).toHaveCount(0);   // el .rtf se descarta
    await expect(page.getByRole('button', { name: 'Guardar 1' })).toBeVisible();
  });
});
