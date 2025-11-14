/**
 * Componente de Layout Principal del Sistema JusticIA.
 * 
 * @module components/Layout
 * @component
 * 
 * Este componente envuelve todas las páginas de la aplicación proporcionando
 * la estructura base: sidebar, header, breadcrumbs, y botón de usuario.
 * Maneja también el flujo de cambio de contraseña obligatorio para nuevos usuarios.
 * 
 * Características:
 *   - Sidebar colapsable con menú dinámico según rol
 *   - Header para móviles con botón de menú hamburguesa
 *   - Breadcrumbs dinámicos según la ruta actual
 *   - UserButton flotante con dropdown de perfil
 *   - Drawer modal forzado para cambio de contraseña obligatorio
 *   - Limpieza automática del contexto de chat
 * 
 * Flujo de cambio de contraseña obligatorio:
 *   1. Usuario nuevo/reseteado tiene session.user.requiere_cambio_password = true
 *   2. Se muestra drawer modal que no puede cerrarse
 *   3. Usuario debe cambiar contraseña antes de usar el sistema
 *   4. Al cambiar exitosamente, se quita la bandera y se permite acceso
 * 
 * Responsive:
 *   - Desktop: Sidebar siempre visible, colapsable a iconos
 *   - Tablet/Mobile: Sidebar oculto por defecto, hamburger menu en header
 * 
 * @param {Object} props - Propiedades del componente
 * @param {React.ReactNode} props.children - Contenido de la página a renderizar
 * 
 * @example
 * ```jsx
 * // En _app.js
 * import Layout from '@/components/Layout/Layout';
 * 
 * function MyApp({ Component, pageProps }) {
 *   return (
 *     <Layout>
 *       <Component {...pageProps} />
 *     </Layout>
 *   );
 * }
 * ```
 * 
 * @example
 * ```jsx
 * // Usuario con cambio de contraseña obligatorio
 * // session.user.requiere_cambio_password = true
 * // → Se muestra drawer modal automáticamente
 * // → No puede cerrarse hasta cambiar la contraseña
 * ```
 * 
 * @returns {JSX.Element} Layout completo con sidebar, header, breadcrumbs, y contenido
 */

import React, { useState, useEffect, useRef } from "react";
import { useSession } from "next-auth/react";
import Sidebar from "./Sidebar";
import Header from "./Header";
import { UserButton } from "./UserButton";
import DynamicBreadcrumbs from "./DynamicBreadcrumbs";
import { useChatContextCleanup } from "../../hooks/conversacion/useChatContextCleanup";
import DrawerGeneral from "../ui/DrawerGeneral";
import CambiarContraseña from "@/components/auth/cambioContraseña/CambiarContraseña";

const Layout = ({ children }) => {
  const [toggleCollapse, setToggleCollapse] = useState(false);
  const [isPasswordChangeRequired, setIsPasswordChangeRequired] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const cambiarContraseñaRef = useRef();
  const { data: session } = useSession();
  
  // Hook para limpieza automática del contexto de chat
  useChatContextCleanup();

  // Detectar si el usuario requiere cambio de contraseña obligatorio
  useEffect(() => {
    if (session?.user?.requiere_cambio_password) {
      setIsPasswordChangeRequired(true);
    }
  }, [session]);

  return (
    <div className="h-screen flex w-full overflow-hidden scrollbar-hide">
      {/* Sidebar */}
      <Sidebar
        toggleCollapse={toggleCollapse}
        setToggleCollapse={setToggleCollapse}
      />

      {/* Header (solo visible en móviles) */}
      <Header
        toggleCollapse={toggleCollapse}
        setToggleCollapse={setToggleCollapse}
      />

      {/* Botón de usuario (visible en todas las pantallas) */}
      <div className="absolute -top-1 right-0 z-50 hidden md:block">
        <UserButton />
      </div>

      {/* Contenido principal */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Breadcrumbs */}
        <DynamicBreadcrumbs />
        
        <div className="flex-1 p-4 overflow-auto scrollbar-hide">
          {children}
        </div>
      </div>

      {/* Drawer obligatorio de cambio de contraseña */}
      <DrawerGeneral
        isOpen={isPasswordChangeRequired}
        onOpenChange={() => {}} // No permitir cerrar
        titulo="Cambio de Contraseña Obligatorio"
        size="md"
        mostrarFooter={true}
        botonCerrar={{ 
          mostrar: false // No mostrar botón de cerrar
        }}
        botonAccion={{
          texto: "Cambiar Contraseña",
          color: "primary",
          loading: isLoading,
          onPress: async () => {
            if (isLoading) return;
            setIsLoading(true);
            try {
              const valid = await cambiarContraseñaRef.current?.validateAndSubmit?.();
              if (valid) {
                setIsPasswordChangeRequired(false);
              } else {
                setIsLoading(false);
              }
            } catch (error) {
              console.error("Error inesperado al cambiar contraseña:", error);
              setIsLoading(false);
            }
          }
        }}
        disableClose={true} // No permitir cerrar presionando ESC o click fuera
        hideCloseButton={true} // Ocultar botón X
      >
        <div className="space-y-4">
          {/* Mensaje de alerta */}
          <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-r-lg">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-yellow-700">
                  <strong className="font-semibold">Cambio de contraseña requerido</strong>
                  <br />
                  Por seguridad, debe cambiar su contraseña antes de continuar. 
                  {session?.user?.requiere_cambio_password && (
                    <span> Esta contraseña temporal fue generada por un administrador o es su primer inicio de sesión.</span>
                  )}
                </p>
              </div>
            </div>
          </div>

          {/* Formulario de cambio de contraseña */}
          <CambiarContraseña
            ref={cambiarContraseñaRef}
            cedulaUsuario={session?.user?.id}
            onSuccess={() => {
              setIsPasswordChangeRequired(false);
              setIsLoading(false);
            }}
          />
        </div>
      </DrawerGeneral>
      
    </div>
  );
};

export default Layout;
