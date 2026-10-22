// Cliente del control de la instancia de pruebas (spec 005a, RA-02.49).
// Usa `fetch` de Node, no la API `request` de Playwright: esa entra en las trazas y los informes, y por el control viajan
// contraseñas (RA-02.43). La dirección y el token los fija el orquestador en el entorno del proceso.

const PREFIJO = '/pruebas-e2e';

function urlDesarrollo() {
  return process.env.E2E_URL_DESARROLLO || 'http://localhost:8000';
}

function crearControl({ url = process.env.E2E_URL_API, token = process.env.E2E_TOKEN } = {}) {
  if (!url) throw new Error('Falta E2E_URL_API: las pruebas se ejecutan con `npm run e2e`.');

  async function llamar(metodo, ruta, cuerpo) {
    const cabeceras = { 'X-Control-Pruebas': token || '' };
    if (cuerpo !== undefined) cabeceras['Content-Type'] = 'application/json';
    const respuesta = await fetch(`${url}${PREFIJO}${ruta}`, {
      method: metodo,
      headers: cabeceras,
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
      signal: AbortSignal.timeout(30_000),
    });
    const texto = await respuesta.text();
    let datos = null;
    try {
      datos = texto ? JSON.parse(texto) : null;
    } catch {
      datos = texto;
    }
    if (!respuesta.ok) {
      // El cuerpo enviado (puede traer contraseñas) nunca va en el mensaje; sí el `detail` de la respuesta, que el control
      // redacta sin secretos (en `/limpiar` nombra el paso y el error que falló).
      const detalle = datos && typeof datos.detail === 'string' ? `: ${datos.detail.slice(0, 500)}` : '';
      throw new Error(`El control respondió ${respuesta.status} a ${metodo} ${PREFIJO}${ruta}${detalle}`);
    }
    return datos;
  }

  return {
    url,
    estado: () => llamar('GET', '/estado'),
    apagar: () => llamar('POST', '/apagar'),
    // Un usuario PRUEBA con la contraseña dada (T3): rol 'administrador' o 'usuario'; `temporal` y `inactivo` opcionales.
    crearUsuario: (rol, contrasena, { temporal = false, inactivo = false } = {}) =>
      llamar('POST', '/usuarios', { rol, contrasena, temporal, inactivo }),
    // Lo que hay en el entorno aislado y su limpieza total (T3, RA-02.42).
    residuos: () => llamar('GET', '/residuos'),
    limpiar: () => llamar('POST', '/limpiar'),
    // Recuperación y bitácora (T5, RA-02.49). El código del correo viaja solo en la respuesta: nunca se imprime ni se guarda.
    codigoCorreo: (correo) => llamar('GET', `/correo/codigo?a=${encodeURIComponent(correo)}`),
    correoFalla: (falla = true) => llamar('POST', '/correo', { falla }),
    almacen: (disponible, tipo = 'conexion') => llamar('POST', '/almacen', { disponible, tipo }),
    reloj: (segundos) => llamar('POST', '/reloj', { segundos }),
    bitacora: (cedula, tipo, tema) => llamar('POST', '/bitacora', { cedula, tipo, tema }),
    capacidades: () => llamar('GET', '/capacidades'),
    // Motor, ingesta y notebooks (T6, RA-02.49). Cada `programar` reemplaza la configuración entera: lo omitido vuelve a su
    // valor por omisión. Todos devuelven el estado; `liberar` abre la retención sin cambiar lo demás.
    motor: (cuerpo = {}) => llamar('POST', '/motor', cuerpo),
    motorEstado: () => llamar('GET', '/motor'),
    motorLiberar: () => llamar('POST', '/motor/liberar'),
    ingesta: (cuerpo = {}) => llamar('POST', '/ingesta', cuerpo),
    ingestaEstado: () => llamar('GET', '/ingesta'),
    ingestaLiberar: () => llamar('POST', '/ingesta/liberar'),
    notebooks: (cuerpo = {}) => llamar('POST', '/notebooks', cuerpo),
    notebooksEstado: () => llamar('GET', '/notebooks'),
    notebooksLiberar: () => llamar('POST', '/notebooks/liberar'),
    llamar,
  };
}

module.exports = { crearControl, urlDesarrollo };
