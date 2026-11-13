import React, { useState, useEffect } from 'react';
import {
  Progress,
  Tabs,
  Tab,
  Chip
} from '@heroui/react';
import { IoDocument, IoCheckmarkCircle } from 'react-icons/io5';
import DrawerGeneral from '@/components/ui/DrawerGeneral';
import ResumenTab from './ResumenTab';
import DocumentosTab from './DocumentosTab';

const CaseDetailsModal = ({
  isOpen,
  onClose,
  selectedCase,
  getSimilarityColor
}) => {
  const [selectedTab, setSelectedTab] = useState("resumen");
  
  // Estados para generación de resumen IA - organizados por expediente
  const [aiSummaries, setAiSummaries] = useState({}); // { expedienteNumber: { summary, stats, isGenerating } }
  
  // Calcular documentCount directamente sin estado
  const documentCount = selectedCase?.documents?.length || selectedCase?.totalDocuments || 0;
  
  // El tema es de nombre libre: ya no se parte como número de expediente judicial (año, oficina y materia no existen).
  const numeroExpediente = selectedCase?.expedientNumber || selectedCase?.expedient || selectedCase?.expedientId;

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
      titulo={`Tema: ${numeroExpediente || 'No definido'}`}
      isOpen={isOpen}
      onOpenChange={onClose}
      size="3xl"
      botonCerrar={{ 
        mostrar: true, 
        texto: "Cerrar",
        onPress: () => onClose(false)
      }}
    >
      <div className="bg-white">
        {/* La similitud va a la izquierda de las pestañas, en la misma fila */}
        <div className="flex flex-wrap items-center gap-x-6 border-b border-gray-200">
          <div className="flex h-12 shrink-0 items-center gap-3 border-r border-gray-200 pr-6">
            <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
              <IoCheckmarkCircle className="w-4 h-4 text-green-600" />
            </div>
            <div className="leading-tight">
              <p className="text-xs font-medium text-gray-600 uppercase tracking-wide">Similitud</p>
              <p className="text-base font-semibold text-green-700">{selectedCase.similarityPercentage}%</p>
            </div>
          </div>

          <Tabs
            selectedKey={selectedTab}
            onSelectionChange={setSelectedTab}
            variant="underlined"
            classNames={{
              tabList: "relative rounded-none p-0",
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
            />
            <Tab
              key="documentos"
              title={
                <div className="flex items-center gap-2">
                  <IoDocument className="w-4 h-4" />
                  <span>Documentos ({documentCount})</span>
                </div>
              }
            />
          </Tabs>
        </div>

        {/* Contenido de la pestaña elegida */}
        <div className="pt-6">
          {selectedTab === "resumen" ? (
            <ResumenTab
              selectedCase={selectedCase}
              aiSummary={currentExpedientState.aiSummary}
              setAiSummary={setAiSummary}
              isGeneratingResumen={currentExpedientState.isGenerating}
              setIsGeneratingResumen={setIsGeneratingResumen}
              generationStats={currentExpedientState.generationStats}
              setGenerationStats={setGenerationStats}
            />
          ) : (
            <DocumentosTab selectedCase={selectedCase} />
          )}
        </div>
      </div>
    </DrawerGeneral>
  );
};

export default CaseDetailsModal;
