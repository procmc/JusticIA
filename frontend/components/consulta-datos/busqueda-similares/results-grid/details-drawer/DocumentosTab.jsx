import React from 'react';
import {
  Button,
  Card,
  CardBody
} from '@heroui/react';
import { IoDocument, IoDownload, IoEye } from 'react-icons/io5';

const DocumentosTab = ({ selectedCase }) => {
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
  );
};

export default DocumentosTab;
