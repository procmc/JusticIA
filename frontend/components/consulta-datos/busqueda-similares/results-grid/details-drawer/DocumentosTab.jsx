import React, { useState, useEffect } from 'react';
import {
  Button,
  Card,
  CardBody,
  Spinner
} from '@heroui/react';
import { IoDocument, IoDownload, IoFolderOpen } from 'react-icons/io5';
import downloadService from '../../../../../services/downloadService';

const DocumentosTab = ({ selectedCase }) => {
  const [documents, setDocuments] = useState([]);
  const [downloadingDoc, setDownloadingDoc] = useState(null);

  // Extraer documentos del caso seleccionado
  useEffect(() => {
    if (!selectedCase) {
      setDocuments([]);
      return;
    }

    const documentosArray = selectedCase?.documents;
    setDocuments(documentosArray || []);
  }, [selectedCase]);

  // Función para descargar documento individual
  const handleDownloadDocument = async (doc) => {
    try {
      setDownloadingDoc(doc.id);
      await downloadService.downloadFile(doc.filePath, doc.name);
    } catch (error) {
      console.error('Error descargando documento:', error);
    } finally {
      setDownloadingDoc(null);
    }
  };

  return (
    <div className="space-y-3 mt-4">
      {/* Lista de documentos */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-gray-600">
            Documentos del Expediente ({documents.length})
          </h4>
        </div>
        
        {documents.length === 0 ? (
          <Card className="border-dashed border-2 border-gray-300">
            <CardBody className="p-6 text-center">
              <IoFolderOpen className="w-8 h-8 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-500">
                No hay documentos disponibles para este expediente
              </p>
            </CardBody>
          </Card>
        ) : (
          documents.map((doc, index) => (
            <Card key={doc.id || index} className="hover:bg-gray-50 cursor-pointer transition-colors">
              <CardBody className="p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-red-100 rounded">
                      <IoDocument className="w-4 h-4 text-red-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-700">
                        {doc.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        Similitud: {doc.similarityPercentage}%
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant="light"
                      color="secondary"
                      startContent={
                        downloadingDoc === doc.id ? (
                          <Spinner size="sm" color="secondary" />
                        ) : (
                          <IoDownload className="w-3 h-3" />
                        )
                      }
                      onPress={() => handleDownloadDocument(doc)}
                      className="text-xs px-2"
                      isDisabled={downloadingDoc === doc.id}
                    >
                      {downloadingDoc === doc.id ? 'Descargando...' : 'Descargar'}
                    </Button>
                  </div>
                </div>
              </CardBody>
            </Card>
          ))
        )}
      </div>
    </div>
  );
};

export default DocumentosTab;
