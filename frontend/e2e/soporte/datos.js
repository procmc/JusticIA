// Ayudas de datos de la red de seguridad de extremo a extremo (spec 005b, T2): hablan con la API real de la instancia, sin
// navegador. Salen de `infraestructura/capacidades.spec.js` para que las usen también los flujos de carga y notebooks.
// Los datos son inventados con el prefijo PRUEBA; la limpieza tras cada prueba (fixtures.js) los borra.
const { expect } = require('@playwright/test');

// Una imagen PNG válida de 1 × 1: el HTR simulado no la lee, pero la carga la valida por extensión y tipo.
const PNG_MINIMO = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');

let consecutivo = 0;
const aleatorio = () => Math.random().toString(16).slice(2, 10);
// Un tema en el formato heredado que el chat acotado reconoce hoy.
const nuevoTema = () => `99-${String(500000 + (consecutivo += 1))}-0001-PE`;

async function enviar(control, metodo, ruta, cuerpo, token) {
  const cabeceras = { 'Content-Type': 'application/json' };
  if (token) cabeceras.Authorization = `Bearer ${token}`;
  return fetch(`${control.url}${ruta}`, { method: metodo, headers: cabeceras, body: cuerpo ? JSON.stringify(cuerpo) : undefined });
}

// Inicio de sesión por la API (no por la pantalla): devuelve el token del usuario creado con `crearUsuario`.
async function iniciarSesion(control, usuario) {
  const respuesta = await enviar(control, 'POST', '/auth/login', { email: usuario.correo, password: usuario.contrasena });
  expect(respuesta.status).toBe(200);
  return (await respuesta.json()).access_token;
}

// Un documento de texto inventado con una frase distintiva única (como `documento_de_prueba` de pytest).
function documentoDePrueba() {
  const sufijo = aleatorio();
  const frase = `la quebrada ficticia ${sufijo} desemboca en la laguna inventada de los patos azules`;
  const texto = `PRUEBA documento inventado número ${sufijo}. Este texto es ficticio y sirve solo para las pruebas automatizadas `
    + `de ServIA: ${frase}. Describe un expediente imaginario de una oficina que no existe, con fechas, nombres y lugares `
    + 'inventados, y se repite lo suficiente para formar al menos un fragmento completo cuando el sistema lo divide.';
  return { nombre: `PRUEBA_${sufijo}.txt`, contenido: Buffer.from(texto, 'utf-8'), frase, tipo: 'text/plain' };
}

// Un PDF mínimo y válido de una página con texto: Tika lo lee. Los desplazamientos de la tabla `xref` se calculan, porque
// un PDF con la tabla mal armada puede rechazarse en lugar de leerse.
function pdfMinimo(texto) {
  const limpio = texto.replace(/[()\\]/g, ' ');
  const flujo = `BT /F1 12 Tf 40 700 Td (${limpio}) Tj ET`;
  const objetos = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    `<< /Length ${flujo.length} >>\nstream\n${flujo}\nendstream`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ];
  let cuerpo = '%PDF-1.4\n';
  const desplazamientos = [];
  objetos.forEach((objeto, i) => {
    desplazamientos.push(cuerpo.length);
    cuerpo += `${i + 1} 0 obj\n${objeto}\nendobj\n`;
  });
  const inicioXref = cuerpo.length;
  cuerpo += `xref\n0 ${objetos.length + 1}\n0000000000 65535 f \n`;
  for (const d of desplazamientos) cuerpo += `${String(d).padStart(10, '0')} 00000 n \n`;
  cuerpo += `trailer\n<< /Size ${objetos.length + 1} /Root 1 0 R >>\nstartxref\n${inicioXref}\n%%EOF\n`;
  return Buffer.from(cuerpo, 'latin1');
}

async function cargar(control, token, tema, archivos) {
  const formulario = new FormData();
  formulario.append('CT_Num_expediente', tema);
  for (const archivo of archivos) {
    formulario.append('files', new Blob([archivo.contenido], { type: archivo.tipo || 'text/plain' }), archivo.nombre);
  }
  const respuesta = await fetch(`${control.url}/ingesta/archivos`, {
    method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: formulario,
  });
  expect(respuesta.status).toBe(200);
  const { task_ids: ids } = await respuesta.json();
  expect(ids.every((id) => typeof id === 'string')).toBe(true);
  return ids;
}

const estadoDeLaTarea = async (control, token, id) => (
  await (await enviar(control, 'GET', `/ingesta/progress/${id}`, undefined, token)).json()
).status;

const esperarTarea = (control, token, id, esperado) => expect.poll(
  () => estadoDeLaTarea(control, token, id), { timeout: 30_000, intervals: [100, 250, 500], message: `tarea ${id}` },
).toBe(esperado);

// Sube un documento de texto al tema y espera a que quede procesado.
async function subirYProcesar(control, token, tema, documento) {
  const [id] = await cargar(control, token, tema, [documento]);
  await esperarTarea(control, token, id, 'completado');
}

function leerEventos(texto) {
  return texto.split('\n').filter((linea) => linea.startsWith('data: ')).map((linea) => JSON.parse(linea.slice(6)));
}
const textoDeLosEventos = (eventos) => eventos.filter((e) => e.type === 'chunk').map((e) => e.content).join('');

function cuerpoDeChat(usuario, pregunta, { tema, notebook, sesion } = {}) {
  const cuerpo = { query: pregunta, session_id: sesion || `session_${usuario.cedula}_${aleatorio()}` };
  if (tema !== undefined) cuerpo.expediente_number = tema;
  if (notebook !== undefined) cuerpo.notebook_id = String(notebook);
  return cuerpo;
}

async function preguntar(control, token, usuario, pregunta, opciones) {
  const respuesta = await enviar(control, 'POST', '/rag/consulta-con-historial-stream', cuerpoDeChat(usuario, pregunta, opciones), token);
  expect(respuesta.status).toBe(200);
  return leerEventos(await respuesta.text());
}

// Abre la consulta SIN esperar su final y va guardando lo que llega, para ver el texto parcial de una respuesta retenida.
function abrirConsulta(control, token, usuario, pregunta, opciones) {
  const visto = { texto: '', terminado: false };
  const fin = (async () => {
    const respuesta = await enviar(control, 'POST', '/rag/consulta-con-historial-stream', cuerpoDeChat(usuario, pregunta, opciones), token);
    visto.estado = respuesta.status;
    const decodificador = new TextDecoder();
    for await (const parte of respuesta.body) visto.texto += decodificador.decode(parte, { stream: true });
    visto.terminado = true;
  })();
  return { visto, fin };
}

// La carga mixta de la 004: un válido, uno vacío y uno de nombre no válido. El navegador envía sin alterar un nombre de más
// de 255 bytes (separadores y caracteres de control sí los altera), así que ese es el no válido.
function cargaMixta() {
  const sufijo = aleatorio();
  return {
    valido: documentoDePrueba(),
    vacio: { nombre: `PRUEBA_vacio_${sufijo}.txt`, contenido: Buffer.alloc(0), tipo: 'text/plain' },
    largo: { nombre: `PRUEBA_${'a'.repeat(260)}_${sufijo}.txt`, contenido: Buffer.from('PRUEBA contenido inventado'), tipo: 'text/plain' },
  };
}

const rutaCitada = (tema, documento) => `(uploads/${tema}/${documento.nombre})`;

// Un notebook propio (por la API): devuelve el notebook, con su `id` y su `clave_interna` (el tema de sus documentos).
async function crearNotebook(control, token, nombre = `PRUEBA notebook ${aleatorio()}`) {
  const creacion = await enviar(control, 'POST', '/notebooks', { nombre }, token);
  expect(creacion.status).toBe(200);
  return creacion.json();
}

const listarDocumentos = async (control, token, notebook) => (
  await (await enviar(control, 'GET', `/notebooks/${notebook.id}/documentos`, undefined, token)).json()
);

// Un notebook propio con un documento procesado: devuelve el notebook, el documento y su identificador.
async function notebookConDocumento(control, token, documento = documentoDePrueba()) {
  const notebook = await crearNotebook(control, token);
  await subirYProcesar(control, token, notebook.clave_interna, documento);
  const fila = (await listarDocumentos(control, token, notebook)).find((d) => d.nombre_archivo === documento.nombre);
  expect(fila?.estado).toBe('Procesado');
  return { notebook, documento, id: fila.id };
}

module.exports = {
  PNG_MINIMO, aleatorio, nuevoTema, enviar, iniciarSesion, documentoDePrueba, pdfMinimo, cargar, estadoDeLaTarea, esperarTarea,
  subirYProcesar, leerEventos, textoDeLosEventos, preguntar, abrirConsulta, rutaCitada, crearNotebook, listarDocumentos,
  notebookConDocumento, cargaMixta,
};
