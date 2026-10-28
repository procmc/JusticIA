// Capacidades del control (spec 005a, RA-02.49). T5: recuperación y bitácora (RF-02.42, RF-03.40, RF-03.41, RF-21.40,
// RF-21.41, RF-22.40). T6: motor, ingesta y notebooks, que usará la 005b (RF-11.40-43, RF-16.40, RF-18.40, RF-19.41,
// RF-19.42). Sin navegador: hablan con la API real de la instancia y con el control.
// El código del correo y las contraseñas nunca se imprimen: las aserciones comparan booleanos, no valores.
const { test, expect } = require('../soporte/fixtures.js');
const {
  PNG_MINIMO, aleatorio, nuevoTema, enviar, iniciarSesion, documentoDePrueba, cargar, estadoDeLaTarea, esperarTarea,
  subirYProcesar, textoDeLosEventos, preguntar, abrirConsulta, rutaCitada, notebookConDocumento, crearNotebook, listarDocumentos,
} = require('../soporte/datos.js');

const solicitar = (control, correo) => enviar(control, 'POST', '/auth/solicitar-recuperacion', { email: correo });
const verificar = (control, token, codigo) => enviar(control, 'POST', '/auth/verificar-codigo', { token, codigo });

// El correo sale después de responder (tarea posterior): se espera a que el código llegue al buzón simulado.
async function leerCodigo(control, correo) {
  await expect.poll(
    () => control.codigoCorreo(correo).then(() => true, () => false),
    { timeout: 10_000, intervals: [100, 250, 500] },
  ).toBe(true);
  const { codigo } = await control.codigoCorreo(correo);
  expect(/^[0-9]{6}$/.test(codigo)).toBe(true);
  return codigo;
}

test.describe('capacidades del control: recuperación y bitácora', () => {
  test('RF-03.41 · código del correo por el control', async ({ control, crearUsuario }) => {
    const usuario = await crearUsuario('usuario');
    const solicitud = await solicitar(control, usuario.correo);
    expect(solicitud.status).toBe(200);
    const cuerpo = await solicitud.json();

    const codigo = await leerCodigo(control, usuario.correo);
    // Lo que recibe el navegador (la respuesta de la API) nunca trae el código.
    expect(JSON.stringify(cuerpo).includes(codigo)).toBe(false);
    // El código leído sirve: la API lo acepta.
    expect((await verificar(control, cuerpo.token, codigo)).status).toBe(200);

    // Sin correo enviado a esa dirección no hay código; sin token, 403.
    await expect(control.codigoCorreo('nadie@prueba.invalid')).rejects.toThrow(/404/);
    const sinToken = await fetch(`${control.url}/pruebas-e2e/correo/codigo?a=${encodeURIComponent(usuario.correo)}`,
      { headers: { 'X-Control-Pruebas': 'token-incorrecto' } });
    expect(sinToken.status).toBe(403);
  });

  test('RF-02.42 · correo en fallo: el reseteo no se entrega y el control lo restablece', async ({ control, crearUsuario }) => {
    const administrador = await crearUsuario('administrador');
    const primero = await crearUsuario('usuario');
    const segundo = await crearUsuario('usuario');
    const token = await iniciarSesion(control, administrador);
    const resetear = (u) => enviar(control, 'POST', `/usuarios/${u.cedula}/resetear-contrasenna`, undefined, token);

    expect((await control.capacidades()).correo_en_fallo).toBe(false);
    expect((await resetear(primero)).status).toBe(200);
    expect((await control.capacidades()).correos_enviados).toBe(1);

    await control.correoFalla(true);
    expect((await control.capacidades()).correo_en_fallo).toBe(true);
    const fallida = await resetear(segundo);
    expect(fallida.status).toBe(502);
    expect(typeof (await fallida.json()).detail).toBe('string');
    expect((await control.capacidades()).correos_enviados).toBe(2); // el intento quedó registrado en el buzón simulado

    await control.correoFalla(false);
    expect((await control.capacidades()).correo_en_fallo).toBe(false);
  });

  test('RF-03.41 · almacén no disponible: error de servicio uniforme y la limpieza lo restablece', async ({ control, crearUsuario }) => {
    const usuario = await crearUsuario('usuario');
    for (const tipo of ['conexion', 'tiempo']) {
      await control.almacen(false, tipo);
      expect((await control.capacidades()).almacen_no_disponible).toBe(true);
      const respuesta = await solicitar(control, usuario.correo);
      // Nunca 401/403/404: la interfaz cerraría la sesión.
      expect(respuesta.status).toBe(503);
    }
    await control.almacen(true);
    expect((await control.capacidades()).almacen_no_disponible).toBe(false);
    expect((await solicitar(control, usuario.correo)).status).toBe(200);

    // Un fallo programado y olvidado lo deshace la limpieza (la que corre tras cada prueba).
    await control.almacen(false);
    await control.correoFalla(true);
    await control.limpiar();
    expect(await control.capacidades()).toEqual({ correo_en_fallo: false, almacen_no_disponible: false, correos_enviados: 0 });

    // Valores inválidos.
    await expect(control.almacen(false, 'otro')).rejects.toThrow(/400/);
  });

  test('RF-03.41 · reloj vence el código', async ({ control, crearUsuario }) => {
    const usuario = await crearUsuario('usuario');
    const solicitud = await solicitar(control, usuario.correo);
    expect(solicitud.status).toBe(200);
    const { token } = await solicitud.json();
    const codigo = await leerCodigo(control, usuario.correo);

    // El código vale 15 minutos (900 s): pasados, la API responde 400 (nunca 401/403/404) aunque el código sea el correcto.
    expect((await control.reloj(901)).avanzado).toBe(901);
    const vencido = await verificar(control, token, codigo);
    expect(vencido.status).toBe(400);
    expect(typeof (await vencido.json()).detail).toBe('string');

    await expect(control.reloj(0)).rejects.toThrow(/400/);
    await expect(control.reloj(-1)).rejects.toThrow(/400/);
  });

  test('RF-22.40 · filas de bitácora de cada tipo (carga, notebooks y conversación)', async ({ control, crearUsuario }) => {
    const administrador = await crearUsuario('administrador');
    const usuario = await crearUsuario('usuario');
    const tipos = {
      carga_iniciada: 'Carga iniciada',
      carga_inicio: 'Inicio del procesamiento',
      carga_almacenada: 'Documento almacenado',
      carga_terminada: 'Procesamiento terminado',
      carga_error: 'Error de procesamiento',
      carga_rechazada: 'Carga rechazada',
      carga_cancelada: 'Cancelación',
      carga_error_cancelacion: 'Error de cancelación',
      carga_error_general: 'Error de procesamiento',
    };
    const otros = {
      crear_notebook: 'Crear Notebook',
      quitar_documento_notebook: 'Quitar Documento de Notebook',
      gestionar_conversacion: 'Gestionar Conversación',
    };
    const ids = {};
    for (const tipo of [...Object.keys(tipos), ...Object.keys(otros)]) {
      const fila = await control.bitacora(usuario.cedula, tipo);
      expect(fila.tipo).toBe(tipo);
      ids[tipo] = fila.id;
    }
    expect(new Set(Object.values(ids)).size).toBe(12);

    const token = await iniciarSesion(control, administrador);
    const lista = await enviar(control, 'GET', `/bitacora/registros?usuario=${encodeURIComponent(usuario.cedula)}&limite=100`, undefined, token);
    expect(lista.status).toBe(200);
    const items = Object.fromEntries((await lista.json()).items.map((item) => [item.id, item]));

    for (const [tipo, visible] of Object.entries(tipos)) {
      const item = items[ids[tipo]];
      expect(item, tipo).toBeDefined();
      expect(item.tipoAccion, tipo).toBe('Carga de Documentos');
      expect(item.detalle_carga.tipo, tipo).toBe(visible);
    }
    for (const [tipo, visible] of Object.entries(otros)) {
      expect(items[ids[tipo]]?.tipoAccion, tipo).toBe(visible); // el nombre, no «Acción 16»
    }

    // Tipo desconocido, 400; sin token, 403.
    await expect(control.bitacora(usuario.cedula, 'inventado')).rejects.toThrow(/400/);
    const sinToken = await fetch(`${control.url}/pruebas-e2e/bitacora`, {
      method: 'POST', headers: { 'X-Control-Pruebas': 'token-incorrecto', 'Content-Type': 'application/json' },
      body: JSON.stringify({ cedula: usuario.cedula, tipo: 'carga_iniciada' }),
    });
    expect(sinToken.status).toBe(403);
  });
});

// --- T6: motor, ingesta y notebooks (las ayudas de datos están en soporte/datos.js) ---------------------------------------------

test.describe('capacidades del control: motor, ingesta y notebooks', () => {
  test('RA-02.49 · motor cita, retiene, secuencia, falla y no emite', async ({ control, crearUsuario }) => {
    const usuario = await crearUsuario('usuario');
    const token = await iniciarSesion(control, usuario);
    const temaA = nuevoTema();
    const temaB = nuevoTema();
    const docA = documentoDePrueba();
    const docB = documentoDePrueba();
    await subirYProcesar(control, token, temaA, docA);
    await subirYProcesar(control, token, temaB, docB);
    const pregunta = `¿Qué dice el documento sobre ${docB.frase}?`;

    // Cita: acotado al tema A cita solo el archivo de A aunque la pregunta sea por la frase de B; sin tema, también el de B.
    expect((await control.motorEstado()).modo).toBe('cita');
    const acotada = textoDeLosEventos(await preguntar(control, token, usuario, pregunta, { tema: temaA }));
    expect(acotada.includes(rutaCitada(temaA, docA))).toBe(true);
    expect(acotada.includes(docB.nombre)).toBe(false);
    const general = textoDeLosEventos(await preguntar(control, token, usuario, pregunta));
    expect(general.includes(rutaCitada(temaB, docB))).toBe(true);
    expect((await control.motorEstado()).consultas).toBe(2);

    // Retenida tras dos fragmentos: llega el texto parcial, la respuesta espera y al liberar llega el final.
    await control.motor({ modo: 'texto', texto: 'uno dos tres cuatro', retener_tras: 2 });
    const retenida = abrirConsulta(control, token, usuario, pregunta, { tema: temaA });
    await expect.poll(async () => (await control.motorEstado()).esperando, { timeout: 15_000 }).toBe(1);
    await expect.poll(() => retenida.visto.texto.includes('dos'), { timeout: 10_000 }).toBe(true);
    expect(retenida.visto.texto.includes('tres')).toBe(false);
    expect(retenida.visto.terminado).toBe(false);
    expect((await control.motorLiberar()).retenida).toBe(false);
    await retenida.fin;
    expect(retenida.visto.texto.includes('cuatro')).toBe(true);
    expect((await control.motorEstado()).esperando).toBe(0);

    // Secuencia (vacío y luego respuesta) en la MISMA conversación: la reformulación con historial no la consume.
    await control.motor({ secuencia: ['', 'Segunda respuesta de PRUEBA.'] });
    const sesion = `session_${usuario.cedula}_${aleatorio()}`;
    const primera = textoDeLosEventos(await preguntar(control, token, usuario, pregunta, { tema: temaA, sesion }));
    expect(primera.includes('Segunda respuesta')).toBe(false);
    expect((await control.motorEstado()).secuencia_pendiente).toBe(1);
    const segunda = textoDeLosEventos(await preguntar(control, token, usuario, pregunta, { tema: temaA, sesion }));
    expect(segunda.includes('Segunda respuesta de PRUEBA.')).toBe(true);
    expect((await control.motorEstado()).secuencia_pendiente).toBe(0);

    // Fallo por conexión: el error viaja dentro de la conversación, sin texto de respuesta, y el flujo cierra.
    await control.motor({ modo: 'conexion' });
    const caido = await preguntar(control, token, usuario, pregunta, { tema: temaA });
    const tipos = caido.map((e) => e.type);
    expect(tipos.includes('error')).toBe(true);
    expect(tipos.includes('chunk')).toBe(false);
    expect(tipos[tipos.length - 1]).toBe('done');

    // Sin emitir ningún dato: la respuesta queda abierta, sin un solo fragmento, hasta liberarla.
    await control.motor({ modo: 'sin_datos' });
    const callada = abrirConsulta(control, token, usuario, pregunta, { tema: temaA });
    await expect.poll(async () => (await control.motorEstado()).esperando, { timeout: 15_000 }).toBe(1);
    expect(callada.visto.terminado).toBe(false);
    expect(/"type":\s*"chunk"/.test(callada.visto.texto)).toBe(false);
    await control.motorLiberar();
    await callada.fin;
    expect(callada.visto.terminado).toBe(true);

    // Programación inválida y sin token.
    await expect(control.motor({ modo: 'inventado' })).rejects.toThrow(/400/);
    await expect(control.motor({ modo: 'texto' })).rejects.toThrow(/400/);
    await expect(control.motor({ retener_tras: -1 })).rejects.toThrow(/400/);
    const sinToken = await fetch(`${control.url}/pruebas-e2e/motor`, { headers: { 'X-Control-Pruebas': 'token-incorrecto' } });
    expect(sinToken.status).toBe(403);

    // La limpieza lo restablece todo (la que corre tras cada prueba): modo de cita, sin secuencia, sin retención.
    await control.motor({ modo: 'conexion', secuencia: ['x'], retener_tras: 1 });
    await control.limpiar();
    expect(await control.motorEstado()).toEqual({
      modo: 'cita', secuencia_pendiente: 0, retener_tras: null, retenida: false, esperando: 0, consultas: 0,
    });
  });

  test('RA-02.49 · ingesta procesa en el proceso, falla y retiene', async ({ control, crearUsuario }) => {
    const usuario = await crearUsuario('usuario');
    const token = await iniciarSesion(control, usuario);
    const tema = nuevoTema();
    const bueno = documentoDePrueba();
    const malo = documentoDePrueba();
    const lento = documentoDePrueba();

    // Procesa en el proceso, sin worker: queda un documento con sus fragmentos.
    await subirYProcesar(control, token, tema, bueno);
    const sano = await control.residuos();
    expect(sano.filas.T_Documento).toBe(1);
    expect(sano.puntos).toBeGreaterThan(0);

    // Falla por nombre: la tarea termina fallida; deja su documento en Error (RF-07.2) y ningún fragmento nuevo.
    await control.ingesta({ fallar: [malo.nombre] });
    const [idMalo] = await cargar(control, token, tema, [malo]);
    await esperarTarea(control, token, idMalo, 'fallido');
    const tras = await control.residuos();
    expect(tras.filas.T_Documento).toBe(2);
    expect(tras.puntos).toBe(sano.puntos);

    // Retiene por nombre: no termina mientras esté retenido; al liberar, termina bien.
    await control.ingesta({ retener: [lento.nombre] });
    const [idLento] = await cargar(control, token, tema, [lento]);
    await expect.poll(async () => (await control.ingestaEstado()).esperando, { timeout: 15_000 }).toBe(1);
    expect(['completado', 'fallido']).not.toContain(await estadoDeLaTarea(control, token, idLento));
    expect((await control.ingestaLiberar()).retenida).toBe(false);
    await esperarTarea(control, token, idLento, 'completado');
    expect((await control.residuos()).filas.T_Documento).toBe(3);

    // Un documento retenido cuando se limpia no deja nada: la limpieza lo suelta, espera a que termine y recién borra.
    const otro = documentoDePrueba();
    await control.ingesta({ retener: [otro.nombre] });
    await cargar(control, token, tema, [otro]);
    await expect.poll(async () => (await control.ingestaEstado()).esperando, { timeout: 15_000 }).toBe(1);
    const limpio = await control.limpiar();
    expect(limpio.total).toBe(0);
    const estado = await control.ingestaEstado();
    expect(estado).toMatchObject({ fallar: [], retener: [], retenida: false, esperando: 0, pendientes: 0, htr_falla: false, audio_falla: false });
    expect(estado.htr_llamadas).toEqual([]);

    // Programación inválida y sin token.
    await expect(control.ingesta({ fallar: 'no-es-una-lista' })).rejects.toThrow(/422|400/);
    await expect(control.ingesta({ retener: Array(21).fill('a.txt') })).rejects.toThrow(/400/);
    const sinToken = await fetch(`${control.url}/pruebas-e2e/ingesta`, { headers: { 'X-Control-Pruebas': 'token-incorrecto' } });
    expect(sinToken.status).toBe(403);
  });

  test('RA-02.49 · imagen con HTR simulado', async ({ control, crearUsuario }) => {
    const usuario = await crearUsuario('usuario');
    const token = await iniciarSesion(control, usuario);
    const tema = nuevoTema();
    const imagen = { nombre: `PRUEBA_${aleatorio()}.png`, contenido: PNG_MINIMO, tipo: 'image/png' };
    const texto = `Texto manuscrito inventado del HTR simulado ${aleatorio()} sobre la laguna de los patos azules de PRUEBA.`;

    await control.ingesta({ htr_texto: texto });
    const [idImagen] = await cargar(control, token, tema, [imagen]);
    await esperarTarea(control, token, idImagen, 'completado');

    // El HTR simulado recibió la imagen (nombre y tamaño, no su contenido) y su texto quedó en fragmentos.
    const estado = await control.ingestaEstado();
    expect(estado.htr_llamadas).toEqual([{ nombre: imagen.nombre, bytes: PNG_MINIMO.length }]);
    const residuos = await control.residuos();
    expect(residuos.filas.T_Documento).toBe(1);
    expect(residuos.puntos).toBeGreaterThan(0);
    const citada = textoDeLosEventos(await preguntar(control, token, usuario, 'Qué dice el texto manuscrito sobre la laguna de los patos azules', { tema }));
    expect(citada.includes(rutaCitada(tema, imagen))).toBe(true);

    // Si el HTR falla, la carga de la imagen termina fallida y su documento queda en Error (RF-07.2), sin fragmentos nuevos.
    await control.ingesta({ htr_falla: true });
    const otraImagen = { nombre: `PRUEBA_${aleatorio()}.png`, contenido: PNG_MINIMO, tipo: 'image/png' };
    const [idFallida] = await cargar(control, token, tema, [otraImagen]);
    await esperarTarea(control, token, idFallida, 'fallido');
    expect((await control.residuos()).filas.T_Documento).toBe(2);
    expect((await control.ingestaEstado()).htr_llamadas.length).toBe(2);

    // Un audio sigue el mismo camino con la transcripción simulada.
    const audio = { nombre: `PRUEBA_${aleatorio()}.mp3`, contenido: Buffer.from('PRUEBA audio inventado'), tipo: 'audio/mpeg' };
    await control.ingesta({ audio_texto: `Transcripción inventada del audio ${aleatorio()} sobre los patos azules de PRUEBA.` });
    const [idAudio] = await cargar(control, token, tema, [audio]);
    await esperarTarea(control, token, idAudio, 'completado');
    expect((await control.ingestaEstado()).audio_llamadas.map((l) => l.nombre)).toEqual([audio.nombre]);
    expect((await control.residuos()).filas.T_Documento).toBe(3);
  });

  test('RA-02.49 · vista previa retenida', async ({ control, crearUsuario }) => {
    const dueno = await crearUsuario('usuario');
    const ajeno = await crearUsuario('usuario');
    const token = await iniciarSesion(control, dueno);
    const tokenAjeno = await iniciarSesion(control, ajeno);
    const { notebook, documento, id } = await notebookConDocumento(control, token);
    const ruta = `/notebooks/${notebook.id}/documentos/${id}/archivo`;

    // Sin retención, la entrega es inmediata y trae el archivo tal cual.
    const directa = await enviar(control, 'GET', ruta, undefined, token);
    expect(directa.status).toBe(200);
    expect(Buffer.from(await directa.arrayBuffer()).equals(documento.contenido)).toBe(true);

    // Retenida: la petición del dueño espera; la del ajeno recibe de inmediato el 404 uniforme (no se retiene lo que no se entrega).
    await control.notebooks({ retener_vista_previa: true });
    const retenida = enviar(control, 'GET', ruta, undefined, token);
    await expect.poll(async () => (await control.notebooksEstado()).esperando_vista_previa, { timeout: 15_000 }).toBe(1);
    expect(await Promise.race([retenida.then(() => 'resuelta'), Promise.resolve('pendiente')])).toBe('pendiente');
    expect((await enviar(control, 'GET', ruta, undefined, tokenAjeno)).status).toBe(404);

    // Al liberar, termina y entrega el archivo.
    expect((await control.notebooksLiberar()).esperando_vista_previa).toBe(0);
    const entregada = await retenida;
    expect(entregada.status).toBe(200);
    expect(Buffer.from(await entregada.arrayBuffer()).equals(documento.contenido)).toBe(true);

    // La retención no toca la eliminación, y lo inválido se rechaza.
    expect((await control.notebooksEstado()).retener_quitar).toBe(false);
    await expect(control.notebooks({ retener_vista_previa: 'si' })).rejects.toThrow(/422|400/);
    const sinToken = await fetch(`${control.url}/pruebas-e2e/notebooks`, { headers: { 'X-Control-Pruebas': 'token-incorrecto' } });
    expect(sinToken.status).toBe(403);
  });

  test('RA-02.49 · quitar retenido y fallido', async ({ control, crearUsuario }) => {
    const usuario = await crearUsuario('usuario');
    const token = await iniciarSesion(control, usuario);
    const { notebook, documento, id } = await notebookConDocumento(control, token);
    const listar = async () => (await (await enviar(control, 'GET', `/notebooks/${notebook.id}/documentos`, undefined, token)).json());
    const quitar = () => enviar(control, 'DELETE', `/notebooks/${notebook.id}/documentos/${id}`, undefined, token);
    const pregunta = `¿Qué dice el documento sobre ${documento.frase}?`;
    const citaEnElChat = async () => textoDeLosEventos(await preguntar(control, token, usuario, pregunta, { notebook: notebook.id }))
      .includes(documento.nombre);
    expect(await citaEnElChat()).toBe(true);

    // Retenido y con fallo: mientras espera, el documento sigue listado; al liberar, falla con el aviso y sigue listado.
    await control.notebooks({ retener_quitar: true, fallar_quitar: true });
    const fallida = quitar();
    await expect.poll(async () => (await control.notebooksEstado()).esperando_quitar, { timeout: 15_000 }).toBe(1);
    expect(await Promise.race([fallida.then(() => 'resuelta'), Promise.resolve('pendiente')])).toBe('pendiente');
    expect((await listar()).map((d) => d.id)).toContain(id);
    await control.notebooksLiberar();
    const respuesta = await fallida;
    expect(respuesta.status).toBe(500);
    expect((await respuesta.json()).detail).toBe('No se pudo quitar el documento. Intente de nuevo.');
    expect((await listar()).map((d) => d.id)).toContain(id);
    expect((await control.residuos()).puntos).toBeGreaterThan(0);
    expect(await citaEnElChat()).toBe(true);

    // Un nuevo intento sin el fallo lo quita: deja de listarse y el chat del notebook ya no lo cita.
    await control.notebooks({});
    expect((await quitar()).status).toBe(200);
    expect(await listar()).toEqual([]);
    const despues = await control.residuos();
    expect(despues.filas.T_Documento).toBe(0);
    expect(despues.puntos).toBe(0);
    expect(await citaEnElChat()).toBe(false);

    // La limpieza lo restablece todo; sin token, 403.
    await control.notebooks({ retener_vista_previa: true, retener_quitar: true, fallar_quitar: true });
    await control.limpiar();
    expect(await control.notebooksEstado()).toEqual({
      retener_vista_previa: false, retener_quitar: false, fallar_quitar: false, esperando_vista_previa: 0, esperando_quitar: 0,
    });
  });

  test('RA-02.49 · ingesta retiene y falla en la vectorización', async ({ control, crearUsuario }) => {
    const usuario = await crearUsuario('usuario');
    const token = await iniciarSesion(control, usuario);
    const notebook = await crearNotebook(control, token);
    const lento = documentoDePrueba();
    const malo = documentoDePrueba();
    const estadoDe = async (documento) => (
      (await listarDocumentos(control, token, notebook)).find((d) => d.nombre_archivo === documento.nombre)?.estado
    );

    // Retenido en la vectorización: el documento YA existe (Pendiente) y la tarea no termina; al liberar, queda Procesado.
    await control.ingesta({ etapa: 'vectorizacion', retener: [lento.nombre] });
    const [idLento] = await cargar(control, token, notebook.clave_interna, [lento]);
    await expect.poll(async () => (await control.ingestaEstado()).esperando, { timeout: 15_000 }).toBe(1);
    expect(await estadoDe(lento)).toBe('Pendiente');
    expect(['completado', 'fallido']).not.toContain(await estadoDeLaTarea(control, token, idLento));
    await control.ingestaLiberar();
    await esperarTarea(control, token, idLento, 'completado');
    expect(await estadoDe(lento)).toBe('Procesado');

    // Fallo en la vectorización: la tarea falla, el documento ya estaba registrado y no se vectoriza (sin fragmentos nuevos).
    // RF-07 (corregido en la T3b): el documento queda en «Error»; antes quedaba en «Pendiente» porque el manejador de
    // errores llamaba a `update_progress(..., status="error")`, parámetro que no existe.
    const antes = (await control.residuos()).puntos;
    await control.ingesta({ etapa: 'vectorizacion', fallar: [malo.nombre] });
    const [idMalo] = await cargar(control, token, notebook.clave_interna, [malo]);
    await esperarTarea(control, token, idMalo, 'fallido');
    expect(await estadoDe(malo)).toBe('Error');
    expect((await control.residuos()).puntos).toBe(antes);

    // Con la etapa por omisión (extracción) el documento ya está registrado y queda en «Error» (RF-07.2; antes nunca llegaba
    // a registrarse); una etapa inválida se rechaza.
    const otro = documentoDePrueba();
    await control.ingesta({ fallar: [otro.nombre] });
    const [idOtro] = await cargar(control, token, notebook.clave_interna, [otro]);
    await esperarTarea(control, token, idOtro, 'fallido');
    expect(await estadoDe(otro)).toBe('Error');
    await expect(control.ingesta({ etapa: 'inventada' })).rejects.toThrow(/400/);

    // La limpieza devuelve la etapa a su valor por omisión.
    await control.ingesta({ etapa: 'vectorizacion' });
    await control.limpiar();
    expect((await control.ingestaEstado()).etapa).toBe('extraccion');
  });
});
