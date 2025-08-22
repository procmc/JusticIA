import React, { useState } from "react";
import Sidebar from "./Sidebar";
import Header from "./Header";
import { UserButton } from "./UserButton";
import DynamicBreadcrumbs from "./DynamicBreadcrumbs";

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
      <div className="absolute -top-2 right-0 z-50 hidden md:block">
        <UserButton />
      </div>

      {/* Contenido principal */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Breadcrumbs */}
        <DynamicBreadcrumbs />
        
        <div className="flex-1 p-4 overflow-auto">
          {children}
        </div>
      </div>
      
    </div>
  );
};

export default Layout;
