import { Dropdown, DropdownItem, DropdownMenu, DropdownTrigger } from "@heroui/react";
import { useRouter } from "next/router";
import { useCallback, useState, useRef } from "react";
import { useSession, signOut } from "next-auth/react";
import Image from "next/image";
import DrawerGeneral from "../ui/DrawerGeneral";
import CambiarContraseña from "@/components/auth/cambioContraseña/CambiarContraseña";
import { clearAllChatContext } from "../../utils/chatContextUtils";
import authService from "@/services/authService";

export function UserButton() {
    const { data: session, status } = useSession();
    const router = useRouter();
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const cambiarContraseñaRef = useRef();

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
                            <button className="rounded-full p-0.5 cursor-pointer focus:outline-none focus-visible:ring-0">
                                <Image
                                    src="/usuario.png"
                                    alt="User Avatar"
                                    className="rounded-full"
                                    width={40}
                                    height={40}
                                />
                            </button>
                        </DropdownTrigger>

                        <DropdownMenu
                            aria-label="Profile Actions"
                            variant="flat"
                            className="w-64"
                        >
                            <DropdownItem key="profile" className="px-4 py-1 cursor-default pointer-events-none" textValue="profile">
                                <div className="flex items-center gap-3">
                                    <div className={`w-10 h-10 rounded-full overflow-hidden flex-shrink-0`}> 
                                        <Image
                                            src="/usuario.png"
                                            alt="User Avatar"
                                            className="object-cover"
                                            width={40}
                                            height={40}
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