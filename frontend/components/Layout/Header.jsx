import React from "react";
import Image from "next/image";
import { FiMenu } from "react-icons/fi";
import { UserButton } from "./UserButton";

const Header = ({ toggleCollapse, setToggleCollapse }) => {
  return (
    <div className="fixed top-0 left-0 w-full h-16 bg-white shadow-md flex items-center justify-between px-4 z-50 md:hidden">
      {/* Botón de menú y logo */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => setToggleCollapse(!toggleCollapse)}
          className="text-gray-700 text-lg"
        >
          <FiMenu className="w-6 h-6" />
        </button>
        <div className="flex items-center">
          <Image
            src="/logo.png"
            alt="logo"
            width={40}
            height={40}
            className="w-10 h-10"
          />
          <span className="text-2xl font-bold text-azulOscuro ml-2">
            MiLoker
          </span>
        </div>
      </div>

      {/* Botón de usuario */}
      <UserButton />
    </div>
  );
};

export default Header;