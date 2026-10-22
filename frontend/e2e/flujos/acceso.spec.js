// Acceso y menú (spec 005a, T7): RF-01.40 a RF-01.44 y RF-02.40. Spec retroactiva: cada prueba sigue al ERS (RF-01, RF-02) y a
// los casos de uso CU-01, CU-02 y CU-03, no a lo que hoy hace el código. Corre en `escritorio` (1366) y `pequena` (616).
// Las contraseñas las genera la suite (`crearUsuario`) y viven solo en la memoria de la prueba.
const { test, expect, fallaEsperada, pulsar, escribir } = require('../soporte/fixtures.js');

const ROLES = ['administrador', 'usuario'];

const campoCorreo = (page) => page.getByLabel('Correo electrónico');
const campoContrasena = (page) => page.getByLabel('Contraseña', { exact: true });
const botonEntrar = (page) => page.getByRole('button', { name: 'Iniciar sesión' });
const tituloInicioSesion = (page) => page.getByRole('heading', { name: 'Inicio de sesión' });
// El aviso rojo de la pantalla de inicio de sesión (se ubica por su estilo, no por el texto que se comprueba).
const avisoDeError = (page) => page.locator('div.bg-red-50');
const panelObligatorio = (page) => page.getByText('Cambio de Contraseña Obligatorio');
// La barra lateral es la única caja con `bg-primary` y el botón «Cerrar sesión».
const barraLateral = (page) => page.locator('div.bg-primary').filter({ has: page.getByText('Cerrar sesión', { exact: true }) });
const botonUsuario = (page) => page.locator('button:has(img[alt="User Avatar"]):visible');

// Espera a que React hidrate la página: si se envía antes, el formulario viajaría por GET con la contraseña en la dirección.
async function irAInicioSesion(page, ruta = '/auth/login') {
  await page.goto(ruta);
  await expect(tituloInicioSesion(page)).toBeVisible();
  await page.waitForFunction(() => Boolean(window.next && window.next.router && window.next.router.isReady));
}

async function escribirCredenciales(page, correo, contrasena) {
  if (correo !== undefined) await escribir(campoCorreo(page), correo);
  if (contrasena !== undefined) await escribir(campoContrasena(page), contrasena);
}

async function iniciarSesion(page, correo, contrasena, ruta) {
  await irAInicioSesion(page, ruta);
  await escribirCredenciales(page, correo, contrasena);
  await pulsar(botonEntrar(page));
}

async function esperarPagina(page, ruta) {
  await page.waitForURL((url) => url.pathname === ruta, { timeout: 10_000 });
}

// Con sesión en inicio: el saludo de la página y la barra lateral están a la vista (o disponibles tras abrir el menú).
async function esperarInicio(page) {
  await esperarPagina(page, '/');
  await expect(page.getByText('Bienvenid@')).toBeVisible();
}

// A 616 px el menú lateral se abre con el botón de hamburguesa del encabezado; a 1366 px ya está a la vista.
async function mostrarMenu(page) {
  const barra = barraLateral(page);
  if (!(await barra.isVisible()) || !(await barra.getByText('Inicio', { exact: true }).isVisible())) {
    await pulsar(page.locator('div.fixed button:has(svg)').first());
  }
  await expect(barra.getByText('Inicio', { exact: true })).toBeVisible();
}

// Despliega los grupos del menú y devuelve sus entradas en orden: `texto` y `enlace` (null en los grupos).
async function leerMenu(page) {
  await mostrarMenu(page);
  const barra = barraLateral(page);
  for (const grupo of ['Administración', 'Búsqueda y Consulta']) {
    const entrada = barra.getByText(grupo, { exact: true });
    if (await entrada.count()) await pulsar(entrada);
  }
  return barra.evaluate((caja) => {
    const entradas = [];
    caja.querySelectorAll('a[href], div.cursor-pointer').forEach((nodo) => {
      const texto = nodo.innerText.trim().replace(/\s+/g, ' ');
      if (!texto || texto === 'Cerrar sesión' || texto.startsWith('ServIA') || nodo.querySelector('a[href]')) return;
      entradas.push({ texto, enlace: nodo.getAttribute('href') });
    });
    return entradas;
  });
}

const SIMILARES = '/consulta-datos/busqueda-similares';

// Las páginas a las que lleva el menú de cada rol (RF-02.40).
const DESTINOS = {
  administrador: ['/', '/administracion/gestion-usuarios', '/administracion/bitacora'],
  usuario: ['/', '/consulta-datos/chat', SIMILARES, '/ingesta-datos', '/notebooks'],
};

test.describe('RF-01.40 · sin sesión', () => {
  test('RF-01.40 · sin sesión, una página protegida lleva a Inicio de sesión', async ({ page }) => {
    await page.goto('/consulta-datos/chat');
    await esperarPagina(page, '/auth/login');
    await expect(tituloInicioSesion(page)).toBeVisible();
    await expect(barraLateral(page)).toHaveCount(0);
  });

  test('RF-01.40 · tras autenticarse vuelve a la página pedida', async ({ page, crearUsuario }) => {
    // Hoy el formulario siempre lleva a «/» y descarta la página pedida (el parámetro `callbackUrl` no se usa).
    fallaEsperada(test, 'RF-01.40 · autenticación');
    const usuario = await crearUsuario('usuario');
    await page.goto('/consulta-datos/chat');
    await esperarPagina(page, '/auth/login');
    await expect(tituloInicioSesion(page)).toBeVisible();
    await page.waitForFunction(() => Boolean(window.next && window.next.router && window.next.router.isReady));
    await escribirCredenciales(page, usuario.correo, usuario.contrasena);
    await pulsar(botonEntrar(page));
    // Con sesión, la página pedida: nunca el inicio.
    await esperarPagina(page, '/consulta-datos/chat');
  });
});

for (const rol of ROLES) {
  test.describe(`RF-01.41 · RF-02.40 · ${rol}`, () => {
    test(`RF-01.41 · el ${rol} entra a inicio con su menú y sus tarjetas`, async ({ page, crearUsuario }) => {
      const usuario = await crearUsuario(rol);
      await iniciarSesion(page, usuario.correo, usuario.contrasena);
      await esperarInicio(page);

      // Menú lateral: solo las opciones del rol, con los nombres del ERS (el de «Temas Similares» se prueba aparte).
      const menu = await leerMenu(page);
      if (rol === 'administrador') {
        expect(menu.map((e) => e.texto)).toEqual(['Inicio', 'Administración', 'Usuarios del Sistema', 'Historial de Actividades']);
      } else {
        const esperado = ['Inicio', 'Búsqueda y Consulta', 'Asistente Virtual', '<Similares>', 'Ingesta de Datos', 'NotebookServIA'];
        expect(menu.map((e) => (e.enlace === SIMILARES ? '<Similares>' : e.texto))).toEqual(esperado);
      }
      expect(menu.filter((e) => e.enlace).map((e) => e.enlace)).toEqual(DESTINOS[rol]);

      // Tarjetas de inicio: cada una lleva a una página del rol y todas las páginas del rol (menos el inicio) tienen tarjeta.
      const tarjetas = page.locator('div.cursor-pointer:has(> h3)');
      const total = await tarjetas.count();
      expect(total).toBeGreaterThan(0);
      const destinos = new Set();
      for (let i = 0; i < total; i += 1) {
        await esperarInicio(page);
        // Al volver, la página se vuelve a dibujar un instante: el pulso se reintenta si la tarjeta se reemplazó.
        await expect(async () => { await pulsar(tarjetas.nth(i)); }).toPass({ timeout: 10_000 });
        await expect.poll(() => new URL(page.url()).pathname, { timeout: 10_000 }).not.toBe('/');
        destinos.add(new URL(page.url()).pathname);
        await page.goBack();
      }
      expect([...destinos].sort()).toEqual(DESTINOS[rol].filter((d) => d !== '/').sort());
    });
  });
}

test('RF-02.40 · el menú del Usuario Gubernamental llama «Temas Similares» a la búsqueda de temas', async ({ page, crearUsuario }) => {
  // «Estado actual» del módulo 6 del ERS: la opción del menú todavía se llama «Casos Similares».
  fallaEsperada(test, 'RF-02.40 · menú');
  const usuario = await crearUsuario('usuario');
  await iniciarSesion(page, usuario.correo, usuario.contrasena);
  await esperarInicio(page);
  const menu = await leerMenu(page);
  expect(menu.find((e) => e.enlace === SIMILARES)?.texto).toBe('Temas Similares');
});

test.describe('RF-01.42 · credenciales y datos del formulario', () => {
  const CASOS = [
    { nombre: 'correo que no existe', preparar: async () => ({ correo: 'prueba-no-existe@prueba.invalid', contrasena: 'PRUEBA-No-Existe-1' }) },
    {
      nombre: 'contraseña que no coincide',
      preparar: async (crearUsuario) => {
        const usuario = await crearUsuario('usuario');
        return { correo: usuario.correo, contrasena: `${usuario.contrasena}x` };
      },
    },
    {
      nombre: 'cuenta Inactiva con la contraseña correcta',
      preparar: async (crearUsuario) => {
        const usuario = await crearUsuario('usuario', { inactivo: true });
        return { correo: usuario.correo, contrasena: usuario.contrasena };
      },
    },
  ];

  for (const caso of CASOS) {
    test(`RF-01.42 · credenciales inválidas, idénticas: ${caso.nombre}`, async ({ page, crearUsuario, consola }) => {
      consola.provocado(/401/);
      const { correo, contrasena } = await caso.preparar(crearUsuario);
      await iniciarSesion(page, correo, contrasena);
      await expect(avisoDeError(page)).toHaveText('Credenciales inválidas');
      await expect(tituloInicioSesion(page)).toBeVisible();
      expect(new URL(page.url()).pathname).toBe('/auth/login');
      // Sin sesión: la página de inicio sigue pidiendo iniciar sesión.
      await page.goto('/');
      await esperarPagina(page, '/auth/login');
    });
  }

  test('RF-01.42 · campos obligatorios sin enviar', async ({ page, red }) => {
    const envios = [];
    page.on('request', (peticion) => { if (peticion.url().includes('/api/auth/callback/credentials')) envios.push(peticion.url()); });
    await irAInicioSesion(page);

    // Vacío: los dos avisos y ninguna solicitud.
    await pulsar(botonEntrar(page));
    await expect(page.getByText('El correo electrónico es obligatorio')).toBeVisible();
    await expect(page.getByText('La contraseña es obligatoria')).toBeVisible();

    // Solo el correo: falta la contraseña.
    await escribirCredenciales(page, 'prueba@prueba.invalid', undefined);
    await pulsar(botonEntrar(page));
    await expect(page.getByText('La contraseña es obligatoria')).toBeVisible();
    await expect(page.getByText('El correo electrónico es obligatorio')).toHaveCount(0);

    // Solo la contraseña: falta el correo.
    await escribir(campoCorreo(page), '');
    await escribir(campoContrasena(page), 'PRUEBA-Solo-Contrasena-1');
    await pulsar(botonEntrar(page));
    await expect(page.getByText('El correo electrónico es obligatorio')).toBeVisible();
    await expect(page.getByText('La contraseña es obligatoria')).toHaveCount(0);

    expect(envios).toEqual([]);
    expect(new URL(page.url()).pathname).toBe('/auth/login');
  });

  test('RF-01.42 · correo sin formato: mensaje en español y sin enviar', async ({ page }) => {
    const envios = [];
    page.on('request', (peticion) => { if (peticion.url().includes('/api/auth/callback/credentials')) envios.push(peticion.url()); });
    await irAInicioSesion(page);
    await escribirCredenciales(page, 'PRUEBA-sin-arroba', 'PRUEBA-Formato-1');
    await pulsar(botonEntrar(page));
    // El aviso del campo de correo (no el de «obligatorio»): debe estar en español.
    const aviso = page.locator('[data-slot="error-message"]');
    await expect(aviso).toBeVisible();
    await expect(aviso).toContainText(/correo/i);
    expect(envios).toEqual([]);
    expect(new URL(page.url()).pathname).toBe('/auth/login');
  });
});

test.describe('RF-01.43 · panel de cambio de contraseña obligatorio', () => {
  async function entrarConTemporal(page, crearUsuario, rol = 'usuario') {
    const usuario = await crearUsuario(rol, { temporal: true });
    await iniciarSesion(page, usuario.correo, usuario.contrasena);
    await expect(panelObligatorio(page)).toBeVisible();
    return usuario;
  }

  const campoActual = (page) => page.getByLabel('Contraseña actual', { exact: true });
  const campoNueva = (page) => page.getByLabel('Nueva contraseña', { exact: true });
  const campoConfirmar = (page) => page.getByLabel('Confirmar nueva contraseña', { exact: true });
  const botonCambiar = (page) => page.getByRole('button', { name: 'Cambiar Contraseña' });

  async function llenarPanel(page, { actual, nueva, confirmar }) {
    await escribir(campoActual(page), actual);
    await escribir(campoNueva(page), nueva);
    await escribir(campoConfirmar(page), confirmar);
    await pulsar(botonCambiar(page));
  }

  test('RF-01.43 · el panel no se cierra con Escape ni con clic fuera, y no deja navegar', async ({ page, crearUsuario }) => {
    await entrarConTemporal(page, crearUsuario);

    await page.keyboard.press('Escape');
    await expect(panelObligatorio(page)).toBeVisible();

    // Clic fuera del panel, sobre el fondo (en la franja izquierda, donde está el menú).
    await page.mouse.click(8, 400);
    await expect(panelObligatorio(page)).toBeVisible();
    expect(new URL(page.url()).pathname).toBe('/');

    // Otra página protegida abierta por su dirección: el panel sigue encima.
    await page.goto('/consulta-datos/chat');
    await expect(panelObligatorio(page)).toBeVisible();
    // Y no deja pulsar nada detrás del panel.
    await expect(barraLateral(page).getByText('Inicio', { exact: true }).click({ timeout: 2_000, trial: true }))
      .rejects.toThrow(/intercepts pointer events/);
  });

  const ERRORES = [
    {
      nombre: 'la temporal es incorrecta',
      campos: (u) => ({ actual: `${u.contrasena}x`, nueva: `${u.contrasena}-Nueva9`, confirmar: `${u.contrasena}-Nueva9` }),
      mensaje: /contraseña/i,
    },
    {
      nombre: 'la nueva tiene menos de 8 caracteres',
      campos: (u) => ({ actual: u.contrasena, nueva: 'Ab1-xyz', confirmar: 'Ab1-xyz' }),
      mensaje: /8 caracteres/i,
    },
    {
      nombre: 'la nueva es igual a la actual',
      campos: (u) => ({ actual: u.contrasena, nueva: u.contrasena, confirmar: u.contrasena }),
      mensaje: /diferente/i,
    },
    {
      nombre: 'la confirmación no coincide',
      campos: (u) => ({ actual: u.contrasena, nueva: `${u.contrasena}-Nueva9`, confirmar: `${u.contrasena}-Otra9` }),
      mensaje: /no coinciden/i,
    },
  ];

  for (const error of ERRORES) {
    test(`RF-01.43 · errores del panel: ${error.nombre}`, async ({ page, crearUsuario, consola }) => {
      // El rechazo del servidor (4xx) lo provoca esta prueba; el console.error de la interfaz está en CONSOLA_DECLARADA.
      consola.provocado(/40[0-9]/);
      const usuario = await entrarConTemporal(page, crearUsuario);
      await llenarPanel(page, error.campos(usuario));
      // Mensaje en español, en el campo o como aviso, y el panel sigue abierto.
      const aviso = page.locator('[data-slot="error-message"], [role="alert"], [role="status"]').filter({ hasText: error.mensaje });
      await expect(aviso.first()).toBeVisible();
      await expect(panelObligatorio(page)).toBeVisible();
      expect(new URL(page.url()).pathname).toBe('/');
    });
  }

  test('RF-01.43 · tras cambiarla, el usuario continúa en la página de inicio', async ({ page, crearUsuario }) => {
    // Hoy, al cambiarla, la interfaz cierra la sesión y lleva a «Inicio de sesión» (CambiarContraseña.jsx: `signOut`).
    fallaEsperada(test, 'RF-01.43 · autenticación');
    const usuario = await entrarConTemporal(page, crearUsuario);
    const nueva = `${usuario.contrasena}-Nueva9`;
    await llenarPanel(page, { actual: usuario.contrasena, nueva, confirmar: nueva });
    // Sin pasar por Inicio de sesión: el panel se cierra y se ve el inicio.
    await expect(panelObligatorio(page)).toHaveCount(0);
    await esperarInicio(page);
  });

  test('RF-01.43 · el siguiente inicio de sesión no muestra el panel', async ({ page, crearUsuario, generadorContrasenas, context }) => {
    const usuario = await entrarConTemporal(page, crearUsuario);
    const nueva = generadorContrasenas.siguiente();
    await llenarPanel(page, { actual: usuario.contrasena, nueva, confirmar: nueva });
    // Se espera a que el cambio quede aplicado (el panel se cierra o la sesión se cierra) y se empieza de cero.
    await expect.poll(async () => (await panelObligatorio(page).count()) === 0 || new URL(page.url()).pathname === '/auth/login').toBe(true);
    await context.clearCookies();
    await iniciarSesion(page, usuario.correo, nueva);
    await esperarInicio(page);
    await expect(panelObligatorio(page)).toHaveCount(0);
    // La contraseña temporal ya no sirve.
    await context.clearCookies();
    await page.goto('/auth/login');
    await expect(tituloInicioSesion(page)).toBeVisible();
  });
});

test.describe('RF-01.44 · cierre de sesión', () => {
  test('RF-01.44 · cerrar sesión: ni Atrás ni la dirección vuelven a una página protegida', async ({ page, crearUsuario, consola }) => {
    // Al volver con Atrás o abrir la dirección, la interfaz puede pedir datos sin sesión y recibir 401.
    consola.provocado(/401/);
    const usuario = await crearUsuario('usuario');
    await iniciarSesion(page, usuario.correo, usuario.contrasena);
    await esperarInicio(page);

    await pulsar(botonUsuario(page));
    await pulsar(page.getByRole('menuitem', { name: 'Cerrar sesión' }));
    await esperarPagina(page, '/auth/login');
    await expect(tituloInicioSesion(page)).toBeVisible();

    // Atrás: debe llegar a Inicio de sesión y, ya en ella, no mostrar el menú ni la página protegida.
    await page.goBack();
    await expect(tituloInicioSesion(page)).toBeVisible();
    await expect(page.getByText('Bienvenid@')).toHaveCount(0);
    await expect(barraLateral(page)).toHaveCount(0);

    // La dirección directa de la página protegida.
    for (const ruta of ['/', '/consulta-datos/chat']) {
      await page.goto(ruta);
      await esperarPagina(page, '/auth/login');
      await expect(tituloInicioSesion(page)).toBeVisible();
      await expect(page.getByText('Bienvenid@')).toHaveCount(0);
      await expect(barraLateral(page)).toHaveCount(0);
    }
  });
});
