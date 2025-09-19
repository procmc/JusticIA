import React, { useState, useEffect } from 'react';
import {
  Progress,
  Tabs,
  Tab,
  Chip
} from '@heroui/react';
import { IoCalendar, IoScale, IoDocument, IoCheckmarkCircle } from 'react-icons/io5';
import DrawerGeneral from '@/components/ui/DrawerGeneral';
import ResumenTab from './ResumenTab';
import DocumentosTab from './DocumentosTab';

const CaseDetailsModal = ({
  isOpen,
  onClose,
  selectedCase,
  parseExpedientNumber,
  getMatterDescription,
  getSimilarityColor
}) => {
  const [selectedTab, setSelectedTab] = useState("resumen");
  
  // Estados para generación de resumen IA - organizados por expediente
  const [aiSummaries, setAiSummaries] = useState({}); // { expedienteNumber: { summary, stats, isGenerating } }
  
  // Calcular documentCount directamente sin estado
  const documentCount = selectedCase?.documents?.length || selectedCase?.totalDocuments || 0;
  
  // Calcular datos del expediente (puede ser null)
  const numeroExpediente = selectedCase?.expedientNumber || selectedCase?.expedient || selectedCase?.expedientId;
  const expedientData = numeroExpediente ? parseExpedientNumber(numeroExpediente) : null;
  const matterDescription = expedientData ? getMatterDescription(expedientData.matter) : null;

  // Resetear tab al cambiar expediente
  useEffect(() => {
    if (numeroExpediente) {
      setSelectedTab("resumen");
    }
  }, [numeroExpediente]);

  // Early return DESPUÉS de todos los hooks
  if (!selectedCase || !numeroExpediente) return null;

  // Obtener estado específico de este expediente
  const currentExpedientState = aiSummaries[numeroExpediente] || {
    aiSummary: null,
    isGenerating: false,
    generationStats: null
  };

  // Funciones para actualizar estado de este expediente específico
  const updateExpedientState = (updates) => {
    setAiSummaries(prev => ({
      ...prev,
      [numeroExpediente]: {
        ...prev[numeroExpediente],
        ...updates
      }
    }));
  };

  const setAiSummary = (summary) => updateExpedientState({ aiSummary: summary });
  const setIsGeneratingResumen = (isGenerating) => updateExpedientState({ isGenerating });
  const setGenerationStats = (stats) => updateExpedientState({ generationStats: stats });

  return (
    <DrawerGeneral
      titulo={`Expediente: ${numeroExpediente || 'No definido'}`}
      isOpen={isOpen}
      onOpenChange={onClose}
      size="3xl"
      botonCerrar={{ 
        mostrar: true, 
        texto: "Cerrar",
        onPress: () => onClose(false)
      }}
    >
      <div className="space-y-6">
        {/* Header con información básica */}
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-x-8 gap-y-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                <IoCalendar className="w-4 h-4 text-blue-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600 uppercase tracking-wide">Año</p>
                <p className="text-lg font-semibold text-gray-900">{expedientData.year}</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                <IoScale className="w-4 h-4 text-purple-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600 uppercase tracking-wide">Oficina</p>
                <p className="text-lg font-semibold text-gray-900">{expedientData.office}</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center">
                <IoDocument className="w-4 h-4 text-indigo-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600 uppercase tracking-wide">Materia</p>
                <p className="text-lg font-semibold text-gray-900">{matterDescription}</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                <IoCheckmarkCircle className="w-4 h-4 text-green-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600 uppercase tracking-wide">Similitud</p>
                <p className="text-lg font-semibold text-green-700">{selectedCase.similarityPercentage}%</p>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs content */}
        <div className="bg-white">
          <Tabs
            selectedKey={selectedTab}
            onSelectionChange={setSelectedTab}
            variant="underlined"
            classNames={{
              tabList: "w-full relative rounded-none p-0 border-b border-gray-200",
              cursor: "w-full bg-primary-500",
              tab: "max-w-fit px-4 h-12",
              tabContent: "group-data-[selected=true]:text-primary-600 font-medium text-gray-500",
            }}
          >
            <Tab
              key="resumen"
              title={
                <div className="flex items-center gap-2">
                  <IoDocument className="w-4 h-4" />
                  <span>Resumen IA</span>
                  {currentExpedientState.isGenerating && (
                    <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse"></div>
                  )}
                </div>
              }
            >
              <div className="pt-6">
                <ResumenTab 
                  selectedCase={selectedCase}
                  expedientData={expedientData}
                  matterDescription={matterDescription}
                  aiSummary={currentExpedientState.aiSummary}
                  setAiSummary={setAiSummary}
                  isGeneratingResumen={currentExpedientState.isGenerating}
                  setIsGeneratingResumen={setIsGeneratingResumen}
                  generationStats={currentExpedientState.generationStats}
                  setGenerationStats={setGenerationStats}
                />
              </div>
            </Tab>

            <Tab
              key="documentos"
              title={
                <div className="flex items-center gap-2">
                  <IoDocument className="w-4 h-4" />
                  <span>Documentos ({documentCount})</span>
                </div>
              }
            >
              <div className="pt-6">
                <DocumentosTab selectedCase={selectedCase} />
              </div>
            </Tab>
          </Tabs>
        </div>
      </div>
    </DrawerGeneral>
  );
};

export default CaseDetailsModal;
