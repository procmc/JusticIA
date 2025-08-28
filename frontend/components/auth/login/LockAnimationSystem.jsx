import React from 'react';
import Image from 'next/image';
import { LockClosedIcon, LockOpenIcon } from '../../icons/LockIcons';

const LockAnimationSystem = ({ isUnlocked, showSuccess, isClosing }) => {
  return (
    <div className="w-full h-full bg-primary border shadow-lg flex items-center justify-center py-4 md:py-8 relative overflow-hidden">
      {/* Animación de fondo simple */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/90 to-primary opacity-60"></div>
      
      {/* Título de bienvenida */}
      <div className="absolute top-4 md:top-16 left-1/2 transform -translate-x-1/2 text-center z-20">
        <h2 className="text-white text-sm md:text-base font-light mb-1 tracking-wide opacity-90">
          Bienvenido a
        </h2>
        <h1 className="text-white text-xl md:text-3xl lg:text-4xl font-bold tracking-wider">
          JusticIA
        </h1>
        <div className="w-12 md:w-16 h-0.5 bg-white/40 mx-auto mt-2 rounded-full"></div>
      </div>
      
      <div className="relative z-10">
        {/* Candado cerrado */}
        <LockClosedIcon 
          className={`w-[100px] h-[100px] md:w-[200px] md:h-[200px] lg:w-[220px] lg:h-[220px] text-white lock-icon ${
            isUnlocked && !isClosing ? 'lock-icon-opening' : 'lock-icon-closed'
          } ${isClosing ? 'lock-icon-closing' : ''}`}
        />
        
        {/* Animación circular dentro del candado */}
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 translate-y-1/3">
          <div className="w-5 h-5 md:w-10 md:h-10 border-2 border-white/30 rounded-full animate-pulse"></div>
          <div className="absolute top-0.5 left-0.5 md:top-1 md:left-1 w-4 h-4 md:w-8 md:h-8 border-2 border-blue-300/50 rounded-full animate-pulse"></div>
        </div>
        
        {/* Candado abierto */}
        <LockOpenIcon 
          className={`absolute top-0 left-0 w-[100px] h-[100px] md:w-[200px] md:h-[200px] lg:w-[220px] lg:h-[220px] text-white lock-icon ${
            isUnlocked && !isClosing ? 'lock-icon-open' : 'opacity-0 scale-90 rotate-0'
          } ${isClosing ? 'lock-icon-open-closing' : ''}`}
        />
        
        {/* Mensaje de éxito */}
        {showSuccess && !isClosing && (
          <SuccessMessage />
        )}
        
        {/* Efecto de partículas cuando se abre */}
        {isUnlocked && !isClosing && (
          <OpenParticles />
        )}
        
        {/* Efecto de cierre mágico */}
        {isClosing && (
          <ClosingEffects />
        )}
        
        {/* Mensaje de cierre */}
        {isClosing && (
          <ClosingMessage />
        )}
      </div>
      
      {/* Logos institucionales en la parte inferior */}
      <div className="absolute bottom-4 md:bottom-8 left-1/2 transform -translate-x-1/2 flex items-center gap-2 md:gap-3 opacity-70">
        <div className="relative w-12 h-7 md:w-16 md:h-10">
          <Image 
            src="/logoPj.png" 
            alt="Logo Poder Judicial" 
            fill 
            className="object-contain filter brightness-0 invert" 
          />
        </div>
        <div className="relative w-10 h-6 md:w-14 md:h-8">
          <Image 
            src="/InteligenciaInformacion.png" 
            alt="Inteligencia Información" 
            fill 
            className="object-contain filter brightness-0 invert" 
          />
        </div>
      </div>
    </div>
  );
};

// Componente para el mensaje de éxito
const SuccessMessage = () => (
  <div className="absolute -top-16 left-1/2 transform -translate-x-1/2 animate-fadeInDown">
    <div className="bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center space-x-2 whitespace-nowrap">
      <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
      </svg>
      <span className="text-sm font-medium">¡Acceso autorizado!</span>
    </div>
  </div>
);

// Componente para las partículas cuando se abre
const OpenParticles = () => (
  <div className="absolute inset-0 pointer-events-none">
    {/* Partículas flotantes simples */}
    <div className="absolute w-2 h-2 bg-yellow-300 rounded-full animate-bounce top-1/3 left-1/4 animation-delay-100"></div>
    <div className="absolute w-3 h-3 bg-green-300 rounded-full animate-pulse top-1/2 right-1/3 animation-delay-200"></div>
    <div className="absolute w-2 h-2 bg-blue-300 rounded-full animate-ping top-2/3 left-1/3 animation-delay-300"></div>
    <div className="absolute w-2 h-2 bg-purple-300 rounded-full animate-bounce bottom-1/3 right-1/4 animation-delay-400"></div>
  </div>
);

// Componente para los efectos de cierre
const ClosingEffects = () => (
  <div className="absolute inset-0 flex items-center justify-center">
    {/* Sin efectos adicionales - solo los círculos del candado */}
  </div>
);

// Componente para el mensaje de cierre
const ClosingMessage = () => (
  <div className="absolute -bottom-10 left-1/2 transform -translate-x-1/2">
    <div className="text-center">
      {/* Texto con efecto de carga en las letras */}
      <div className="text-white">
        <p className="text-sm font-medium tracking-wide">
          <span className="animate-pulse animation-delay-0">V</span>
          <span className="animate-pulse animation-delay-100">e</span>
          <span className="animate-pulse animation-delay-200">r</span>
          <span className="animate-pulse animation-delay-300">i</span>
          <span className="animate-pulse animation-delay-400">f</span>
          <span className="animate-pulse animation-delay-500">i</span>
          <span className="animate-pulse animation-delay-600">c</span>
          <span className="animate-pulse animation-delay-700">a</span>
          <span className="animate-pulse animation-delay-800">n</span>
          <span className="animate-pulse animation-delay-900">d</span>
          <span className="animate-pulse animation-delay-1000">o</span>
          <span className="mx-1"></span>
          <span className="animate-pulse animation-delay-1100">c</span>
          <span className="animate-pulse animation-delay-1200">r</span>
          <span className="animate-pulse animation-delay-1300">e</span>
          <span className="animate-pulse animation-delay-1400">d</span>
          <span className="animate-pulse animation-delay-1500">e</span>
          <span className="animate-pulse animation-delay-1600">n</span>
          <span className="animate-pulse animation-delay-1700">c</span>
          <span className="animate-pulse animation-delay-1800">i</span>
          <span className="animate-pulse animation-delay-1900">a</span>
          <span className="animate-pulse animation-delay-2000">l</span>
          <span className="animate-pulse animation-delay-2100">e</span>
          <span className="animate-pulse animation-delay-2200">s</span>
        </p>
        
        {/* Puntos de progreso debajo */}
        <div className="flex items-center justify-center gap-1 mt-2">
          <div className="w-1 h-1 bg-white/60 rounded-full animate-pulse"></div>
          <div className="w-1 h-1 bg-white/60 rounded-full animate-pulse animation-delay-300"></div>
          <div className="w-1 h-1 bg-white/60 rounded-full animate-pulse animation-delay-600"></div>
        </div>
      </div>
    </div>
  </div>
);

export default LockAnimationSystem;
