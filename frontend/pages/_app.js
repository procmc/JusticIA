import "@/styles/globals.css";
import "@/styles/login-animations.css";
import { HeroUIProvider, ToastProvider } from "@heroui/react";
import Layout from "@/components/Layout/Layout";
import { useRouter } from "next/router";
import { SessionProvider, signOut } from "next-auth/react";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { useEffect } from "react";
import Toast from "@/components/ui/CustomAlert";

// Componente que maneja el contenido de la aplicación
function AppContent({ Component, pageProps }) {
  const router = useRouter();

  // Rutas sin Layout
  const noLayoutPages = ["/auth/login", "/auth/recuperar-contrasenna"];

  // Manejar expiración de sesión globalmente
  useEffect(() => {
    const handleUnauthorized = async () => {
      // Mostrar notificación de sesión expirada
      Toast.warning(
        'Sesión Expirada', 
        'Tu sesión ha expirado. Por favor inicia sesión nuevamente.'
      );
      
      // Cerrar sesión y redirigir a login
      await signOut({ 
        callbackUrl: '/auth/login',
        redirect: true 
      });
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
        <ToastProvider placement={"top-right"} toastOffset={60} />
        {noLayoutPages.includes(router.pathname) ? (
          <Component {...pageProps} />
        ) : (
          <Layout>
            <Component {...pageProps} />
          </Layout>
        )}
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
