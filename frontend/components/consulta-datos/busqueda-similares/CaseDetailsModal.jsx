import React from 'react';
import { 
  Modal, 
  ModalContent, 
  ModalHeader, 
  ModalBody, 
  ModalFooter, 
  Button, 
  Progress 
} from '@heroui/react';
import { IoCalendar, IoScale, IoDocument } from 'react-icons/io5';

const CaseDetailsModal = ({ 
  isOpen, 
  onClose, 
  selectedCase, 
  parseExpedientNumber, 
  getMatterDescription, 
  getSimilarityColor 
}) => {
  if (!selectedCase) return null;

  const expedientData = parseExpedientNumber(selectedCase.expedient);
  const matterDescription = getMatterDescription(expedientData.matter);

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="2xl" scrollBehavior="inside">
      <ModalContent>
        <ModalHeader className="flex flex-col gap-1">
          <h3 className="text-xl font-bold">{selectedCase.expedient}</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <IoCalendar className="w-4 h-4 text-gray-500" />
                <span className="text-gray-600">Año:</span>
                <span className="font-medium">{expedientData.year}</span>
              </div>
              <div className="flex items-center gap-2">
                <IoScale className="w-4 h-4 text-gray-500" />
                <span className="text-gray-600">Oficina:</span>
                <span className="font-medium">{expedientData.office}</span>
              </div>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <IoScale className="w-4 h-4 text-gray-500" />
                <span className="text-gray-600">Materia:</span>
                <span className="font-medium">{expedientData.matter}</span>
              </div>
              <div className="text-sm text-gray-500">
                {matterDescription}
              </div>
            </div>
          </div>
        </ModalHeader>
        
        <ModalBody>
          <div className="space-y-6">
            {/* Similitud prominente */}
            <div className="space-y-3">
              <h4 className="text-lg font-semibold">Similitud</h4>
              <div className="flex items-center gap-4">
                <Progress
                  value={selectedCase.similarity}
                  color={getSimilarityColor(selectedCase.similarity)}
                  size="lg"
                  className="flex-1"
                />
                <span className="text-xl font-bold">{selectedCase.similarity}%</span>
              </div>
            </div>

            {/* Información del Expediente */}
            <div className="space-y-3">
              <h4 className="text-lg font-semibold">Información del Expediente</h4>
              <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-600">
                      Número de Expediente
                    </label>
                    <p className="text-sm">{selectedCase.expedient}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">
                      Fecha de Creación
                    </label>
                    <p className="text-sm">{selectedCase.date}</p>
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-600">
                    Documentos Asociados
                  </label>
                  <p className="text-sm flex items-center gap-2">
                    <IoDocument className="w-4 h-4" />
                    {selectedCase.documentCount} documentos en el expediente
                  </p>
                </div>
              </div>
            </div>

            {/* Análisis de Similitud */}
            <div className="space-y-3">
              <h4 className="text-lg font-semibold">Análisis de Similitud</h4>
              <div className="bg-blue-50 rounded-lg p-4">
                <p className="text-sm text-gray-700">
                  Este expediente ha sido identificado como similar basándose en el análisis 
                  de documentos utilizando embeddings vectoriales. La similitud se calcula 
                  comparando el contenido semántico de los textos legales.
                </p>
                <div className="mt-3 text-xs text-gray-600">
                  <strong>Criterios de similitud:</strong> Análisis de contenido semántico, 
                  términos legales, y estructura documental.
                </div>
              </div>
            </div>
          </div>
        </ModalBody>
        
        <ModalFooter>
          <Button color="danger" variant="light" onPress={onClose}>
            Cerrar
          </Button>
          <Button 
            color="primary" 
            onPress={onClose}
            startContent={<IoDocument className="w-4 h-4" />}
          >
            Ver Documentos
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default CaseDetailsModal;
