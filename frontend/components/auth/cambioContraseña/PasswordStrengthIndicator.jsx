import { useMemo } from 'react';
import zxcvbn from 'zxcvbn';

const PasswordStrengthIndicator = ({ password, showInstructions = true }) => {
  const strength = useMemo(() => {
    if (!password) return null;
    return zxcvbn(password);
  }, [password]);

  const getStrengthConfig = (score) => {
    const configs = {
      0: { 
        label: 'Muy débil', 
        color: 'bg-red-500', 
        textColor: 'text-red-600',
        width: '20%' 
      },
      1: { 
        label: 'Débil', 
        color: 'bg-orange-500', 
        textColor: 'text-orange-600',
        width: '40%' 
      },
      2: { 
        label: 'Aceptable', 
        color: 'bg-yellow-500', 
        textColor: 'text-yellow-600',
        width: '60%' 
      },
      3: { 
        label: 'Buena', 
        color: 'bg-blue-500', 
        textColor: 'text-blue-600',
        width: '80%' 
      },
      4: { 
        label: 'Muy fuerte', 
        color: 'bg-green-500', 
        textColor: 'text-green-600',
        width: '100%' 
      }
    };
    return configs[score] || configs[0];
  };

  // Mostrar instrucciones solo si no hay contraseña
  if (!password && showInstructions) {
    return (
      <div className="-mt-2 w-full p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-xs font-medium text-blue-900 mb-2">
          ✨ Crea una contraseña segura:
        </p>
        <ul className="text-xs text-blue-700 space-y-1">
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Mínimo 8 caracteres</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Combina letras mayúsculas y minúsculas</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Incluye números y símbolos (!@#$%)</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Evita palabras comunes o información personal</span>
          </li>
        </ul>
      </div>
    );
  }

  if (!password || !strength) return null;

  const config = getStrengthConfig(strength.score);

  return (
    <div className="-mt-2 w-full">
      {/* Barra de fortaleza - siempre mismo ancho */}
      <div className="w-full bg-gray-200 rounded-md h-2 overflow-hidden mb-2">
        <div
          className={`h-full ${config.color} transition-all duration-300 ease-out rounded-md`}
          style={{ width: config.width }}
        />
      </div>

      {/* Etiqueta de fortaleza */}
      <div className="w-full flex items-center justify-between mb-2">
        <span className={`text-xs font-medium ${config.textColor}`}>
          Fortaleza: {config.label}
        </span>
      </div>

      {/* Sugerencias personalizadas en español */}
      {strength.score < 2 && (
        <div className="w-full text-xs text-gray-600 bg-orange-50 border border-orange-200 rounded-lg p-2.5">
          <p className="font-medium text-orange-800 mb-1.5">💡 Sugerencias para mejorar:</p>
          <ul className="space-y-1">
            {password.length < 8 && (
              <li>• Agrega más caracteres (mínimo 8)</li>
            )}
            {!/[A-Z]/.test(password) && (
              <li>• Incluye letras mayúsculas</li>
            )}
            {!/[0-9]/.test(password) && (
              <li>• Agrega números</li>
            )}
            {!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password) && (
              <li>• Incluye símbolos especiales (!@#$%)</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
};

export default PasswordStrengthIndicator;
