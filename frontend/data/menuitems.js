/**
 * @fileoverview Configuración del menú de navegación con control de acceso por roles.
 * 
 * Este módulo define la estructura completa del menú de navegación de JusticIA,
 * incluyendo items principales, subitems anidados, iconos de React Icons,
 * y permisos basados en roles (RBAC).
 * 
 * Características:
 * - Menú jerárquico con subitems
 * - Control de acceso basado en roles (ADMIN, USER)
 * - Iconos de react-icons/io5
 * - Filtrado dinámico por rol del usuario
 * - Compatible con Sidebar y navegación móvil
 * 
 * Estructura del menú:
 * - Inicio: Acceso a dashboard principal
 * - Administración (ADMIN only):
 *   - Usuarios del Sistema
 *   - Historial de Actividades (Bitácora)
 * - Búsqueda y Consulta (USER):
 *   - Asistente Virtual (Chat RAG)
 *   - Casos Similares (Búsqueda vectorial)
 * - Ingesta de Datos (USER): Carga de documentos
 * 
 * @module menuitems
 * @requires react-icons/io5
 * @requires ../common/roles
 * 
 * @example
 * import { menuItems, filterMenuByRole } from '@/data/menuitems';
 * import { ROLES } from '@/common/roles';
 * 
 * // Obtener menú completo
 * console.log(menuItems);
 * 
 * // Filtrar menú por rol de usuario
 * const userMenu = filterMenuByRole(menuItems, ROLES.USER);
 * const adminMenu = filterMenuByRole(menuItems, ROLES.ADMIN);
 * 
 * @example
 * // En Sidebar.jsx
 * function Sidebar() {
 *   const { data: session } = useSession();
 *   const userRole = session?.user?.rol;
 *   const filteredMenu = filterMenuByRole(menuItems, userRole);
 *   
 *   return (
 *     <nav>
 *       {filteredMenu.map(item => (
 *         <MenuItem key={item.id} {...item} />
 *       ))}
 *     </nav>
 *   );
 * }
 * 
 * @see {@link ../components/Sidebar.jsx} Componente que renderiza el menú
 * @see {@link ../common/roles.js} Definición de roles del sistema
 * 
 * @author JusticIA Team
 * @version 1.0.0
 */
import { 
  IoHomeOutline,
  IoSearchOutline,
  IoCloudUploadOutline,
  IoSettingsOutline,
  IoPeopleOutline,
  IoTimeOutline,
  IoChatbubbleOutline,
  IoDocumentsOutline
} from "react-icons/io5";
import { ROLES } from "../common/roles";

/**
 * Configuración del menú de navegación.
 * 
 * Array de objetos que definen la estructura del menú con:
 * - id: Identificador único del item
 * - label: Texto visible en el menú
 * - icon: Componente de icono de react-icons
 * - link: Ruta de navegación (opcional si tiene subItems)
 * - roles: Array de roles permitidos (ROLES.ADMIN, ROLES.USER)
 * - subItems: Array de subitems anidados (opcional)
 * 
 * @constant {Array<Object>}
 */
export const menuItems = [
  {
    id: 0,
    label: "Inicio",
    icon: IoHomeOutline,
    link: "/",
    roles: [ROLES.ADMIN, ROLES.USER],
  },
  {
    id: 1,
    label: "Administración", 
    icon: IoSettingsOutline,
    roles: [ROLES.ADMIN],
    subItems: [
      {
        label: "Usuarios del Sistema",
        link: "/administracion/gestion-usuarios",
        icon: IoPeopleOutline,
        roles: [ROLES.ADMIN],
      },
      {
        label: "Historial de Actividades",
        link: "/administracion/bitacora",
        icon: IoTimeOutline,
        roles: [ROLES.ADMIN],
      },
    ],
  },
  {
    id: 2,
    label: "Búsqueda y Consulta",
    icon: IoSearchOutline,
    roles: [ROLES.USER],
    subItems: [
      {
        label: "Asistente Virtual",
        link: "/consulta-datos/chat",
        icon: IoChatbubbleOutline,
        roles: [ROLES.USER],
      },
      {
        label: "Casos Similares", 
        link: "/consulta-datos/busqueda-similares",
        icon: IoDocumentsOutline,
        roles: [ROLES.USER],
      },
    ],
  },
  {
    id: 3,
    label: "Ingesta de Datos",
    icon: IoCloudUploadOutline,
    link: "/ingesta-datos",
    roles: [ROLES.USER],
  },
];

/**
 * Filtra los items del menú según el rol del usuario.
 * 
 * Aplica filtrado recursivo:
 * 1. Filtra items principales por roles permitidos
 * 2. Filtra subitems por roles permitidos
 * 3. Elimina items sin subItems válidos
 * 
 * @function filterMenuByRole
 * @param {Array<Object>} items - Array de items del menú a filtrar.
 * @param {string} userRole - Rol del usuario actual (ROLES.ADMIN | ROLES.USER).
 * @returns {Array<Object>} Array de items filtrados según el rol.
 * 
 * @example
 * // Usuario con rol USER
 * const userMenu = filterMenuByRole(menuItems, ROLES.USER);
 * // Retorna: [Inicio, Búsqueda y Consulta, Ingesta de Datos]
 * // NO incluye: Administración
 * 
 * @example
 * // Usuario con rol ADMIN
 * const adminMenu = filterMenuByRole(menuItems, ROLES.ADMIN);
 * // Retorna: [Inicio, Administración]
 * // NO incluye: Búsqueda y Consulta, Ingesta de Datos
 * 
 * @example
 * // Sin rol
 * const noMenu = filterMenuByRole(menuItems, null);
 * // Retorna: [] (array vacío)
 * 
 * @note Los items con subItems vacíos después del filtrado se eliminan.
 * @note Si userRole es null/undefined, retorna array vacío.
 */
export const filterMenuByRole = (items, userRole) => {
  if (!userRole) return [];
  
  return items
    .filter(item => {
      if (item.roles && !item.roles.includes(userRole)) {
        return false;
      }
      return true;
    })
    .map(item => {
      if (item.subItems) {
        return {
          ...item,
          subItems: item.subItems.filter(subItem => {
            if (subItem.roles && !subItem.roles.includes(userRole)) {
              return false;
            }
            return true;
          })
        };
      }
      return item;
    })
    .filter(item => !item.subItems || item.subItems.length > 0);
};
