import { useState, useEffect } from 'react';

export const useLoginAnimations = () => {
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [isClosing, setIsClosing] = useState(false);

  // Efecto para demostrar el cierre del candado
  useEffect(() => {
    if (showSuccess) {
      const timer = setTimeout(() => {
        setIsClosing(true);
        // Después de la animación de cierre, resetear todo
        setTimeout(() => {
          setIsUnlocked(false);
          setShowSuccess(false);
          setIsClosing(false);
        }, 800); // Duración de la animación de cierre reducida
      }, 1200); // Mostrar el candado abierto por 1.2 segundos

      return () => clearTimeout(timer);
    }
  }, [showSuccess]);

  const triggerSuccessAnimation = () => {
    setIsUnlocked(true);
    setShowSuccess(true);
  };

  const resetAnimations = () => {
    setIsUnlocked(false);
    setShowSuccess(false);
    setIsClosing(false);
  };

  return {
    isUnlocked,
    showSuccess,
    isClosing,
    triggerSuccessAnimation,
    resetAnimations
  };
};
