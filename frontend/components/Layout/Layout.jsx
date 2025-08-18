import React, { useState } from "react";
import Sidebar from "./Sidebar";
import Header from "./Header";
import { UserButton } from "./UserButton"; // Importa el UserButton

const Layout = ({ children }) => {
  const [toggleCollapse, setToggleCollapse] = useState(false);

  return (
    <div className="h-screen flex w-full overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        toggleCollapse={toggleCollapse}
        setToggleCollapse={setToggleCollapse}
      />

      {/* Header (solo visible en móviles) */}
      <Header
        toggleCollapse={toggleCollapse}
        setToggleCollapse={setToggleCollapse}
      />

      {/* Botón de usuario (visible en todas las pantallas) */}
      <div className="absolute top-0 right-0 z-50 hidden md:block">
        <UserButton />
      </div>

      {/* Contenido principal */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 p-4 mt-16 overflow-auto">
          {children}
        </div>
      </div>
    </div>
  );
};

export default Layout;
