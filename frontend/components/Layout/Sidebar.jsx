/**
 * Componente de Sidebar de Navegación con Menú Dinámico.
 * 
 * @module components/Layout/Sidebar
 * @component
 * 
 * Sidebar colapsable que muestra el menú de navegación principal del sistema JusticIA.
 * El menú se filtra dinámicamente según el rol del usuario (Administrador/Usuario Judicial).
 * 
 * Características:
 *   - Colapsable: Alterna entre vista completa e iconos solamente
 *   - Responsive: En móviles se oculta y se activa con hamburger menu
 *   - Menú dinámico: Filtrado por rol usando filterMenuByRole
 *   - Submenús expandibles: Ítems con subItems pueden expandirse/colapsarse
 *   - Tooltips: En modo colapsado, tooltips muestran etiquetas
 *   - Active states: Resalta ruta activa y subítems activos
 *   - Transiciones suaves: Animaciones CSS para colapsar/expandir
 * 
 * Estados del sidebar:
 *   - Expandido desktop: width: 256px (w-64)
 *   - Colapsado desktop: width: 80px (w-20)
 *   - Móvil cerrado: transform: translateX(-100%) (fuera de pantalla)
 *   - Móvil abierto: transform: translateX(0) (visible)
 * 
 * Flujo de navegación:
 *   1. Usuario autenticado → session.user.role determina menú visible
 *   2. filterMenuByRole filtra menuItems según rol
 *   3. Ítem con subItems → click expande/colapsa submenú
 *   4. Ítem sin subItems → Link directo a la ruta
 *   5. Logout → limpia contexto de chat y cierra sesión
 * 
 * Menú dinámico por rol:
 *   Administrador: Acceso completo (usuarios, bitácora, configuración, etc.)
 *   Usuario Judicial: Acceso limitado (consultas, expedientes, perfil)
 * 
 * @param {Object} props - Propiedades del componente
 * @param {boolean} props.toggleCollapse - Estado de colapso del sidebar
 * @param {Function} props.setToggleCollapse - Función para cambiar estado de colapso
 * 
 * @example
 * ```jsx
 * import Sidebar from '@/components/Layout/Sidebar';
 * 
 * function Layout() {
 *   const [toggleCollapse, setToggleCollapse] = useState(false);
 *   
 *   return (
 *     <Sidebar 
 *       toggleCollapse={toggleCollapse}
 *       setToggleCollapse={setToggleCollapse}
 *     />
 *   );
 * }
 * ```
 * 
 * @example
 * ```jsx
 * // Estructura de menuItem con subItems
 * {
 *   id: 'administracion',
 *   label: 'Administración',
 *   icon: AdminIcon,
 *   subItems: [
 *     { label: 'Usuarios', link: '/usuarios', icon: UserIcon },
 *     { label: 'Bitácora', link: '/bitacora', icon: LogIcon }
 *   ]
 * }
 * 
 * // Ítem simple sin subItems
 * {
 *   id: 'consultas',
 *   label: 'Consultas IA',
 *   icon: ChatIcon,
 *   link: '/consultas'
 * }
 * ```
 * 
 * @returns {JSX.Element} Sidebar con menú de navegación filtrado por rol
 */

import classNames from "classnames";
import Link from "next/link";
import { useRouter } from "next/router";
import React, { useEffect, useState, useMemo } from "react";
import { MdOutlineKeyboardDoubleArrowRight, MdOutlineKeyboardDoubleArrowLeft } from "react-icons/md";
import { FiChevronDown, FiChevronUp } from "react-icons/fi";
import { LogoutIcon } from "../icons";
import { menuItems, filterMenuByRole } from "../../data/menuitems";
import { useSession, signOut } from "next-auth/react";
import { Tooltip } from "@heroui/tooltip";
import { clearAllChatContext } from "../../utils/chatContextUtils";

const Sidebar = ({ toggleCollapse, setToggleCollapse }) => {
  const [isMobile, setIsMobile] = useState(false);
  const [expandedItems, setExpandedItems] = useState([]);
  const { data: session, status } = useSession();
  const router = useRouter();

  // Filtrar menús según el rol del usuario
  const filteredMenuItems = useMemo(() => {
    if (!session?.user?.role) return [];
    return filterMenuByRole(menuItems, session.user.role);
  }, [session?.user?.role]);

  const handleLogout = async () => {
    try {
      // Limpiar contexto de chat usando utilidad centralizada
      clearAllChatContext();

      await signOut({ 
        callbackUrl: '/auth/login',
        redirect: true 
      });
    } catch (error) {
      console.error('Error durante el logout:', error);
      // Fallback: redirigir manualmente si hay error
      router.push('/auth/login');
    }
  };

  useEffect(() => {
    const checkIsMobile = () => {
      if (typeof window !== 'undefined') {
        setIsMobile(!window.matchMedia("(min-width: 768px)").matches);
      }
    };

    checkIsMobile();

    if (typeof window !== 'undefined') {
      const mediaQuery = window.matchMedia("(min-width: 768px)");
      mediaQuery.addListener(checkIsMobile);

      return () => {
        mediaQuery.removeListener(checkIsMobile);
      };
    }
  }, []);

  const handleExpand = (id) => {
    // Si el sidebar está colapsado, primero lo expandimos
    if (toggleCollapse) {
      setToggleCollapse(false);
    }
    
    setExpandedItems((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const checkSubItemsActive = (subItems) => {
    return subItems.some((item) => router.pathname === item.link);
  };

  const getNavItemClasses = (link, hasSubItems = false, subItems = null) => {
    let isActive = false;
    
    if (hasSubItems && subItems) {
      isActive = checkSubItemsActive(subItems);
    } else if (link) {
      isActive = router.pathname === link;
    }
    
    return classNames(
      "flex items-center cursor-pointer hover:bg-gray-100 hover:bg-opacity-20 rounded w-full overflow-hidden whitespace-nowrap mb-1 py-2 px-3",
      {
        "bg-gray-100 bg-opacity-20": isActive,
      }
    );
  };

  return (
    <div
      className={classNames(
        "h-screen px-4 pt-8 pb-4 bg-primary flex flex-col justify-between shadow-xl z-50 transform transition-all duration-500 ease-in-out",
        {
          "w-64": !toggleCollapse,
          "w-20 md:w-20": toggleCollapse,
          "-translate-x-full md:translate-x-0": toggleCollapse && isMobile,
          "fixed md:relative": true,
        }
      )}
      style={{ 
        transition: "width 600ms cubic-bezier(0.25, 0.46, 0.45, 0.94), transform 400ms ease-in-out",
        willChange: "width, transform"
      }}
    >
      <div className="flex flex-col h-full overflow-y-auto scrollbar-hide">
        <div className="flex items-center justify-between relative hidden md:flex">
          <div className="flex items-center gap-4">
            {toggleCollapse ? (
              <div
                onClick={() => setToggleCollapse(false)}
                className="flex-shrink-0 cursor-pointer flex items-center justify-center w-12 h-12 hover:bg-gray-100 hover:bg-opacity-20 rounded"
              >
                <MdOutlineKeyboardDoubleArrowRight className="w-5 h-5 text-white" />
              </div>
            ) : null}
            {!toggleCollapse && (
              <Link href="/" className="block">
                <span
                  className="mb-3 ml-4 text-2xl font-extrabold select-none flex items-center gap-2 relative group cursor-pointer transition-all duration-200 hover:opacity-90 hover:scale-105"
                  style={{letterSpacing: '1px'}}>
                  <span className="relative cursor-pointer transition-all duration-200 group-hover:drop-shadow-lg">
                    <span
                      className="text-3xl font-extrabold bg-clip-text text-transparent drop-shadow-md"
                      style={{
                        background: 'linear-gradient(90deg, #ffffff 0%, #e5e7eb 40%, #ffffffff 100%)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        fontWeight: 900,
                        letterSpacing: '1px',
                      }}
                    >JusticIA</span>
                    <span
                      className="block h-1 w-full rounded-full transition-all duration-300 origin-left mt-1 group-hover:shadow-lg group-hover:shadow-cyan-400/50"
                      style={{background: 'linear-gradient(90deg, #ffffff 0%, #e5e7eb 40%, #ffffffff 100%)', transform: 'scaleX(1)'}}
                    ></span>
                  </span>
                </span>
              </Link>
            )}
          </div>
          {!toggleCollapse && (
            <div
              onClick={() => setToggleCollapse(true)}
              className="p-2 cursor-pointer rounded hover:bg-gray-100 hover:bg-opacity-20 flex items-center justify-center"
            >
              <MdOutlineKeyboardDoubleArrowLeft className="w-5 h-5 text-white" />
            </div>
          )}
        </div>

        <div className="flex flex-col items-start mt-10">
          {(
            filteredMenuItems.map(({ id, icon: Icon, link, label, subItems }) => {
              const hasSubItems = subItems && subItems.length > 0;

              return (
                <div key={id} className="w-full">
                  {hasSubItems ? (
                    <div>
                      <Tooltip content={label} placement="right" isDisabled={!toggleCollapse}>
                        <div
                          className={getNavItemClasses(null, hasSubItems, subItems)}
                          onClick={() => handleExpand(id)}
                        >
                          <div className="flex items-center justify-between w-full">
                            <div className="flex items-center flex-1 mr-2">
                              <div style={{ width: "2.5rem" }}>
                                <Icon className="w-5 h-5 text-white" />
                              </div>
                              {!toggleCollapse && (
                                <span className="text-sm font-medium text-white">
                                  {label}
                                </span>
                              )}
                            </div>
                            {!toggleCollapse && (
                              <div className="flex-shrink-0">
                                {expandedItems.includes(id) ? (
                                  <FiChevronUp className="w-4 h-4 text-white" />
                                ) : (
                                  <FiChevronDown className="w-4 h-4 text-white" />
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      </Tooltip>
                      {!toggleCollapse && expandedItems.includes(id) && (
                        <div className="ml-4 mt-2 mb-2">
                          {subItems.map((subItem, index) => (
                            <Tooltip key={index} content={subItem.label} placement="right" isDisabled={!toggleCollapse}>
                              <Link
                                href={subItem.link}
                                className={classNames(
                                  "flex items-center cursor-pointer hover:bg-gray-100 hover:bg-opacity-20 rounded w-full py-1.5 px-4 mb-1 whitespace-nowrap overflow-hidden",
                                  {
                                    "bg-gray-100 bg-opacity-20 border-l-4 border-blue-400": router.pathname === subItem.link,
                                  }
                                )}
                              >
                                {subItem.icon && (
                                  <div className="flex-shrink-0 mr-2">
                                    <subItem.icon className="w-4 h-4 text-white" />
                                  </div>
                                )}
                                <span className="text-sm text-white truncate">
                                  {subItem.label}
                                </span>
                              </Link>
                            </Tooltip>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <Tooltip content={label} placement="right" isDisabled={!toggleCollapse}>
                      <Link
                        href={link}
                        className={getNavItemClasses(link)}
                      >
                        <div className="flex items-center">
                          <div style={{ width: "2.5rem" }}>
                            <Icon className="w-5 h-5 text-white" />
                          </div>
                          {!toggleCollapse && (
                            <span className="text-sm font-medium text-white">
                              {label}
                            </span>
                          )}
                        </div>
                      </Link>
                    </Tooltip>
                  )}
                </div>
              );
            })
          )}
        </div>
        <Tooltip content="Cerrar sesión" placement="right" isDisabled={!toggleCollapse}>
          <div
            className={classNames(
              "flex items-center px-3 py-2 cursor-pointer hover:bg-gray-100 hover:bg-opacity-20 rounded mt-auto",
              {
                "justify-center": toggleCollapse,
                "justify-start": !toggleCollapse,
              }
            )}
            onClick={handleLogout}
          >
            <div style={{ width: "2.5rem" }} className="flex justify-center">
              <LogoutIcon className="w-4 h-6 text-red-400" />
            </div>
            {!toggleCollapse && (
              <span className="text-sm font-medium text-white">Cerrar sesión</span>
            )}
          </div>
        </Tooltip>
      </div>
    </div>
  );
};

export default Sidebar;