import classNames from "classnames";
import Link from "next/link";
import { useRouter } from "next/router";
import Image from "next/image";
import React, { useEffect, useState } from "react";
import { MdOutlineKeyboardDoubleArrowRight, MdOutlineKeyboardDoubleArrowLeft } from "react-icons/md";
import { FiChevronLeft, FiChevronRight } from "react-icons/fi";
import { LogoutIcon } from "../icons";
import { menuItems } from "../../data/menuitems";
import { useSession } from "next-auth/react";

const Sidebar = ({ toggleCollapse, setToggleCollapse }) => {
  const [isMobile, setIsMobile] = useState(false);
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    const checkIsMobile = () => {
      if (typeof window !== 'undefined') {
        setIsMobile(!window.matchMedia("(min-width: 768px)").matches);
      }
    };

    checkIsMobile();

    if (typeof window !== 'undefined') {
      const mediaQuery = window.matchMedia("(min-width: 768px)");
      mediaQuery.addListener(checkIsMobile);

      return () => {
        mediaQuery.removeListener(checkIsMobile);
      };
    }
  }, []);

  const getNavItemClasses = (link) => {
    const isActive = router.pathname === link;
    
    return classNames(
      "flex items-center cursor-pointer hover:bg-gray-200 rounded w-full overflow-hidden whitespace-nowrap mb-1 py-3 px-3",
      {
        "bg-gray-200": isActive,
      }
    );
  };

  return (
    <div
      className={classNames(
        "h-screen px-4 pt-8 pb-4 bg-white flex flex-col justify-between shadow-xl z-50 transform transition-all duration-500 ease-in-out", // Animación mejorada
        {
          "w-60": !toggleCollapse,
          "w-20 md:w-20": toggleCollapse, // Colapsado en pantallas grandes
          "-translate-x-full md:translate-x-0": toggleCollapse && isMobile, // Oculto en móviles cuando está colapsado
          "fixed md:relative": true, // Drawer en móviles, relativo en pantallas grandes
        }
      )}
      style={{ 
        transition: "width 600ms cubic-bezier(0.25, 0.46, 0.45, 0.94), transform 400ms ease-in-out",
        willChange: "width, transform"
      }}
    >
      <div className="flex flex-col h-full overflow-y-auto scrollbar-hide">
        {/* Encabezado del Sidebar */}
        <div className="flex items-center justify-between relative hidden md:flex">
          <div className="flex items-center gap-4">
            {toggleCollapse ? (
              <div
                onClick={() => setToggleCollapse(false)}
                className="flex-shrink-0 cursor-pointer flex items-center justify-center w-12 h-12 hover:bg-gray-100 rounded"
              >
                <MdOutlineKeyboardDoubleArrowRight className="w-6 h-6 text-gray-500" />
              </div>
            ) : (
              <div className="flex-shrink-0">
                <Image
                  src="/Logo.png"
                  alt="Logo"
                  width={40}
                  height={40}
                  className="w-10 h-10"
                />
              </div>
            )}
            {!toggleCollapse && (
              <span className="mt-2 text-2xl text-azulOscuro font-bold">JusticIA</span>
            )}
          </div>
          {!toggleCollapse && (
            <div
              onClick={() => setToggleCollapse(true)}
              className="p-2 cursor-pointer rounded hover:bg-gray-100 flex items-center justify-center"
            >
              <MdOutlineKeyboardDoubleArrowLeft className="w-6 h-6 text-gray-500" />
            </div>
          )}
        </div>

        {/* Contenido del Sidebar */}
        <div className="flex flex-col items-start mt-10">
          {status === "loading" ? (
            <div className="w-full flex flex-col justify-center items-center py-8 animate-pulse">
              {/* Spinner principal */}
              <div className="relative mb-3">
                <div className="w-8 h-8 border-3 border-celeste border-t-primario rounded-full animate-spin"></div>
                <div className="absolute inset-0 w-8 h-8 border-3 border-transparent border-r-pink-300 rounded-full animate-reverse"></div>
              </div>
              <div className="mt-3 text-sm font-medium text-azulOscuro">
                Cargando menú...
              </div>
              <div className="mt-1 text-xs text-gray-500">
                Verificando permisos
              </div>
            </div>
          ) : (
            menuItems.map(({ id, icon: Icon, link, label }) => (
              <div key={id} className="w-full">
                <Link
                  href={link}
                  className={getNavItemClasses(link)}
                >
                  <div className="flex items-center">
                    <div style={{ width: "2.5rem" }}>
                      <Icon className="w-6 h-6 text-gray-500" />
                    </div>
                    {!toggleCollapse && (
                      <span className="text-sm font-medium text-gray-700">
                        {label}
                      </span>
                    )}
                  </div>
                </Link>
              </div>
            ))
          )}
        </div>
        {/* Botón cerrar sesión */}
        <div
          className={classNames(
            "flex items-center px-3 py-3 cursor-pointer hover:bg-gray-300 rounded mt-auto",
            {
              "justify-center": toggleCollapse, // Centrar el contenido cuando está colapsado
              "justify-start": !toggleCollapse, // Alinear a la izquierda cuando está expandido
            }
          )}
          onClick={() => {
            console.log("Cerrar sesión");
          }}
        >
          <div style={{ width: "2.5rem" }} className="flex justify-center">
            <LogoutIcon className="w-4 h-6 text-red-500" />
          </div>
          {!toggleCollapse && (
            <span className="text-sm font-medium text-red-500">Cerrar sesión</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default Sidebar;