// Pruebas de los fixtures transversales (spec 005a, T4): red (RA-02.41, RNF-09.40), consola (RA-02.45) y 616 px (RA-02.46).
// Corren en `escritorio` y `pequena`. Cada prueba provoca a propósito lo que el fixture vigila, comprueba que lo detectó y lo
// descarta; si no lo descartara, el propio fixture la haría fallar al terminar.
const { test, expect, esLocalDelNavegador, exigirAccesible, iniciarSesion } = require('../soporte/fixtures.js');
const { abrirNotebooks, crearNotebookEnPantalla } = require('../soporte/pantallas.js');
const { esDeclarado, validarLista, CONSOLA_DECLARADA } = require('../soporte/consola_declarada.js');

test.describe('fixtures transversales', () => {
  test('RA-02.41 · el navegador solo habla con la instancia: lo externo se bloquea y se nombra', async ({ page, red, consola }) => {
    await page.goto('/auth/login');
    await expect(page.locator('body')).toBeVisible();
    expect(red.externas()).toEqual([]);

    // Una petición a una dirección externa (dominio .invalid, que nunca resuelve) no sale: se bloquea antes y queda nombrada.
    const resultado = await page.evaluate(() => fetch('http://servia-externo.invalid/prueba').then(() => 'salió', () => 'bloqueada'));
    expect(resultado).toBe('bloqueada');
    await expect.poll(() => red.externas().length).toBe(1);
    expect(red.externas()[0]).toContain('http://servia-externo.invalid/prueba');

    red.descartar();
    consola.descartar();
  });

  test('RA-02.41 · centinela: el servidor de pruebas aún redirige hacia localhost:3100', async ({ request }) => {
    const web = new URL(process.env.E2E_URL_WEB || 'http://127.0.0.1:3100');
    const respuesta = await request.get(`${web.origin}/consulta-datos/chat`, { maxRedirects: 0 });
    const destino = respuesta.headers().location || '';
    expect(
      new URL(destino, web.origin).hostname,
      'Next.js ya no normaliza el loopback a localhost: la reescritura de redirecciones de e2e/soporte/fixtures.js ya sobra y se puede quitar.',
    ).toBe('localhost');
  });

  test('RA-02.41 · la redirección a localhost:3100 se reescribe a 127.0.0.1 sin tocar la red', async ({ page, red }) => {
    await page.goto('/consulta-datos/chat');
    await page.waitForURL((url) => url.pathname === '/auth/login', { timeout: 10_000 });
    expect(page.url()).toMatch(/^http:\/\/127\.0\.0\.1:3100\/auth\/login/);
    expect(red.externas()).toEqual([]);
  });

  test('RA-02.41 · una petición real a localhost:3100 sigue bloqueada y nombrada', async ({ page, red, consola }) => {
    await page.goto('/auth/login');
    const resultado = await page.evaluate(() => fetch('http://localhost:3100/auth/login', { mode: 'no-cors' }).then(() => 'salió', () => 'bloqueada'));
    expect(resultado).toBe('bloqueada');
    await expect.poll(() => red.externas().length).toBe(1);
    expect(red.externas()[0]).toContain('http://localhost:3100/auth/login');

    red.descartar();
    consola.descartar();
  });

  test('RA-02.41 · solo el visor de PDF y chrome://resources cuentan como locales: otra extensión o página chrome: es externa', async () => {
    const visor = 'chrome-extension://mhjfbmdgcfjbbpaeojofohoefgiehjai';
    expect(esLocalDelNavegador(`${visor}/main.js`)).toBe(true);
    expect(esLocalDelNavegador('chrome://resources/css/text_defaults.css')).toBe(true);
    for (const ajena of [
      'chrome-extension://abcdefghijklmnopabcdefghijklmnop/inyectado.js',
      `${visor}abcd/main.js`,
      'chrome://settings/',
      'chrome://resources.externo/x.js',
      'http://servia-externo.invalid/prueba',
    ]) {
      expect(esLocalDelNavegador(ajena), ajena).toBe(false);
    }
  });

  test('RA-02.45 · error de consola no declarado: error y excepción cuentan, la advertencia no', async ({ page, consola }) => {
    await page.setContent('<p>PRUEBA</p>');
    await page.evaluate(() => {
      console.warn('PRUEBA advertencia: no cuenta');
      console.error('PRUEBA error de consola no declarado');
      queueMicrotask(() => { throw new Error('PRUEBA excepción sin capturar'); });
    });
    await expect.poll(() => consola.pendientes().length).toBe(2);
    const texto = consola.pendientes().join('\n');
    expect(texto).toContain('PRUEBA error de consola no declarado');
    expect(texto).toContain('PRUEBA excepción sin capturar');
    expect(texto).not.toContain('advertencia');

    consola.descartar();
    expect(consola.pendientes()).toEqual([]);
  });

  test('RA-02.45 · error provocado y declarado: la prueba lo declara y no cuenta; lo demás sí', async ({ page, consola }) => {
    consola.provocado(/PRUEBA 401 provocado/);
    await page.setContent('<p>PRUEBA</p>');
    await page.evaluate(() => {
      console.error('PRUEBA 401 provocado por la propia prueba');
      console.error('PRUEBA este otro no estaba declarado');
    });
    await expect.poll(() => consola.pendientes().length).toBe(1);
    expect(consola.pendientes()[0]).toContain('PRUEBA este otro no estaba declarado');

    // La lista única de la suite: cada entrada con su patrón, motivo y la spec que la corregirá.
    const lista = [{ patron: /PRUEBA heredado/, motivo: 'error heredado de la interfaz', spec: 'spec retroactiva de PRUEBA' }];
    expect(esDeclarado('PRUEBA heredado en un flujo correcto', lista)).toBe(true);
    expect(esDeclarado('PRUEBA otro error', lista)).toBe(false);
    expect(() => validarLista(lista)).not.toThrow();
    expect(() => validarLista([{ patron: /x/, motivo: 'sin spec' }])).toThrow(/spec/);
    expect(() => validarLista([{ patron: 'no es regex', motivo: 'm', spec: 's' }])).toThrow(/patron/);
    expect(() => validarLista(CONSOLA_DECLARADA)).not.toThrow();
    // Los dos errores heredados que la interfaz emite al mostrar un rechazo del servidor están en la lista única, no en cada prueba.
    expect(esDeclarado('Error al cambiar contraseña: AxiosError')).toBe(true);
    expect(esDeclarado('Error al resetear contraseña: Error')).toBe(true);
    expect(CONSOLA_DECLARADA.every((entrada) => /spec del módulo/.test(entrada.spec))).toBe(true);

    consola.descartar();
  });

  test('RA-02.46 · accesible detecta un control tapado, uno fuera de la ventana y deja pasar uno libre', async ({ page }) => {
    await page.setContent(`
      <button id="libre" style="margin:8px">Libre</button>
      <button id="tapado" style="margin:8px">Tapado</button>
      <div style="position:fixed;inset:0;background:transparent"></div>
      <button id="fuera" style="position:fixed;top:0;left:3000px">Fuera</button>
    `);
    // El velo cubre toda la ventana, incluido el control «libre»: se retira de la vista con un contenedor propio.
    await page.evaluate(() => {
      const velo = document.querySelector('div');
      velo.style.inset = 'auto';
      velo.style.top = '0';
      velo.style.left = '0';
      velo.style.width = '100vw';
      velo.style.height = '40px';
      document.getElementById('libre').style.marginTop = '200px';
      document.getElementById('tapado').style.position = 'fixed';
      document.getElementById('tapado').style.top = '10px';
      document.getElementById('tapado').style.left = '10px';
    });
    await exigirAccesible(page.locator('#libre'));
    await expect(exigirAccesible(page.locator('#tapado'), { timeout: 500 })).rejects.toThrow(/está tapado por <div>/);
    await expect(exigirAccesible(page.locator('#fuera'), { timeout: 500 })).rejects.toThrow(/queda fuera de la ventana/);
  });

  // 005b, T2: los flujos con dos pestañas o dos usuarios no pueden abrir una vía sin vigilar.
  test('RA-02.41 · RA-02.45 · otra pestaña y otro usuario también quedan vigilados', async ({
    page, otraPestana, otroUsuario, crearUsuario, red, consola,
  }) => {
    const usuario = await crearUsuario('usuario');
    await iniciarSesion(page, usuario.correo, usuario.contrasena);

    // Otra pestaña del mismo contexto: comparte la sesión y la vigilancia del contexto (red y consola).
    await abrirNotebooks(otraPestana);
    expect(red.externas()).toEqual([]);
    const desdePestana = await otraPestana.evaluate(() => fetch('http://servia-externo.invalid/pestana').then(() => 'salió', () => 'bloqueada'));
    expect(desdePestana).toBe('bloqueada');
    await expect.poll(() => red.externas().length).toBe(1);
    expect(red.externas()[0]).toContain('http://servia-externo.invalid/pestana');
    consola.descartar(); // el pedido bloqueado también deja su propio error de consola
    await otraPestana.evaluate(() => console.error('PRUEBA error de la otra pestaña'));
    await expect.poll(() => consola.pendientes().length).toBe(1);
    expect(consola.pendientes()[0]).toContain('PRUEBA error de la otra pestaña');
    red.descartar();
    consola.descartar();

    // Otro usuario en un contexto nuevo: tiene su propia red y su propia consola, también vigiladas.
    const { page: paginaAjena, red: redAjena, consola: consolaAjena } = otroUsuario;
    await abrirNotebooks(paginaAjena);
    const nombre = `PRUEBA notebook ajeno ${Date.now()}`;
    await crearNotebookEnPantalla(paginaAjena, nombre);
    expect(redAjena.externas()).toEqual([]);
    const desdeAjeno = await paginaAjena.evaluate(() => fetch('http://servia-externo.invalid/ajeno').then(() => 'salió', () => 'bloqueada'));
    expect(desdeAjeno).toBe('bloqueada');
    await expect.poll(() => redAjena.externas().length).toBe(1);
    expect(red.externas()).toEqual([]); // lo del otro contexto no se mezcla con el de la primera pestaña
    consolaAjena.descartar();
    await paginaAjena.evaluate(() => console.error('PRUEBA error del otro usuario'));
    await expect.poll(() => consolaAjena.pendientes().length).toBe(1);
    expect(consola.pendientes()).toEqual([]);
    redAjena.descartar();
    consolaAjena.descartar();
  });
});
