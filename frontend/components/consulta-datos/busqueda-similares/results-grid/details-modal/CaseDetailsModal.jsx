import React, { useState } from 'react';
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Progress,
  Tabs,
  Tab,
  Chip
} from '@heroui/react';
import { IoCalendar, IoScale, IoDocument } from 'react-icons/io5';
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

  if (!selectedCase) return null;

  const expedientData = parseExpedientNumber(selectedCase.expedient);
  const matterDescription = getMatterDescription(expedientData.matter);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size="3xl"
      scrollBehavior="inside"
    >
      <ModalContent>
        <ModalHeader className="flex flex-col gap-2 py-2 shadow-b shadow-sm">
          {/* Header con badges compacto */}
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-6 mt-2 pl-1">
              <h3 className="text-md font-bold text-gray-700">
                Expediente: {selectedCase.expedient}
              </h3>
            </div>
            <div className="flex items-center gap-2 mr-4 mt-1">
              <Chip
                size="sm"
                color="primary"
                variant="flat"
                className="text-xs font-medium"
              >
                {matterDescription}
              </Chip>
              <Chip
                size="sm"
                color="success"
                variant="solid"
                className="text-xs font-bold text-white"
              >
                {selectedCase.similarity}%
              </Chip>
            </div>
          </div>

          <div className="flex items-center gap-6 pl-1">
            <div className="flex items-center gap-1.5">
              <IoCalendar className="w-3.5 h-3.5 text-blue-500" />
              <span className="text-xs text-gray-500 font-medium">Año:</span>
              <span className="text-xs text-gray-700 font-semibold">{expedientData.year}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <IoScale className="w-3.5 h-3.5 text-purple-500" />
              <span className="text-xs text-gray-500 font-medium">Oficina:</span>
              <span className="text-xs text-gray-700 font-semibold">{expedientData.office}</span>
            </div>
          </div>
        </ModalHeader>

        <ModalBody className="overflow-auto max-h-[60vh]">
          <div className="p-4">
            <Tabs
              selectedKey={selectedTab}
              onSelectionChange={setSelectedTab}
              variant="underlined"
              classNames={{
                tabList: "w-full relative rounded-none p-0",
                cursor: "w-full bg-primary-500",
                tab: "max-w-fit px-4 h-10",
                tabContent: "group-data-[selected=true]:text-primary-600"
              }}
            >
              <Tab
                key="resumen"
                title={
                  <div className="flex items-center gap-2">
                    <IoDocument className="w-4 h-4" />
                    <span className="text-sm">Resumen IA</span>
                  </div>
                }
              >
                <ResumenTab 
                  selectedCase={selectedCase}
                  expedientData={expedientData}
                  matterDescription={matterDescription}
                />
              </Tab>

              <Tab
                key="documentos"
                title={
                  <div className="flex items-center gap-2">
                    <IoDocument className="w-4 h-4" />
                    <span className="text-sm">Documentos (5)</span>
                  </div>
                }
              >
                <DocumentosTab selectedCase={selectedCase} />
              </Tab>
            </Tabs>
          </div>
        </ModalBody>

        <ModalFooter className="py-3">
          <Button color="danger" variant="light" onPress={onClose} size="sm">
            Cerrar
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default CaseDetailsModal;
