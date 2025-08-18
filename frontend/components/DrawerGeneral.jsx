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
    size,
    mostrarBotones = true,
    textoBotonPrimario = "Crear", // Texto del botón primario
    textoBotonSecundario = "Cerrar", // Texto del botón secundario
    onBotonPrimario = () => {}, // Función del botón primario
    onBotonSecundario = () => {}, // Función del botón secundario
    loadingBotonPrimario = false,
    loadingBotonSecundario = false,
    disableClose = false,
}) => {
    return (
        <>
            <Drawer isOpen={isOpen} onOpenChange={disableClose ? undefined : onOpenChange} size={size}>
                <DrawerContent>
                    {(onClose) => (
                        <>
                            <DrawerHeader className="flex flex-col gap-1 text-azulOscuro">
                                {titulo}
                            </DrawerHeader>
                            <DrawerBody className="custom-scrollbar">{children}</DrawerBody>
                            {mostrarBotones && ( // Mostrar los botones solo si mostrarBotones es true
                                <DrawerFooter>
                                    <Button
                                        color="danger"
                                        variant="flat"
                                        isDisabled={loadingBotonPrimario || loadingBotonSecundario}
                                        onPress={onBotonSecundario}
                                    >
                                        {textoBotonSecundario}
                                    </Button>
                                    <Button
                                        color="primary"
                                        isLoading={loadingBotonPrimario || loadingBotonSecundario}
                                        isDisabled={loadingBotonPrimario || loadingBotonSecundario}
                                        onPress={onBotonPrimario}
                                    >
                                        {textoBotonPrimario}
                                    </Button>
                                </DrawerFooter>
                            )}
                        </>
                    )}
                </DrawerContent>
            </Drawer>
        </>
    );
};

export default DrawerGeneral;

