// Pruebas del orquestador (spec 005a, T2): RA-02.40, RA-02.43, RA-02.47.
// Comprueban su lógica con datos inventados, sin navegador y sin tocar la instancia.
const fs = require('node:fs');
const http = require('node:http');
const net = require('node:net');
const os = require('node:os');
const path = require('node:path');
const { test, expect } = require('@playwright/test');
const { generar, nucleo } = require('../soporte/contrasenas.js');
const { crearControl } = require('../soporte/control.js');

const cargarOrquestador = () => import('../ejecutar.mjs');

function carpetaTemporal() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'servia-e2e-prueba-'));
}

function informe(tests) {
  // Estructura mínima del informe JSON de Playwright: archivo → suite → especificaciones → pruebas.
  return {
    suites: [{
      title: 'orquestador.spec.js',
      specs: tests.map((t) => ({
        title: t.titulo,
        tests: [{
          expectedStatus: t.esperado ?? 'passed',
          status: t.estado,
          results: [{ status: t.resultado }],
        }],
      })),
      suites: [],
    }],
  };
}

test.describe('RA-02.40 orquestador', () => {
  test('RA-02.40 · puerto ocupado: el error nombra el puerto y cómo liberarlo', async () => {
    const { comprobarPuertoLibre } = await cargarOrquestador();
    const servidor = net.createServer();
    await new Promise((resolver) => servidor.listen(0, '127.0.0.1', resolver));
    const { port } = servidor.address();
    try {
      await expect(comprobarPuertoLibre('127.0.0.1', port, 'el frontend de pruebas'))
        .rejects.toThrow(new RegExp(`puerto ${port}.*npm run e2e:apagar`, 's'));
    } finally {
      await new Promise((resolver) => servidor.close(resolver));
    }
    await expect(comprobarPuertoLibre('127.0.0.1', port, 'el frontend de pruebas')).resolves.toBeUndefined();
  });

  test('RA-02.40 · sin pruebas recolectadas: la corrida falla y lo dice', async () => {
    const { analizarInforme, veredicto } = await cargarOrquestador();
    for (const vacio of [null, { suites: [] }]) {
      const cuentas = analizarInforme(vacio);
      expect(cuentas.recolectadas).toBe(0);
      const resultado = veredicto({ ...cuentas, codigoPlaywright: 1 });
      expect(resultado.codigo).not.toBe(0);
      expect(resultado.motivos.join(' ')).toContain('no se recolectó ninguna prueba');
    }
  });

  test('RA-02.40 · resumen con XPASS nombrado: un fallo esperado que pasa rompe la corrida', async () => {
    const { analizarInforme, veredicto, textoResumen } = await cargarOrquestador();
    const cuentas = analizarInforme(informe([
      { titulo: 'RF-00.1 · pasa', estado: 'expected', resultado: 'passed' },
      { titulo: 'RF-00.2 · falla', estado: 'unexpected', resultado: 'failed' },
      { titulo: 'RF-00.3 · fallo esperado', esperado: 'failed', estado: 'expected', resultado: 'failed' },
      { titulo: 'RF-00.4 · ahora cumple', esperado: 'failed', estado: 'unexpected', resultado: 'passed' },
    ]));
    expect(cuentas).toMatchObject({ recolectadas: 4, pasan: 1, fallan: 1, esperados: 1 });
    expect(cuentas.xpass).toHaveLength(1);
    expect(cuentas.xpass[0]).toContain('RF-00.4 · ahora cumple');

    const limpia = { contrasenas: 0, coincidenciasRegistro: 0, desarrolloAntes: 200, desarrolloDespues: 200 };
    const soloXpass = analizarInforme(informe([
      { titulo: 'RF-00.4 · ahora cumple', esperado: 'failed', estado: 'unexpected', resultado: 'passed' },
    ]));
    const resultado = veredicto({ ...soloXpass, ...limpia, codigoPlaywright: 1 });
    expect(resultado.codigo).not.toBe(0);
    expect(textoResumen({ ...soloXpass, ...limpia, ...resultado, preparacionMs: 1000, suiteMs: 2000 }))
      .toContain('XPASS (fallos esperados que pasan): 1');
    expect(textoResumen({ ...soloXpass, ...limpia, ...resultado, preparacionMs: 1000, suiteMs: 2000 }))
      .toContain('RF-00.4 · ahora cumple');

    const buena = analizarInforme(informe([{ titulo: 'RF-00.1 · pasa', estado: 'expected', resultado: 'passed' }]));
    expect(veredicto({ ...buena, ...limpia, codigoPlaywright: 0 }).codigo).toBe(0);
    // El desarrollo caído antes o después también rompe la corrida.
    expect(veredicto({ ...buena, ...limpia, desarrolloDespues: 0, codigoPlaywright: 0 }).codigo).not.toBe(0);
  });

  test('RA-02.40 · informe de una corrida anterior: no se cuenta si la corrida aborta antes de Playwright', async () => {
    const { prepararResultados, resumirInforme, veredicto, textoResumen } = await cargarOrquestador();
    const carpeta = carpetaTemporal();
    const ruta = path.join(carpeta, 'test-results', 'informe.json');
    const limpia = { contrasenas: 0, coincidenciasRegistro: 0, desarrolloAntes: 200, desarrolloDespues: 200, codigoPlaywright: 1 };
    try {
      // Queda el informe de la corrida anterior (5 pasan) y la nueva aborta sin que Playwright escriba otro.
      fs.mkdirSync(path.dirname(ruta), { recursive: true });
      fs.writeFileSync(ruta, JSON.stringify(informe(Array.from({ length: 5 }, (_, i) => (
        { titulo: `RF-00.${i} · vieja`, estado: 'expected', resultado: 'passed' }
      )))));
      prepararResultados(path.dirname(ruta));

      const cuentas = resumirInforme(ruta);
      expect(cuentas).toMatchObject({ sinInforme: true, recolectadas: 0, pasan: 0 });
      const resultado = veredicto({ ...cuentas, ...limpia });
      expect(resultado.codigo).not.toBe(0);
      expect(resultado.motivos.join(' ')).toContain('no hubo informe de esta corrida');
      const texto = textoResumen({ ...cuentas, ...limpia, ...resultado, preparacionMs: 0, suiteMs: 0 });
      expect(texto).not.toContain('Pasan: 5');
      expect(texto).toContain('Sin informe de esta corrida');

      // «Sin informe» no es lo mismo que «0 pruebas»: un informe vacío escrito por esta corrida sí muestra sus cifras.
      fs.mkdirSync(path.dirname(ruta), { recursive: true });
      fs.writeFileSync(ruta, JSON.stringify({ suites: [] }));
      const vacio = resumirInforme(ruta);
      expect(vacio).toMatchObject({ sinInforme: false, recolectadas: 0 });
      const textoVacio = textoResumen({ ...vacio, ...limpia, ...veredicto({ ...vacio, ...limpia }), preparacionMs: 0, suiteMs: 0 });
      expect(textoVacio).toContain('Recolectadas: 0');
      expect(textoVacio).not.toContain('Sin informe de esta corrida');
    } finally {
      fs.rmSync(carpeta, { recursive: true, force: true });
    }
  });

  test('RA-02.43 · búsqueda de contraseñas: encuentra una en texto y en binario y nunca la devuelve', async () => {
    const { buscarContrasenas } = await cargarOrquestador();
    const semilla = Buffer.from('a'.repeat(64), 'hex');
    const carpeta = carpetaTemporal();
    try {
      fs.writeFileSync(path.join(carpeta, 'limpio.txt'), 'nada sensible aquí, solo texto y 1234567890 abcdef');
      expect(buscarContrasenas({ semilla, carpetas: [carpeta], textos: ['salida sin nada'] }).total).toBe(0);

      const contrasena = generar(semilla, 3, 7);
      fs.writeFileSync(path.join(carpeta, 'informe.json'), `{"valor": "${contrasena}"}`);
      fs.writeFileSync(path.join(carpeta, 'captura.png'), Buffer.concat([
        Buffer.from([0x89, 0x50, 0x4e, 0x47, 0, 1, 2, 255]),
        Buffer.from(nucleo(semilla, 0, 0), 'latin1'),
        Buffer.from([0, 255, 254]),
      ]));
      const resultado = buscarContrasenas({
        semilla, carpetas: [carpeta], textos: [`salida con ${nucleo(semilla, 199, 199)} dentro`],
      });
      expect(resultado.total).toBe(3);
      expect(resultado.donde.map((d) => path.basename(d)).sort()).toEqual(['captura.png', 'informe.json', 'salida']);
      expect(JSON.stringify(resultado)).not.toContain(nucleo(semilla, 3, 7));
      // Fuera del rango de trabajadores y repeticiones que se recalcula no cuenta (no es una contraseña de la corrida).
      expect(buscarContrasenas({ semilla, carpetas: [], textos: [nucleo(semilla, 500, 0)] }).total).toBe(0);
    } finally {
      fs.rmSync(carpeta, { recursive: true, force: true });
    }
  });

  test('RA-02.43 · ocultar contraseñas: los artefactos de texto quedan con el marcador y la búsqueda da 0', async () => {
    const { buscarContrasenas, ocultarContrasenas, MARCADOR_CONTRASENA } = await cargarOrquestador();
    const semilla = Buffer.from('b'.repeat(64), 'hex');
    const carpeta = carpetaTemporal();
    try {
      const contrasena = generar(semilla, 2, 5);
      // Como el error-context.md de Playwright: el valor de un campo dentro de un texto, y una repetición en otro archivo.
      const original = `- textbox "Contraseña": ${contrasena}\n- button "Entrar"\n`;
      fs.mkdirSync(path.join(carpeta, 'prueba-1'), { recursive: true });
      const contexto = path.join(carpeta, 'prueba-1', 'error-context.md');
      fs.writeFileSync(contexto, original);
      fs.writeFileSync(path.join(carpeta, 'informe.json'), JSON.stringify({ campo: contrasena, otro: 'texto normal' }));
      const captura = path.join(carpeta, 'prueba-1', 'captura.png');
      const bytes = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0, 1, 2, 255]);
      fs.writeFileSync(captura, bytes);
      expect(buscarContrasenas({ semilla, carpetas: [carpeta] }).total).toBe(2);

      const ocultadas = ocultarContrasenas({ semilla, carpetas: [carpeta] });
      expect(ocultadas).toBe(2);
      expect(buscarContrasenas({ semilla, carpetas: [carpeta] }).total).toBe(0);
      // Se conserva el archivo para el diagnóstico, con el marcador y el resto del texto intacto.
      expect(fs.readFileSync(contexto, 'utf8')).toBe(`- textbox "Contraseña": ${MARCADOR_CONTRASENA}\n- button "Entrar"\n`);
      expect(JSON.parse(fs.readFileSync(path.join(carpeta, 'informe.json'), 'utf8')))
        .toEqual({ campo: MARCADOR_CONTRASENA, otro: 'texto normal' });
      // Los binarios no se tocan.
      expect(fs.readFileSync(captura).equals(bytes)).toBe(true);
    } finally {
      fs.rmSync(carpeta, { recursive: true, force: true });
    }
  });

  test('RA-02.44 · anotación de fallo esperado: exige «<requisito> · <módulo>» y marca el fallo', async () => {
    const { fallaEsperada, validarAnotacion } = require('../soporte/fixtures.js');
    for (const valida of ['RF-19.40 · notebooks', 'RNF-04.1 · interfaz', 'RA-02.44 · fixtures']) {
      expect(() => validarAnotacion(valida)).not.toThrow();
    }
    for (const invalida of ['', 'notebooks', 'RF-19.40', 'RF-19.40 notebooks', 'RF-19.40 · ', 'rf-19.40 · notebooks', 'XX-19.40 · notebooks']) {
      expect(() => validarAnotacion(invalida), invalida).toThrow(/RF-19\.40 · notebooks|requisito/);
    }

    // Marca la prueba con `test.fail(true, anotación)`: Playwright lo trata como fallo esperado estricto.
    const llamadas = [];
    fallaEsperada({ fail: (...argumentos) => llamadas.push(argumentos) }, 'RF-19.40 · notebooks');
    expect(llamadas).toEqual([[true, 'RF-19.40 · notebooks']]);
    expect(() => fallaEsperada({ fail: () => llamadas.push('no debe') }, 'sin formato')).toThrow();
    expect(llamadas).toHaveLength(1);
  });

  test('RA-02.41 · con el entorno aislado no disponible, la suite aborta antes de abrir el navegador', async () => {
    const { validarEstado } = await cargarOrquestador();
    const bueno = {
      listo: true, nombre_activo: 'servia_pruebas_e2e', base: 'servia_pruebas_e2e', coleccion: 'servia_pruebas_e2e',
      todos_simulados: true, redis_simulado: true, simulados: { ollama: true, htr: true, audio: true, correo: true },
    };
    expect(validarEstado(bueno)).toBeNull();

    // Cada caso es un motivo para abortar; el mensaje dice cuál es.
    expect(validarEstado(null)).toContain('no se declara lista');
    expect(validarEstado({ ...bueno, listo: false })).toContain('no se declara lista');
    for (const cambio of [{ nombre_activo: 'servia_pruebas' }, { base: 'db_ServIA' }, { coleccion: 'servia_pruebas' }]) {
      expect(validarEstado({ ...bueno, ...cambio }), JSON.stringify(cambio)).toContain('no usa servia_pruebas_e2e');
    }
    const sinHtr = validarEstado({ ...bueno, todos_simulados: false, simulados: { ...bueno.simulados, htr: false } });
    expect(sinHtr).toContain('faltan simulados activos');
    expect(sinHtr).toContain('htr');
    expect(validarEstado({ ...bueno, redis_simulado: false })).toContain('redis');
  });

  test('RA-02.42 · el error del control incluye el detail de la respuesta y nunca el cuerpo enviado', async () => {
    const servidor = http.createServer((peticion, respuesta) => {
      respuesta.writeHead(500, { 'Content-Type': 'application/json' });
      respuesta.end(JSON.stringify({ detail: 'No se pudo limpiar: tablas de datos (RuntimeError: T_Usuario deadlock)' }));
      peticion.resume();
    });
    await new Promise((resolver) => servidor.listen(0, '127.0.0.1', resolver));
    try {
      const control = crearControl({ url: `http://127.0.0.1:${servidor.address().port}`, token: 'ficticio' });
      const error = await control.llamar('POST', '/limpiar', { contrasena: 'NoDebeAparecer-123' }).catch((e) => e);
      expect(error.message).toContain('500');
      expect(error.message).toContain('T_Usuario deadlock');
      expect(error.message).not.toContain('NoDebeAparecer');
    } finally {
      servidor.close();
    }
  });

  test('RA-02.47 · sin pausas fijas: ni waitForTimeout ni setTimeout en los flujos', async () => {
    const { buscarPausasFijas } = await cargarOrquestador();
    const flujos = path.join(__dirname, '..', 'flujos');
    expect(buscarPausasFijas(flujos)).toEqual([]);

    const carpeta = carpetaTemporal();
    try {
      fs.writeFileSync(path.join(carpeta, 'mala.spec.js'), 'await page.waitForTimeout(500);\n');
      fs.writeFileSync(path.join(carpeta, 'otra.spec.js'), 'ok();\nsetTimeout(() => {}, 10);\n');
      fs.writeFileSync(path.join(carpeta, 'buena.spec.js'), 'await expect(page.getByText("x")).toBeVisible();\n');
      const halladas = buscarPausasFijas(carpeta).map((h) => `${path.basename(h.archivo)}:${h.linea}`).sort();
      expect(halladas).toEqual(['mala.spec.js:1', 'otra.spec.js:2']);
    } finally {
      fs.rmSync(carpeta, { recursive: true, force: true });
    }
  });
});
