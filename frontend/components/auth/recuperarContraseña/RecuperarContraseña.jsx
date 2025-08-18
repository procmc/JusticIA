import React, { useState } from "react";
import { Card, CardBody } from "@heroui/react";
import { useRouter } from "next/router";
import RecuperarContraseñaForm from "./RecuperarContraseñaForm";
import { LockClosedIcon } from "@/components/icons/LockIcons"; // Asegúrate de que esta ruta sea correcta

const RecuperarContraseña = () => {
    const router = useRouter();

    return (
        <div className="flex justify-center items-center min-h-screen bg-fondoLogin px-4 md:px-6 py-6">
            <Card className="flex flex-col md:flex-row w-full max-w-lg md:max-w-4xl lg:max-w-5xl h-auto md:min-h-[600px] shadow-lg pb-8 md:pb-0" shadow="lg" radius="lg">

                {/* Sección izquierda con diseño consistente al login */}
                <div className="w-full md:w-[380px] lg:w-[420px] bg-primario flex items-center justify-center py-8 md:py-0 relative overflow-hidden">
                    {/* Ondas de fondo animadas sutiles */}
                    <div className="absolute inset-0">
                        <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-blue-400/10 to-blue-600/10 animate-pulse"></div>
                        <div className="absolute top-1/4 -left-1/4 w-1/2 h-1/2 bg-blue-300/5 rounded-full animate-bounce animation-delay-1000"></div>
                        <div className="absolute bottom-1/4 -right-1/4 w-1/2 h-1/2 bg-blue-400/5 rounded-full animate-pulse animation-delay-2000"></div>
                        
                        {/* Partículas flotantes adicionales */}
                        <div className="absolute top-1/3 left-1/4 w-3 h-3 bg-white/10 rounded-full animate-ping animation-delay-500"></div>
                        <div className="absolute bottom-1/3 right-1/3 w-2 h-2 bg-white/15 rounded-full animate-bounce animation-delay-700"></div>
                        <div className="absolute top-2/3 right-1/4 w-1 h-1 bg-white/20 rounded-full animate-pulse animation-delay-900"></div>
                    </div>

                    <div className="relative z-10 text-center px-6">
                        <div className="mb-8">
                            {/* Icono principal más grande y consistente */}
                            <div className="mx-auto w-[140px] h-[140px] md:w-[160px] md:h-[160px] lg:w-[180px] lg:h-[180px] flex items-center justify-center mb-6 relative">
                                {/* Resplandor sutil detrás del icono */}
                                <div className="absolute inset-0 bg-white/10 rounded-full blur-xl animate-pulse"></div>
                                <LockClosedIcon className="w-full h-full text-white relative z-10 drop-shadow-lg" />
                            </div>
                            
                            <h2 className="text-xl md:text-2xl lg:text-3xl font-bold text-white mb-4 drop-shadow-sm">
                                Recuperar Contraseña
                            </h2>
                            <p className="text-white/90 text-xs md:text-sm lg:text-base leading-relaxed px-2">
                                Sigue los pasos para recuperar el acceso a tu cuenta de forma segura
                            </p>
                        </div>
                    </div>
                </div>

                {/* Sección derecha con el formulario */}
                <CardBody className="w-full md:w-1/2 p-0">
                    <RecuperarContraseñaForm />
                </CardBody>
            </Card>
        </div>
    );
};

export default RecuperarContraseña;
