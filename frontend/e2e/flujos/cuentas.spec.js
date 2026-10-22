// Cuentas (spec 005a, T8): RF-02.42 (crear una cuenta) y RF-03.40 (resetear la contraseña), desde «Usuarios del Sistema».
// Spec retroactiva: sigue al ERS (RF-02 «Gestión de cuentas», RF-03 vía (a); CU-05), no a lo que hoy hace el código.
// El texto de éxito o de advertencia lo dicta la API: aquí se comprueba que la pantalla lo presenta tal cual.
// Las contraseñas las genera la suite (`crearUsuario`) y viven solo en la memoria de la prueba.
const crypto = require('node:crypto');
const { test, expect, iniciarSesion, pulsar, escribir } = require('../soporte/fixtures.js');

const RUTA = '/administracion/gestion-usuarios';

const buscador = (page) => page.getByPlaceholder('Buscar usuarios...');
const filaDe = (page, correo) => page.getByRole('row').filter({ hasText: correo });
const cuadro = (page) => page.getByRole('dialog');

async function abrirUsuarios(page) {
  await page.goto(RUTA);
  await expect(page.getByRole('grid', { name: 'Tabla de usuarios' })).toBeVisible();
}

// Deja en la lista solo lo que coincide con el correo (la lista tiene páginas y puede traer cuentas de otras pruebas).
async function filtrarPorCorreo(page, correo) {
  await escribir(buscador(page), correo);
  await expect(filaDe(page, correo)).toBeVisible();
}

// Una cédula de 10 dígitos distinta en cada llamada (el formulario solo acepta números, así que no lleva el prefijo PRUEBA).
const cedulaNueva = () => `9${crypto.randomInt(0, 1_000_000_000).toString().padStart(9, '0')}`;
const correoNuevo = () => `prueba${crypto.randomInt(0, 1_000_000_000)}.cuenta@prueba.invalid`;

// El selector de rol cierra su lista si el cuerpo del cajón se desplaza mientras está abierta (el cajón se mide justo al abrir);
// en ese caso la opción desaparece del DOM. Se vuelve a abrir y a elegir hasta que la opción queda elegida, sin pausas fijas.
async function elegirRol(page, nombre) {
  // Con la lista abierta el resto de la página queda oculto para el árbol de accesibilidad: `includeHidden` sigue hallándolo.
  const selector = page.getByRole('button', { name: /Rol del Usuario/, includeHidden: true });
  const opcion = page.getByRole('option', { name: nombre });
  await expect(async () => {
    if ((await selector.getAttribute('aria-expanded')) !== 'true') await pulsar(selector);
    await expect(selector).toHaveAttribute('aria-expanded', 'true', { timeout: 1_000 });
    await pulsar(opcion, { timeout: 2_000 });
  }).toPass({ timeout: 20_000 });
  await expect(selector).toContainText(nombre);
}

async function llenarFormulario(page, { cedula, correo }) {
  await expect(page.getByRole('heading', { name: 'Crear Nuevo Usuario' })).toBeVisible();
  await escribir(page.getByLabel('Cédula'), cedula);
  await escribir(page.getByLabel('Nombre', { exact: true }), 'PRUEBA Cuenta');
  await escribir(page.getByLabel('Primer Apellido'), 'PRUEBA Uno');
  await escribir(page.getByLabel('Segundo Apellido'), 'PRUEBA Dos');
  await escribir(page.getByLabel('Correo Electrónico'), correo);
  await elegirRol(page, 'Usuario Judicial');
}

// Envía el formulario y devuelve la respuesta de la API (su `mensaje` es el que la pantalla debe mostrar).
async function enviarCreacion(page) {
  const [respuesta] = await Promise.all([
    page.waitForResponse((r) => ['/usuarios', '/usuarios/'].includes(new URL(r.url()).pathname) && r.request().method() === 'POST' && (r.status() < 300 || r.status() >= 400)),
    pulsar(page.getByRole('button', { name: 'Crear Usuario' })),
  ]);
  return { estado: respuesta.status(), cuerpo: await respuesta.json() };
}

test('RF-02.42 · crear cuenta: éxito y correo en fallo', async ({ page, crearUsuario, control }) => {
  const administrador = await crearUsuario('administrador');
  await iniciarSesion(page, administrador.correo, administrador.contrasena);
  await abrirUsuarios(page);

  // Éxito: la pantalla muestra el texto de éxito de la API y la cuenta aparece en la lista.
  const exitosa = { cedula: cedulaNueva(), correo: correoNuevo() };
  await pulsar(page.getByRole('button', { name: /Agregar/ }));
  await llenarFormulario(page, exitosa);
  const creada = await enviarCreacion(page);
  expect(creada.estado).toBe(200);
  expect(creada.cuerpo.notificacion_entregada).toBe(true);
  // El ERS (RF-02, «Salida») fija el texto de confirmación.
  expect(creada.cuerpo.mensaje).toBe('Usuario creado exitosamente');
  const avisoExito = page.getByText(creada.cuerpo.mensaje, { exact: true });
  await expect(avisoExito).toBeVisible();
  await expect(page.getByText('Éxito', { exact: true })).toBeVisible();
  await expect(page.getByText('Advertencia', { exact: true })).toHaveCount(0);
  await filtrarPorCorreo(page, exitosa.correo);
  // El aviso de éxito se cierra solo antes de la segunda creación, para no confundirlo con el de la advertencia.
  await expect(avisoExito).toBeHidden();
  // Estado asentado antes de la segunda creación: el cajón anterior cerrado y la lista ya refrescada con la cuenta nueva.
  await expect(page.getByRole('heading', { name: 'Crear Nuevo Usuario' })).toBeHidden();
  await expect(filaDe(page, exitosa.correo)).toBeVisible();

  // Correo en fallo: la cuenta se crea, pero la pantalla muestra la advertencia de la API, distinta del aviso de éxito.
  await control.correoFalla(true);
  const fallida = { cedula: cedulaNueva(), correo: correoNuevo() };
  await pulsar(page.getByRole('button', { name: /Agregar/ }));
  await llenarFormulario(page, fallida);
  const advertida = await enviarCreacion(page);
  expect(advertida.estado).toBe(200);
  expect(advertida.cuerpo.notificacion_entregada).toBe(false);
  expect(advertida.cuerpo.mensaje).not.toBe(creada.cuerpo.mensaje);
  // El ERS (RF-02 «Manejo de errores»): el aviso indica el correo de la cuenta y sugiere «Resetear Contraseña».
  expect(advertida.cuerpo.mensaje).toContain(fallida.correo);
  expect(advertida.cuerpo.mensaje).toContain('Resetear Contraseña');
  await expect(page.getByText(advertida.cuerpo.mensaje, { exact: true })).toBeVisible();
  await expect(page.getByText('Advertencia', { exact: true })).toBeVisible();
  await expect(page.getByText(creada.cuerpo.mensaje, { exact: true })).toHaveCount(0);
  await filtrarPorCorreo(page, fallida.correo);

  // Limpieza: las cuentas del formulario (cédula numérica, sin el prefijo PRUEBA) cuentan como residuo mientras la prueba corre
  // y la limpieza total las borra igual que a las PRUEBA (el administrador de la prueba + las dos creadas aquí).
  expect((await control.residuos()).filas.T_Usuario).toBe(3);
  const tras = await control.limpiar();
  expect(tras.total, `Quedó: ${tras.texto}`).toBe(0);
});

test('RF-03.40 · resetear: explicación, éxito y correo en fallo con sesión activa', async ({ page, crearUsuario, control, consola }) => {
  // El fallo del correo responde 502: lo provoca esta prueba (el console.error de la interfaz está en CONSOLA_DECLARADA).
  consola.provocado(/502/);
  const administrador = await crearUsuario('administrador');
  const cuenta = await crearUsuario('usuario');
  await iniciarSesion(page, administrador.correo, administrador.contrasena);
  await abrirUsuarios(page);
  await filtrarPorCorreo(page, cuenta.correo);

  const abrirCuadro = async () => {
    await pulsar(filaDe(page, cuenta.correo).getByRole('button', { name: /Acciones/ }).or(filaDe(page, cuenta.correo).getByRole('button').last()).first());
    await pulsar(page.getByRole('menuitem', { name: 'Resetear Contraseña' }));
    await expect(cuadro(page)).toBeVisible();
  };
  const confirmar = async () => {
    const [respuesta] = await Promise.all([
      page.waitForResponse((r) => /\/usuarios\/[^/]+\/resetear-contrasenna$/.test(new URL(r.url()).pathname)),
      pulsar(cuadro(page).getByRole('button', { name: 'Sí, Resetear' })),
    ]);
    return { estado: respuesta.status(), cuerpo: await respuesta.json() };
  };

  // Explicación: el cuadro dice que se enviará una contraseña temporal al correo de la cuenta.
  await abrirCuadro();
  await expect(cuadro(page)).toContainText('Se enviará una contraseña temporal');
  await expect(cuadro(page)).toContainText(cuenta.correo);

  // Éxito: la pantalla muestra el texto de la API y el cuadro se cierra.
  const exito = await confirmar();
  expect(exito.estado).toBe(200);
  await expect(page.getByText(exito.cuerpo.mensaje, { exact: true })).toBeVisible();
  await expect(cuadro(page)).toBeHidden();

  // Correo en fallo: el cuadro sigue abierto con el texto de la API y la sesión sigue activa.
  await control.correoFalla(true);
  await abrirCuadro();
  const fallo = await confirmar();
  expect(fallo.estado).toBe(502);
  // El ERS (RF-03, «Manejo de errores») fija el texto del fallo.
  expect(fallo.cuerpo.detail).toBe(
    `No se pudo enviar el correo a ${cuenta.correo}. La contraseña no fue modificada. Verifique el servicio de correo e inténtelo de nuevo.`,
  );
  await expect(page.getByText(fallo.cuerpo.detail, { exact: true })).toBeVisible();
  await expect(cuadro(page)).toBeVisible();
  const sesion = await page.evaluate(() => fetch('/api/auth/session').then((r) => r.json()));
  expect(Boolean(sesion && sesion.user), 'la sesión del Administrador debe seguir activa').toBe(true);

  // Reintentar: con el correo disponible, el mismo cuadro termina el reseteo.
  await control.correoFalla(false);
  const reintento = await confirmar();
  expect(reintento.estado).toBe(200);
  await expect(cuadro(page)).toBeHidden();
  await page.reload();
  expect(new URL(page.url()).pathname).toBe(RUTA);
  await expect(page.getByRole('grid', { name: 'Tabla de usuarios' })).toBeVisible();
});
