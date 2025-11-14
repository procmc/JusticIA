/**
 * Componente de Breadcrumbs Dinámicos basados en Ruta.
 * 
 * @module components/Layout/DynamicBreadcrumbs
 * @component
 * 
 * Muestra breadcrumbs de navegación que se generan automáticamente según la ruta actual
 * del router. Utiliza una configuración centralizada (breadcrumbsConfig) para mapear
 * rutas a breadcrumbs específicos.
 * 
 * Características:
 *   - Generación automática: Lee router.pathname y busca en breadcrumbsConfig
 *   - Ícono de inicio: Primera miga siempre muestra ícono de casa
 *   - Links activos: Migas no finales son clicables
 *   - Miga actual: Última miga no es clicable (isCurrent=true)
 *   - Oculto en home: No se muestra en la página de inicio (/)
 *   - Separador visual: Usa › para separar migas
 * 
 * Configuración de breadcrumbs:
 *   breadcrumbsConfig mapea rutas a arrays de objetos breadcrumb:
 *   ```javascript
 *   {
 *     '/usuarios': [
 *       { label: 'Inicio', href: '/', isHome: true },
 *       { label: 'Administración', href: '/administracion' },
 *       { label: 'Usuarios', href: '#', isCurrent: true }
 *     ]
 *   }
 *   ```
 * 
 * Propiedades de breadcrumb:
 *   - label: Texto a mostrar
 *   - href: URL del link (# para miga actual)
 *   - isHome: true para mostrar ícono de casa en lugar de texto
 *   - isCurrent: true para miga actual (no clicable)
 * 
 * @returns {JSX.Element|null} Breadcrumbs o null si está en la página de inicio
 * 
 * @example
 * ```jsx
 * import DynamicBreadcrumbs from '@/components/Layout/DynamicBreadcrumbs';
 * 
 * function Layout() {
 *   return (
 *     <div>
 *       <DynamicBreadcrumbs />
 *       {/* Contenido de la página */}
 *     </div>
 *   );
 * }
 * ```
 * 
 * @example
 * ```jsx
 * // En /data/breadcrumbs.js
 * export const breadcrumbsConfig = {
 *   '/consultas': [
 *     { label: 'Inicio', href: '/', isHome: true },
 *     { label: 'Consultas IA', href: '#', isCurrent: true }
 *   ],
 *   '/usuarios/nuevo': [
 *     { label: 'Inicio', href: '/', isHome: true },
 *     { label: 'Administración', href: '/administracion' },
 *     { label: 'Usuarios', href: '/usuarios' },
 *     { label: 'Nuevo Usuario', href: '#', isCurrent: true }
 *   ]
 * };
 * ```
 */

import React from "react";
import { useRouter } from "next/router";
import { IoHomeSharp } from "react-icons/io5";
import { Breadcrumbs, BreadcrumbItem } from "@heroui/react";
import { breadcrumbsConfig } from "../../data/breadcrumbs";
import ThemeToggleButton from "../ui/ThemeToggleButton";

const DynamicBreadcrumbs = () => {
  const router = useRouter();

  // Función para obtener breadcrumbs basados en la ruta
  const getBreadcrumbs = () => {
    const path = router.pathname;
    
    return breadcrumbsConfig[path] || [{ label: 'Inicio', href: '/', isHome: true }];
  };

  const breadcrumbs = getBreadcrumbs();

  // No mostrar breadcrumbs en la página de inicio
  if (router.pathname === '/') {
    return null;
  }

  return (
    <div className="bg-white border-b px-4 py-3">
      <Breadcrumbs
        classNames={{
          list: "bg-white px-4 py-1",
        }}
        itemClasses={{
          item: "text-slate-600 data-[current=true]:text-slate-800 data-[current=true]:font-semibold hover:text-blue-600 transition-colors",
          separator: "text-slate-400 mx-1",
        }}
        variant="solid"
        separator="›"
      >
        {breadcrumbs.map((breadcrumb, index) => {
          const isLast = index === breadcrumbs.length - 1;
          
          return (
            <BreadcrumbItem 
              key={index}
              href={breadcrumb.isCurrent || breadcrumb.href === '#' ? undefined : breadcrumb.href}
              isCurrent={breadcrumb.isCurrent}
            >
              <div className="flex items-center gap-1">
                {breadcrumb.isHome ? (
                  <IoHomeSharp className="w-4 h-4 text-slate-600"/>
                ) : (
                  <span className="text-sm font-medium">{breadcrumb.label}</span>
                )}
              </div>
            </BreadcrumbItem>
          );
        })}
      </Breadcrumbs>
    </div>
  );
};

export default DynamicBreadcrumbs;
