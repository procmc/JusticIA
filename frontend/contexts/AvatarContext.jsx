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

// Context para el avatar
const AvatarContext = createContext(undefined);

/**
 * Provider de Avatar - Gestiona el estado global del avatar del usuario
 * Este es el ÚNICO lugar donde se maneja el estado del avatar
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
 * Hook para usar el contexto de avatar
 * Debe usarse dentro de un AvatarProvider
 */
export const useAvatar = () => {
  const context = useContext(AvatarContext);
  if (context === undefined) {
    throw new Error('useAvatar debe usarse dentro de un AvatarProvider');
  }
  return context;
};

export default AvatarContext;
