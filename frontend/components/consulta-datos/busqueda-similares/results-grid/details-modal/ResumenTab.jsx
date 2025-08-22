import React from 'react';
import {
  Card,
  CardBody,
  Chip
} from '@heroui/react';

const ResumenTab = ({ selectedCase, expedientData, matterDescription }) => {
  // Datos simulados para el resumen de IA
  const aiSummary = {
    resumen: "Este caso involucra un procedimiento civil relacionado con responsabilidad contractual. El demandante busca compensación por daños derivados de incumplimiento de contrato de servicios profesionales. Los elementos clave incluyen la existencia de contrato válido, incumplimiento demostrable y daños cuantificables.",
    palabrasClave: ["Responsabilidad Civil", "Incumplimiento Contractual", "Daños y Perjuicios", "Contrato de Servicios"],
    factores: ["Existencia de contrato válido", "Incumplimiento probado", "Nexo causal", "Cuantificación de daños"],
    conclusion: "Caso con alta probabilidad de éxito basado en documentación contractual sólida y evidencia de incumplimiento."
  };

  return (
    <div className="space-y-4 mt-4">
      {/* Resumen principal */}
      <Card>
        <CardBody className="p-4">
          <h4 className="text-sm font-semibold mb-2 text-gray-600">
            Resumen del Caso
          </h4>
          <p className="text-sm text-gray-700 leading-relaxed">
            {aiSummary.resumen}
          </p>
        </CardBody>
      </Card>

      {/* Palabras clave */}
      <Card>
        <CardBody className="p-4">
          <h4 className="text-sm font-semibold mb-3 text-gray-600">
            Palabras Clave Identificadas
          </h4>
          <div className="flex flex-wrap gap-2">
            {aiSummary.palabrasClave.map((palabra, index) => (
              <Chip
                key={index}
                size="sm"
                variant="flat"
                color="primary"
                className="text-xs"
              >
                {palabra}
              </Chip>
            ))}
          </div>
        </CardBody>
      </Card>

      {/* Factores de similitud */}
      <Card>
        <CardBody className="p-4">
          <h4 className="text-sm font-semibold mb-3 text-gray-600">
            Factores de Similitud
          </h4>
          <ul className="space-y-2">
            {aiSummary.factores.map((factor, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                <div className="w-1.5 h-1.5 bg-primary-500 rounded-full mt-2 flex-shrink-0"></div>
                {factor}
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>

      {/* Conclusión */}
      <Card className="bg-blue-50 border border-blue-200">
        <CardBody className="p-4">
          <h4 className="text-sm font-semibold mb-2 text-blue-600">
            Conclusión del Análisis
          </h4>
          <p className="text-sm text-blue-700">
            {aiSummary.conclusion}
          </p>
        </CardBody>
      </Card>
    </div>
  );
};

export default ResumenTab;
