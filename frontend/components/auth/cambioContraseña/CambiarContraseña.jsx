import { useState, useEffect, forwardRef, useImperativeHandle, useCallback } from "react";
import { Form, Input, Button } from "@heroui/react";
import { cambiarContraseñaService } from "../../../services/authService";
import { Toast } from "../../ui/CustomAlert";
import { EyeFilledIcon } from "../../icons/EyeFilledIcon";
import { EyeSlashFilledIcon } from "../../icons/EyeSlashFilledIcon";
import { signOut } from "next-auth/react";
import PasswordStrengthIndicator, { mensajeContraseñaIncompleta, evaluarContraseña } from "./PasswordStrengthIndicator";

const CambiarContraseña = forwardRef(({ cedulaUsuario, onSuccess, onValidezChange }, ref) => {
    const [formData, setFormData] = useState({
        contraseñaActual: "",
        nuevaContraseña: "",
        confirmarContraseña: ""
    });
    const [loading, setLoading] = useState(false);
    const [showPasswords, setShowPasswords] = useState({
        actual: false,
        nueva: false,
        confirmar: false
    });
    const [errors, setErrors] = useState({});

    // Componente para el botón de mostrar/ocultar contraseña
    const PasswordToggle = ({ isVisible, toggleVisibility }) => (
        <button
            aria-label="toggle password visibility"
            className="focus:outline-none p-1 rounded-full hover:bg-gray-100 transition-colors duration-200 ease-in-out"
            type="button"
            onClick={toggleVisibility}
        >
            {isVisible ? (
                <EyeSlashFilledIcon className="text-lg md:text-xl text-gray-500 hover:text-primary transition-colors duration-200" />
            ) : (
                <EyeFilledIcon className="text-lg md:text-xl text-gray-500 hover:text-primary transition-colors duration-200" />
            )}
        </button>
    );

    const handleChange = (field, value) => {
        setFormData(prev => ({
            ...prev,
            [field]: value
        }));

        // Limpiar error específico cuando el usuario empiece a escribir
        if (errors[field]) {
            setErrors(prev => ({
                ...prev,
                [field]: ""
            }));
        }
    };

    const validateForm = useCallback(() => {
        const newErrors = {};

        if (!formData.contraseñaActual.trim()) {
            newErrors.contraseñaActual = "La contraseña actual es requerida";
        }

        if (!formData.nuevaContraseña.trim()) {
            newErrors.nuevaContraseña = "La nueva contraseña es requerida";
        } else if (mensajeContraseñaIncompleta(formData.nuevaContraseña)) {
            // Misma regla que el indicador y el botón (seis criterios)
            newErrors.nuevaContraseña = mensajeContraseñaIncompleta(formData.nuevaContraseña);
        }

        if (!formData.confirmarContraseña.trim()) {
            newErrors.confirmarContraseña = "Debe confirmar la nueva contraseña";
        } else if (formData.nuevaContraseña !== formData.confirmarContraseña) {
            newErrors.confirmarContraseña = "Las contraseñas no coinciden";
        }

        if (formData.contraseñaActual === formData.nuevaContraseña && formData.contraseñaActual.trim()) {
            newErrors.nuevaContraseña = "La nueva contraseña debe ser diferente a la actual";
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    }, [formData]);

    // Avisa al contenedor si el botón de enviar puede activarse: los seis criterios y la confirmación coinciden.
    const puedeCambiar = evaluarContraseña(formData.nuevaContraseña).completa
        && formData.nuevaContraseña === formData.confirmarContraseña;
    // Aviso en vivo bajo la confirmación: explica por qué el botón sigue desactivado.
    const noCoinciden = formData.confirmarContraseña !== ""
        && formData.confirmarContraseña !== formData.nuevaContraseña;
    useEffect(() => {
        onValidezChange && onValidezChange(puedeCambiar);
    }, [puedeCambiar, onValidezChange]);
    // Al cerrarse el formulario, el botón del contenedor vuelve a quedar desactivado.
    useEffect(() => () => { onValidezChange && onValidezChange(false); }, [onValidezChange]);

    // Exponer validateAndSubmit a través de la ref
    useImperativeHandle(ref, () => ({
        validateAndSubmit: async () => {
            if (!validateForm()) {
                return false;
            }

            setLoading(true);
            
            try {
                const result = await cambiarContraseñaService(
                    formData.contraseñaActual,
                    formData.nuevaContraseña,
                    cedulaUsuario
                );

                if (result.error) {
                    // Detectar error específico: contraseña nueva igual a la actual
                    const mensajeError = result.message || "Error al cambiar contraseña";
                    
                    if (mensajeError.toLowerCase().includes("nueva contraseña debe ser diferente") || 
                        mensajeError.toLowerCase().includes("debe ser diferente a la actual")) {
                        // Mostrar error en el campo de nueva contraseña
                        setErrors(prev => ({
                            ...prev,
                            nuevaContraseña: "La nueva contraseña debe ser diferente a la actual"
                        }));
                    } else if (mensajeError.toLowerCase().includes("contraseña actual incorrecta") ||
                               mensajeError.toLowerCase().includes("contraseña incorrecta")) {
                        // Error en contraseña actual
                        setErrors(prev => ({
                            ...prev,
                            contraseñaActual: "Contraseña actual incorrecta"
                        }));
                    } else {
                        // Otros errores se muestran como toast
                        Toast.error("Error", mensajeError);
                    }
                    setLoading(false);
                    return false;
                } else {
                    Toast.success("Éxito", result.message || "Contraseña cambiada exitosamente");
                    setFormData({
                        contraseñaActual: "",
                        nuevaContraseña: "",
                        confirmarContraseña: ""
                    });
                    
                    try {
                        await signOut({ 
                            callbackUrl: '/auth/login',
                            redirect: true 
                        });
                    } catch (error) {
                        console.error('Error al cerrar sesión:', error);
                        window.location.href = '/auth/login';
                    }
                    
                    onSuccess && onSuccess();
                    return true;
                }
            } catch (error) {
                console.error("Error al cambiar contraseña:", error);
                
                // Intentar extraer mensaje del error
                const mensajeError = error.message || "Error inesperado al cambiar contraseña";
                
                // Verificar si es el error de contraseña repetida
                if (mensajeError.toLowerCase().includes("nueva contraseña debe ser diferente") || 
                    mensajeError.toLowerCase().includes("debe ser diferente a la actual")) {
                    setErrors(prev => ({
                        ...prev,
                        nuevaContraseña: "La nueva contraseña debe ser diferente a la actual"
                    }));
                } else if (mensajeError.toLowerCase().includes("contraseña actual incorrecta") ||
                           mensajeError.toLowerCase().includes("contraseña incorrecta")) {
                    setErrors(prev => ({
                        ...prev,
                        contraseñaActual: "Contraseña actual incorrecta"
                    }));
                } else {
                    Toast.error("Error", mensajeError);
                }
                
                setLoading(false);
                return false;
            }
        }
    }), [formData, cedulaUsuario, onSuccess, validateForm]);

    const togglePasswordVisibility = (field) => {
        setShowPasswords(prev => ({
            ...prev,
            [field]: !prev[field]
        }));
    };

    return (
        <Form
            className="w-full space-y-4"
            validationBehavior="native"
        >
            <Input
                label="Contraseña actual"
                type={showPasswords.actual ? "text" : "password"}
                value={formData.contraseñaActual}
                onValueChange={(value) => handleChange("contraseñaActual", value)}
                isRequired
                errorMessage={errors.contraseñaActual}
                isInvalid={!!errors.contraseñaActual}
                placeholder="Ingrese su contraseña actual"
                color="primary"
                variant="bordered"
                size="sm"
                radius="md"
                endContent={
                    <PasswordToggle 
                        isVisible={showPasswords.actual}
                        toggleVisibility={() => togglePasswordVisibility("actual")}
                    />
                }
            />

            <PasswordStrengthIndicator password={formData.nuevaContraseña} />

            <Input
                label="Nueva contraseña"
                type={showPasswords.nueva ? "text" : "password"}
                value={formData.nuevaContraseña}
                onValueChange={(value) => handleChange("nuevaContraseña", value)}
                isRequired
                errorMessage={errors.nuevaContraseña}
                isInvalid={!!errors.nuevaContraseña}
                placeholder="Ingrese su nueva contraseña (mínimo 8 caracteres)"
                color="primary"
                variant="bordered"
                size="sm"
                radius="md"
                endContent={
                    <PasswordToggle 
                        isVisible={showPasswords.nueva}
                        toggleVisibility={() => togglePasswordVisibility("nueva")}
                    />
                }
            />

            <Input
                label="Confirmar nueva contraseña"
                type={showPasswords.confirmar ? "text" : "password"}
                value={formData.confirmarContraseña}
                onValueChange={(value) => handleChange("confirmarContraseña", value)}
                isRequired
                errorMessage={errors.confirmarContraseña || (noCoinciden ? "Las contraseñas no coinciden" : "")}
                isInvalid={!!errors.confirmarContraseña || noCoinciden}
                placeholder="Confirme su nueva contraseña"
                color="primary"
                variant="bordered"
                size="sm"
                radius="md"
                endContent={
                    <PasswordToggle 
                        isVisible={showPasswords.confirmar}
                        toggleVisibility={() => togglePasswordVisibility("confirmar")}
                    />
                }
            />
        </Form>
    );
});

CambiarContraseña.displayName = 'CambiarContraseña';

export default CambiarContraseña;
