/**
 * Utilidades para localStorage con protección SSR
 */
import { useState, useCallback } from 'react';

/**
 * Obtiene un item del localStorage de forma segura
 * @param {string} key - Clave del localStorage
 * @param {*} defaultValue - Valor por defecto si no existe o hay error
 * @returns {*} Valor del localStorage o el valor por defecto
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
 * Establece un item en localStorage de forma segura
 * @param {string} key - Clave del localStorage
 * @param {*} value - Valor a guardar
 * @returns {boolean} true si se guardó correctamente, false si hubo error
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
 * Elimina un item del localStorage de forma segura
 * @param {string} key - Clave del localStorage
 * @returns {boolean} true si se eliminó correctamente, false si hubo error
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
 * Hook personalizado para localStorage con SSR
 * @param {string} key - Clave del localStorage
 * @param {*} initialValue - Valor inicial
 * @returns {[value, setValue]} Array con el valor actual y función para actualizarlo
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