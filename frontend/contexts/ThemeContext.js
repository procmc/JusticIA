/**
 * @fileoverview Context de React para gestión de tema claro/oscuro.
 * 
 * Este módulo implementa el sistema de temas de JusticIA, permitiendo
 * alternar entre modo claro y oscuro. Persiste la preferencia del usuario
 * en localStorage y detecta automáticamente la preferencia del sistema.
 * 
 * Características:
 * - Persistencia en localStorage (clave: 'theme')
 * - Detección de preferencia del sistema (prefers-color-scheme)
 * - Aplicación automática de clase 'dark' en document.documentElement
 * - Compatible con Tailwind CSS dark mode
 * - Protección SSR (solo ejecuta en cliente)
 * 
 * Integración con Tailwind:
 * - Tailwind config debe tener: darkMode: 'class'
 * - Clases dark: dark:bg-gray-900, dark:text-white, etc.
 * 
 * @module ThemeContext
 * @requires react
 * 
 * @example
 * // En _app.js
 * import { ThemeProvider } from '@/contexts/ThemeContext';
 * 
 * function MyApp({ Component, pageProps }) {
 *   return (
 *     <ThemeProvider>
 *       <Component {...pageProps} />
 *     </ThemeProvider>
 *   );
 * }
 * 
 * @example
 * // En cualquier componente
 * import { useTheme } from '@/contexts/ThemeContext';
 * 
 * function ThemeToggle() {
 *   const { isDark, toggleTheme, theme } = useTheme();
 *   
 *   return (
 *     <button onClick={toggleTheme}>
 *       {isDark ? '☾ Modo Oscuro' : '☀️ Modo Claro'}
 *     </button>
 *   );
 * }
 * 
 * @see {@link https://tailwindcss.com/docs/dark-mode} Tailwind Dark Mode
 * @see {@link https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme} prefers-color-scheme
 * 
 * @author JusticIA Team
 * @version 1.0.0
 */
import React, { createContext, useContext, useState, useEffect } from 'react';

/**
 * Context de React para el tema.
 * No se exporta directamente, usar useTheme() hook.
 * @private
 */
const ThemeContext = createContext();

/**
 * Hook para usar el contexto de tema.
 * 
 * Proporciona acceso al estado del tema y función para alternarlo.
 * Debe usarse dentro de un ThemeProvider.
 * 
 * @hook
 * @returns {Object} Objeto con estado y funciones del tema:
 * @returns {boolean} returns.isDark - true si el tema actual es oscuro.
 * @returns {Function} returns.toggleTheme - Función para alternar entre claro/oscuro.
 * @returns {string} returns.theme - Tema actual como string: "dark" | "light".
 * 
 * @throws {Error} Si se usa fuera de un ThemeProvider.
 * 
 * @example
 * function Header() {
 *   const { isDark, toggleTheme } = useTheme();
 *   
 *   return (
 *     <header className={isDark ? 'bg-gray-900' : 'bg-white'}>
 *       <button onClick={toggleTheme}>
 *         {isDark ? 'Modo Claro' : 'Modo Oscuro'}
 *       </button>
 *     </header>
 *   );
 * }
 * 
 * @example
 * // Con icono condicional
 * function ThemeIcon() {
 *   const { theme } = useTheme();
 *   return theme === 'dark' ? <MoonIcon /> : <SunIcon />;
 * }
 */
export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme debe ser usado dentro de un ThemeProvider');
  }
  return context;
};

/**
 * Provider de Tema - Gestiona el estado global del tema claro/oscuro.
 * 
 * Maneja:
 * - Carga inicial del tema desde localStorage
 * - Detección de preferencia del sistema (primera vez)
 * - Aplicación de clase 'dark' en document.documentElement
 * - Persistencia automática en localStorage
 * 
 * @component
 * @param {Object} props
 * @param {React.ReactNode} props.children - Componentes hijos envueltos por el provider.
 * @returns {JSX.Element} Provider que envuelve children con contexto de tema.
 * 
 * @example
 * // Envolver la aplicación
 * <ThemeProvider>
 *   <Layout>
 *     <App />
 *   </Layout>
 * </ThemeProvider>
 * 
 * @note La clase 'dark' se aplica en <html> para que Tailwind dark: funcione.
 * @note Seguro para SSR (solo ejecuta localStorage en cliente).
 */
export const ThemeProvider = ({ children }) => {
  const [isDark, setIsDark] = useState(false);

  // Cargar tema desde localStorage al inicializar
  useEffect(() => {
    // Solo ejecutar en el cliente
    if (typeof window === 'undefined') return;
    
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
      setIsDark(savedTheme === 'dark');
    } else {
      // Detectar preferencia del sistema
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setIsDark(prefersDark);
    }
  }, []);

  // Aplicar tema al documento
  useEffect(() => {
    // Solo ejecutar en el cliente
    if (typeof window === 'undefined') return;
    
    if (isDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  /**
   * Alterna entre tema claro y oscuro.
   * Actualiza el estado y aplica/remueve clase 'dark' automáticamente.
   */
  const toggleTheme = () => {
    setIsDark(!isDark);
  };

  const value = {
    isDark,
    toggleTheme,
    theme: isDark ? 'dark' : 'light'
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};
