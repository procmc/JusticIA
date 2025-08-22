import React from 'react';
import { Card, CardBody, Chip } from '@heroui/react';
import { FiFileText, FiMusic, FiSave, FiLoader } from 'react-icons/fi';

const ResumenArchivos = ({ archivos, subiendoArchivos, progreso }) => {
  if (archivos.length === 0) return null;

  const totalArchivos = archivos.length;
  const documentos = archivos.filter(a => a.tipo === 'documento').length;
  const audios = archivos.filter(a => a.tipo === 'audio').length;
  const tamañoTotal = archivos.reduce((total, archivo) => total + archivo.tamaño, 0);
  
  const formatearTamañoTotal = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const tamaños = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + tamaños[i];
  };

  return (
    <Card className="mb-6">
      <CardBody className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-tituloSeccion">
            Resumen de archivos
          </h3>
          {subiendoArchivos && (
            <div className="flex items-center text-blue-600">
              <FiLoader className="animate-spin mr-2" />
              <span className="text-sm">Subiendo...</span>
            </div>
          )}
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="flex items-center space-x-3 p-3 bg-blue-50 rounded-lg">
            <div className="p-2 bg-blue-100 rounded-full">
              <FiSave className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700">Total</p>
              <p className="text-lg font-bold text-blue-600">{totalArchivos}</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3 p-3 bg-green-50 rounded-lg">
            <div className="p-2 bg-green-100 rounded-full">
              <FiFileText className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700">Documentos</p>
              <p className="text-lg font-bold text-green-600">{documentos}</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3 p-3 bg-purple-50 rounded-lg">
            <div className="p-2 bg-purple-100 rounded-full">
              <FiMusic className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700">Audios</p>
              <p className="text-lg font-bold text-purple-600">{audios}</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3 p-3 bg-orange-50 rounded-lg">
            <div className="p-2 bg-orange-100 rounded-full">
              <FiSave className="w-5 h-5 text-orange-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700">Tamaño</p>
              <p className="text-lg font-bold text-orange-600">{formatearTamañoTotal(tamañoTotal)}</p>
            </div>
          </div>
        </div>

        {subiendoArchivos && (
          <div className="mt-4">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span>Progreso de subida</span>
              <span>{progreso}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progreso}%` }}
              />
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
};

export default ResumenArchivos;
