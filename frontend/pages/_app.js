import "@/styles/globals.css";
import "@/styles/login-animations.css";
import { HeroUIProvider, ToastProvider } from "@heroui/react";
import Layout from "@/components/Layout/Layout";
import { useRouter } from "next/router";
import { SessionProvider, signOut, useSession } from "next-auth/react";
import httpService from "@/services/httpService";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { AvatarProvider } from "@/contexts/AvatarContext";
import { useEffect } from "react";
import Toast from "@/components/ui/CustomAlert";

// Componente que maneja el contenido de la aplicación
function AppContent({ Component, pageProps }) {
  const router = useRouter();
  const { data: sesion, status } = useSession();

  // El cliente HTTP usa este token en cada petición, en vez de leer la sesión del servidor cada vez (ver `httpService`).
  useEffect(() => {
    if (status === "authenticated") httpService.fijarTokenDeSesion(sesion?.accessToken);
    else if (status === "unauthenticated") httpService.fijarTokenDeSesion(null);
  }, [status, sesion?.accessToken]);

  // Rutas sin Layout
  const noLayoutPages = ["/auth/login", "/auth/recuperar-contrasenna"];

  // Manejar expiración de sesión globalmente
  useEffect(() => {
    // Varias peticiones en curso pueden recibir 401 a la vez: el aviso y el cierre de sesión se hacen una sola vez.
    let cerrandoSesion = false;

    const handleUnauthorized = async () => {
      if (cerrandoSesion) return;
      cerrandoSesion = true;

      // Mostrar notificación de sesión expirada
      Toast.warning(
        'Sesión Expirada',
        'Tu sesión ha expirado. Por favor inicia sesión nuevamente.'
      );

      // Cerrar sesión y redirigir a login
      try {
        await signOut({
          callbackUrl: '/auth/login',
          redirect: true
        });
      } catch (error) {
        cerrandoSesion = false;
        throw error;
      }
    };

    // Escuchar evento global de sesión no autorizada
    window.addEventListener('unauthorized', handleUnauthorized);
    
    return () => {
      window.removeEventListener('unauthorized', handleUnauthorized);
    };
  }, []);

  return (
    <ThemeProvider>
      <HeroUIProvider locale="es-ES">
        <AvatarProvider>
          <ToastProvider placement={"top-right"} toastOffset={60} />
          {noLayoutPages.includes(router.pathname) ? (
            <Component {...pageProps} />
          ) : (
            <Layout>
              <Component {...pageProps} />
            </Layout>
          )}
        </AvatarProvider>
      </HeroUIProvider>
    </ThemeProvider>
  );
}

//punto de entrada de la aplicación
function MyApp({ Component, pageProps: { session, ...pageProps } }) {
  return (
    <SessionProvider 
      session={session}
      refetchInterval={5 * 60}
      refetchOnWindowFocus={true}
      refetchWhenOffline={false}
    >
      <AppContent Component={Component} pageProps={pageProps} />
    </SessionProvider>
  );
}

export default MyApp;
