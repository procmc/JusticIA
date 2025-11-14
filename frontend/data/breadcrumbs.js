/**
 * @fileoverview Configuración de breadcrumbs (migas de pan) para navegación.
 * 
 * Este módulo define el mapeo de rutas a breadcrumbs para el componente
 * DynamicBreadcrumbs. Proporciona trails de navegación jerárquica para
 * todas las páginas de la aplicación.
 * 
 * Características:
 * - Mapeo directo de ruta a array de breadcrumb items
 * - Soporte para indicador de home (isHome)
 * - Indicador de página actual (isCurrent)
 * - Links clicables para navegación hacia atrás
 * - Compatible con Next.js routing
 * 
 * Propiedades de breadcrumb item:
 * - label: Texto visible del breadcrumb
 * - href: Ruta de navegación (usar '#' para no-clicable)
 * - isHome: true si es el item de inicio (opcional)
 * - isCurrent: true si es la página actual (opcional)
 * 
 * @module breadcrumbs
 * 
 * @example
 * import { breadcrumbsConfig } from '@/data/breadcrumbs';
 * import { useRouter } from 'next/router';
 * 
 * function MyBreadcrumbs() {
 *   const router = useRouter();
 *   const breadcrumbs = breadcrumbsConfig[router.pathname] || [];
 *   
 *   return (
 *     <nav>
 *       {breadcrumbs.map((crumb, i) => (
 *         <a key={i} href={crumb.href}>{crumb.label}</a>
 *       ))}
 *     </nav>
 *   );
 * }
 * 
 * @example
 * // Agregar nueva ruta
 * breadcrumbsConfig['/nueva-ruta'] = [
 *   { label: 'Inicio', href: '/', isHome: true },
 *   { label: 'Categoría', href: '/categoria' },
 *   { label: 'Nueva Ruta', href: '/nueva-ruta', isCurrent: true }
 * ];
 * 
 * @see {@link ../components/DynamicBreadcrumbs.jsx} Componente que usa esta config
 * 
 * @author JusticIA Team
 * @version 1.0.0
 */

/**
 * Mapeo de rutas a breadcrumbs.
 * 
 * Objeto donde:
 * - Key: Pathname de Next.js (ej: '/consulta-datos/chat')
 * - Value: Array de objetos breadcrumb con label, href, isHome, isCurrent
 * 
 * @constant {Object<string, Array<Object>>}
 */
export const breadcrumbsConfig = {
  '/': [
    { label: 'Inicio', href: '/', isHome: true }
  ],
  '/consulta-datos/busqueda-similares': [
    { label: 'Inicio', href: '/', isHome: true },
    { label: 'Búsqueda y Consulta', href: '#' },
    { label: 'Casos Similares', href: '/consulta-datos/busqueda-similares', isCurrent: true }
  ],
  '/consulta-datos/chat': [
    { label: 'Inicio', href: '/', isHome: true },
    { label: 'Búsqueda y Consulta', href: '#' },
    { label: 'Asistente Virtual', href: '/consulta-datos/chat', isCurrent: true }
  ],
  '/administracion/gestion-usuarios': [
    { label: 'Inicio', href: '/', isHome: true },
    { label: 'Administración', href: '#' },
    { label: 'Usuarios del Sistema', href: '/administracion/gestion-usuarios', isCurrent: true }
  ],
  '/administracion/bitacora': [
    { label: 'Inicio', href: '/', isHome: true },
    { label: 'Administración', href: '#' },
    { label: 'Historial de Actividades', href: '/administracion/bitacora', isCurrent: true }
  ],
  '/ingesta-datos': [
    { label: 'Inicio', href: '/', isHome: true },
    { label: 'Cargar Documentos', href: '/ingesta-datos', isCurrent: true }
  ]
};
