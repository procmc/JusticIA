/**
 * Hook simple para mantener sesión viva y accesible
 * Sin lógica de permisos, solo normaliza el acceso a la sesión
 */
import { useSession } from 'next-auth/react';
import { useMemo } from 'react';

export const useAuthSession = () => {
  const { data, status } = useSession();
  
  return useMemo(() => {
    const user = data?.user || {};
    
    return {
      // Estados básicos
      status,
      isLoading: status === 'loading',
      isAuthenticated: status === 'authenticated',
      
      // Usuario siempre disponible (evita chequeos null)
      user: {
        id: user.id || null,
        name: user.name || '',
        email: user.email || '',
        role: user.role || 'user',
        image: user.image || null
      },
      
      // Token de acceso para API calls
      accessToken: data?.accessToken || null,
      
      // Sesión raw por si la necesitas
      session: data
    };
  }, [data, status]);
};
