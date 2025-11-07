import { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import httpService from '@/services/httpService';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Hook para gestionar avatares de usuario desde el backend
 * Maneja tanto imágenes personalizadas como avatares predefinidos
 */
export const useUserAvatar = (userId) => {
  const { data: session } = useSession();
  const [avatar, setAvatar] = useState('/usser hombre.png'); // Avatar por defecto
  const [avatarTipo, setAvatarTipo] = useState(null); // Tipo de avatar
  const [isLoading, setIsLoading] = useState(true);

  /**
   * Generar avatar con iniciales
   */
  const generateInitialsAvatar = useCallback(() => {
    if (!session?.user?.name) return '/usser hombre.png';
    
    const fullName = session.user.name.trim();
    const partes = fullName.split(' ');
    const firstName = partes[0] || '';
    const lastName = partes.length >= 3 ? partes[2] : (partes[1] || '');
    const initials = `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase() || 'U';
    
    const svg = `data:image/svg+xml,${encodeURIComponent(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
        <circle cx="100" cy="100" r="100" fill="#1B5E9F"/>
        <text x="100" y="100" font-family="Arial, sans-serif" font-size="80" font-weight="bold" 
              fill="white" text-anchor="middle" dominant-baseline="central">${initials}</text>
      </svg>
    `)}`;
    
    return svg;
  }, [session]);

  /**
   * Cargar avatar desde la sesión o el backend
   */
  useEffect(() => {
    if (!userId) {
      setIsLoading(false);
      return;
    }

    const cargarAvatar = async () => {
      try {
        // Obtener desde la sesión (siempre disponible después del login)
        if (session?.user) {
          if (session.user.avatarRuta) {
            setAvatar(`${API_URL}/${session.user.avatarRuta}`);
            setAvatarTipo('custom');
          } else if (session.user.avatarTipo) {
            setAvatarTipo(session.user.avatarTipo);
            
            // Mapear tipo a ruta de avatar
            if (session.user.avatarTipo === 'initials') {
              setAvatar(generateInitialsAvatar());
            } else {
              const tipoMap = {
                'hombre': '/usser hombre.png',
                'mujer': '/usser mujer.png'
              };
              setAvatar(tipoMap[session.user.avatarTipo] || '/usser hombre.png');
            }
          }
          // Si no hay avatar en sesión, usar default
        }
      } catch (error) {
        console.error('Error cargando avatar:', error);
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
  }, [userId, session, generateInitialsAvatar]);

  /**
   * Subir nueva imagen de avatar
   * @param {File} file - Archivo de imagen
   */
  const subirAvatar = useCallback(async (file) => {
    if (!userId) return false;

    try {
      const formData = new FormData();
      formData.append('file', file);

      await httpService.post(`/usuarios/${userId}/avatar/upload`, formData);

      // Actualizar estado local inmediatamente
      const fileExtension = file.name.split('.').pop();
      const newAvatarUrl = `${API_URL}/uploads/profiles/${userId}.${fileExtension}?t=${Date.now()}`;
      setAvatar(newAvatarUrl);
      setAvatarTipo('custom');
      
      // Emitir evento para actualizar otros componentes
      window.dispatchEvent(new CustomEvent('avatarUpdated', { detail: { avatar: newAvatarUrl, tipo: 'custom' } }));
      
      return true;
    } catch (error) {
      console.error('Error subiendo avatar:', error);
      return false;
    }
  }, [userId]);

  /**
   * Actualizar tipo de avatar (sin subir imagen)
   * @param {string} avatarTipo - Tipo de avatar: 'hombre', 'mujer', 'initials'
   */
  const actualizarTipoAvatar = useCallback(async (tipo) => {
    if (!userId) return false;

    try {
      await httpService.put(`/usuarios/${userId}/avatar/tipo`, { avatar_tipo: tipo });

      setAvatarTipo(tipo);
      
      // Mapear tipo a ruta o generar SVG
      let nuevoAvatar;
      if (tipo === 'initials') {
        nuevoAvatar = generateInitialsAvatar();
      } else {
        const tipoMap = {
          'hombre': '/usser hombre.png',
          'mujer': '/usser mujer.png'
        };
        nuevoAvatar = tipoMap[tipo] || '/usser hombre.png';
      }
      
      setAvatar(nuevoAvatar);
      
      // Emitir evento para actualizar otros componentes
      window.dispatchEvent(new CustomEvent('avatarUpdated', { detail: { avatar: nuevoAvatar, tipo } }));
      
      return true;
    } catch (error) {
      console.error('Error actualizando tipo de avatar:', error);
      return false;
    }
  }, [userId, generateInitialsAvatar]);

  /**
   * Eliminar avatar personalizado
   */
  const eliminarAvatar = useCallback(async () => {
    if (!userId) return;

    try {
      await httpService.delete(`/usuarios/${userId}/avatar`);

      setAvatar('/usser hombre.png');
    } catch (error) {
      console.error('Error eliminando avatar:', error);
    }
  }, [userId]);

  /**
   * Verificar si el usuario tiene un avatar personalizado
   */
  const hasCustomAvatar = useCallback(() => {
    return avatar !== '/usser hombre.png' && !avatar.startsWith('/usser');
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

export default useUserAvatar;
