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
  // Usar expedientNumber del servicio en lugar de expedient
  const expedientData = parseExpedientNumber(caseData.expedientNumber || caseData.expedient);
  const matterDescription = getMatterDescription(expedientData.matter);
  
  // Usar similarityPercentage del servicio
  const similarityPercent = caseData.similarityPercentage || Math.round((caseData.similarity || 0) * 100);
  
  // Usar totalDocuments del servicio
  const documentCount = caseData.totalDocuments || caseData.documentCount || 0;

  return (
    <Card className="hover:shadow-lg transition-shadow cursor-pointer">
      <CardBody className="p-8">
        <div className="space-y-6">
          {/* Header con número de expediente y año/oficina */}
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="inline-flex items-center gap-2 mb-2">
                <div className="p-2.5 bg-primary-100 rounded-xl">
                  <IoDocument className="w-5 h-5 text-primary-600" />
                </div>
                <h3 className="bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent text-md tracking-wide">
                  {caseData.expedientNumber || caseData.expedient}
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
              <span className="font-bold text-xl text-primary">{similarityPercent}%</span>
            </div>
            <Progress
              value={similarityPercent}
              color={getSimilarityColor(similarityPercent)}
              size="sm"
              className="w-full h-2"
              classNames={{
                track: "drop-shadow-sm border border-default h-2.5",
                indicator: "bg-gradient-to-r from-primary-400 to-primary-600 h-2.5",
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
                <span className="font-medium">{documentCount} documentos</span>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Creado: {caseData.date}
              </div>
            </div>
            <Button
              size="sm"
              color="default"
              variant="solid"
              startContent={<IoEye className="w-4 h-4 text-primary" />}

              onPress={() => onViewDetails(caseData)}
              className="text-xs px-3 bg-gray-100 hover:bg-gray-300 text-primary"
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
