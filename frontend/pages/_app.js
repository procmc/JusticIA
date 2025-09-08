import "@/styles/globals.css";
import "@/styles/login-animations.css";
import { HeroUIProvider, ToastProvider } from "@heroui/react";
import Layout from "@/components/Layout/Layout";
import { useRouter } from "next/router";
import { SessionProvider} from "next-auth/react";
import { ThemeProvider } from "@/contexts/ThemeContext";

// Componente que maneja el contenido de la aplicación
function AppContent({ Component, pageProps }) {
  const router = useRouter();

  // Rutas sin Layout
  const noLayoutPages = ["/auth/login", "/auth/recuperar-contrasenna"];

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
      refetchInterval={10000} // Refrescar cada 10 segundos
      refetchOnWindowFocus={true}
    >
      <AppContent Component={Component} pageProps={pageProps} />
    </SessionProvider>
  );
}

export default MyApp;
