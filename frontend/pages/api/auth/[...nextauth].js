import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import { loginService } from "../../../services/authService";

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
    maxAge: 60 * 60 * 2, 
  },
  jwt: {
    maxAge: 60 * 60 * 2, 
  },
  callbacks: {
    async jwt({ token, user }) {
      // Copia los datos del usuario al token
      if (user) {
        token.id = user.id;
        token.name = user.name;
        token.email = user.email;
        token.role = user.role;
        token.accessToken = user.accessToken; // guardar access token
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