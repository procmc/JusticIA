import { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import httpService from '@/services/httpService';
import {
  generateInitialsAvatar,
  mapAvatarTypeToPath,
  buildAvatarUrl,
  validateAvatarFile,
  emitAvatarUpdateEvent,
  isCustomAvatar
} from '@/services/avatarService';
import { AVATAR_PATHS, AVATAR_TYPES } from '@/constants/avatarConstants';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Caché global para verificaciones de avatares (evita múltiples HEAD requests)
const avatarExistsCache = new Map();

/**
 * Hook para gestionar avatares de usuario desde el backend
 * Maneja tanto imágenes personalizadas como avatares predefinidos
 */
export const useUserAvatar = (userId) => {
  const { data: session, update } = useSession();
  const [avatar, setAvatar] = useState(AVATAR_PATHS.DEFAULT_HOMBRE);
  const [avatarTipo, setAvatarTipo] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  /**
   * Cargar avatar desde la sesión
   */
  useEffect(() => {
    if (!userId) {
      setIsLoading(false);
      return;
    }

    const cargarAvatar = async () => {
      try {
        if (session?.user) {
          // Avatar personalizado
          if (session.user.avatarRuta) {
            const avatarUrl = buildAvatarUrl(session.user.avatarRuta, API_URL);
            
            // Verificar caché primero
            const cachedResult = avatarExistsCache.get(avatarUrl);
            
            if (cachedResult !== undefined) {
              // Usar resultado del caché
              if (cachedResult) {
                setAvatar(avatarUrl);
                setAvatarTipo(AVATAR_TYPES.CUSTOM);
              } else {
                setAvatar(generateInitialsAvatar(session.user.name));
                setAvatarTipo(AVATAR_TYPES.INITIALS);
              }
            } else {
              // Verificar si la imagen existe antes de asignarla (solo si no está en caché)
              try {
                const response = await fetch(avatarUrl, { method: 'HEAD' });
                const exists = response.ok;
                
                // Guardar en caché (con expiración de 5 minutos)
                avatarExistsCache.set(avatarUrl, exists);
                setTimeout(() => avatarExistsCache.delete(avatarUrl), 5 * 60 * 1000);
                
                if (exists) {
                  setAvatar(avatarUrl);
                  setAvatarTipo(AVATAR_TYPES.CUSTOM);
                } else {
                  // Si no existe, usar iniciales como fallback
                  console.warn('Avatar no encontrado, usando iniciales');
                  setAvatar(generateInitialsAvatar(session.user.name));
                  setAvatarTipo(AVATAR_TYPES.INITIALS);
                }
              } catch (fetchError) {
                // Si hay error de red, usar iniciales
                console.warn('Error verificando avatar, usando iniciales', fetchError);
                avatarExistsCache.set(avatarUrl, false);
                setAvatar(generateInitialsAvatar(session.user.name));
                setAvatarTipo(AVATAR_TYPES.INITIALS);
              }
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
        }
      } catch (error) {
        console.error('Error cargando avatar:', error);
        // Fallback final: usar iniciales
        if (session?.user?.name) {
          setAvatar(generateInitialsAvatar(session.user.name));
          setAvatarTipo(AVATAR_TYPES.INITIALS);
        }
      } finally {
        setIsLoading(false);
      }
    };

    cargarAvatar();

    // Escuchar eventos de actualización de avatar
    const handleAvatarUpdate = (event) => {
      setAvatar(event.detail.avatar);
      setAvatarTipo(event.detail.tipo);
    };

    window.addEventListener('avatarUpdated', handleAvatarUpdate);

    return () => {
      window.removeEventListener('avatarUpdated', handleAvatarUpdate);
    };
  }, [userId, session]);

  /**
   * Subir nueva imagen de avatar
   * @param {File} file - Archivo de imagen
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  const subirAvatar = useCallback(async (file) => {
    if (!userId) {
      return { success: false, error: 'No hay usuario' };
    }

    // Validar archivo
    const validation = validateAvatarFile(file);
    if (!validation.valid) {
      return { success: false, error: validation.error };
    }

    try {
      const formData = new FormData();
      formData.append('file', file);

      await httpService.post(`/usuarios/${userId}/avatar/upload`, formData);

      // Actualizar estado local
      const fileExtension = file.name.split('.').pop();
      const avatarRuta = `uploads/profiles/${userId}.${fileExtension}`;
      const timestamp = Date.now();
      
      // Limpiar caché completa para forzar recarga
      avatarExistsCache.clear();
      
      // Construir URL con timestamp para evitar caché del navegador al subir nueva imagen
      const newAvatarUrl = `${API_URL}/${avatarRuta}?v=${timestamp}`;
      
      setAvatar(newAvatarUrl);
      setAvatarTipo(AVATAR_TYPES.CUSTOM);
      
      // Actualizar sesión de NextAuth con ruta que incluye versión
      await update({
        ...session,
        user: {
          ...session.user,
          avatarRuta: `${avatarRuta}?v=${timestamp}`,
          avatarTipo: AVATAR_TYPES.CUSTOM
        }
      });
      
      // Emitir evento
      emitAvatarUpdateEvent(newAvatarUrl, AVATAR_TYPES.CUSTOM);
      
      return { success: true };
    } catch (error) {
      console.error('Error subiendo avatar:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Error al subir avatar' 
      };
    }
  }, [userId, session, update]);

  /**
   * Actualizar tipo de avatar (sin subir imagen)
   * @param {string} tipo - Tipo de avatar: 'hombre', 'mujer', 'initials'
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  const actualizarTipoAvatar = useCallback(async (tipo) => {
    if (!userId) {
      return { success: false, error: 'No hay usuario' };
    }

    try {
      await httpService.put(`/usuarios/${userId}/avatar/tipo`, { avatar_tipo: tipo });

      setAvatarTipo(tipo);
      
      const nuevoAvatar = mapAvatarTypeToPath(tipo, session?.user?.name);
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
      
      // Emitir evento
      emitAvatarUpdateEvent(nuevoAvatar, tipo);
      
      return { success: true };
    } catch (error) {
      console.error('Error actualizando tipo de avatar:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Error al actualizar avatar' 
      };
    }
  }, [userId, session, update]);

  /**
   * Eliminar avatar personalizado
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  const eliminarAvatar = useCallback(async () => {
    if (!userId) {
      return { success: false, error: 'No hay usuario' };
    }

    try {
      await httpService.delete(`/usuarios/${userId}/avatar`);

      const defaultAvatar = AVATAR_PATHS.DEFAULT_HOMBRE;
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
      
      // Emitir evento
      emitAvatarUpdateEvent(defaultAvatar, null);
      
      return { success: true };
    } catch (error) {
      console.error('Error eliminando avatar:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Error al eliminar avatar' 
      };
    }
  }, [userId, session, update]);

  /**
   * Verificar si el usuario tiene un avatar personalizado
   */
  const hasCustomAvatar = useCallback(() => {
    return isCustomAvatar(avatar);
  }, [avatar]);

  return {
    avatar,
    avatarTipo,
    isLoading,
    subirAvatar,
    actualizarTipoAvatar,
    eliminarAvatar,
    hasCustomAvatar
  };
};

/**
 * Función auxiliar para limpiar la caché de avatares
 * Útil después de cambios masivos o para debugging
 */
export const clearAvatarCache = () => {
  avatarExistsCache.clear();
};

export default useUserAvatar;
