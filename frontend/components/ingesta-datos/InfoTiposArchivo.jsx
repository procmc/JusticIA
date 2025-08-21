import React, { useState } from 'react';
import { Card, CardBody, Chip } from '@heroui/react';
import { FiInfo, FiChevronDown, FiChevronUp } from 'react-icons/fi';

const InfoTiposArchivo = () => {
  const [expandido, setExpandido] = useState(false);

  const tiposPermitidos = [
    {
      categoria: 'Documentos',
      tipos: [
        { ext: 'PDF', desc: 'Documentos portátiles', color: 'danger' },
        { ext: 'DOC/DOCX', desc: 'Microsoft Word', color: 'primary' },
        { ext: 'RTF', desc: 'Texto enriquecido', color: 'warning' },
        { ext: 'TXT', desc: 'Texto plano', color: 'default' }
      ]
    },
    {
      categoria: 'Audio',
      tipos: [
        { ext: 'MP3', desc: 'Audio MPEG', color: 'secondary' },
        { ext: 'WAV', desc: 'Audio sin comprimir', color: 'secondary' },
        { ext: 'M4A', desc: 'Audio AAC', color: 'secondary' },
        { ext: 'OGG', desc: 'Audio Ogg Vorbis', color: 'secondary' }
      ]
    }
  ];

  return (
    <Card className="mb-6">
      <CardBody className="p-4">
        <div 
          className="flex items-center justify-between cursor-pointer"
          onClick={() => setExpandido(!expandido)}
        >
          <div className="flex items-center space-x-2">
            <FiInfo className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-tituloSeccion">
              Tipos de archivo permitidos
            </h3>
          </div>
          {expandido ? (
            <FiChevronUp className="w-5 h-5 text-gray-500" />
          ) : (
            <FiChevronDown className="w-5 h-5 text-gray-500" />
          )}
        </div>

        {expandido && (
          <div className="mt-4 space-y-4">
            {tiposPermitidos.map((categoria, index) => (
              <div key={index}>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">
                  {categoria.categoria}
                </h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {categoria.tipos.map((tipo, tipoIndex) => (
                    <div key={tipoIndex} className="flex flex-col space-y-1">
                      <Chip 
                        color={tipo.color} 
                        variant="flat" 
                        size="sm"
                        className="self-start"
                      >
                        {tipo.ext}
                      </Chip>
                      <span className="text-xs text-gray-500">
                        {tipo.desc}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
            
            <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex items-start space-x-2">
                <FiInfo className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm">
                  <p className="font-medium text-amber-800 mb-1">
                    Consideraciones importantes:
                  </p>
                  <ul className="text-amber-700 space-y-1 text-xs">
                    <li>• Tamaño máximo por archivo: 50 MB</li>
                    <li>• Los documentos se procesarán con OCR si es necesario</li>
                    <li>• Los audios se transcribirán automáticamente</li>
                    <li>• Se recomienda usar nombres descriptivos</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
};

export default InfoTiposArchivo;
