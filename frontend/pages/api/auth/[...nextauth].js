import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import { loginService, refreshTokenWithTokenService } from "../../../services/authService";

export default NextAuth({
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        try {
          const result = await loginService(credentials.email, credentials.password);
          if (result?.error || !result?.user) return null;
          
          // Mapear el usuario al formato NextAuth
          const user = result.user;
          
          const userToReturn = {
            id: String(user.id),
            name: user.name,
            email: user.email,
            role: user.role,
            // Incluir el access_token del backend para que pase a callbacks
            accessToken: result.access_token
          };
          
          return userToReturn;
        } catch (error) {
          console.error("Error en la autenticación:", error);
          return null;
        }
      }
    })
  ],
  secret: process.env.NEXTAUTH_SECRET,
  session: {
    strategy: "jwt",
    maxAge: 60 * 60, // 1 hora - tiempo máximo de inactividad
    updateAge: 5 * 60, // Actualizar token cada 5 minutos si hay actividad
  },
  jwt: {
    maxAge: 60 * 60, // 1 hora
  },
  callbacks: {
    async jwt({ token, user, trigger }) {
      const now = Date.now();
      
      // Copia los datos del usuario al token en el primer login
      if (user) {
        token.id = user.id;
        token.name = user.name;
        token.email = user.email;
        token.role = user.role;
        token.accessToken = user.accessToken;
        token.accessTokenExpires = now + 60 * 60 * 1000; // 1 hora
      }
      
      // Si el token del backend está cerca de expirar (menos de 10 minutos)
      // y el token de NextAuth aún es válido, renovar el backend token
      const timeUntilExpiration = token.accessTokenExpires - now;
      const shouldRefresh = timeUntilExpiration < 10 * 60 * 1000; // menos de 10 minutos
      
      if (shouldRefresh && !user) {
        const result = await refreshTokenWithTokenService(token.accessToken);
        
        if (result?.success && result?.access_token) {
          token.accessToken = result.access_token;
          token.accessTokenExpires = now + 60 * 60 * 1000; // 1 hora
        }
      }
      
      return token;
    },
    async session({ session, token }) {
      // Asegúrate de que session.user exista
      if (!session.user) session.user = {};
      
      // Copia los datos del token a la sesión
      session.user.id = token.id;
      session.user.name = token.name;
      session.user.email = token.email;
      session.user.role = token.role;
      // Exponer accessToken en la sesión para el httpService
      session.accessToken = token.accessToken;
      
      return session;
    }
  },
  pages: {
    signIn: "/auth/login",
  },
  debug: process.env.NODE_ENV === "development",
});