import {
    Drawer,
    DrawerContent,
    DrawerHeader,
    DrawerBody,
    DrawerFooter,
    Button,
} from "@heroui/react";

const DrawerGeneral = ({
    children,
    titulo,
    isOpen,
    onOpenChange,
    size = "md",
    mostrarFooter = true,
    botonCerrar = { mostrar: true, texto: "Cerrar" },
    botonAccion = null, // { texto: "Guardar", onPress: fn, loading: false, color: "primary" }
    disableClose = false,
    hideCloseButton = false,
}) => {
    const handleCerrar = () => {
        if (botonCerrar.onPress) {
            botonCerrar.onPress();
        } else {
            onOpenChange(false);
        }
    };

    return (
        <Drawer 
            isOpen={isOpen} 
            onOpenChange={disableClose ? undefined : onOpenChange} 
            size={size}
            hideCloseButton={hideCloseButton}
            isDismissable={!disableClose}
            isKeyboardDismissDisabled={disableClose}
            classNames={{
                base: "border-none",
                backdrop: "bg-gradient-to-t from-zinc-900/50 to-zinc-900/10",
            }}
        >
            <DrawerContent>
                {(onClose) => (
                    <>
                        <DrawerHeader className="flex flex-col gap-1 text-azulOscuro border-b border-gray-200">
                            <h2 className="text-md font-semibold">{titulo}</h2>
                        </DrawerHeader>
                        
                        <DrawerBody className="custom-scrollbar p-6">
                            {children}
                        </DrawerBody>
                        
                        {mostrarFooter && (botonCerrar.mostrar || botonAccion) && (
                            <DrawerFooter className="border-t border-gray-200">
                                {botonCerrar.mostrar && (
                                    <Button
                                        color="danger"
                                        variant="flat"
                                        isDisabled={botonAccion?.loading}
                                        onPress={handleCerrar}
                                    >
                                        {botonCerrar.texto}
                                    </Button>
                                )}
                                
                                {botonAccion && (
                                    <Button
                                        color={botonAccion.color || "primary"}
                                        variant={botonAccion.variant || "solid"}
                                        isLoading={botonAccion.loading}
                                        isDisabled={botonAccion.loading || botonAccion.disabled}
                                        onPress={botonAccion.onPress}
                                    >
                                        {botonAccion.texto}
                                    </Button>
                                )}
                            </DrawerFooter>
                        )}
                    </>
                )}
            </DrawerContent>
        </Drawer>
    );
};

export default DrawerGeneral;

