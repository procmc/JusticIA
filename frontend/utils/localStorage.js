/**
 * @fileoverview Utilidades para localStorage con protección SSR y manejo de errores.
 * 
 * Este módulo proporciona wrappers seguros para operaciones de localStorage que:
 * - Protegen contra errores de SSR (verifican typeof window)
 * - Manejan errores de parseo JSON gracefully
 * - Proporcionan valores por defecto en caso de error
 * - Incluyen hook personalizado compatible con React
 * 
 * Problemas comunes que resuelve:
 * - "localStorage is not defined" en SSR (Next.js)
 * - Errores de parseo JSON en datos corruptos
 * - QuotaExceededError cuando el storage está lleno
 * - Inconsistencia entre estado React y localStorage
 * 
 * API proporcionada:
 * - safeGetLocalStorage(): Leer con valor por defecto
 * - safeSetLocalStorage(): Escribir con manejo de errores
 * - safeRemoveLocalStorage(): Eliminar con manejo de errores
 * - useLocalStorage(): Hook React para sincronizar estado con localStorage
 * - isLocalStorageAvailable(): Verificar disponibilidad
 * 
 * @module localStorage
 * @requires react
 * 
 * @example
 * import { safeGetLocalStorage, safeSetLocalStorage, useLocalStorage } from '@/utils/localStorage';
 * 
 * // Leer valor con fallback
 * const theme = safeGetLocalStorage('theme', 'light');
 * 
 * // Escribir valor
 * safeSetLocalStorage('theme', 'dark');
 * 
 * // Hook React
 * function MyComponent() {
 *   const [count, setCount] = useLocalStorage('count', 0);
 *   return <button onClick={() => setCount(count + 1)}>{count}</button>;
 * }
 * 
 * @see {@link https://nextjs.org/docs/messages/react-hydration-error} Errores de hidratación en Next.js
 * @see {@link https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage} API localStorage
 * 
 * @author JusticIA Team
 * @version 1.0.0
 */
import { useState, useCallback } from 'react';

/**
 * Obtiene un item del localStorage de forma segura con manejo de errores.
 * 
 * Maneja automáticamente:
 * - Verificación de SSR (retorna defaultValue en servidor)
 * - Parseo JSON (intenta parsear, retorna defaultValue si falla)
 * - Valores null/undefined (retorna defaultValue)
 * - Errores de acceso a localStorage (permisos, privacidad)
 * 
 * @function safeGetLocalStorage
 * @param {string} key - Clave del localStorage a leer.
 * @param {*} [defaultValue=null] - Valor por defecto si no existe o hay error.
 * @returns {*} Valor parseado del localStorage o el valor por defecto.
 * 
 * @example
 * // Leer configuración con fallback
 * const theme = safeGetLocalStorage('theme', 'light');
 * const settings = safeGetLocalStorage('settings', { notifications: true });
 * 
 * @example
 * // Leer array con fallback
 * const favorites = safeGetLocalStorage('favorites', []);
 * favorites.forEach(item => console.log(item));
 * 
 * @note Los valores se almacenan como JSON, por lo que se parsean automáticamente.
 * @note Seguro para SSR (retorna defaultValue en servidor).
 */
export const safeGetLocalStorage = (key, defaultValue = null) => {
  try {
    // Verificar que estamos en el cliente
    if (typeof window === 'undefined') return defaultValue;
    
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch (error) {
    console.warn(`Error leyendo localStorage[${key}]:`, error);
    return defaultValue;
  }
};

/**
 * Establece un item en localStorage de forma segura con manejo de errores.
 * 
 * Maneja automáticamente:
 * - Verificación de SSR (no intenta escribir en servidor)
 * - Serialización JSON (stringify automático)
 * - QuotaExceededError (storage lleno)
 * - Errores de acceso (permisos, modo privado)
 * 
 * @function safeSetLocalStorage
 * @param {string} key - Clave del localStorage donde guardar.
 * @param {*} value - Valor a guardar (se serializa a JSON automáticamente).
 * @returns {boolean} true si se guardó correctamente, false si hubo error.
 * 
 * @example
 * // Guardar configuración
 * const success = safeSetLocalStorage('theme', 'dark');
 * if (!success) {
 *   console.error('No se pudo guardar la configuración');
 * }
 * 
 * @example
 * // Guardar objeto complejo
 * safeSetLocalStorage('user-preferences', {
 *   fontSize: 16,
 *   colorScheme: 'auto',
 *   notifications: true
 * });
 * 
 * @note Los valores se serializan automáticamente con JSON.stringify.
 * @note Retorna false en SSR sin intentar escribir.
 */
export const safeSetLocalStorage = (key, value) => {
  try {
    // Verificar que estamos en el cliente
    if (typeof window === 'undefined') return false;
    
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (error) {
    console.warn(`Error guardando localStorage[${key}]:`, error);
    return false;
  }
};

/**
 * Elimina un item del localStorage de forma segura con manejo de errores.
 * 
 * @function safeRemoveLocalStorage
 * @param {string} key - Clave del localStorage a eliminar.
 * @returns {boolean} true si se eliminó correctamente, false si hubo error.
 * 
 * @example
 * // Eliminar al hacer logout
 * const handleLogout = () => {
 *   safeRemoveLocalStorage('auth-token');
 *   safeRemoveLocalStorage('user-data');
 *   router.push('/login');
 * };
 * 
 * @example
 * // Eliminar con verificación
 * if (safeRemoveLocalStorage('temp-data')) {
 *   console.log('Datos temporales eliminados');
 * }
 * 
 * @note Seguro para SSR (retorna false en servidor sin intentar eliminar).
 */
export const safeRemoveLocalStorage = (key) => {
  try {
    // Verificar que estamos en el cliente
    if (typeof window === 'undefined') return false;
    
    localStorage.removeItem(key);
    return true;
  } catch (error) {
    console.warn(`Error eliminando localStorage[${key}]:`, error);
    return false;
  }
};

/**
 * Hook personalizado para sincronizar estado de React con localStorage.
 * 
 * Proporciona una API similar a useState pero persiste el valor en localStorage.
 * Compatible con SSR (Next.js) y maneja errores automáticamente.
 * 
 * Características:
 * - Sincronización automática entre estado y localStorage
 * - Valor inicial seguro (usa safeGetLocalStorage internamente)
 * - Soporte para funciones actualizadoras (como useState)
 * - Memoización con useCallback para optimización
 * 
 * @function useLocalStorage
 * @param {string} key - Clave del localStorage.
 * @param {*} initialValue - Valor inicial si no existe en localStorage.
 * @returns {[*, Function]} Tupla [valor, setValue] compatible con useState.
 * 
 * @example
 * // Uso básico (similar a useState)
 * function ThemeToggle() {
 *   const [theme, setTheme] = useLocalStorage('theme', 'light');
 *   
 *   return (
 *     <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
 *       Tema: {theme}
 *     </button>
 *   );
 * }
 * 
 * @example
 * // Con función actualizadora
 * function Counter() {
 *   const [count, setCount] = useLocalStorage('count', 0);
 *   
 *   return (
 *     <button onClick={() => setCount(prev => prev + 1)}>
 *       Count: {count}
 *     </button>
 *   );
 * }
 * 
 * @example
 * // Con objetos complejos
 * function UserPreferences() {
 *   const [prefs, setPrefs] = useLocalStorage('preferences', {
 *     fontSize: 16,
 *     notifications: true
 *   });
 *   
 *   const toggleNotifications = () => {
 *     setPrefs(prev => ({ ...prev, notifications: !prev.notifications }));
 *   };
 *   
 *   return <Switch checked={prefs.notifications} onChange={toggleNotifications} />;
 * }
 * 
 * @note El hook usa useCallback para optimizar renders.
 * @note Los valores se sincronizan automáticamente en cada cambio.
 * @note Compatible con hidratación de Next.js (no causa errores de SSR).
 */
export const useLocalStorage = (key, initialValue) => {
  const [storedValue, setStoredValue] = useState(() => {
    return safeGetLocalStorage(key, initialValue);
  });

  const setValue = useCallback((value) => {
    try {
      // Permitir que value sea una función para consistencia con useState
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      
      setStoredValue(valueToStore);
      safeSetLocalStorage(key, valueToStore);
    } catch (error) {
      console.error(`Error en useLocalStorage[${key}]:`, error);
    }
  }, [key, storedValue]);

  return [storedValue, setValue];
};

/**
 * Verifica si localStorage está disponible
 * @returns {boolean} true si localStorage está disponible
 */
export const isLocalStorageAvailable = () => {
  try {
    return typeof window !== 'undefined' && 'localStorage' in window;
  } catch (error) {
    return false;
  }
};