import React from "react";
import { FiMenu } from "react-icons/fi";
import { UserButton } from "./UserButton";
import Link from "next/link";

const Header = ({ toggleCollapse, setToggleCollapse }) => {
  return (
    <div className="fixed top-0 left-0 w-full h-14 bg-white shadow-md flex items-center justify-between px-4 z-50 md:hidden">
      {/* Botón de menú y logo */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => setToggleCollapse(!toggleCollapse)}
          className="text-gray-700 text-lg"
        >
          <FiMenu className="w-6 h-6" />
        </button>
        <div className="flex items-center">
          <Link href="/" className="block">
            <span
              className="ml-4 text-2xl font-extrabold select-none flex items-center gap-2 relative group cursor-pointer transition-all duration-200 hover:opacity-90 hover:scale-105"
              style={{ letterSpacing: '1px' }}>
              <span className="relative cursor-pointer transition-all duration-200 group-hover:drop-shadow-lg">
                <span
                  className="text-3xl font-extrabold bg-clip-text text-transparent drop-shadow-md"
                  style={{
                    background: 'linear-gradient(90deg, #0e4269ff 0%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    fontWeight: 900,
                    letterSpacing: '1px',
                  }}
                >JusticIA</span>
               
              </span>
            </span>
          </Link>
        </div>
      </div>

      <div className="top-2 z-50">
        {/* Botón de usuario */}
        <UserButton />
      </div>
    </div>
  );
};

export default Header;