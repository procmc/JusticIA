import React, { useState } from 'react';
import {
  Card,
  CardBody,
  Chip,
  Button,
  Divider
} from '@heroui/react';
import { IoSparkles, IoRefresh, IoTime, IoDocument, IoCheckmarkCircle } from 'react-icons/io5';
import similarityService from '../../../../../services/similarityService';
import { Toast } from '../../../../ui/CustomAlert';

const ResumenTab = ({ 
  selectedCase, 
  aiSummary,
  setAiSummary,
  isGeneratingResumen,
  setIsGeneratingResumen,
  generationStats,
  setGenerationStats
}) => {

  const handleGenerateResumen = async () => {
    // Intentar múltiples campos posibles para el número de expediente
    const numeroExpediente = selectedCase?.expedientNumber || selectedCase?.expedient || selectedCase?.expedientId;
    
    if (!numeroExpediente) {
      Toast.error('Error', 'No se encontró el número de expediente');
      return;
    }

    setIsGeneratingResumen(true);
    
    try {
      const result = await similarityService.generateCaseSummary(numeroExpediente);
      
      // Validación defensiva de la respuesta
      if (!result) {
        throw new Error('No se recibió respuesta del servidor');
      }

      setAiSummary({
        resumen: result.resumen || 'No se pudo generar el resumen',
        palabrasClave: Array.isArray(result.palabrasClave) ? result.palabrasClave : [],
        factoresSimilitud: Array.isArray(result.factoresSimilitud) ? result.factoresSimilitud : [],
        conclusion: result.conclusion || 'No se pudo generar la conclusión'
      });

      setGenerationStats({
        totalDocumentos: result.totalDocumentosAnalizados || 0,
        tiempoGeneracion: result.tiempoGeneracionSegundos || 0
      });

      Toast.success('¡Éxito!', 'Resumen de IA generado exitosamente');
      
    } catch (error) {
      console.error('Error generando resumen:', error);
      Toast.error('Error', error.message || 'Error generando resumen de IA');
    } finally {
      setIsGeneratingResumen(false);
    }
  };

  const renderEmptyState = () => (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="p-4 bg-primary-100 rounded-full mb-4">
        <IoSparkles className="w-8 h-8 text-primary-600" />
      </div>
      <h3 className="text-lg font-semibold text-gray-700 mb-2">
        Generar Resumen con IA
      </h3>
      <p className="text-sm text-gray-500 text-center mb-6 max-w-md">
        Analiza todos los documentos del expediente y genera un resumen inteligente 
        con palabras clave, factores de similitud y conclusiones.
      </p>
      <Button
        color="primary"
        variant="solid"
        size="lg"
        startContent={!isGeneratingResumen ? <IoSparkles className="w-4 h-4" /> : null}
        onPress={handleGenerateResumen}
        isLoading={isGeneratingResumen}
        isDisabled={isGeneratingResumen}
        className="min-w-48"
      >
        {isGeneratingResumen ? 'Generando resumen...' : 'Generar Resumen IA'}
      </Button>
      {isGeneratingResumen && (
        <p className="text-xs text-gray-500 mt-3 animate-pulse">
          Analizando documentos y generando resumen inteligente...
        </p>
      )}
    </div>
  );

  const renderGeneratedSummary = () => {
    // Validación de seguridad
    if (!aiSummary) {
      return renderEmptyState();
    }
    
    return (
    <div className="space-y-4 mt-4">
      {/* Header con estadísticas y botón regenerar */}
      {generationStats && (
        <Card className="bg-green-50 border border-green-200">
          <CardBody className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <IoCheckmarkCircle className="w-5 h-5 text-green-600" />
                <span className="text-sm font-medium text-green-700">
                  Resumen generado exitosamente
                </span>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-4 text-xs text-green-600">
                  <div className="flex items-center gap-1">
                    <IoDocument className="w-3 h-3" />
                    {generationStats.totalDocumentos} documentos
                  </div>
                  <div className="flex items-center gap-1">
                    <IoTime className="w-3 h-3" />
                    {generationStats.tiempoGeneracion}s
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="flat"
                  color="primary"
                  startContent={!isGeneratingResumen ? <IoRefresh className="w-3 h-3" /> : null}
                  onPress={handleGenerateResumen}
                  isLoading={isGeneratingResumen}
                  isDisabled={isGeneratingResumen}
                  className="text-xs h-7"
                >
                  {isGeneratingResumen ? 'Regenerando...' : 'Regenerar'}
                </Button>
              </div>
            </div>
          </CardBody>
        </Card>
      )}

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
            {aiSummary.palabrasClave?.map((palabra, index) => (
              <Chip
                key={index}
                size="sm"
                variant="flat"
                color="primary"
                className="text-xs"
              >
                {palabra}
              </Chip>
            )) || <p className="text-xs text-gray-500">No se generaron palabras clave</p>}
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
            {aiSummary.factoresSimilitud?.map((factor, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                <div className="w-1.5 h-1.5 bg-primary-500 rounded-full mt-2 flex-shrink-0"></div>
                {factor}
              </li>
            )) || <p className="text-xs text-gray-500">No se generaron factores de similitud</p>}
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

  return (
    <div>
      {!aiSummary ? renderEmptyState() : renderGeneratedSummary()}
    </div>
  );
};

export default ResumenTab;
