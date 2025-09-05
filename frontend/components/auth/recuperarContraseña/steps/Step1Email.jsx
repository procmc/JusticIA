import React from "react";
import { Form, Input, Button } from "@heroui/react";

const Step1Email = ({ 
    formData, 
    errors, 
    loading, 
    handleChange, 
    handleSolicitarRecuperacion 
}) => {
    return (
        <div className="w-full md:w-3/4">
            <Form onSubmit={handleSolicitarRecuperacion} className="flex flex-col items-center gap-4 md:gap-5">
                <div className="w-full">
                    <Input
                        label="Correo electrónico"
                        type="email"
                        value={formData.email}
                        onValueChange={(value) => handleChange("email", value)}
                        isRequired
                        errorMessage={errors.email}
                        placeholder="tu-correo@ejemplo.com"
                        color="primary"
                        variant="bordered"
                        size="sm"
                        radius="md"
                        className="focus:border-primario"
                        validationBehavior="native"
                    />
                </div>

                <div className="w-full flex justify-end">
                    <Button
                        type="submit"
                        className="bg-gradient-to-r from-primary to-blue-600 text-white w-[120px] md:w-[140px] lg:w-[160px] h-8 md:h-10 text-base md:text-lg lg:text-xl font-semibold shadow-lg hover:shadow-xl hover:scale-105 hover:from-blue-600 hover:to-primary transition-all duration-300 ease-in-out transform active:scale-95"
                        isLoading={loading}
                        disabled={loading}
                        radius="lg"
                    >
                        <span className="text-sm md:text-base">
                            {loading ? "Enviando..." : "Enviar Código"}
                        </span>
                    </Button>
                </div>
            </Form>
        </div>
    );
};

export default Step1Email;
