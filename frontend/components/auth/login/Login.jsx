import React, { useState } from "react";
import { Card, CardBody } from "@heroui/react";
import { useRouter } from "next/router";
import { loginService } from "../../../services/authService";
import LockAnimationSystem from "./LockAnimationSystem";
import LoginForm from "./LoginForm";
import { signIn } from "next-auth/react";

const Login = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const router = useRouter();
  const toggleVisibility = () => setIsVisible(!isVisible);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage(null);

    let formData = Object.fromEntries(new FormData(e.currentTarget));
    try {
      // Usar signIn de NextAuth
      const result = await signIn("credentials", {
        redirect: false,
        email: formData.email,
        password: formData.password
      });
      if (result?.error) {
        setErrorMessage("Credenciales inválidas");
      } else if (result?.ok) {
        triggerSuccessAnimation();
        setTimeout(() => {
          router.push("/");
        }, 2200);
      } else {
        setErrorMessage("Credenciales inválidas");
      }
    } catch (error) {
      setErrorMessage("Ocurrió un error. Intente nuevamente.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex justify-center items-center min-h-screen bg-primary/95 px-4 md:px-6">
      <Card className="flex flex-col md:flex-row w-full max-w-sm sm:max-w-md md:max-w-4xl lg:max-w-5xl h-auto min-h-[700px] md:min-h-[600px] shadow-2xl pb-6 md:pb-0" shadow="lg" radius="lg">
        {/* Sección izquierda con animaciones del candado */}
        <div className="w-full md:w-[380px] lg:w-[420px] h-80 md:h-auto">
          <LockAnimationSystem 
            isUnlocked={true}
            showSuccess={false}
            isClosing={true}
          />
        </div>

        {/* Sección derecha con el formulario */}
        <CardBody className="w-full md:w-1/2 p-4 md:p-0 flex-1">
          <LoginForm 
            isVisible={isVisible}
            toggleVisibility={toggleVisibility}
            handleLogin={handleLogin}
            loading={loading}
            errorMessage={errorMessage}
          />
        </CardBody>
      </Card>
    </div>
  );
};

export default Login;
