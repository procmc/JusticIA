import { 
  IoHomeOutline,        // 🏠 Inicio
  IoSearchOutline,      // 🔍 Búsqueda
  IoCloudUploadOutline, // ☁️📤 Cargar documentos
  IoSettingsOutline,    // ⚙️ Administración
  IoPeopleOutline,      // 👥 Usuarios
  IoTimeOutline,        // ⏰ Historial
  IoChatbubbleOutline,  // 💬 Chat/Asistente
  IoDocumentsOutline    // 📄 Casos similares
} from "react-icons/io5";

export const menuItems = [
  {
    id: 0,
    label: "Inicio",
    icon: IoHomeOutline,
    link: "/",
  },
  {
    id: 1,
    label: "Administración", 
    icon: IoSettingsOutline,
    subItems: [
      {
        label: "Usuarios del Sistema",
        link: "/administracion/gestion-usuarios",
        icon: IoPeopleOutline, // 👥 Opcional para subitems
      },
      {
        label: "Historial de Actividades",
        link: "/administracion/bitacora",
        icon: IoTimeOutline, // ⏰ Opcional para subitems
      },
    ],
  },
  {
    id: 2,
    label: "Búsqueda y Consulta",
    icon: IoSearchOutline,
    subItems: [
      {
        label: "Asistente Virtual",
        link: "/consulta-datos/chat",
        icon: IoChatbubbleOutline, // 💬 Opcional para subitems
      },
      {
        label: "Casos Similares", 
        link: "/consulta-datos/busqueda-similares",
        icon: IoDocumentsOutline, // 📄 Opcional para subitems
      },
    ],
  },
  {
    id: 3,
    label: "Cargar Documentos",
    icon: IoCloudUploadOutline,
    link: "/ingesta-datos",
  },
];