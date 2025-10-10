/**
 * Middleware de Next.js para protección de rutas con NextAuth
 * 
 * Este middleware:
 * 1. Protege todas las rutas excepto /auth/login y públicas
 * 2. Valida roles de usuario para rutas administrativas
 * 3. Redirige a login si no hay sesión
 * 4. Redirige a inicio si el usuario no tiene permisos
 */

import { withAuth } from "next-auth/middleware";
import { NextResponse } from "next/server";

// Configuración de rutas por rol (2 roles: Administrador y Usuario Judicial)
const ROUTE_PERMISSIONS = {
  // Rutas de administración - Solo Administrador
  "/administracion": ["Administrador"],
  "/administracion/gestion-usuarios": ["Administrador"],
  "/administracion/bitacora": ["Administrador"],
  
  // Rutas de ingesta - Solo Usuario Judicial
  "/ingesta-datos": ["Usuario Judicial"],
  
  // Rutas de consulta - Solo Usuario Judicial
  "/consulta-datos": ["Usuario Judicial"],
  "/consulta-datos/chat": ["Usuario Judicial"],
  "/consulta-datos/busqueda-similares": ["Usuario Judicial"],
  
  // Ruta de inicio - Todos los usuarios autenticados
  "/": ["Administrador", "Usuario Judicial"],
};

/**
 * Verifica si un usuario tiene permiso para acceder a una ruta
 */
function hasPermission(userRole, pathname) {
  // Buscar la configuración más específica que coincida
  let matchedRoute = null;
  let matchedRoles = null;
  
  for (const [route, roles] of Object.entries(ROUTE_PERMISSIONS)) {
    if (pathname === route || pathname.startsWith(route + "/")) {
      // Preferir rutas más específicas (más largas)
      if (!matchedRoute || route.length > matchedRoute.length) {
        matchedRoute = route;
        matchedRoles = roles;
      }
    }
  }
  
  // Si no hay configuración, denegar por defecto
  if (!matchedRoles) {
    return false;
  }
  
  // Verificar si el rol del usuario está en la lista de roles permitidos
  return matchedRoles.includes(userRole);
}

export default withAuth(
  function middleware(req) {
    const { pathname } = req.nextUrl;
    const token = req.nextauth.token;
    
    // Si no hay token (no debería pasar por withAuth, pero por seguridad)
    if (!token) {
      const loginUrl = new URL("/auth/login", req.url);
      loginUrl.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(loginUrl);
    }
    
    const userRole = token.role;
    
    // Verificar permisos para la ruta actual
    if (!hasPermission(userRole, pathname)) {
      console.log(`❌ Acceso denegado: Usuario con rol ${userRole} intentó acceder a ${pathname}`);
      
      // Redirigir a inicio con mensaje de error
      const homeUrl = new URL("/", req.url);
      homeUrl.searchParams.set("error", "unauthorized");
      return NextResponse.redirect(homeUrl);
    }
    return NextResponse.next();
  },
  {
    callbacks: {
      /**
       * Determina si el middleware debe ejecutarse
       * Si retorna false, redirige a login
       */
      authorized: ({ token }) => {
        // Solo usuarios con token válido pueden acceder
        return !!token;
      },
    },
    pages: {
      signIn: "/auth/login",
    },
  }
);

/**
 * Configuración de rutas donde el middleware se ejecuta
 * Excluye rutas públicas y estáticas
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - /auth/* (todas las páginas de autenticación: login, recuperar contraseña, cambiar contraseña)
     * - /api/auth (endpoints de NextAuth)
     * - /_next/static (archivos estáticos)
     * - /_next/image (optimización de imágenes)
     * - /favicon.ico, /robots.txt (archivos públicos)
     * - /public (carpeta pública)
     */
    "/((?!auth|api/auth|_next/static|_next/image|favicon.ico|robots.txt|.*\\.png|.*\\.jpg|.*\\.jpeg|.*\\.gif|.*\\.svg|.*\\.ico).*)",
  ],
};
