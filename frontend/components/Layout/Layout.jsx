import React, { useState } from "react";
import Sidebar from "./Sidebar";
import Header from "./Header";
import { UserButton } from "./UserButton";
import DynamicBreadcrumbs from "./DynamicBreadcrumbs";
import { useChatContextCleanup } from "../../hooks/conversacion/useChatContextCleanup";

const Layout = ({ children }) => {
  const [toggleCollapse, setToggleCollapse] = useState(false);
  
  // Hook para limpieza automática del contexto de chat
  useChatContextCleanup();

  return (
    <div className="h-screen flex w-full overflow-hidden scrollbar-hide">
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
      <div className="absolute -top-1 right-0 z-50 hidden md:block">
        <UserButton />
      </div>

      {/* Contenido principal */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Breadcrumbs */}
        <DynamicBreadcrumbs />
        
        <div className="flex-1 p-4 overflow-auto scrollbar-hide">
          {children}
        </div>
      </div>
      
    </div>
  );
};

export default Layout;
