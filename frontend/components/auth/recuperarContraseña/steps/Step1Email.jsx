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
        <div className="w-full max-w-sm mx-auto flex justify-center">
            <Form onSubmit={handleSolicitarRecuperacion} className="space-y-6 md:space-y-8 w-full">
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
                    size="md"
                    radius="md"
                    className="text-sm md:text-base"
                    validationBehavior="native"
                />

                <Button
                    type="submit"
                    color="primary"
                    size="lg"
                    className="w-full font-semibold text-sm md:text-base"
                    isLoading={loading}
                    disabled={loading}
                >
                    {loading ? "Enviando..." : "Enviar Código"}
                </Button>
            </Form>
        </div>
    );
};

export default Step1Email;
