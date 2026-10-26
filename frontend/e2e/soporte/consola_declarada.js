// Lista única de errores de consola heredados que la interfaz emite en un flujo correcto o en un error provocado (RA-02.45).
// Cada entrada lleva el patrón del mensaje, el motivo y la spec del módulo que lo corregirá. No son fallos esperados:
// quitar la entrada es parte de esa corrección. Las respuestas 4xx/5xx que provoca la propia prueba no van aquí: las
// declara cada prueba con `consola.provocado(/…/)`.
//
// Formato: { patron: /texto del mensaje/, motivo: 'por qué aparece', spec: 'spec que lo corregirá' }
const CONSOLA_DECLARADA = [
  {
    patron: /Error al cambiar contraseña:/,
    motivo: 'la interfaz registra con console.error el rechazo del servidor que ella misma muestra al usuario (CambiarContraseña.jsx:150, authService.js:182)',
    spec: 'spec del módulo de autenticación y usuarios que lo corrija',
  },
  {
    patron: /Error al resetear contraseña:/,
    motivo: 'la interfaz registra con console.error el fallo del reseteo que ella misma muestra al Administrador (GestionUsuarios.jsx:174, usuarioService.js:168)',
    spec: 'spec del módulo de autenticación y usuarios que lo corrija',
  },
];

// Valida la forma de la lista: una entrada incompleta es un error de la suite, no un permiso silencioso.
function validarLista(lista) {
  lista.forEach((entrada, indice) => {
    if (!(entrada.patron instanceof RegExp)) throw new Error(`Consola declarada #${indice}: falta el patron (una expresión regular).`);
    if (!entrada.motivo || typeof entrada.motivo !== 'string') throw new Error(`Consola declarada #${indice}: falta el motivo.`);
    if (!entrada.spec || typeof entrada.spec !== 'string') throw new Error(`Consola declarada #${indice}: falta la spec que lo corregirá.`);
  });
}

function esDeclarado(texto, lista = CONSOLA_DECLARADA) {
  return lista.some((entrada) => entrada.patron.test(texto));
}

validarLista(CONSOLA_DECLARADA);

module.exports = { CONSOLA_DECLARADA, esDeclarado, validarLista };
