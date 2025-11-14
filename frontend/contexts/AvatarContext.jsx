/**
 * @fileoverview Context de React para gestión global del avatar de usuario.
 * 
 * Este módulo implementa el state management centralizado para el avatar del usuario
 * en JusticIA. Gestiona tres tipos de avatares: personalizados (uploads), predefinidos
 * (iconos del sistema) e iniciales (generadas automáticamente).
 * 
 * Responsabilidades:
 * - Cargar avatar desde sesión de NextAuth
 * - Subir nuevas imágenes de avatar
 * - Cambiar tipo de avatar (predefinido/iniciales)
 * - Eliminar avatar personalizado
 * - Sincronizar con backend y sesión
 * - Validar archivos antes de subir
 * 
 * Tipos de avatar soportados:
 * - CUSTOM: Imagen subida por el usuario (uploads/profiles/{userId}.{ext})
 * - PREDEFINED: Iconos predefinidos del sistema (hombre, mujer, neutro, etc.)
 * - INITIALS: Avatar generado con iniciales del nombre
 * 
 * Arquitectura:
 * - AvatarProvider: Componente provider que envuelve la app
 * - useAvatar: Hook para consumir el contexto
 * - AvatarContext: Context de React (no exportado directamente)
 * 
 * State management:
 * - avatar: URL o data URI del avatar actual
 * - avatarTipo: Tipo de avatar (AVATAR_TYPES constant)
 * - isLoading: Estado de carga inicial
 * 
 * Integración:
 * - Sincroniza con NextAuth session
 * - Usa avatarService para lógica de avatares
 * - Usa httpService para peticiones al backend
 * - Se inyecta en _app.js para disponibilidad global
 * 
 * @module AvatarContext
 * @requires react
 * @requires next-auth/react
 * @requires @/services/httpService
 * @requires @/services/avatarService
 * @requires @/constants/avatarConstants
 * 
 * @example
 * // En _app.js
 * import { AvatarProvider } from '@/contexts/AvatarContext';
 * 
 * function MyApp({ Component, pageProps }) {
 *   return (
 *     <SessionProvider session={pageProps.session}>
 *       <AvatarProvider>
 *         <Component {...pageProps} />
 *       </AvatarProvider>
 *     </SessionProvider>
 *   );
 * }
 * 
 * @example
 * // En cualquier componente
 * import { useAvatar } from '@/contexts/AvatarContext';
 * 
 * function UserProfile() {
 *   const { avatar, subirAvatar, isLoading } = useAvatar();
 *   
 *   const handleFileUpload = async (file) => {
 *     const result = await subirAvatar(file);
 *     if (result.success) {
 *       console.log('Avatar actualizado');
 *     }
 *   };
 *   
 *   return <Avatar src={avatar} />;
 * }
 * 
 * @see {@link ../services/avatarService.js} Servicio de lógica de avatares
 * @see {@link ../constants/avatarConstants.js} Constantes de tipos y paths
 * @see {@link ../components/UserButton.jsx} Componente que usa el avatar
 * 
 * @author JusticIA Team
 * @version 1.0.0
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import httpService from '@/services/httpService';
import {
  generateInitialsAvatar,
  mapAvatarTypeToPath,
  buildAvatarUrl,
  validateAvatarFile
} from '@/services/avatarService';
import { AVATAR_PATHS, AVATAR_TYPES } from '@/constants/avatarConstants';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Context de React para el avatar del usuario.
 * No se exporta directamente, usar useAvatar() hook.
 * @private
 */
const AvatarContext = createContext(undefined);

/**
 * Provider de Avatar - Gestiona el estado global del avatar del usuario.
 * 
 * Este es el ÚNICO lugar donde se maneja el estado del avatar. Todos los componentes
 * que necesiten acceder o modificar el avatar deben usar el hook useAvatar().
 * 
 * Características:
 * - Carga inicial desde sesión de NextAuth
 * - Verificación de existencia de avatar personalizado (HEAD request)
 * - Fallback automático a iniciales si el avatar no existe
 * - Sincronización instantánea con UI al actualizar
 * - Actualización de sesión de NextAuth
 * 
 * @component
 * @param {Object} props
 * @param {React.ReactNode} props.children - Componentes hijos envueltos por el provider.
 * @returns {JSX.Element} Provider que envuelve children con contexto de avatar.
 * 
 * @example
 * // Envolver la aplicación
 * <SessionProvider>
 *   <AvatarProvider>
 *     <App />
 *   </AvatarProvider>
 * </SessionProvider>
 */
export const AvatarProvider = ({ children }) => {
  const { data: session, update } = useSession();
  const [avatar, setAvatar] = useState(AVATAR_PATHS.DEFAULT_HOMBRE);
  const [avatarTipo, setAvatarTipo] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  /**
   * Cargar avatar inicial desde la sesión
   */
  useEffect(() => {
    const cargarAvatar = async () => {
      if (!session?.user) {
        setIsLoading(false);
        return;
      }

      try {
        // Avatar personalizado
        if (session.user.avatarRuta) {
          const avatarUrl = buildAvatarUrl(session.user.avatarRuta, API_URL);
          
          // Verificar si la imagen existe antes de usarla
          try {
            const response = await fetch(avatarUrl, { method: 'HEAD' });
            if (response.ok) {
              setAvatar(avatarUrl);
              setAvatarTipo(AVATAR_TYPES.CUSTOM);
            } else {
              // Si la imagen no existe (404), usar iniciales
              console.warn('Avatar personalizado no encontrado, usando iniciales');
              setAvatar(generateInitialsAvatar(session.user.name));
              setAvatarTipo(AVATAR_TYPES.INITIALS);
            }
          } catch (fetchError) {
            // Si hay error de red, usar iniciales
            console.warn('Error verificando avatar, usando iniciales', fetchError);
            setAvatar(generateInitialsAvatar(session.user.name));
            setAvatarTipo(AVATAR_TYPES.INITIALS);
          }
        } 
        // Avatar predefinido o iniciales
        else if (session.user.avatarTipo) {
          setAvatarTipo(session.user.avatarTipo);
          setAvatar(mapAvatarTypeToPath(session.user.avatarTipo, session.user.name));
        }
        // Sin avatar configurado, usar iniciales por defecto
        else {
          setAvatar(generateInitialsAvatar(session.user.name));
          setAvatarTipo(AVATAR_TYPES.INITIALS);
        }
      } catch (error) {
        console.error('Error cargando avatar:', error);
        if (session?.user?.name) {
          setAvatar(generateInitialsAvatar(session.user.name));
          setAvatarTipo(AVATAR_TYPES.INITIALS);
        }
      } finally {
        setIsLoading(false);
      }
    };

    cargarAvatar();
  }, [session?.user?.id, session?.user?.avatarRuta, session?.user?.avatarTipo, session?.user?.name]);

  /**
   * Subir nueva imagen de avatar
   */
  const subirAvatar = useCallback(async (file) => {
    const userId = session?.user?.id;
    if (!userId) {
      return { success: false, error: 'No hay usuario' };
    }

    const validation = validateAvatarFile(file);
    if (!validation.valid) {
      return { success: false, error: validation.error };
    }

    try {
      const formData = new FormData();
      formData.append('file', file);

      await httpService.post(`/usuarios/${userId}/avatar/upload`, formData);

      const fileExtension = file.name.split('.').pop();
      const avatarRuta = `uploads/profiles/${userId}.${fileExtension}`;
      const timestamp = Date.now();
      const newAvatarUrl = `${API_URL}/${avatarRuta}?v=${timestamp}`;
      
      // Actualizar estado local INMEDIATAMENTE
      setAvatar(newAvatarUrl);
      setAvatarTipo(AVATAR_TYPES.CUSTOM);
      
      // Actualizar sesión de NextAuth
      await update({
        ...session,
        user: {
          ...session.user,
          avatarRuta: `${avatarRuta}?v=${timestamp}`,
          avatarTipo: AVATAR_TYPES.CUSTOM
        }
      });
      
      return { success: true };
    } catch (error) {
      console.error('Error subiendo avatar:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Error al subir avatar' 
      };
    }
  }, [session, update]);

  /**
   * Actualizar tipo de avatar predefinido
   */
  const actualizarTipoAvatar = useCallback(async (tipo) => {
    const userId = session?.user?.id;
    if (!userId) {
      return { success: false, error: 'No hay usuario' };
    }

    try {
      await httpService.put(`/usuarios/${userId}/avatar/tipo`, { avatar_tipo: tipo });

      const nuevoAvatar = mapAvatarTypeToPath(tipo, session?.user?.name);
      
      // Actualizar estado local INMEDIATAMENTE
      setAvatarTipo(tipo);
      setAvatar(nuevoAvatar);
      
      // Actualizar sesión de NextAuth
      await update({
        ...session,
        user: {
          ...session.user,
          avatarRuta: null,
          avatarTipo: tipo
        }
      });
      
      return { success: true };
    } catch (error) {
      console.error('Error actualizando tipo de avatar:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Error al actualizar avatar' 
      };
    }
  }, [session, update]);

  /**
   * Eliminar avatar personalizado
   */
  const eliminarAvatar = useCallback(async () => {
    const userId = session?.user?.id;
    if (!userId) {
      return { success: false, error: 'No hay usuario' };
    }

    try {
      await httpService.delete(`/usuarios/${userId}/avatar`);

      const defaultAvatar = AVATAR_PATHS.DEFAULT_HOMBRE;
      
      // Actualizar estado local INMEDIATAMENTE
      setAvatar(defaultAvatar);
      setAvatarTipo(null);
      
      // Actualizar sesión de NextAuth
      await update({
        ...session,
        user: {
          ...session.user,
          avatarRuta: null,
          avatarTipo: null
        }
      });
      
      return { success: true };
    } catch (error) {
      console.error('Error eliminando avatar:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Error al eliminar avatar' 
      };
    }
  }, [session, update]);

  const value = {
    avatar,
    avatarTipo,
    isLoading,
    subirAvatar,
    actualizarTipoAvatar,
    eliminarAvatar
  };

  return <AvatarContext.Provider value={value}>{children}</AvatarContext.Provider>;
};

/**
 * Hook para usar el contexto de avatar.
 * 
 * Proporciona acceso al estado y funciones del avatar del usuario.
 * Debe usarse dentro de un AvatarProvider.
 * 
 * @hook
 * @returns {Object} Objeto con estado y funciones del avatar:
 * @returns {string} returns.avatar - URL o data URI del avatar actual.
 * @returns {string|null} returns.avatarTipo - Tipo de avatar (AVATAR_TYPES).
 * @returns {boolean} returns.isLoading - true si está cargando el avatar inicial.
 * @returns {Function} returns.subirAvatar - Función async para subir nueva imagen.
 * @returns {Function} returns.actualizarTipoAvatar - Función async para cambiar tipo.
 * @returns {Function} returns.eliminarAvatar - Función async para eliminar avatar.
 * 
 * @throws {Error} Si se usa fuera de un AvatarProvider.
 * 
 * @example
 * function ProfilePicture() {
 *   const { avatar, isLoading, subirAvatar } = useAvatar();
 *   
 *   if (isLoading) return <Skeleton />;
 *   
 *   const handleUpload = async (e) => {
 *     const file = e.target.files[0];
 *     const result = await subirAvatar(file);
 *     if (result.success) {
 *       toast.success('Avatar actualizado');
 *     } else {
 *       toast.error(result.error);
 *     }
 *   };
 *   
 *   return (
 *     <div>
 *       <Avatar src={avatar} />
 *       <input type="file" onChange={handleUpload} />
 *     </div>
 *   );
 * }
 * 
 * @example
 * // Cambiar a avatar predefinido
 * function AvatarSelector() {
 *   const { actualizarTipoAvatar } = useAvatar();
 *   
 *   const handleSelect = async (tipo) => {
 *     const result = await actualizarTipoAvatar(tipo);
 *     if (result.success) {
 *       console.log('Avatar cambiado a tipo:', tipo);
 *     }
 *   };
 *   
 *   return (
 *     <div>
 *       <button onClick={() => handleSelect('HOMBRE')}>Hombre</button>
 *       <button onClick={() => handleSelect('MUJER')}>Mujer</button>
 *     </div>
 *   );
 * }
 */
export const useAvatar = () => {
  const context = useContext(AvatarContext);
  if (context === undefined) {
    throw new Error('useAvatar debe usarse dentro de un AvatarProvider');
  }
  return context;
};

export default AvatarContext;
