/**
 * Componente de Botón de Usuario con Dropdown y Gestión de Perfil.
 * 
 * @module components/Layout/UserButton
 * @component
 * 
 * Botón flotante con avatar del usuario que despliega un menú dropdown con opciones
 * de perfil, cambio de avatar, cambio de contraseña y cierre de sesión.
 * 
 * Características:
 *   - Avatar dinámico: Carga desde AvatarContext (uploads, predefinidos, iniciales)
 *   - Dropdown con perfil: Muestra nombre, email y rol con badge de color
 *   - Cambio de avatar: Modal AvatarSelector para subir imagen o elegir predefinido
 *   - Cambio de contraseña: Drawer modal con formulario CambiarContraseña
 *   - Logout con auditoría: Registra en bitácora antes de cerrar sesión
 *   - Fallback de avatar: Si falla carga, muestra iniciales generadas
 * 
 * Gestión de avatares:
 *   - Usa AvatarContext para centralizar estado
 *   - Soporta 3 tipos: 'upload' (imagen subida), 'icon' (predefinido), 'default' (iniciales)
 *   - Maneja errores de carga con fallback automático
 *   - Avatar se actualiza en tiempo real al cambiar
 * 
 * Roles y badges:
 *   - Administrador: Badge rojo (border-red-500, text-danger)
 *   - Usuario Judicial: Badge verde (border-green-500, text-green-600)
 *   - Por defecto: Badge gris (border-gray-400, text-default-600)
 * 
 * Flujo de cambio de avatar:
 *   1. Usuario click en "Cambiar avatar" → abre AvatarSelector
 *   2. Usuario selecciona/sube avatar → handleSaveAvatar
 *   3. Si es File → subirAvatar() → upload al backend
 *   4. Si es predefinido → actualizarTipoAvatar() → guarda preferencia
 *   5. AvatarContext se actualiza → UI refleja cambio inmediatamente
 * 
 * Flujo de logout:
 *   1. Usuario click en "Cerrar sesión" → handleLogout
 *   2. authService.logout() → registra en bitácora del backend
 *   3. clearAllChatContext() → limpia localStorage de conversaciones
 *   4. signOut() → limpia sesión NextAuth y redirige a /auth/login
 * 
 * @returns {JSX.Element} Botón de usuario con dropdown de perfil y opciones
 * 
 * @example
 * ```jsx
 * import { UserButton } from '@/components/Layout/UserButton';
 * 
 * function Layout() {
 *   return (
 *     <div className="absolute top-0 right-0">
 *       <UserButton />
 *     </div>
 *   );
 * }
 * ```
 * 
 * @example
 * ```jsx
 * // Estructura de sesión esperada
 * session = {
 *   user: {
 *     id: '123456789',           // Cédula del usuario
 *     name: 'Juan Pérez García',  // Nombre completo
 *     email: 'juan@example.com',  // Email
 *     role: 'Administrador',      // Rol para badge
 *     avatar_ruta: '/uploads/...',// Ruta del avatar (opcional)
 *     avatar_tipo: 'upload'       // Tipo de avatar (opcional)
 *   }
 * }
 * ```
 */

import { Dropdown, DropdownItem, DropdownMenu, DropdownTrigger } from "@heroui/react";
import { useRouter } from "next/router";
import { useCallback, useState, useRef, useEffect } from "react";
import { useSession, signOut } from "next-auth/react";
import Image from "next/image";
import DrawerGeneral from "../ui/DrawerGeneral";
import CambiarContraseña from "@/components/auth/cambioContraseña/CambiarContraseña";
import AvatarSelector from "@/components/perfil/AvatarSelector";
import { clearAllChatContext } from "../../utils/chatContextUtils";
import authService from "@/services/authService";
import { useAvatar } from "@/contexts/AvatarContext";
import { generateInitialsAvatar } from "@/services/avatarService";

export function UserButton() {
    const { data: session, status } = useSession();
    const router = useRouter();
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [isAvatarModalOpen, setIsAvatarModalOpen] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [avatarError, setAvatarError] = useState(false);
    const cambiarContraseñaRef = useRef();
    
    // Usar contexto de avatar en lugar del hook
    const { avatar, subirAvatar, actualizarTipoAvatar } = useAvatar();
    
    // Resetear error cuando cambie el avatar
    useEffect(() => {
        setAvatarError(false);
    }, [avatar]);
    
    // Avatar a mostrar (con fallback a iniciales si hay error)
    const displayAvatar = avatarError ? generateInitialsAvatar(session?.user?.name) : avatar;

    const formatearNombre = (nombreCompleto) => {
        if (!nombreCompleto) return "Usuario";
        
        const capitalizarPalabra = (palabra) => {
            return palabra.charAt(0).toUpperCase() + palabra.slice(1).toLowerCase();
        };
        
        const partes = nombreCompleto.trim().split(' ');
        if (partes.length >= 3) {
            // Mostrar primer nombre (posición 0) y primer apellido (posición 2)
            return `${capitalizarPalabra(partes[0])} ${capitalizarPalabra(partes[2])}`;
        } else if (partes.length === 2) {
            // Si solo hay 2 palabras, mostrar ambas
            return `${capitalizarPalabra(partes[0])} ${capitalizarPalabra(partes[1])}`;
        }
        // Si solo hay una palabra, mostrarla
        return capitalizarPalabra(partes[0]);
    };

    const getRoleStyles = (role) => {
        switch (role) {
            case 'Administrador':
                return {
                    borderColor: 'border-red-500',
                    textColor: 'text-danger',
                    bgColor: 'bg-danger-50',
                    label: 'Administrador'
                };
            case 'Usuario Judicial':
                return {
                    borderColor: 'border-green-500',
                    textColor: 'text-green-600',
                    bgColor: 'bg-green-50',
                    label: 'Usuario Judicial'
                };
            default:
                return {
                    borderColor: 'border-gray-400',
                    textColor: 'text-default-600',
                    bgColor: 'bg-default-50',
                    label: role || 'Usuario'
                };
        }
    };

    const handleLogout = useCallback(async () => {
        try {
            // Registrar el logout en la bitácora del backend usando el servicio
            await authService.logout(session?.user?.id, session?.user?.email);
            
            // Limpiar contexto de chat usando utilidad centralizada
            clearAllChatContext();
            
            await signOut({ 
                callbackUrl: '/auth/login',
                redirect: true 
            });
        } catch (error) {
            console.error('Error durante el logout:', error);
            // Fallback: redirigir manualmente si hay error
            router.push('/auth/login');
        }
    }, [router, session]);

    const handleOpenChangePassword = () => {
        setIsDrawerOpen(true);
    };

    const handleCloseDrawer = () => {
        setIsDrawerOpen(false);
        setIsLoading(false);
    };

    const handlePasswordChangeSuccess = () => {
        setIsDrawerOpen(false);
        setIsLoading(false);
    };

    const handleOpenAvatarSelector = () => {
        setIsAvatarModalOpen(true);
    };

    const handleSaveAvatar = async (newAvatar) => {
        try {
            // Si newAvatar es un archivo (File), subirlo
            if (newAvatar instanceof File) {
                const result = await subirAvatar(newAvatar);
                return result.success || false;
            }
            
            // Si es una ruta de avatar predefinido, actualizar tipo
            if (typeof newAvatar === 'string') {
                // Si es data URL (iniciales), guardar como tipo 'initials'
                if (newAvatar.startsWith('data:image/svg+xml')) {
                    const result = await actualizarTipoAvatar('initials');
                    return result.success || false;
                }
                
                // Mapear rutas a tipos
                const avatarMap = {
                    '/avatar-male-default.png': 'hombre',
                    '/avatar-female-default.png': 'mujer'
                };
                
                const tipo = avatarMap[newAvatar];
                if (tipo) {
                    const result = await actualizarTipoAvatar(tipo);
                    return result.success || false;
                }
            }
            
            return false;
        } catch (error) {
            console.error('Error en handleSaveAvatar:', error);
            return false;
        }
    };

    // Extraer nombre y apellido del usuario para las iniciales
    const getUserName = () => {
        const fullName = session?.user?.name || '';
        const partes = fullName.trim().split(' ');
        return partes[0] || 'Usuario';
    };

    const getUserLastName = () => {
        const fullName = session?.user?.name || '';
        const partes = fullName.trim().split(' ');
        // Si hay 3 o más palabras, el apellido está en posición 2
        // Si hay 2 palabras, el apellido está en posición 1
        if (partes.length >= 3) return partes[2] || '';
        if (partes.length === 2) return partes[1] || '';
        return 'Apellido';
    };

    // Mostrar loading o datos por defecto mientras carga la sesión
    if (status === "loading") {
        return (
            <div className="absolute top-0 right-0 mr-2">
                <div className="flex py-4 px-3 items-center w-full h-full">
                    <div style={{ width: "2.5rem" }}>
                        <div className="w-8 h-8 bg-gray-200 rounded-full animate-pulse"></div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="absolute -top-1.5 right-2.5 mr-2">
            <div className="flex py-4 px-3 items-center w-full h-full">
                <div style={{ width: "2.5rem" }}>
                    <Dropdown placement="bottom-end">
                        <DropdownTrigger>
                            <button className="rounded-full p-0.5 cursor-pointer focus:outline-none focus-visible:ring-0 hover:ring-2 hover:ring-primary/50 transition-all">
                                <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-gray-100">
                                    <Image
                                        key={displayAvatar}
                                        src={displayAvatar}
                                        alt="User Avatar"
                                        className="w-full h-full object-cover"
                                        width={56}
                                        height={56}
                                        unoptimized={displayAvatar.startsWith('data:')}
                                        onError={() => setAvatarError(true)}
                                    />
                                </div>
                            </button>
                        </DropdownTrigger>

                        <DropdownMenu
                            aria-label="Profile Actions"
                            variant="flat"
                            className="w-64"
                        >
                            <DropdownItem key="profile" className="px-4 py-1 cursor-default pointer-events-none" textValue="profile">
                                <div className="flex items-center gap-3">
                                    <div className="w-14 h-14 rounded-full overflow-hidden flex-shrink-0 border-2 border-gray-100"> 
                                        <Image
                                            key={displayAvatar}
                                            src={displayAvatar}
                                            alt="User Avatar"
                                            className="w-full h-full object-cover"
                                            width={56}
                                            height={56}
                                            unoptimized={displayAvatar.startsWith('data:')}
                                            onError={() => setAvatarError(true)}
                                        />
                                    </div>
                                    <div className="flex-1">
                                        <p className="font-semibold text-gray-800 leading-tight">
                                            {formatearNombre(session?.user?.name || "Usuario")}
                                        </p>
                                        <p className="text-xs text-gray-500 truncate">
                                            {session?.user?.email || "usuario@example.com"}
                                        </p>
                                        <div className="mt-2">
                                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${getRoleStyles(session?.user?.role).borderColor} ${getRoleStyles(session?.user?.role).textColor}`}>
                                                {getRoleStyles(session?.user?.role).label}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </DropdownItem>

                            <DropdownItem
                                key="divider2"
                                className="h-0 min-h-0 py-0 my-1 border-t border-gray-200 opacity-100 cursor-default pointer-events-none"
                                textValue="divider"
                            >
                            </DropdownItem>
                            <DropdownItem
                                key="avatar"
                                className="px-4 py-3 hover:bg-gray-50 transition-colors"
                                onPress={handleOpenAvatarSelector}
                            >
                                <span className="text-gray-700">Cambiar avatar</span>
                            </DropdownItem>
                            <DropdownItem
                                key="settings"
                                className="px-4 py-3 hover:bg-gray-50 transition-colors"
                                onPress={handleOpenChangePassword}
                            >
                                <span className="text-gray-700">Cambiar contraseña</span>
                            </DropdownItem>
                            <DropdownItem
                                key="logout"
                                className="px-4 py-3 hover:bg-red-50 transition-colors"
                                onPress={handleLogout}
                            >
                                <span className="font-medium text-red-600">Cerrar sesión</span>
                            </DropdownItem>
                        </DropdownMenu>
                    </Dropdown>
                </div>
            </div>
            
            {/* Modal para seleccionar avatar */}
            <AvatarSelector
                isOpen={isAvatarModalOpen}
                onClose={() => setIsAvatarModalOpen(false)}
                currentAvatar={avatar}
                onSave={handleSaveAvatar}
                userName={getUserName()}
                userLastName={getUserLastName()}
            />

            {/* Drawer para cambiar contraseña */}
            <DrawerGeneral
                isOpen={isDrawerOpen}
                onOpenChange={(open) => {
                    if (!isLoading && open === false) setIsDrawerOpen(open);
                }}
                titulo="Cambiar Contraseña"
                size="md"
                mostrarFooter={true}
                botonCerrar={{ 
                    mostrar: true, 
                    texto: "Cancelar",
                    onPress: () => {
                        if (!isLoading) {
                            handleCloseDrawer();
                        }
                    }
                }}
                botonAccion={{
                    texto: "Cambiar Contraseña",
                    color: "primary",
                    loading: isLoading,
                    onPress: async () => {
                        if (isLoading) return;
                        setIsLoading(true);
                        try {
                            const valid = await cambiarContraseñaRef.current?.validateAndSubmit?.();
                            if (!valid) {
                                setIsLoading(false);
                            }
                        } catch (error) {
                            console.error("Error inesperado al cambiar contraseña:", error);
                            setIsLoading(false);
                        }
                    }
                }}
                disableClose={isLoading}
            >
                <CambiarContraseña
                    ref={cambiarContraseñaRef}
                    cedulaUsuario={session?.user?.id || 1}
                    onSuccess={handlePasswordChangeSuccess}
                />
            </DrawerGeneral>
        </div>
    );
}