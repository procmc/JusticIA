import React, { useState } from "react";
import { Card, CardBody } from "@heroui/react";
import { useRouter } from "next/router";
import RecuperarContraseñaForm from "./RecuperarContraseñaForm";
import { LockClosedIcon } from "@/components/icons/LockIcons";

const RecuperarContraseña = () => {
    const router = useRouter();

    return (
        <div className="flex justify-center items-center min-h-screen bg-primary/95 px-4 md:px-6">
            <Card className="flex flex-col md:flex-row w-full max-w-sm sm:max-w-md md:max-w-4xl lg:max-w-5xl h-auto min-h-[700px] md:min-h-[600px] shadow-2xl pb-6 md:pb-0" shadow="lg" radius="lg">
                
                {/* Sección izquierda con el mismo fondo que login */}
                <div className="w-full md:w-[380px] lg:w-[420px] h-80 md:h-auto bg-primary border shadow-lg flex items-center justify-center relative overflow-hidden">
                    {/* Elementos de fondo sutiles como en login */}
                    <div className="absolute inset-0">
                        {/* Gradiente sutil de fondo igual al login */}
                        <div className="absolute inset-0 bg-gradient-to-br from-primary/90 to-primary opacity-60"></div>
                        
                        {/* Círculos flotantes más sutiles */}
                        <div className="absolute top-1/4 left-1/4 w-32 h-32 bg-white/5 rounded-full blur-xl animate-pulse"></div>
                        <div className="absolute bottom-1/3 right-1/4 w-24 h-24 bg-white/3 rounded-full blur-lg animate-pulse animation-delay-1000"></div>
                        
                        {/* Puntos decorativos pequeños */}
                        <div className="absolute top-1/3 right-1/3 w-2 h-2 bg-white/20 rounded-full animate-pulse animation-delay-500"></div>
                        <div className="absolute bottom-1/4 left-1/3 w-1 h-1 bg-white/30 rounded-full animate-pulse animation-delay-700"></div>
                    </div>

                    <div className="relative z-10 text-center px-6">
                        {/* Icono principal */}
                        <div className="mx-auto w-[120px] h-[120px] md:w-[140px] md:h-[140px] lg:w-[160px] lg:h-[160px] flex items-center justify-center mb-6 relative">
                            {/* Resplandor sutil */}
                            <div className="absolute inset-0 bg-white/10 rounded-full blur-lg"></div>
                            <LockClosedIcon className="w-full h-full text-white relative z-10 drop-shadow-lg" />
                        </div>
                        
                        <h2 className="text-xl md:text-2xl lg:text-3xl font-bold text-white mb-4 drop-shadow-sm">
                            Recuperar Contraseña
                        </h2>
                        <p className="text-white/90 text-xs md:text-sm lg:text-base leading-relaxed px-2">
                            Ingresa tu correo para recibir un código de verificación
                        </p>
                    </div>
                </div>

                {/* Sección derecha con el formulario */}
                <CardBody className="w-full md:w-1/2 p-4 md:p-0 flex-1">
                    <RecuperarContraseñaForm />
                </CardBody>
            </Card>
        </div>
    );
};

export default RecuperarContraseña;
