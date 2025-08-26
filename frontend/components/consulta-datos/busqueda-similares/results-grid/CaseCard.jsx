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
      <CardBody className="p-8">
        <div className="space-y-6">
          {/* Header con número de expediente y año/oficina */}
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="inline-flex items-center gap-2 mb-2">
                <div className="p-1.5 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-lg shadow-sm">
                  <IoDocument className="w-3 h-3 text-white" />
                </div>
                <h3 className="bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent text-sm tracking-wide">
                  {caseData.expedient}
                </h3>
              </div>
            </div>
            <div className="text-right">
              <div className="flex items-center gap-1 text-xs text-gray-500 mb-1">
                <IoCalendar className="w-3 h-3" />
                <span>Año: {expedientData.year}</span>
              </div>
              <div className="flex items-center gap-1 text-xs text-gray-500">
                <IoScale className="w-3 h-3" />
                <span>Oficina: {expedientData.office}</span>
              </div>
            </div>
          </div>

          {/* Chip de materia */}
          <div className="flex justify-start">
            <Chip
              color="primary"
              variant="flat"
              size="sm"
              startContent={<IoScale className="w-4 h-4 pr-1" />}
              className="text-xs"
            >
              {matterDescription}
            </Chip>
          </div>

          {/* Barra de similitud prominente */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 font-medium">Similitud</span>
              <span className="font-bold text-xl text-gray-900">{caseData.similarity}%</span>
            </div>
            <Progress
              value={caseData.similarity}
              color={getSimilarityColor(caseData.similarity)}
              size="md"
              className="w-full"
              classNames={{
                track: "drop-shadow-sm border border-default",
                indicator: "bg-gradient-to-r from-green-400 to-green-600",
                label: "tracking-wider font-medium text-default-600",
                value: "text-foreground/60"
              }}
            />
          </div>

          {/* Footer con documentos y botón */}
          <div className="flex items-center justify-between pt-3 border-t border-gray-100">
            <div className="text-sm">
              <div className="flex items-center gap-1 text-gray-600">
                <IoDocument className="w-4 h-4" />
                <span className="font-medium">{caseData.documentCount} documentos</span>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Creado: {caseData.date}
              </div>
            </div>
            <Button
              size="sm"
              color="primary"
              variant="ghost"
              startContent={<IoEye className="w-4 h-4" />}
              onPress={() => onViewDetails(caseData)}
              className="text-xs px-3"
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
