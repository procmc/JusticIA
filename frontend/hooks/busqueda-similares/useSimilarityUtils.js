import { useMemo } from 'react';
import { CODIGOS_MATERIA } from '@/utils/validation/expedienteValidator';

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
  // Usa el catálogo centralizado de CODIGOS_MATERIA
  const getMatterDescription = (matterCode) => {
    return CODIGOS_MATERIA[matterCode] || matterCode;
  };

  // Función para obtener color de similitud
  const getSimilarityColor = (similarity) => {
    if (similarity >= 80) return 'success';
    if (similarity >= 60) return 'warning';
    return 'danger';
  };

  return {
    parseExpedientNumber,
    getMatterDescription,
    getSimilarityColor
  };
};

export default useSimilarityUtils;
