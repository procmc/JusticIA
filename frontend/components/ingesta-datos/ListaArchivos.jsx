import React from 'react';
import { Card, CardBody, Button, Chip, Progress } from '@heroui/react';
import { FiFile, FiTrash2, FiMusic } from 'react-icons/fi';
import { formatearTamano, obtenerTipoArchivo } from './funciones';

const ListaArchivos = ({ 
  archivos, 
  alEliminarArchivo, 
  subiendoArchivos, 
  progresoIndividual 
}) => {
  if (archivos.length === 0) return null;

  const obtenerIcono = (archivo) => {
    const tipo = obtenerTipoArchivo(archivo.name);
    return tipo === 'audio' ? FiMusic : FiFile;
  };

  const obtenerColorChip = (archivo) => {
    const tipo = obtenerTipoArchivo(archivo.name);
    return tipo === 'audio' ? 'secondary' : 'primary';
  };

  return (
    <Card>
      <CardBody className="p-4">
        <h3 className="text-lg font-semibold text-tituloSeccion mb-4">
          Archivos seleccionados
        </h3>
        
        <div className="space-y-2 max-h-64 overflow-y-auto custom-blue-scroll">
          {archivos.map((archivo, index) => {
            const Icono = obtenerIcono(archivo);
            const progreso = progresoIndividual[archivo.id] || 0;
            
            return (
              <div key={archivo.id} className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  <div className="flex-shrink-0">
                    <Icono className="w-5 h-5 text-gray-500" />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {archivo.name}
                      </p>
                      <Chip 
                        size="sm" 
                        variant="flat" 
                        color={obtenerColorChip(archivo)}
                      >
                        {archivo.name.split('.').pop().toUpperCase()}
                      </Chip>
                    </div>
                    
                    <p className="text-xs text-gray-500">
                      {formatearTamano(archivo.tamaño)}
                    </p>
                    
                    {subiendoArchivos && progreso > 0 && (
                      <div className="mt-2">
                        <Progress 
                          size="sm" 
                          value={progreso} 
                          color="primary"
                          className="max-w-full"
                        />
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="flex-shrink-0 ml-3">
                  <Button
                    isIconOnly
                    size="sm"
                    variant="light"
                    color="danger"
                    onClick={() => alEliminarArchivo(archivo.id)}
                    disabled={subiendoArchivos}
                    className="hover:bg-red-50"
                  >
                    <FiTrash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      </CardBody>
    </Card>
  );
};

export default ListaArchivos;
