import { useMemo } from 'react';
import zxcvbn from 'zxcvbn';

// Regla única de la contraseña nueva: la usan el indicador, el botón de enviar y la validación al enviar.
// El backend todavía acepta 6 caracteres (pendiente RNF-08); esta regla es solo del frontend.
export const CRITERIOS_CONTRASEÑA = [
  { id: 'longitud', texto: 'Al menos 8 caracteres', cumple: (p) => p.length >= 8 },
  { id: 'mayuscula', texto: 'Al menos una letra mayúscula', cumple: (p) => /\p{Lu}/u.test(p) },
  { id: 'minuscula', texto: 'Al menos una letra minúscula', cumple: (p) => /\p{Ll}/u.test(p) },
  { id: 'numero', texto: 'Al menos un número', cumple: (p) => /[0-9]/.test(p) },
  { id: 'simbolo', texto: 'Al menos un símbolo (!@#$%…)', cumple: (p) => /[^\p{L}\p{N}\s]/u.test(p) },
  // Mismo umbral que antes: puntaje de zxcvbn >= 2.
  { id: 'comun', texto: 'No es una contraseña común o fácil de adivinar', cumple: (p) => p.length > 0 && zxcvbn(p).score >= 2 },
];

export const evaluarContraseña = (password) => {
  const valor = password || '';
  const criterios = CRITERIOS_CONTRASEÑA.map((c) => ({ id: c.id, texto: c.texto, cumplido: c.cumple(valor) }));
  const cumplidos = criterios.filter((c) => c.cumplido).length;
  return { criterios, cumplidos, total: criterios.length, completa: cumplidos === criterios.length };
};

// Mensaje de error al enviar (respaldo del botón): el primer criterio que falta, o null si cumple los seis.
export const mensajeContraseñaIncompleta = (password) => {
  const faltante = evaluarContraseña(password).criterios.find((c) => !c.cumplido);
  return faltante ? `La contraseña no cumple: ${faltante.texto.charAt(0).toLowerCase()}${faltante.texto.slice(1)}` : null;
};

const nivelDeFortaleza = (cumplidos) => {
  if (cumplidos <= 1) return { label: 'Muy débil', color: 'bg-red-500', textColor: 'text-red-600 dark:text-red-400' };
  if (cumplidos === 2) return { label: 'Débil', color: 'bg-orange-500', textColor: 'text-orange-600 dark:text-orange-400' };
  if (cumplidos <= 4) return { label: 'Aceptable', color: 'bg-yellow-500', textColor: 'text-yellow-600 dark:text-yellow-400' };
  if (cumplidos === 5) return { label: 'Buena', color: 'bg-blue-500', textColor: 'text-blue-600 dark:text-blue-400' };
  return { label: 'Muy fuerte', color: 'bg-green-500', textColor: 'text-green-600 dark:text-green-400' };
};

const PasswordStrengthIndicator = ({ password }) => {
  const evaluacion = useMemo(() => evaluarContraseña(password), [password]);
  const nivel = nivelDeFortaleza(evaluacion.cumplidos);

  return (
    <div className="w-full">
      <div
        className="w-full bg-gray-200 dark:bg-gray-700 rounded-md h-2 overflow-hidden mb-2"
        role="progressbar"
        aria-label="Fortaleza de la contraseña"
        aria-valuemin={0}
        aria-valuemax={evaluacion.total}
        aria-valuenow={evaluacion.cumplidos}
      >
        <div
          className={`h-full ${nivel.color} transition-all duration-300 ease-out rounded-md`}
          style={{ width: `${(evaluacion.cumplidos / evaluacion.total) * 100}%` }}
        />
      </div>

      <div className="w-full flex items-center justify-between mb-2">
        <span className={`text-xs font-medium ${nivel.textColor}`}>Fortaleza: {nivel.label}</span>
        <span className="text-xs text-gray-500 dark:text-gray-400">{evaluacion.cumplidos}/{evaluacion.total}</span>
      </div>

      <ul className="w-full space-y-1" aria-label="Requisitos de la contraseña">
        {evaluacion.criterios.map((c) => (
          <li
            key={c.id}
            data-criterio={c.id}
            data-cumplido={c.cumplido ? 'true' : 'false'}
            className={`flex items-start text-xs ${c.cumplido ? 'text-green-700 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'}`}
          >
            <span aria-hidden="true" className="mr-2 w-3 shrink-0 text-center font-bold">{c.cumplido ? '✓' : '○'}</span>
            <span>{c.texto}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default PasswordStrengthIndicator;
