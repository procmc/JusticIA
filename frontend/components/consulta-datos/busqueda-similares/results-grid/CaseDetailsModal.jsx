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
  Card,
  CardBody,
  Chip
} from '@heroui/react';
import { IoCalendar, IoScale, IoDocument, IoList, IoDownload, IoEye } from 'react-icons/io5';

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

  // Datos simulados para el resumen de IA
  const aiSummary = {
    resumen: "Este caso involucra un procedimiento civil relacionado con responsabilidad contractual. El demandante busca compensación por daños derivados de incumplimiento de contrato de servicios profesionales. Los elementos clave incluyen la existencia de contrato válido, incumplimiento demostrable y daños cuantificables.",
    palabrasClave: ["Responsabilidad Civil", "Incumplimiento Contractual", "Daños y Perjuicios", "Contrato de Servicios"],
    factores: ["Existencia de contrato válido", "Incumplimiento probado", "Nexo causal", "Cuantificación de daños"],
    conclusion: "Caso con alta probabilidad de éxito basado en documentación contractual sólida y evidencia de incumplimiento."
  };

  // Datos simulados para documentos
  const documents = [
    { id: 1, nombre: "Demanda inicial", tipo: "PDF", fecha: "2023-03-15", tamaño: "2.1 MB" },
    { id: 2, nombre: "Contestación", tipo: "PDF", fecha: "2023-04-02", tamaño: "1.8 MB" },
    { id: 3, nombre: "Pruebas documentales", tipo: "PDF", fecha: "2023-04-15", tamaño: "4.2 MB" },
    { id: 4, nombre: "Peritaje técnico", tipo: "PDF", fecha: "2023-05-01", tamaño: "3.5 MB" },
    { id: 5, nombre: "Alegatos finales", tipo: "PDF", fecha: "2023-05-20", tamaño: "2.9 MB" }
  ];

  // Función para descargar documento individual
  const handleDownloadDocument = (doc) => {
    // Aquí iría la lógica para descargar el documento específico
    console.log(`Descargando: ${doc.nombre}`);
    // Ejemplo: window.open(`/api/documents/download/${doc.id}`);
  };

  // Función para ver documento
  const handleViewDocument = (doc) => {
    // Aquí iría la lógica para abrir el documento en una nueva pestaña
    console.log(`Viendo: ${doc.nombre}`);
    // Ejemplo: window.open(`/api/documents/view/${doc.id}`);
  };

  // Función para descargar todos los documentos
  const handleDownloadAll = () => {
    // Aquí iría la lógica para descargar todos los documentos como ZIP
    console.log(`Descargando todos los documentos del expediente: ${selectedCase.expedient}`);
    // Ejemplo: window.open(`/api/expedients/${selectedCase.expedient}/download-all`);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size="3xl"
      scrollBehavior="inside"
      classNames={{
        base: "max-h-[90vh]",
        body: "p-0"
      }}
    >
      <ModalContent>
        <ModalHeader className="flex flex-col gap-2 py-2 shadow-b shadow-sm z-10">
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
              </Tab>

              <Tab
                key="documentos"
                title={
                  <div className="flex items-center gap-2">
                    <IoDocument className="w-4 h-4" />
                    <span className="text-sm">Documentos ({documents.length})</span>
                  </div>
                }
              >
                <div className="space-y-3 mt-4">
                  {/* Lista de documentos */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold text-gray-600">
                        Documentos del Expediente
                      </h4>
                      <Button
                        size="sm"
                        color="primary"
                        variant="flat"
                        startContent={<IoDownload className="w-3 h-3" />}
                        onPress={handleDownloadAll}
                        className="text-xs"
                      >
                        Descargar Todos
                      </Button>
                    </div>
                    {documents.map((doc) => (
                      <Card key={doc.id} className="hover:bg-gray-50 cursor-pointer transition-colors">
                        <CardBody className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div className="p-2 bg-red-100 rounded">
                                <IoDocument className="w-4 h-4 text-red-600" />
                              </div>
                              <div>
                                <p className="text-sm font-medium text-gray-700">
                                  {doc.nombre}
                                </p>
                                <p className="text-xs text-gray-500">
                                  {doc.fecha} • {doc.tamaño}
                                </p>
                              </div>
                            </div>
                            <div className="flex gap-1">
                              <Button
                                size="sm"
                                variant="light"
                                color="primary"
                                startContent={<IoEye className="w-3 h-3" />}
                                onPress={() => handleViewDocument(doc)}
                                className="text-xs px-2"
                              >
                                Ver
                              </Button>
                              <Button
                                size="sm"
                                variant="light"
                                color="secondary"
                                startContent={<IoDownload className="w-3 h-3" />}
                                onPress={() => handleDownloadDocument(doc)}
                                className="text-xs px-2"
                              >
                                Descargar
                              </Button>
                            </div>
                          </div>
                        </CardBody>
                      </Card>
                    ))}
                  </div>
                </div>
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
