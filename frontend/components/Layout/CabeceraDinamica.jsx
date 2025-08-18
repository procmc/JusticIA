import React from "react";
import Image from "next/image";

const CabezeraDinamica = ({ title, breadcrumb }) => {
  return (
    <div
      className="bg-cabecera p-6 rounded-lg shadow-md flex items-center w-full max-w-5xl mx-auto h-24 relative overflow-hidden"
    >
      {/* Contenedor exclusivo para la imagen */}
      <div className="absolute right-8 top-1/2 transform -translate-y-1/2">
        <Image
          width={80}
          height={80}
          src="/image.png"
          alt="Imagen de cabecera"
          className="w-30 h-auto"
        />
      </div>

      {/* Contenido */}
      <div className="relative z-10">
        <h2 className="md:text-2xl text-xl font-semibold text-white">{title}</h2>
        <p className="text-sm text-gray-100">{breadcrumb}</p>
      </div>
    </div>
  );
};

export default CabezeraDinamica;