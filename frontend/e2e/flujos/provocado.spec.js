// Comprobación de RA-02.43 (spec 005a, plan §5): una prueba que falla a propósito con la contraseña escrita en el campo, para
// verificar que ninguna contraseña queda en los artefactos (captura, informe, informe de errores).
// Solo existe con `E2E_FALLO_PROVOCADO=1` (`E2E_FALLO_PROVOCADO=1 npm run e2e -- --grep RA-02.43`): en una corrida normal no se
// recolecta. La corrida sale con fallos a propósito; lo que se comprueba es «Contraseñas en artefactos: 0».
const { test, expect, escribir } = require('../soporte/fixtures.js');

if (process.env.E2E_FALLO_PROVOCADO === '1') {
  test('RA-02.43 · fallo provocado con la contraseña en el campo: no deja contraseñas en los artefactos', async ({ page, crearUsuario }) => {
    const usuario = await crearUsuario('usuario');
    await page.goto('/auth/login');
    await expect(page.getByRole('heading', { name: 'Inicio de sesión' })).toBeVisible();
    await escribir(page.getByLabel('Correo electrónico'), usuario.correo);
    await escribir(page.getByLabel('Contraseña', { exact: true }), usuario.contrasena);
    // Fallo intencional: la captura y el informe se generan con la contraseña ya escrita.
    await expect(page.getByText('texto que no existe en la pantalla (fallo provocado)')).toBeVisible({ timeout: 1_000 });
  });
}
