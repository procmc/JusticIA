import React, { useState, useEffect } from 'react';
import { Avatar } from '@heroui/react';

const TypingIndicator = ({ showAvatar = true, compact = false }) => {
  const [currentPhase, setCurrentPhase] = useState(0);
  const phases = ['Analizando documentos', 'Procesando consulta', 'Generando respuesta'];

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentPhase(prev => (prev + 1) % phases.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  // Versión compacta para usar dentro de MessageBubble
  if (compact) {
    return (
      <div className="inline-flex flex-col items-start gap-2">
        <div className="flex gap-1.5">
          <div className="w-2 h-2 rounded-full bg-gray-400 animate-pulse-formal delay-0"></div>
          <div className="w-2 h-2 rounded-full bg-gray-400 animate-pulse-formal delay-300"></div>
          <div className="w-2 h-2 rounded-full bg-gray-400 animate-pulse-formal delay-600"></div>
        </div>
        <span className="text-xs text-gray-600 font-medium">
          {phases[currentPhase]}...
        </span>
        
        <style jsx>{`
          @keyframes pulse-formal {
            0%, 80%, 100% { 
              transform: scale(0.8); 
              opacity: 0.4;
            }
            40% { 
              transform: scale(1); 
              opacity: 1;
            }
          }
          
          .animate-pulse-formal {
            animation: pulse-formal 1.8s ease-in-out infinite;
          }
          
          .delay-0 { animation-delay: 0ms; }
          .delay-300 { animation-delay: 300ms; }
          .delay-600 { animation-delay: 600ms; }
        `}</style>
      </div>
    );
  }

  // Versión completa con avatar para usar independientemente
  return (
    <div className="flex gap-4 mb-6 max-w-4xl mx-auto px-4">
      {showAvatar && (
        <Avatar
          size="md"
          src="/bot.png"
          name="J"
          className="flex-shrink-0"
          showFallback
        />
      )}
      
      <div className="flex-1 min-w-0">
        <div className="relative">
          <div className="relative bg-gray-50 border border-gray-200 rounded-xl p-4">
            <div className="flex items-center gap-4">
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-gray-500 animate-professional-pulse delay-0"></div>
                <div className="w-2.5 h-2.5 rounded-full bg-gray-500 animate-professional-pulse delay-400"></div>
                <div className="w-2.5 h-2.5 rounded-full bg-gray-500 animate-professional-pulse delay-800"></div>
              </div>
              
              <span className="text-sm font-medium text-gray-700">
                {phases[currentPhase]}...
              </span>
              
              <div className="ml-auto">
                <div className="flex gap-1">
                  <div className="w-1 h-3 bg-gray-400 rounded-full animate-bar-formal delay-0"></div>
                  <div className="w-1 h-3 bg-gray-400 rounded-full animate-bar-formal delay-150"></div>
                  <div className="w-1 h-3 bg-gray-400 rounded-full animate-bar-formal delay-300"></div>
                  <div className="w-1 h-3 bg-gray-400 rounded-full animate-bar-formal delay-450"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <style jsx>{`
        @keyframes professional-pulse {
          0%, 70%, 100% { 
            transform: scale(0.8); 
            opacity: 0.3;
          }
          35% { 
            transform: scale(1.1); 
            opacity: 1;
          }
        }
        
        @keyframes bar-formal {
          0%, 100% { 
            transform: scaleY(0.4); 
            opacity: 0.4;
          }
          50% { 
            transform: scaleY(1); 
            opacity: 0.9;
          }
        }
        
        .animate-professional-pulse {
          animation: professional-pulse 2.4s ease-in-out infinite;
        }
        
        .animate-bar-formal {
          animation: bar-formal 1.6s ease-in-out infinite;
        }
        
        .delay-0 { animation-delay: 0ms; }
        .delay-150 { animation-delay: 150ms; }
        .delay-300 { animation-delay: 300ms; }
        .delay-400 { animation-delay: 400ms; }
        .delay-450 { animation-delay: 450ms; }
        .delay-600 { animation-delay: 600ms; }
        .delay-800 { animation-delay: 800ms; }
      `}</style>
    </div>
  );
};

export default TypingIndicator;
