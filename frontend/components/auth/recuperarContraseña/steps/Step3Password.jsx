import React from "react";
import { Form, Input, Button } from "@heroui/react";
import { EyeFilledIcon } from "../../../icons/EyeFilledIcon";
import { EyeSlashFilledIcon } from "../../../icons/EyeSlashFilledIcon";
import PasswordStrengthIndicator from "../../cambioContraseña/PasswordStrengthIndicator";

const Step3Password = ({ 
    formData, 
    errors, 
    loading, 
    timeLeft,
    showPasswords,
    handleChange, 
    handleCambiarContraseña,
    handleVolverAtras,
    togglePasswordVisibility,
    onRestart
}) => {
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

    return (
        <div className="w-full max-w-sm mx-auto">
            <Form onSubmit={handleCambiarContraseña} className="space-y-4 md:space-y-6">
                <Input
                    label="Nueva contraseña"
                    type={showPasswords.nueva ? "text" : "password"}
                    value={formData.nuevaContraseña}
                    onValueChange={(value) => handleChange("nuevaContraseña", value)}
                    isRequired
                    errorMessage={errors.nuevaContraseña}
                    isInvalid={!!errors.nuevaContraseña}
                    placeholder="Mínimo 8 caracteres"
                    color="primary"
                    variant="bordered"
                    size="md"
                    radius="md"
                    className="text-sm md:text-base"
                    endContent={
                        <PasswordToggle
                            isVisible={showPasswords.nueva}
                            toggleVisibility={() => togglePasswordVisibility("nueva")}
                        />
                    }
                />
                <PasswordStrengthIndicator password={formData.nuevaContraseña} showInstructions={false} />

                <Input
                    label="Confirmar nueva contraseña"
                    type={showPasswords.confirmar ? "text" : "password"}
                    value={formData.confirmarContraseña}
                    onValueChange={(value) => handleChange("confirmarContraseña", value)}
                    isRequired
                    errorMessage={errors.confirmarContraseña}
                    isInvalid={!!errors.confirmarContraseña}
                    placeholder="Repite la nueva contraseña"
                    color="primary"
                    variant="bordered"
                    size="md"
                    radius="md"
                    className="text-sm md:text-base"
                    endContent={
                        <PasswordToggle
                            isVisible={showPasswords.confirmar}
                            toggleVisibility={() => togglePasswordVisibility("confirmar")}
                        />
                    }
                />

                <div className="w-full max-w-sm mx-auto">
                    <Button
                        type="submit"
                        color="primary"
                        size="lg"
                        className="w-full font-semibold text-sm md:text-base"
                        isLoading={loading}
                        disabled={loading || timeLeft === 0}
                    >
                        {loading ? "Cambiando..." : "Cambiar Contraseña"}
                    </Button>

                    {/* Botón volver atrás mejorado */}
                    <div className="text-center pt-6">
                        <button
                            type="button"
                            onClick={handleVolverAtras}
                            className="inline-flex items-center text-primary-600 hover:text-primary-700 text-sm font-medium transition-colors duration-200 group"
                        >
                            <svg 
                                className="w-4 h-4 mr-2 transition-transform duration-200 group-hover:-translate-x-1" 
                                fill="none" 
                                viewBox="0 0 24 24" 
                                stroke="currentColor"
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                            </svg>
                            Cambiar código de verificación
                        </button>
                    </div>
                </div>

                {timeLeft === 0 && (
                    <div className="text-center space-y-4 p-4 bg-red-50 rounded-lg border border-red-200">
                        <div className="flex items-center justify-center">
                            <svg 
                                className="w-5 h-5 text-red-500 mr-2" 
                                fill="none" 
                                viewBox="0 0 24 24" 
                                stroke="currentColor"
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <p className="text-red-600 text-sm font-medium">La sesión ha expirado</p>
                        </div>
                        <button
                            type="button"
                            onClick={onRestart}
                            className="inline-flex items-center px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-md transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                        >
                            <svg 
                                className="w-4 h-4 mr-2" 
                                fill="none" 
                                viewBox="0 0 24 24" 
                                stroke="currentColor"
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                            </svg>
                            Iniciar de nuevo
                        </button>
                    </div>
                )}
            </Form>
        </div>
    );
};

export default Step3Password;
