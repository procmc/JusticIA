// Páginas y roles (spec 005a, T8): RA-02.48 (la lista de páginas) y RF-02.41 (cada rol contra cada clase). Spec retroactiva:
// sigue al ERS (RF-02 «Control en la interfaz», CU-03 FE-02), no a lo que hoy hace el código.
// La comparación con `pages/` no usa el navegador; el recorrido por rol solo navega por dirección (sin diferencia de diseño),
// así que corre en escritorio.
const { test, expect, iniciarSesion } = require('../soporte/fixtures.js');
const { CLASES, paginasClasificadas, compararConLasPaginas } = require('../soporte/paginas.js');

test('RA-02.48 · lista de páginas completa: toda página de pages/ está clasificada y toda la clasificada existe', async () => {
  const { sinClasificar, noExisten, conPaginaPropia } = compararConLasPaginas();
  expect(
    sinClasificar,
    `Páginas de frontend/pages/ sin clasificar en e2e/soporte/paginas.js (RA-02.48): ${sinClasificar.join(', ')}`,
  ).toEqual([]);
  expect(
    noExisten,
    `Direcciones clasificadas en e2e/soporte/paginas.js que no existen en frontend/pages/ (RA-02.48): ${noExisten.join(', ')}`,
  ).toEqual([]);
  expect(
    conPaginaPropia,
    `Direcciones clasificadas como «grupo sin página» o «inexistente» que ahora tienen página (RA-02.48): ${conPaginaPropia.join(', ')}`,
  ).toEqual([]);
});

const ROLES = ['administrador', 'usuario'];

for (const rol of ROLES) {
  test(`RF-02.41 · @solo-escritorio cada rol contra cada clase: ${rol}`, async ({ page, crearUsuario, consola }) => {
    // Las direcciones sin página responden 404 (y su archivo de datos también): lo provoca esta prueba a propósito.
    consola.provocado(/404/);
    const usuario = await crearUsuario(rol);
    await iniciarSesion(page, usuario.correo, usuario.contrasena);

    const propias = CLASES.porRol[rol];
    // Páginas de otro rol: las clasificadas que este rol no puede abrir.
    const deOtroRol = paginasClasificadas().filter((d) => !CLASES.publica.includes(d) && !propias.includes(d));
    expect(deOtroRol.length, 'la lista debe tener páginas de otro rol que probar').toBeGreaterThan(0);

    const irA = async (direccion) => {
      const respuesta = await page.goto(direccion);
      return { ruta: new URL(page.url()).pathname, estado: respuesta ? respuesta.status() : null };
    };

    // Página del propio rol: se muestra, sin redirección.
    for (const direccion of propias) {
      const { ruta } = await irA(direccion);
      expect(ruta, `el ${rol} debe poder abrir ${direccion}`).toBe(direccion);
    }

    // Página de otro rol: no se muestra y lo dirige a la página de inicio.
    for (const direccion of deOtroRol) {
      const { ruta } = await irA(direccion);
      expect(ruta, `el ${rol} escribió ${direccion}, página de otro rol: debía dirigirlo a inicio`).toBe('/');
      await expect(page.getByText('Bienvenid@')).toBeVisible();
    }

    // Grupo sin página e inexistente: sin contenido protegido; sirve la página de error o lo dirige a inicio (no se exige redirección).
    for (const direccion of [...CLASES.grupoSinPagina, ...CLASES.inexistente]) {
      const { ruta, estado } = await irA(direccion);
      if (ruta === '/') {
        await expect(page.getByText('Bienvenid@')).toBeVisible();
      } else {
        expect(ruta, `${direccion} no tiene página: solo puede quedarse en ella con la página de error`).toBe(direccion);
        expect(estado, `${direccion} no tiene página: debe responder 404`).toBe(404);
      }
    }
  });
}
