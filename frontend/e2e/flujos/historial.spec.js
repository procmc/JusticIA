// Historial de Actividades (spec 005a, T9): RF-21.40, el detalle de los registros de cuentas y de recuperación (RF-21.3, RF-21.6,
// RF-22; CU-15 FA-01). Spec retroactiva: sigue al ERS (RF-21 «Contenido del registro», RF-22 «Detalle y exportación»), no a lo
// que hoy hace el código. Corre en `escritorio` (1366) y `pequena` (616).
// Las filas se producen con la API real de la instancia (cuentas y recuperación); el navegador solo las consulta como
// Administrador. Las contraseñas y los códigos viven solo en la memoria de la prueba y nunca se imprimen.
const crypto = require('node:crypto');
const { test, expect, fallaEsperada, iniciarSesion, pulsar, escribir } = require('../soporte/fixtures.js');

const RUTA = '/administracion/bitacora';

const cedulaNueva = () => `9${crypto.randomInt(0, 1_000_000_000).toString().padStart(9, '0')}`;
const correoNuevo = (sufijo) => `prueba${crypto.randomInt(0, 1_000_000_000)}.${sufijo}@prueba.invalid`;

// --- API de la instancia (Node, no la API `request` de Playwright: no entra en trazas ni informes) ---

async function llamar(control, metodo, ruta, cuerpo, token) {
  const cabeceras = { 'Content-Type': 'application/json' };
  if (token) cabeceras.Authorization = `Bearer ${token}`;
  const respuesta = await fetch(`${control.url}${ruta}`, { method: metodo, headers: cabeceras, body: cuerpo ? JSON.stringify(cuerpo) : undefined });
  const texto = await respuesta.text();
  let datos = null;
  try { datos = texto ? JSON.parse(texto) : null; } catch { datos = texto; }
  return { estado: respuesta.status, datos };
}

async function tokenDe(control, usuario) {
  const respuesta = await llamar(control, 'POST', '/auth/login', { email: usuario.correo, password: usuario.contrasena });
  expect(respuesta.estado).toBe(200);
  return respuesta.datos.access_token;
}

// Una cuenta de Usuario Gubernamental creada por el Administrador (la API devuelve si el correo salió).
async function crearCuenta(control, token) {
  const cedula = cedulaNueva();
  const respuesta = await llamar(control, 'POST', '/usuarios/', {
    cedula, nombre_usuario: `prueba${cedula}`, nombre: 'PRUEBA Historial', apellido_uno: 'PRUEBA Uno', apellido_dos: 'PRUEBA Dos',
    correo: correoNuevo('historial'), id_rol: 2,
  }, token);
  expect(respuesta.estado).toBe(200);
  return { cedula, entregada: respuesta.datos.notificacion_entregada };
}

const resetear = (control, token, cedula) => llamar(control, 'POST', `/usuarios/${cedula}/resetear-contrasenna`, undefined, token);

// El correo sale después de responder: se espera a que llegue al buzón simulado. Las comparaciones son booleanas.
async function leerCodigo(control, correo) {
  await expect.poll(
    () => control.codigoCorreo(correo).then(() => true, () => false),
    { timeout: 10_000, intervals: [100, 250, 500] },
  ).toBe(true);
  const { codigo } = await control.codigoCorreo(correo);
  expect(/^[0-9]{6}$/.test(codigo)).toBe(true);
  return codigo;
}

// --- Pantalla ---

const tabla = (page) => page.getByRole('grid', { name: 'Tabla de registros de bitácora' });
const filaDe = (page, texto) => tabla(page).getByRole('row').filter({ hasText: texto });
const detalle = (page) => page.getByRole('dialog');

async function abrirHistorial(page) {
  await page.goto(RUTA);
  await expect(page.getByText('Registros de Bitácora')).toBeVisible();
  await page.waitForFunction(() => Boolean(window.next && window.next.router && window.next.router.isReady));
}

async function buscar(page) {
  const [respuesta] = await Promise.all([
    page.waitForResponse((r) => new URL(r.url()).pathname.includes('/bitacora/registros') && r.request().method() === 'GET'),
    pulsar(page.getByRole('button', { name: 'Buscar' })),
  ]);
  expect(respuesta.status()).toBe(200);
}

// Filtra por el correo del usuario que hizo la acción.
async function filtrarPorUsuario(page, correo) {
  await escribir(page.getByPlaceholder('Nombre, apellido o correo'), correo);
  await buscar(page);
}

async function filtrarPorTipo(page, tipo) {
  await pulsar(page.getByRole('button', { name: /Tipo de Acción/ }));
  await pulsar(page.getByRole('option', { name: tipo, exact: true }));
  await buscar(page);
}

// Abre el detalle de la fila que contiene el texto y lo devuelve; `cerrar` lo cierra para abrir otro.
async function abrirDetalle(page, texto) {
  const fila = filaDe(page, texto);
  await expect(fila, `fila «${texto}»`).toHaveCount(1);
  await pulsar(fila.getByRole('button'));
  await expect(detalle(page)).toBeVisible();
  await expect(detalle(page).getByText(/Detalle del Evento #/)).toBeVisible();
  return detalle(page);
}

async function cerrarDetalle(page) {
  await pulsar(detalle(page).getByRole('button', { name: 'Cerrar' }));
  await expect(detalle(page)).toBeHidden();
}

test.describe('RF-21.40 · Historial de Actividades', () => {
  test('RF-21.40 · detalle de creación y reseteo', async ({ page, crearUsuario, control, consola }) => {
    // El reseteo con el correo en fallo responde 502: lo provoca esta prueba.
    consola.provocado(/status of 502/);
    const administrador = await crearUsuario('administrador');
    const token = await tokenDe(control, administrador);

    // Dos cuentas y dos reseteos: uno con el correo entregado y otro con el correo en fallo.
    const entregada = await crearCuenta(control, token);
    expect(entregada.entregada).toBe(true);
    expect((await resetear(control, token, entregada.cedula)).estado).toBe(200);
    await control.correoFalla(true);
    const noEntregada = await crearCuenta(control, token);
    expect(noEntregada.entregada).toBe(false);
    expect((await resetear(control, token, noEntregada.cedula)).estado).toBe(502);
    await control.correoFalla(false);

    await iniciarSesion(page, administrador.correo, administrador.contrasena);
    await abrirHistorial(page);
    await filtrarPorUsuario(page, administrador.correo);

    const casos = [
      ['creación con el correo entregado', `Creación de usuario: PRUEBA Historial PRUEBA Uno PRUEBA Dos (Cédula: ${entregada.cedula})`, 'Entregada', 'No entregada'],
      ['reseteo con el correo entregado', `Reseteo de contraseña de usuario: ${entregada.cedula}`, 'Entregada', 'No entregada'],
      ['creación con el correo en fallo', `Creación de usuario: PRUEBA Historial PRUEBA Uno PRUEBA Dos (Cédula: ${noEntregada.cedula})`, 'No entregada', 'Entregada'],
      ['reseteo con el correo en fallo', `Intento de reseteo de contraseña de usuario: ${noEntregada.cedula}`, 'No entregada', 'Entregada'],
    ];
    for (const [caso, fila, esperado, contrario] of casos) {
      const panel = await abrirDetalle(page, fila);
      await expect(panel.getByText('Notificación por correo', { exact: true }), caso).toBeVisible();
      await expect(panel.getByText(esperado, { exact: true }), caso).toBeVisible();
      await expect(panel.getByText(contrario, { exact: true }), caso).toHaveCount(0);
      await cerrarDetalle(page);
    }
  });

  test('RF-21.40 · detalle de recuperación', async ({ page, crearUsuario, generadorContrasenas, control }) => {
    const administrador = await crearUsuario('administrador');
    const cuenta = await crearUsuario('usuario');
    const nueva = generadorContrasenas.siguiente();

    // Los cuatro pasos de una recuperación, por la API: solicitud, código incorrecto, código correcto y contraseña nueva.
    const solicitud = await llamar(control, 'POST', '/auth/solicitar-recuperacion', { email: cuenta.correo });
    expect(solicitud.estado).toBe(200);
    const codigo = await leerCodigo(control, cuenta.correo);
    const erroneo = codigo.slice(0, 5) + String((Number(codigo[5]) + 1) % 10);
    expect((await llamar(control, 'POST', '/auth/verificar-codigo', { token: solicitud.datos.token, codigo: erroneo })).estado).toBe(400);
    const verificado = await llamar(control, 'POST', '/auth/verificar-codigo', { token: solicitud.datos.token, codigo });
    expect(verificado.estado).toBe(200);
    const cambio = await llamar(control, 'POST', '/auth/cambiar-contrasenna-recuperacion',
      { verificationToken: verificado.datos.verificationToken, nuevaContrasenna: nueva });
    expect(cambio.estado).toBe(200);

    await iniciarSesion(page, administrador.correo, administrador.contrasena);
    await abrirHistorial(page);
    await filtrarPorUsuario(page, cuenta.correo);

    const pasos = [
      ['solicitud', 'Solicitud de recuperación de contraseña para', 'Solicitud', 'Código enviado'],
      ['código incorrecto', 'Verificación del código de recuperación de contraseña: código incorrecto', 'Verificación del código', 'Código incorrecto'],
      ['código verificado', 'Verificación del código de recuperación de contraseña: código verificado', 'Verificación del código', 'Código verificado'],
      ['contraseña nueva', 'Cambio de contraseña por recuperación: contraseña cambiada', 'Cambio de contraseña', 'Contraseña cambiada'],
    ];
    for (const [caso, fila, paso, resultado] of pasos) {
      const panel = await abrirDetalle(page, fila);
      await expect(panel.getByText('Paso', { exact: true }), caso).toBeVisible();
      await expect(panel.getByText(paso, { exact: true }), caso).toBeVisible();
      await expect(panel.getByText('Resultado', { exact: true }), caso).toBeVisible();
      await expect(panel.getByText(resultado, { exact: true }), caso).toBeVisible();
      // Sin el código ni la contraseña (RF-21).
      const texto = await panel.innerText();
      expect(texto.includes(codigo), `${caso}: el detalle no trae el código`).toBe(false);
      expect(texto.includes(nueva), `${caso}: el detalle no trae la contraseña`).toBe(false);
      await cerrarDetalle(page);
    }
  });

  test('RF-21.40 · filtro trae recuperaciones sin usuario', async ({ page, crearUsuario, control }) => {
    const administrador = await crearUsuario('administrador');
    const cuenta = await crearUsuario('usuario');
    const sinCuenta = correoNuevo('sinregistro');

    // Una solicitud de una cuenta registrada y otra de un correo que no existe (esa fila no tiene usuario asociado).
    expect((await llamar(control, 'POST', '/auth/solicitar-recuperacion', { email: cuenta.correo })).estado).toBe(200);
    expect((await llamar(control, 'POST', '/auth/solicitar-recuperacion', { email: sinCuenta })).estado).toBe(200);

    await iniciarSesion(page, administrador.correo, administrador.contrasena);
    await abrirHistorial(page);
    await filtrarPorTipo(page, 'Recuperación de Contraseña');

    // El filtro por tipo trae las dos: la de la cuenta y la que no tiene usuario.
    const conUsuario = filaDe(page, cuenta.correo);
    const sinUsuario = filaDe(page, `Solicitud de recuperación de contraseña para ${sinCuenta}`);
    await expect(conUsuario).toHaveCount(1);
    await expect(sinUsuario).toHaveCount(1);
    // La fila de la cuenta nombra a su usuario y la otra no nombra a ninguna de las cuentas de la prueba (la primera celda de
    // datos es la del usuario; la fecha es el encabezado de la fila).
    await expect(conUsuario.getByRole('gridcell').first()).toContainText(cuenta.correo);
    await expect(sinUsuario.getByRole('gridcell').first()).not.toContainText(cuenta.correo);
    await expect(sinUsuario.getByRole('gridcell').first()).not.toContainText(administrador.correo);

    const panel = await abrirDetalle(page, `Solicitud de recuperación de contraseña para ${sinCuenta}`);
    // El ERS (RF-21, RF-22) pide el paso y su resultado; no fija cómo se nombra al usuario ausente.
    await expect(panel.getByText('Paso', { exact: true })).toBeVisible();
    await expect(panel.getByText('Solicitud', { exact: true })).toBeVisible();
    await expect(panel.getByText('Resultado', { exact: true })).toBeVisible();
    await expect(panel.getByText('Correo no registrado', { exact: true })).toBeVisible();
  });
  test('RF-22 (ERS, no fijado en la spec 005a) · la hora del registro es la hora actual de Costa Rica', async ({ page, crearUsuario, control }) => {
    // La spec 005a no fija la hora; el ERS (RF-21 «Contenido del registro» y RF-22) pide la fecha y hora exacta de cada acción, que la tabla muestra en la
    // hora de Costa Rica (UTC-6). Un registro recién hecho debe verse con la hora de ahora, con unos minutos de margen.
    const administrador = await crearUsuario('administrador');
    const cuenta = await crearUsuario('usuario');
    expect((await llamar(control, 'POST', '/auth/solicitar-recuperacion', { email: cuenta.correo })).estado).toBe(200);

    await iniciarSesion(page, administrador.correo, administrador.contrasena);
    await abrirHistorial(page);
    await filtrarPorUsuario(page, cuenta.correo);
    const fila = filaDe(page, 'Solicitud de recuperación de contraseña para');
    await expect(fila).toHaveCount(1);
    const mostrado = await fila.getByRole('rowheader').innerText();

    // «dd/MM/yyyy» y «hh:mm:ss a» (o sin segundos), en la hora de Costa Rica.
    const [, dia, mes, anio, hora12, minuto, , periodo] = /(\d{2})\/(\d{2})\/(\d{4})\s+(\d{1,2}):(\d{2})(:\d{2})?\s*([AaPp])/.exec(mostrado) || [];
    expect(hora12, `no se pudo leer la fecha y hora de «${mostrado.replace(/\s+/g, ' ')}»`).toBeDefined();
    const hora24 = (Number(hora12) % 12) + (periodo.toLowerCase() === 'p' ? 12 : 0);
    const mostradoEnMinutos = Date.UTC(Number(anio), Number(mes) - 1, Number(dia), hora24, Number(minuto)) / 60_000;
    const ahora = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'America/Costa_Rica', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    }).formatToParts(new Date()).reduce((acc, parte) => ({ ...acc, [parte.type]: parte.value }), {});
    const ahoraEnMinutos = Date.UTC(Number(ahora.year), Number(ahora.month) - 1, Number(ahora.day), Number(ahora.hour), Number(ahora.minute)) / 60_000;
    expect(Math.abs(ahoraEnMinutos - mostradoEnMinutos), `mostrado «${mostrado.replace(/\s+/g, ' ')}»`).toBeLessThanOrEqual(5);
  });
});
