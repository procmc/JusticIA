import React from "react";
import { useRouter } from "next/router";
import { IoHomeSharp } from "react-icons/io5";
import { Breadcrumbs, BreadcrumbItem } from "@heroui/react";
import { breadcrumbsConfig } from "../../data/breadcrumbs";
import ThemeToggleButton from "../ui/ThemeToggleButton";

const DynamicBreadcrumbs = () => {
  const router = useRouter();

  // Función para obtener breadcrumbs basados en la ruta
  const getBreadcrumbs = () => {
    const path = router.pathname;
    
    return breadcrumbsConfig[path] || [{ label: 'Inicio', href: '/', isHome: true }];
  };

  const breadcrumbs = getBreadcrumbs();

  // No mostrar breadcrumbs en la página de inicio
  if (router.pathname === '/') {
    return null;
  }

  return (
    <div className="bg-white border-b px-4 py-3">
      <Breadcrumbs
        classNames={{
          list: "bg-white px-4 py-1",
        }}
        itemClasses={{
          item: "text-slate-600 data-[current=true]:text-slate-800 data-[current=true]:font-semibold hover:text-blue-600 transition-colors",
          separator: "text-slate-400 mx-1",
        }}
        variant="solid"
        separator="›"
      >
        {breadcrumbs.map((breadcrumb, index) => {
          const isLast = index === breadcrumbs.length - 1;
          
          return (
            <BreadcrumbItem 
              key={index}
              href={breadcrumb.isCurrent || breadcrumb.href === '#' ? undefined : breadcrumb.href}
              isCurrent={breadcrumb.isCurrent}
            >
              <div className="flex items-center gap-1">
                {breadcrumb.isHome ? (
                  <IoHomeSharp className="w-4 h-4 text-slate-600"/>
                ) : (
                  <span className="text-sm font-medium">{breadcrumb.label}</span>
                )}
              </div>
            </BreadcrumbItem>
          );
        })}
      </Breadcrumbs>
    </div>
  );
};

export default DynamicBreadcrumbs;
