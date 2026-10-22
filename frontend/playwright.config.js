// Configuración de Playwright para la red de seguridad de extremo a extremo (spec 005a).
// No se ejecuta directamente: `npm run e2e` (e2e/ejecutar.mjs) prepara la instancia y el frontend de pruebas, fija las
// variables E2E_* y apaga todo al terminar.
const { defineConfig } = require('@playwright/test');

const URL_WEB = process.env.E2E_URL_WEB || 'http://127.0.0.1:3100';

const navegador = { channel: 'chrome', headless: true };

module.exports = defineConfig({
  testDir: 'e2e',
  testMatch: '**/*.spec.js',
  outputDir: 'test-results/artefactos',
  // Límites de la spec (RA-02.47): 10 min la suite y 60 s cada prueba.
  timeout: 60_000,
  globalTimeout: 600_000,
  expect: { timeout: 10_000 },
  // La instancia es compartida: un solo trabajador y sin reintentos que oculten fallos.
  workers: 1,
  fullyParallel: false,
  retries: 0,
  forbidOnly: true,
  reporter: [['list'], ['json', { outputFile: 'test-results/informe.json' }]],
  use: {
    baseURL: URL_WEB,
    // Trazas y video guardan los valores de los campos (contraseñas): apagados (RA-02.43).
    trace: 'off',
    video: 'off',
    screenshot: 'only-on-failure',
  },
  projects: [
    // Sin navegador: orquestador e instancia.
    { name: 'infraestructura', testDir: 'e2e/infraestructura' },
    // Flujos de la interfaz: Chrome instalado, escritorio y una pantalla más pequeña (RNF-04).
    {
      name: 'escritorio',
      testDir: 'e2e/flujos',
      use: { ...navegador, viewport: { width: 1366, height: 768 } },
    },
    {
      name: 'pequena',
      testDir: 'e2e/flujos',
      grepInvert: /@solo-escritorio/,
      use: { ...navegador, viewport: { width: 616, height: 768 } },
    },
  ],
});
