// Pruebas de la instancia de extremo a extremo (spec 005a, T2 y T3): RA-02.41, RA-02.42, RA-02.49, RNF-09.40.
// Sin navegador: hablan con el control de la instancia (puerto 8100) y, solo con GET, con el backend de desarrollo.
const { test, expect } = require('../soporte/fixtures.js');
const { crearControl, urlDesarrollo } = require('../soporte/control.js');

const NOMBRE = 'servia_pruebas_e2e';

test.describe('instancia de pruebas', () => {
  test('RNF-09.40 · simulados activos: Ollama, HTR, audio y correo', async () => {
    const estado = await crearControl().estado();
    expect(estado.listo).toBe(true);
    expect(estado.simulados).toEqual({ ollama: true, htr: true, audio: true, correo: true });
    expect(estado.todos_simulados).toBe(true);
  });

  test('RA-02.41 · usa servia_pruebas_e2e: base, colección y Redis simulado', async () => {
    const estado = await crearControl().estado();
    expect(estado.nombre_activo).toBe(NOMBRE);
    expect(estado.base).toBe(NOMBRE);
    expect(estado.coleccion).toBe(NOMBRE);
    expect(estado.redis_simulado).toBe(true);
  });

  test('RA-02.49 · control ausente en desarrollo (404)', async () => {
    const respuesta = await fetch(`${urlDesarrollo()}/pruebas-e2e/estado`);
    expect(respuesta.status).toBe(404);
  });

  test('RA-02.49 · el control rechaza apagar sin token válido (403)', async () => {
    const respuesta = await fetch(`${crearControl().url}/pruebas-e2e/apagar`, {
      method: 'POST',
      headers: { 'X-Control-Pruebas': 'token-incorrecto' },
    });
    expect(respuesta.status).toBe(403);
  });

  test('RA-02.41 · desarrollo responde mientras corre la instancia', async () => {
    const respuesta = await fetch(`${urlDesarrollo()}/`);
    expect(respuesta.status).toBe(200);
  });

  test('RA-02.42 · crea usuarios PRUEBA de cada rol, temporal e Inactivo', async ({ control, crearUsuario, generadorContrasenas }) => {
    const administrador = await crearUsuario('administrador');
    const gubernamental = await crearUsuario('usuario');
    const temporal = await crearUsuario('usuario', { temporal: true });
    const inactivo = await crearUsuario('administrador', { inactivo: true });

    // Datos inventados con el prefijo PRUEBA.
    for (const u of [administrador, gubernamental, temporal, inactivo]) {
      expect(u.cedula).toMatch(/^PRUEBA/);
      expect(u.nombre_usuario).toMatch(/^PRUEBA/);
      expect(u.correo).toMatch(/@prueba\.invalid$/);
    }
    // La respuesta del control nunca trae la contraseña (solo su dueño la conoce).
    const cruda = await control.crearUsuario('usuario', generadorContrasenas.siguiente());
    expect(Object.keys(cruda).sort()).toEqual(['cedula', 'correo', 'inactivo', 'nombre_usuario', 'rol', 'temporal']);
    expect(new Set([administrador, gubernamental, temporal, inactivo].map((u) => u.cedula)).size).toBe(4);

    // El inicio de sesión del sistema real acepta la contraseña de cada uno y refleja su rol y su estado.
    const ingresar = (u, contrasena = u.contrasena) => fetch(`${control.url}/auth/login`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: u.correo, password: contrasena }),
    });
    const a = await (await ingresar(administrador)).json();
    expect(a.user.role).toBe('Administrador');
    expect(a.user.requiere_cambio_password).toBe(false);
    const g = await (await ingresar(gubernamental)).json();
    expect(g.user.role).toBe('Usuario Judicial');
    expect(g.user.requiere_cambio_password).toBe(false);
    const t = await (await ingresar(temporal)).json();
    expect(t.user.requiere_cambio_password).toBe(true);
    expect((await ingresar(inactivo)).status).toBe(401);
    expect((await ingresar(gubernamental, `${gubernamental.contrasena}x`)).status).toBe(401);

    // Un rol que no existe se rechaza.
    await expect(control.llamar('POST', '/usuarios', { rol: 'superusuario', contrasena: 'PRUEBA-no-se-crea' }))
      .rejects.toThrow(/400/);
  });

  test('RA-02.42 · limpiar deja residuos en cero', async ({ control, crearUsuario }) => {
    await crearUsuario('administrador');
    await crearUsuario('usuario', { temporal: true });
    const antes = await control.residuos();
    expect(antes.total).toBeGreaterThan(0);
    expect(antes.filas.T_Usuario).toBe(2);
    expect(antes.texto).toContain('T_Usuario: 2');

    await control.limpiar();
    const despues = await control.residuos();
    expect(despues.total).toBe(0);
    expect(despues.texto).toBe('ninguno');
    expect(despues.filas.T_Usuario).toBe(0);

    // La instancia sigue sana (el administrador sembrado y los catálogos no se tocaron).
    const estado = await control.estado();
    expect(estado.listo).toBe(true);
    const ingreso = await fetch(`${control.url}/auth/login`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: 'nadie@prueba.invalid', password: 'x' }),
    });
    expect(ingreso.status).toBe(401);
  });

  test('RA-02.42 · el control de usuarios y de limpieza exige el token', async ({ control }) => {
    for (const [metodo, ruta, cuerpo] of [
      ['POST', '/usuarios', { rol: 'usuario', contrasena: 'PRUEBA-sin-token' }],
      ['POST', '/limpiar', undefined],
      ['GET', '/residuos', undefined],
    ]) {
      const respuesta = await fetch(`${control.url}/pruebas-e2e${ruta}`, {
        method: metodo,
        headers: { 'X-Control-Pruebas': 'token-incorrecto', 'Content-Type': 'application/json' },
        body: cuerpo ? JSON.stringify(cuerpo) : undefined,
      });
      expect(respuesta.status, `${metodo} ${ruta}`).toBe(403);
    }
  });
});
