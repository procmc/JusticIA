import React from "react";
import { Form, Button, InputOtp } from "@heroui/react";

const Step2Code = ({ 
    formData, 
    errors, 
    loading, 
    timeLeft,
    handleChange, 
    handleVerificarCodigo,
    handleVolverAtras,
    handleSolicitarNuevoCodigo 
}) => {
    return (
        <div className="w-full max-w-sm mx-auto flex justify-center">
            <Form onSubmit={handleVerificarCodigo} className="space-y-6 md:space-y-8">
                <div className="space-y-4 md:space-y-6">
                    <label className="block text-sm md:text-base font-medium text-gray-700 text-center">
                        Código de verificación
                    </label>

                    <div className="w-full flex justify-center">
                        <div className="flex">
                            <InputOtp
                                length={6}
                                value={formData.codigo}
                                onValueChange={(value) => handleChange("codigo", value)}
                                variant="bordered"
                                color="primary"
                                radius="md"
                                size="lg"
                                errorMessage={errors.codigo}
                                isInvalid={!!errors.codigo}
                                isRequired
                            />
                        </div>
                    </div>

                    {errors.codigo && (
                        <div className="w-full flex justify-center">
                            <p className="text-red-500 text-sm text-center">{errors.codigo}</p>
                        </div>
                    )}

                    <div className="text-center space-y-2">
                        <p className="text-gray-500 text-xs md:text-sm">
                            Ingresa el código de 6 dígitos enviado a tu correo
                        </p>
                        <p className="text-gray-400 text-xs md:text-sm break-all">
                            {formData.email}
                        </p>
                    </div>

                    <div className="flex flex-col space-y-3 md:space-y-4">
                        <Button
                            type="submit"
                            color="primary"
                            size="lg"
                            className="w-full font-semibold text-sm md:text-base"
                            isLoading={loading}
                            disabled={loading || timeLeft === 0 || formData.codigo.length !== 6}
                        >
                            {loading ? "Verificando..." : "Verificar Código"}
                        </Button>

                        {/* Botón volver atrás mejorado */}
                        <div className="text-center pt-2">
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
                                Cambiar correo electrónico
                            </button>
                        </div>
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
                            <p className="text-red-600 text-sm font-medium">El código ha expirado</p>
                        </div>
                        <button
                            type="button"
                            onClick={handleSolicitarNuevoCodigo}
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
                            Solicitar nuevo código
                        </button>
                    </div>
                )}
            </Form>
        </div>
    );
};

export default Step2Code;
