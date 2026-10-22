// Lista de las direcciones de la interfaz (spec 005a, RA-02.48), escrita desde el ERS (RF-02, CU-03), no desde el código.
// Cada dirección vive en una clase; `direccionesDeLasPaginas()` lee `frontend/pages/` para que la prueba compare las dos.
const fs = require('node:fs');
const path = require('node:path');

const CLASES = {
  // Abiertas sin sesión: «Inicio de sesión» y la recuperación de contraseña.
  publica: ['/auth/login', '/auth/recuperar-contrasenna'],
  // Cada página con el rol que puede abrirla (roles del control: `administrador` y `usuario`).
  porRol: {
    administrador: ['/', '/administracion/gestion-usuarios', '/administracion/bitacora'],
    usuario: ['/', '/ingesta-datos', '/consulta-datos/chat', '/consulta-datos/busqueda-similares', '/notebooks'],
  },
  // Prefijos de grupo del control de acceso que no tienen página propia (Administración, Búsqueda y Consulta).
  grupoSinPagina: ['/administracion', '/consulta-datos'],
  // Una dirección inventada.
  inexistente: ['/PRUEBA-no-existe'],
};

const RAIZ_PAGINAS = path.resolve(__dirname, '../../pages');
const EXTENSIONES = new Set(['.js', '.jsx', '.ts', '.tsx']);

// Páginas de la lista que existen: las públicas y las de algún rol, sin repetir.
function paginasClasificadas() {
  return [...new Set([...CLASES.publica, ...CLASES.porRol.administrador, ...CLASES.porRol.usuario])].sort();
}

// Las direcciones que Next.js sirve desde `pages/`: sin `_app`, `_document`, `api/` ni los recursos (fuentes).
function direccionesDeLasPaginas(raiz = RAIZ_PAGINAS) {
  const direcciones = [];
  const recorrer = (carpeta, prefijo) => {
    for (const entrada of fs.readdirSync(carpeta, { withFileTypes: true })) {
      if (entrada.isDirectory()) {
        if (prefijo === '' && (entrada.name === 'api' || entrada.name === 'fonts')) continue;
        recorrer(path.join(carpeta, entrada.name), `${prefijo}/${entrada.name}`);
        continue;
      }
      const { name, ext } = path.parse(entrada.name);
      if (!EXTENSIONES.has(ext) || name.startsWith('_')) continue;
      direcciones.push(name === 'index' ? prefijo || '/' : `${prefijo}/${name}`);
    }
  };
  recorrer(raiz, '');
  return direcciones.sort();
}

// Compara la lista con `pages/`: lo que existe sin clasificar y lo clasificado que no existe (o que no debería tener página).
function compararConLasPaginas(existentes = direccionesDeLasPaginas()) {
  const clasificadas = paginasClasificadas();
  const sinClasificar = existentes.filter((d) => !clasificadas.includes(d));
  const noExisten = clasificadas.filter((d) => !existentes.includes(d));
  // Un grupo sin página o una dirección inventada que de pronto tiene página dejó de ser de su clase.
  const conPaginaPropia = [...CLASES.grupoSinPagina, ...CLASES.inexistente].filter((d) => existentes.includes(d));
  return { sinClasificar, noExisten, conPaginaPropia };
}

module.exports = { CLASES, paginasClasificadas, direccionesDeLasPaginas, compararConLasPaginas };
