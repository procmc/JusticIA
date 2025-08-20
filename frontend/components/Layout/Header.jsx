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
          <span
            className="mb-3 ml-4 text-2xl font-extrabold select-none flex items-center gap-2 relative group cursor-pointer transition-all duration-200 hover:opacity-90 hover:scale-105"
            style={{ letterSpacing: '1px' }}>
            <span className="relative cursor-pointer transition-all duration-200 group-hover:drop-shadow-lg">
              <span
                className="text-3xl font-extrabold bg-clip-text text-transparent drop-shadow-md"
                style={{
                  background: 'linear-gradient(90deg, #1a357a 0%, #4f8cff 60%, #1a357a 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  fontWeight: 900,
                  letterSpacing: '1px',
                }}
              >JusticIA</span>
              <span
                className="block h-1 w-full rounded-full transition-all duration-300 origin-left mt-1 group-hover:shadow-lg group-hover:shadow-blue-400/50"
                style={{ background: 'linear-gradient(90deg, #1a357a 0%, #4f8cff 60%, #1a357a 100%)', transform: 'scaleX(1)' }}
              ></span>
            </span>
          </span>
        </div>
      </div>

      {/* Botón de usuario */}
      <UserButton />
    </div>
  );
};

export default Header;