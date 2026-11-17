// Recorrido del vocabulario «tema» en las pantallas del Usuario Gubernamental (spec 011, T4): RT-06.130, RT-07.130 y RNF-04.130. Abre
// cada pantalla y comprueba que el texto visible no dice «expediente» (ni «Expediente»): lo que el barrido de código no vea, lo
// detecta este recorrido. El contenido que escribe el usuario o que traen los documentos no se toca. Corre en `escritorio` (1366) y
// `pequena` (616).
const { test, expect, iniciarSesion } = require('../soporte/fixtures.js');

const PANTALLAS = [
  ['Ingesta de Datos', '/ingesta-datos'],
  ['Chat general', '/consulta-datos/chat'],
  ['Chat de un tema', '/consulta-datos/chat?mode=expediente'],
  ['Temas Similares por descripción', '/consulta-datos/busqueda-similares?mode=descripcion'],
  ['Temas Similares por tema', '/consulta-datos/busqueda-similares?mode=expediente'],
  ['NotebookServIA', '/notebooks'],
  ['Inicio', '/'],
];

test.describe('Recorrido «tema» del Usuario Gubernamental', () => {
  for (const [nombre, ruta] of PANTALLAS) {
    test(`RT-06.130 · ${nombre}: ningún texto visible dice «expediente»`, async ({ page, crearUsuario }) => {
      const usuario = await crearUsuario('usuario');
      await iniciarSesion(page, usuario.correo, usuario.contrasena);
      await page.goto(ruta);
      await expect(page.getByRole('main').or(page.locator('body')).first()).toBeVisible();
      await page.waitForLoadState('networkidle');

      await expect(page.locator('body')).not.toContainText(/expediente/i);
      // Los textos cambiados caben en la pantalla (RNF-04.130).
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1),
        'sin desborde horizontal de la página').toBe(true);
    });
  }
});
