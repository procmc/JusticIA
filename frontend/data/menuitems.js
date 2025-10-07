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
