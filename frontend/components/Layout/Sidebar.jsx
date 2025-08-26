import classNames from "classnames";
import Link from "next/link";
import { useRouter } from "next/router";
import React, { useEffect, useState } from "react";
import { MdOutlineKeyboardDoubleArrowRight, MdOutlineKeyboardDoubleArrowLeft } from "react-icons/md";
import { FiChevronDown, FiChevronUp } from "react-icons/fi";
import { LogoutIcon } from "../icons";
import { menuItems } from "../../data/menuitems";
import { useSession } from "next-auth/react";
import { Tooltip } from "@heroui/tooltip";

const Sidebar = ({ toggleCollapse, setToggleCollapse }) => {
  const [isMobile, setIsMobile] = useState(false);
  const [expandedItems, setExpandedItems] = useState([]);
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

  const handleExpand = (id) => {
    // Si el sidebar está colapsado, primero lo expandimos
    if (toggleCollapse) {
      setToggleCollapse(false);
    }
    
    setExpandedItems((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const checkSubItemsActive = (subItems) => {
    return subItems.some((item) => router.pathname === item.link);
  };

  const getNavItemClasses = (link, hasSubItems = false, subItems = null) => {
    let isActive = false;
    
    if (hasSubItems && subItems) {
      isActive = checkSubItemsActive(subItems);
    } else if (link) {
      isActive = router.pathname === link;
    }
    
    return classNames(
      "flex items-center cursor-pointer hover:bg-gray-100 hover:bg-opacity-20 rounded w-full overflow-hidden whitespace-nowrap mb-1 py-2 px-3",
      {
        "bg-gray-100 bg-opacity-20": isActive,
      }
    );
  };

  return (
    <div
      className={classNames(
        "h-screen px-4 pt-8 pb-4 bg-azulOscuro flex flex-col justify-between shadow-xl z-50 transform transition-all duration-500 ease-in-out",
        {
          "w-64": !toggleCollapse,
          "w-20 md:w-20": toggleCollapse,
          "-translate-x-full md:translate-x-0": toggleCollapse && isMobile,
          "fixed md:relative": true,
        }
      )}
      style={{ 
        transition: "width 600ms cubic-bezier(0.25, 0.46, 0.45, 0.94), transform 400ms ease-in-out",
        willChange: "width, transform"
      }}
    >
      <div className="flex flex-col h-full overflow-y-auto scrollbar-hide">
        <div className="flex items-center justify-between relative hidden md:flex">
          <div className="flex items-center gap-4">
            {toggleCollapse ? (
              <div
                onClick={() => setToggleCollapse(false)}
                className="flex-shrink-0 cursor-pointer flex items-center justify-center w-12 h-12 hover:bg-gray-100 hover:bg-opacity-20 rounded"
              >
                <MdOutlineKeyboardDoubleArrowRight className="w-5 h-5 text-white" />
              </div>
            ) : null}
            {!toggleCollapse && (
              <Link href="/" className="block">
                <span
                  className="mb-3 ml-4 text-2xl font-extrabold select-none flex items-center gap-2 relative group cursor-pointer transition-all duration-200 hover:opacity-90 hover:scale-105"
                  style={{letterSpacing: '1px'}}>
                  <span className="relative cursor-pointer transition-all duration-200 group-hover:drop-shadow-lg">
                    <span
                      className="text-3xl font-extrabold bg-clip-text text-transparent drop-shadow-md"
                      style={{
                        background: 'linear-gradient(90deg, #ffffff 0%, #e5e7eb 40%, #ffffffff 100%)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        fontWeight: 900,
                        letterSpacing: '1px',
                      }}
                    >JusticIA</span>
                    <span
                      className="block h-1 w-full rounded-full transition-all duration-300 origin-left mt-1 group-hover:shadow-lg group-hover:shadow-cyan-400/50"
                      style={{background: 'linear-gradient(90deg, #ffffff 0%, #e5e7eb 40%, #ffffffff 100%)', transform: 'scaleX(1)'}}
                    ></span>
                  </span>
                </span>
              </Link>
            )}
          </div>
          {!toggleCollapse && (
            <div
              onClick={() => setToggleCollapse(true)}
              className="p-2 cursor-pointer rounded hover:bg-gray-100 hover:bg-opacity-20 flex items-center justify-center"
            >
              <MdOutlineKeyboardDoubleArrowLeft className="w-5 h-5 text-white" />
            </div>
          )}
        </div>

        <div className="flex flex-col items-start mt-10">
          {(
            menuItems.map(({ id, icon: Icon, link, label, subItems }) => {
              const hasSubItems = subItems && subItems.length > 0;

              return (
                <div key={id} className="w-full">
                  {hasSubItems ? (
                    <div>
                      <Tooltip content={label} placement="right" isDisabled={!toggleCollapse}>
                        <div
                          className={getNavItemClasses(null, hasSubItems, subItems)}
                          onClick={() => handleExpand(id)}
                        >
                          <div className="flex items-center justify-between w-full">
                            <div className="flex items-center flex-1 mr-2">
                              <div style={{ width: "2.5rem" }}>
                                <Icon className="w-5 h-5 text-white" />
                              </div>
                              {!toggleCollapse && (
                                <span className="text-sm font-medium text-white">
                                  {label}
                                </span>
                              )}
                            </div>
                            {!toggleCollapse && (
                              <div className="flex-shrink-0">
                                {expandedItems.includes(id) ? (
                                  <FiChevronUp className="w-4 h-4 text-white" />
                                ) : (
                                  <FiChevronDown className="w-4 h-4 text-white" />
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      </Tooltip>
                      {!toggleCollapse && expandedItems.includes(id) && (
                        <div className="ml-4 mt-2 mb-2">
                          {subItems.map((subItem, index) => (
                            <Tooltip key={index} content={subItem.label} placement="right" isDisabled={!toggleCollapse}>
                              <Link
                                href={subItem.link}
                                className={classNames(
                                  "flex items-center cursor-pointer hover:bg-gray-100 hover:bg-opacity-20 rounded w-full py-1.5 px-4 mb-1 whitespace-nowrap overflow-hidden",
                                  {
                                    "bg-gray-100 bg-opacity-20 border-l-4 border-blue-400": router.pathname === subItem.link,
                                  }
                                )}
                              >
                                {subItem.icon && (
                                  <div className="flex-shrink-0 mr-2">
                                    <subItem.icon className="w-4 h-4 text-white" />
                                  </div>
                                )}
                                <span className="text-sm text-white truncate">
                                  {subItem.label}
                                </span>
                              </Link>
                            </Tooltip>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <Tooltip content={label} placement="right" isDisabled={!toggleCollapse}>
                      <Link
                        href={link}
                        className={getNavItemClasses(link)}
                      >
                        <div className="flex items-center">
                          <div style={{ width: "2.5rem" }}>
                            <Icon className="w-5 h-5 text-white" />
                          </div>
                          {!toggleCollapse && (
                            <span className="text-sm font-medium text-white">
                              {label}
                            </span>
                          )}
                        </div>
                      </Link>
                    </Tooltip>
                  )}
                </div>
              );
            })
          )}
        </div>
        <Tooltip content="Cerrar sesión" placement="right" isDisabled={!toggleCollapse}>
          <div
            className={classNames(
              "flex items-center px-3 py-2 cursor-pointer hover:bg-gray-100 hover:bg-opacity-20 rounded mt-auto",
              {
                "justify-center": toggleCollapse,
                "justify-start": !toggleCollapse,
              }
            )}
          >
            <div style={{ width: "2.5rem" }} className="flex justify-center">
              <LogoutIcon className="w-4 h-6 text-red-400" />
            </div>
            {!toggleCollapse && (
              <span className="text-sm font-medium text-white">Cerrar sesión</span>
            )}
          </div>
        </Tooltip>
      </div>
    </div>
  );
};

export default Sidebar;