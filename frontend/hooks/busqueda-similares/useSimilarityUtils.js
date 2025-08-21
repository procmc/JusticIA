import { useMemo } from 'react';

const useSimilarityUtils = () => {
  // Función para parsear número de expediente
  const parseExpedientNumber = (expedient) => {
    if (!expedient) return { year: '', consecutive: '', office: '', matter: '' };
    
    const parts = expedient.split('-');
    if (parts.length >= 4) {
      return {
        year: parts[0],
        consecutive: parts[1],
        office: parts[2],
        matter: parts[3]
      };
    }
    
    return { year: '', consecutive: '', office: '', matter: '' };
  };

  // Función para obtener descripción de materia
  const getMatterDescription = (matterCode) => {
    const matterCodes = {
      'CI': 'Civil',
      'PE': 'Penal',
      'LA': 'Laboral',
      'AD': 'Administrativo',
      'CO': 'Comercial',
      'FA': 'Familia',
      'TU': 'Tutela',
      'AM': 'Amparo',
      'CE': 'Constitucional'
    };
    
    return matterCodes[matterCode] || matterCode;
  };

  // Función para obtener color de similitud
  const getSimilarityColor = (similarity) => {
    if (similarity >= 80) return 'success';
    if (similarity >= 60) return 'warning';
    return 'danger';
  };

  // Datos de ejemplo (puedes moverlos a un archivo separado más tarde)
  const mockResults = useMemo(() => [
    {
      id: 1,
      expedient: "2023-045-01-CI",
      similarity: 87,
      documentCount: 12,
      date: "2023-03-15"
    },
    {
      id: 2,
      expedient: "2023-078-02-PE",
      similarity: 82,
      documentCount: 8,
      date: "2023-04-22"
    },
    {
      id: 3,
      expedient: "2024-012-01-LA",
      similarity: 75,
      documentCount: 15,
      date: "2024-01-10"
    },
    {
      id: 4,
      expedient: "2023-134-03-CI",
      similarity: 71,
      documentCount: 6,
      date: "2023-08-17"
    },
    {
      id: 5,
      expedient: "2024-089-01-FA",
      similarity: 68,
      documentCount: 9,
      date: "2024-05-03"
    }
  ], []);

  return {
    parseExpedientNumber,
    getMatterDescription,
    getSimilarityColor,
    mockResults
  };
};

export default useSimilarityUtils;
