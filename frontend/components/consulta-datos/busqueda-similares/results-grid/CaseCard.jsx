import React from 'react';
import { Card, CardBody, Chip, Progress, Button } from '@heroui/react';
import { IoCalendar, IoScale, IoDocument, IoEye } from 'react-icons/io5';

const CaseCard = ({ 
  caseData, 
  parseExpedientNumber, 
  getMatterDescription, 
  getSimilarityColor,
  onViewDetails 
}) => {
  const expedientData = parseExpedientNumber(caseData.expedient);
  const matterDescription = getMatterDescription(expedientData.matter);

  return (
    <Card className="hover:shadow-lg transition-shadow cursor-pointer">
      <CardBody className="p-6">
        <div className="space-y-4">
          {/* Header con número de expediente */}
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h3 className="font-bold text-gray-900 text-lg mb-1">
                {caseData.expedient}
              </h3>
              <div className="grid grid-cols-2 gap-2 text-xs text-gray-500">
                <div className="flex items-center gap-1">
                  <IoCalendar className="w-3 h-3" />
                  <span>Año: {expedientData.year}</span>
                </div>
                <div className="flex items-center gap-1">
                  <IoScale className="w-3 h-3" />
                  <span>Oficina: {expedientData.office}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Información de materia */}
          <div className="flex items-center justify-between">
            <Chip
              color="primary"
              variant="flat"
              size="sm"
              startContent={<IoScale className="w-3 h-3" />}
            >
              {matterDescription}
            </Chip>
            <span className="text-xs text-gray-500">
              Código: {expedientData.matter}
            </span>
          </div>

          {/* Similitud prominente */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 font-medium">Similitud</span>
              <span className="font-bold text-lg">{caseData.similarity}%</span>
            </div>
            <Progress
              value={caseData.similarity}
              color={getSimilarityColor(caseData.similarity)}
              size="lg"
              className="h-2"
            />
          </div>

          {/* Información adicional */}
          <div className="flex items-center justify-between pt-2 border-t border-gray-100">
            <div className="text-sm text-gray-600">
              <div className="flex items-center gap-1">
                <IoDocument className="w-4 h-4" />
                <span>{caseData.documentCount} documentos</span>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Creado: {caseData.date}
              </div>
            </div>
            <Button
              size="sm"
              color="primary"
              variant="flat"
              startContent={<IoEye className="w-4 h-4" />}
              onPress={() => onViewDetails(caseData)}
            >
              Ver Detalles
            </Button>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

export default CaseCard;
