// Recuperación de contraseña (spec 005a, T9): RF-03.41, la vía (b) de RF-03 en sus tres pantallas (CU-04). Spec retroactiva:
// cada prueba sigue al ERS (RF-03 «Reglas y validaciones», «Manejo de errores» y «Salida»), no a lo que hoy hace el código.
// Corre en `escritorio` (1366) y `pequena` (616). RF-03 limita a una solicitud por minuto y cinco por hora para cada correo,
// así que cada flujo usa su propio usuario `PRUEBA`. El código se lee del correo simulado por el control: nunca se imprime
// ni se compara con lo que recibe el navegador salvo para comprobar que no viaja. Las contraseñas las genera la suite.
const crypto = require('node:crypto');
const { test, expect, iniciarSesion, pulsar, escribir } = require('../soporte/fixtures.js');

const RUTA = '/auth/recuperar-contrasenna';

// Textos que fija el ERS (RF-03).
const MENSAJE_UNIFORME = 'Si el correo existe en nuestro sistema, recibirás un email con las instrucciones';
const MENSAJE_SERVICIO = 'El servicio de recuperación de contraseña no está disponible por el momento. Inténtalo de nuevo más tarde.';
const MENSAJE_CAMBIADA = 'Contraseña recuperada exitosamente';

// Estados HTTP que cerrarían la sesión de la persona: la recuperación nunca debe devolverlos.
const ESTADOS_QUE_CIERRAN_SESION = [401, 403, 404];
// Lo que Chrome escribe en la consola cuando la API responde con un error que la prueba provoca a propósito.
const ERROR_PROVOCADO = /status of (400|429|503)/;

const correoNuevo = () => `prueba${crypto.randomInt(0, 1_000_000_000)}.sinregistro@prueba.invalid`;

const campoCorreo = (page) => page.getByLabel('Correo electrónico');
const botonEnviar = (page) => page.getByRole('button', { name: 'Enviar Código' });
const campoCodigo = (page) => page.locator('input[autocomplete="one-time-code"]');
const botonVerificar = (page) => page.getByRole('button', { name: 'Verificar Código' });
const botonCambiarCorreo = (page) => page.getByRole('button', { name: 'Cambiar correo electrónico' });
const botonNuevoCodigo = (page) => page.getByRole('button', { name: 'Solicitar nuevo código' });
const campoNueva = (page) => page.getByLabel('Nueva contraseña', { exact: true });
const campoConfirmar = (page) => page.getByLabel('Confirmar nueva contraseña');
const botonCambiar = (page) => page.getByRole('button', { name: 'Cambiar Contraseña' });
const pasoVerificar = (page) => page.getByRole('heading', { name: 'Verificar Código' });
const pasoNuevaContrasena = (page) => page.getByRole('heading', { name: 'Nueva Contraseña' });
// Los avisos de la pantalla (toast) llevan `role="alert"`; se ubican por el texto que debe mostrar.
const aviso = (page, texto) => page.getByRole('alert').filter({ hasText: texto });

async function abrir(page) {
  await page.goto(RUTA);
  await page.waitForFunction(() => Boolean(window.next && window.next.router && window.next.router.isReady));
  await expect(campoCorreo(page)).toBeVisible();
}

const esDe = (ruta) => (r) => new URL(r.url()).pathname.endsWith(ruta) && r.request().method() === 'POST';

async function leerRespuesta(respuesta) {
  const texto = await respuesta.text();
  let cuerpo = null;
  try { cuerpo = JSON.parse(texto); } catch { cuerpo = { detail: texto }; }
  return { estado: respuesta.status(), cuerpo };
}

// Paso 1: escribe el correo y pulsa «Enviar Código». Devuelve la respuesta de la API.
async function solicitar(page, correo) {
  await escribir(campoCorreo(page), correo);
  const [respuesta] = await Promise.all([
    page.waitForResponse(esDe('/auth/solicitar-recuperacion')),
    pulsar(botonEnviar(page)),
  ]);
  return leerRespuesta(respuesta);
}

// Paso 2: escribe el código de 6 dígitos y pulsa «Verificar Código». Devuelve la respuesta de la API.
async function verificar(page, codigo) {
  await escribir(campoCodigo(page), codigo);
  await expect(botonVerificar(page)).toBeEnabled();
  const [respuesta] = await Promise.all([
    page.waitForResponse(esDe('/auth/verificar-codigo')),
    pulsar(botonVerificar(page)),
  ]);
  return leerRespuesta(respuesta);
}

// El correo sale después de responder: se espera a que llegue al buzón simulado. Con `anterior`, a que llegue uno distinto.
// Las comparaciones son booleanas: el código nunca se imprime.
async function leerCodigo(control, correo, anterior = null) {
  await expect.poll(
    async () => {
      try {
        const { codigo } = await control.codigoCorreo(correo);
        return anterior === null || codigo !== anterior;
      } catch {
        return false;
      }
    },
    { timeout: 10_000, intervals: [100, 250, 500] },
  ).toBe(true);
  const { codigo } = await control.codigoCorreo(correo);
  expect(/^[0-9]{6}$/.test(codigo)).toBe(true);
  return codigo;
}

// Un código de 6 dígitos que no es el del correo.
const codigoErroneo = (codigo) => codigo.slice(0, 5) + String((Number(codigo[5]) + 1) % 10);

// La persona sigue en la recuperación: sin «Sesión expirada» ni redirección (los errores de la API nunca la sacan de ahí).
async function exigirSinRedireccion(page) {
  expect(new URL(page.url()).pathname).toBe(RUTA);
  await expect(page.getByText('Sesión expirada')).toHaveCount(0);
}

test.describe('RF-03.41 · recuperación de contraseña', () => {
  test('RF-03.41 · mensaje uniforme en tres casos', async ({ page, crearUsuario, consola }) => {
    consola.provocado(ERROR_PROVOCADO);
    const registrado = await crearUsuario('usuario');
    const inactivo = await crearUsuario('usuario', { inactivo: true });
    const casos = [
      ['registrado', registrado.correo],
      ['no registrado', correoNuevo()],
      ['Inactivo', inactivo.correo],
    ];

    const vistos = [];
    for (const [caso, correo] of casos) {
      await abrir(page);
      const respuesta = await solicitar(page, correo);
      expect(respuesta.estado, caso).toBe(200);
      expect(respuesta.cuerpo.message, caso).toBe(MENSAJE_UNIFORME);

      // Siempre avanza al paso de verificación y el aviso es informativo (no de éxito).
      await expect(pasoVerificar(page), caso).toBeVisible();
      const informativo = aviso(page, MENSAJE_UNIFORME);
      await expect(informativo, caso).toBeVisible();
      await expect(informativo, caso).toContainText('Información');
      await expect(informativo, caso).not.toContainText('Éxito');
      // No afirma que el código se envió.
      expect(await informativo.textContent(), caso).not.toMatch(/enví[oó]|enviad[oa]|enviamos|se ha enviado/i);
      vistos.push({ estado: respuesta.estado, mensaje: respuesta.cuerpo.message, titulo: 'Información' });
    }
    // Los tres casos dan exactamente lo mismo.
    expect(vistos[1]).toEqual(vistos[0]);
    expect(vistos[2]).toEqual(vistos[0]);
  });

  test('RF-03.41 · sin afirmar ni negar la cuenta', async ({ page, crearUsuario, control, consola }) => {
    consola.provocado(ERROR_PROVOCADO);
    // Lo que nunca debe decir una pantalla de la recuperación: que la cuenta existe o no, está inactiva o se pidieron demasiados códigos.
    const REVELA = /no registrad|no existe|no está registrad|inactiv|desactivad|demasiados intentos|límite/i;
    const registrado = await crearUsuario('usuario');
    const inactivo = await crearUsuario('usuario', { inactivo: true });
    const repetido = await crearUsuario('usuario');

    const textoDeLaPantalla = (pagina) => pagina.locator('body').innerText();
    const codigoDeVerificacion = [];
    for (const [caso, correo] of [['registrado', registrado.correo], ['no registrado', correoNuevo()], ['Inactivo', inactivo.correo]]) {
      await abrir(page);
      await solicitar(page, correo);
      await expect(pasoVerificar(page), caso).toBeVisible();
      await expect(aviso(page, MENSAJE_UNIFORME), caso).toBeVisible();
      expect(await textoDeLaPantalla(page), `${caso}: paso 2`).not.toMatch(REVELA);

      // El mismo código incorrecto en los tres casos: la misma respuesta y el mismo aviso.
      let erroneo = '123456';
      if (caso === 'registrado') erroneo = codigoErroneo(await leerCodigo(control, correo));
      const respuesta = await verificar(page, erroneo);
      expect(ESTADOS_QUE_CIERRAN_SESION, `${caso}: estado ${respuesta.estado}`).not.toContain(respuesta.estado);
      expect(respuesta.estado, caso).toBe(400);
      await expect(aviso(page, respuesta.cuerpo.detail), caso).toBeVisible();
      expect(await textoDeLaPantalla(page), `${caso}: tras el código incorrecto`).not.toMatch(REVELA);
      codigoDeVerificacion.push({ estado: respuesta.estado, detalle: respuesta.cuerpo.detail });
    }
    expect(codigoDeVerificacion[1]).toEqual(codigoDeVerificacion[0]);
    expect(codigoDeVerificacion[2]).toEqual(codigoDeVerificacion[0]);

    // Un límite de solicitudes alcanzado (segunda solicitud en menos de un minuto): la misma pantalla, sin avisar del límite.
    await abrir(page);
    await solicitar(page, repetido.correo);
    await expect(pasoVerificar(page)).toBeVisible();
    await pulsar(botonCambiarCorreo(page));
    await expect(campoCorreo(page)).toBeVisible();
    const segunda = await solicitar(page, repetido.correo);
    expect(segunda.estado).toBe(200);
    expect(segunda.cuerpo.message).toBe(MENSAJE_UNIFORME);
    await expect(pasoVerificar(page)).toBeVisible();
    // Quedan los avisos de las dos solicitudes: el de la segunda es el mismo.
    await expect(aviso(page, MENSAJE_UNIFORME)).toHaveCount(2);
    expect(await textoDeLaPantalla(page), 'límite alcanzado').not.toMatch(REVELA);
  });

  test('RF-03.41 · código incorrecto, vencido y almacén no disponible', async ({ page, crearUsuario, control, consola }) => {
    consola.provocado(ERROR_PROVOCADO);

    await test.step('código incorrecto: mensaje de la API y se puede reintentar', async () => {
      const usuario = await crearUsuario('usuario');
      await abrir(page);
      await solicitar(page, usuario.correo);
      const codigo = await leerCodigo(control, usuario.correo);

      const incorrecto = await verificar(page, codigoErroneo(codigo));
      expect(ESTADOS_QUE_CIERRAN_SESION).not.toContain(incorrecto.estado);
      expect(incorrecto.estado).toBe(400);
      expect(typeof incorrecto.cuerpo.detail).toBe('string');
      await expect(aviso(page, incorrecto.cuerpo.detail)).toBeVisible();
      await exigirSinRedireccion(page);
      // Reintentar: sigue en la verificación, con el campo libre, y el código del correo avanza.
      await expect(pasoVerificar(page)).toBeVisible();
      await expect(campoCodigo(page)).toBeEnabled();
      const correcto = await verificar(page, codigo);
      expect(correcto.estado).toBe(200);
      await expect(pasoNuevaContrasena(page)).toBeVisible();
    });

    await test.step('código vencido: mensaje de la API y se puede pedir uno nuevo', async () => {
      const usuario = await crearUsuario('usuario');
      await abrir(page);
      await solicitar(page, usuario.correo);
      const codigo = await leerCodigo(control, usuario.correo);
      // El código vale 15 minutos: se adelanta el tiempo del almacén en vez de esperar.
      await control.reloj(901);

      const vencido = await verificar(page, codigo);
      expect(ESTADOS_QUE_CIERRAN_SESION).not.toContain(vencido.estado);
      expect(vencido.estado).toBe(400);
      expect(typeof vencido.cuerpo.detail).toBe('string');
      await expect(aviso(page, vencido.cuerpo.detail)).toBeVisible();
      await exigirSinRedireccion(page);

      // Pedir uno nuevo: vuelve al primer paso, el correo trae otro código y ese sí sirve.
      await pulsar(botonCambiarCorreo(page));
      await expect(campoCorreo(page)).toBeVisible();
      const nueva = await solicitar(page, usuario.correo);
      expect(nueva.estado).toBe(200);
      await expect(pasoVerificar(page)).toBeVisible();
      const codigoNuevo = await leerCodigo(control, usuario.correo, codigo);
      const aceptado = await verificar(page, codigoNuevo);
      expect(aceptado.estado).toBe(200);
      await expect(pasoNuevaContrasena(page)).toBeVisible();
    });

    await test.step('almacén no disponible al pedir el código: el mismo mensaje y se puede reintentar', async () => {
      const usuario = await crearUsuario('usuario');
      await control.almacen(false, 'conexion');
      await abrir(page);
      const caida = await solicitar(page, usuario.correo);
      expect(ESTADOS_QUE_CIERRAN_SESION).not.toContain(caida.estado);
      expect(caida.estado).toBe(503);
      // El ERS (RF-03 «Manejo de errores») fija el texto.
      expect(caida.cuerpo.detail).toBe(MENSAJE_SERVICIO);
      await expect(aviso(page, MENSAJE_SERVICIO)).toBeVisible();
      await exigirSinRedireccion(page);
      await expect(campoCorreo(page)).toBeVisible();

      await control.almacen(true);
      const recuperada = await solicitar(page, usuario.correo);
      expect(recuperada.estado).toBe(200);
      await expect(pasoVerificar(page)).toBeVisible();
    });

    await test.step('almacén no disponible al verificar el código: el mismo mensaje y se puede reintentar', async () => {
      const usuario = await crearUsuario('usuario');
      await abrir(page);
      await solicitar(page, usuario.correo);
      const codigo = await leerCodigo(control, usuario.correo);

      await control.almacen(false, 'tiempo');
      const caida = await verificar(page, codigo);
      expect(ESTADOS_QUE_CIERRAN_SESION).not.toContain(caida.estado);
      expect(caida.estado).toBe(503);
      expect(caida.cuerpo.detail).toBe(MENSAJE_SERVICIO);
      await expect(aviso(page, MENSAJE_SERVICIO).first()).toBeVisible();
      await exigirSinRedireccion(page);
      await expect(pasoVerificar(page)).toBeVisible();

      await control.almacen(true);
      const recuperada = await verificar(page, codigo);
      expect(recuperada.estado).toBe(200);
      await expect(pasoNuevaContrasena(page)).toBeVisible();
    });
  });

  test('RF-03.41 · cinco intentos', async ({ page, crearUsuario, control, consola }) => {
    consola.provocado(ERROR_PROVOCADO);
    const usuario = await crearUsuario('usuario');
    await abrir(page);
    await solicitar(page, usuario.correo);
    const erroneo = codigoErroneo(await leerCodigo(control, usuario.correo));

    // Cuatro intentos fallidos: cada uno solo informa que el código es incorrecto.
    for (let intento = 1; intento <= 4; intento += 1) {
      const respuesta = await verificar(page, erroneo);
      expect(respuesta.estado, `intento ${intento}`).toBe(400);
      await expect(aviso(page, respuesta.cuerpo.detail).first(), `intento ${intento}`).toBeVisible();
      await expect(campoCodigo(page), `intento ${intento}`).toBeEnabled();
    }

    // El quinto invalida el código: el mensaje de RF-03.9 (pedir uno nuevo y, si se pidió hace menos de un minuto, esperar).
    const quinto = await verificar(page, erroneo);
    expect(ESTADOS_QUE_CIERRAN_SESION).not.toContain(quinto.estado);
    const detalle = quinto.cuerpo.detail;
    expect(typeof detalle).toBe('string');
    expect(detalle).toMatch(/nuevo código/i);
    expect(detalle).toMatch(/minuto/i);
    await expect(page.getByText(detalle, { exact: true })).toBeVisible();
    await exigirSinRedireccion(page);
    // Con el código invalidado solo se puede pedir otro.
    await expect(campoCodigo(page)).toBeDisabled();
    await expect(botonVerificar(page)).toBeDisabled();
    await pulsar(botonNuevoCodigo(page));
    await expect(campoCorreo(page)).toBeVisible();
  });

  test('RF-03.41 · código del correo simulado y nueva contraseña', async ({ page, crearUsuario, generadorContrasenas, control }) => {
    const usuario = await crearUsuario('usuario');
    const nueva = generadorContrasenas.siguiente();
    await abrir(page);
    const solicitud = await solicitar(page, usuario.correo);
    expect(solicitud.estado).toBe(200);
    await expect(pasoVerificar(page)).toBeVisible();

    // El código se lee del correo simulado; lo que recibió el navegador no lo trae.
    const codigo = await leerCodigo(control, usuario.correo);
    const verificacion = await verificar(page, codigo);
    expect(verificacion.estado).toBe(200);
    expect(JSON.stringify(solicitud.cuerpo).includes(codigo), 'la solicitud no devuelve el código').toBe(false);
    expect(JSON.stringify(verificacion.cuerpo).includes(codigo), 'la verificación no devuelve el código').toBe(false);

    // Define la nueva contraseña (escrita dos veces) y la API la acepta.
    await expect(pasoNuevaContrasena(page)).toBeVisible();
    await escribir(campoNueva(page), nueva);
    await escribir(campoConfirmar(page), nueva);
    const [respuesta] = await Promise.all([
      page.waitForResponse(esDe('/auth/cambiar-contrasenna-recuperacion')),
      pulsar(botonCambiar(page)),
    ]);
    const cambio = await leerRespuesta(respuesta);
    expect(cambio.estado).toBe(200);
    // El ERS (RF-03 «Salida») fija el texto de éxito.
    expect(cambio.cuerpo.message).toBe(MENSAJE_CAMBIADA);
    await expect(aviso(page, MENSAJE_CAMBIADA)).toBeVisible();

    // Regresa a «Inicio de sesión» y la contraseña nueva sirve para entrar.
    await page.waitForURL((url) => url.pathname === '/auth/login', { timeout: 10_000 });
    await expect(page.getByRole('heading', { name: 'Inicio de sesión' })).toBeVisible();
    await iniciarSesion(page, usuario.correo, nueva);
  });
});
