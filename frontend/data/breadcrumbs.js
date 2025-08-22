// Mapeo de rutas a breadcrumbs
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
