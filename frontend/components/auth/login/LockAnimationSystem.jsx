import React from 'react';
import { LockClosedIcon, LockOpenIcon } from '../../icons/LockIcons';

const LockAnimationSystem = ({ isUnlocked, showSuccess, isClosing }) => {
  return (
    <div className="w-full md:w-[380px] lg:w-[420px] bg-primario flex items-center justify-center py-8 md:py-0 relative overflow-hidden">
      {/* Ondas de fondo animadas */}
      <div className={`absolute inset-0 animated-background ${showSuccess ? 'animated-background-visible' : 'animated-background-hidden'}`}>
        <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-green-400/20 to-blue-500/20 animate-pulse"></div>
        <div className="absolute top-1/4 -left-1/4 w-1/2 h-1/2 bg-yellow-300/10 rounded-full animate-bounce"></div>
        <div className="absolute bottom-1/4 -right-1/4 w-1/2 h-1/2 bg-purple-300/10 rounded-full animate-pulse"></div>
      </div>
      
      <div className="relative z-10">
        {/* Candado cerrado */}
        <LockClosedIcon 
          className={`w-[140px] h-[140px] md:w-[200px] md:h-[200px] lg:w-[220px] lg:h-[220px] text-white lock-icon ${
            isUnlocked && !isClosing ? 'lock-icon-opening' : 'lock-icon-closed'
          } ${isClosing ? 'lock-icon-closing' : ''}`}
        />
        
        {/* Candado abierto */}
        <LockOpenIcon 
          className={`absolute top-0 left-0 w-[140px] h-[140px] md:w-[200px] md:h-[200px] lg:w-[220px] lg:h-[220px] text-white lock-icon ${
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
      <span className="text-sm font-medium">¡Acceso concedido!</span>
    </div>
  </div>
);

// Componente para las partículas de apertura
const OpenParticles = () => (
  <div className="absolute inset-0 flex items-center justify-center">
    <div className="w-3 h-3 bg-yellow-300 rounded-full animate-ping"></div>
    <div className="absolute w-2 h-2 bg-green-300 rounded-full animate-pulse top-1/4 left-1/4 animation-delay-300"></div>
    <div className="absolute w-2 h-2 bg-blue-300 rounded-full animate-bounce top-3/4 right-1/4 animation-delay-500"></div>
    <div className="absolute w-1 h-1 bg-purple-300 rounded-full animate-ping top-1/2 left-1/3 animation-delay-700"></div>
    <div className="absolute w-2 h-2 bg-pink-300 rounded-full animate-pulse bottom-1/3 left-2/3 animation-delay-900"></div>
  </div>
);

// Componente para los efectos de cierre
const ClosingEffects = () => (
  <div className="absolute inset-0 flex items-center justify-center">
    {/* Círculos concéntricos que se contraen */}
    <div className="absolute w-32 h-32 border-2 border-white/30 rounded-full animate-ping"></div>
    <div className="absolute w-24 h-24 border-2 border-blue-300/50 rounded-full animate-pulse"></div>
    <div className="absolute w-16 h-16 border-2 border-green-300/70 rounded-full animate-spin"></div>
    
    {/* Partículas que se mueven hacia el centro */}
    <div className="absolute w-2 h-2 bg-yellow-400 rounded-full animate-bounce top-0 left-1/2 transform -translate-x-1/2"></div>
    <div className="absolute w-2 h-2 bg-blue-400 rounded-full animate-bounce bottom-0 left-1/2 transform -translate-x-1/2"></div>
    <div className="absolute w-2 h-2 bg-green-400 rounded-full animate-bounce left-0 top-1/2 transform -translate-y-1/2"></div>
    <div className="absolute w-2 h-2 bg-purple-400 rounded-full animate-bounce right-0 top-1/2 transform -translate-y-1/2"></div>
    
    {/* Ondas de energía */}
    <div className="absolute w-8 h-8 bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full opacity-60 animate-ping animation-delay-200"></div>
    <div className="absolute w-6 h-6 bg-gradient-to-r from-purple-400 to-pink-500 rounded-full opacity-80 animate-pulse animation-delay-400"></div>
  </div>
);

// Componente para el mensaje de cierre
const ClosingMessage = () => (
  <div className="absolute -bottom-16 left-1/2 transform -translate-x-1/2 animate-fadeInUp">
    <div className="bg-blue-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center space-x-2 whitespace-nowrap">
      <svg className="w-5 h-5 animate-spin flex-shrink-0" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <span className="text-sm font-medium">Asegurando acceso...</span>
    </div>
  </div>
);

export default LockAnimationSystem;
