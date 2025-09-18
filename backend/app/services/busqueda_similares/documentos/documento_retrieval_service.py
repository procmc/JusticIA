"""
Servicio para procesar documentos coincidentes.
"""

import logging
from typing import List, Dict, Any
from app.services.busqueda_similares.documentos.documento_service import (
    DocumentoService,
)

logger = logging.getLogger(__name__)


class DocumentoRetrievalService:
    """Servicio para procesar documentos coincidentes."""

    def __init__(self):
        self.documento_service = DocumentoService()

    async def procesar_casos_similares(
        self, similar_docs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Procesa documentos similares para generar casos agrupados.

        Args:
            similar_docs: Lista de documentos similares de Milvus

        Returns:
            Lista de casos similares
        """
        # Agrupar documentos por expediente
        expedientes_map = {}
        for doc in similar_docs:
            expedient_id = doc.get("expedient_id")
            if expedient_id:
                if expedient_id not in expedientes_map:
                    expedientes_map[expedient_id] = {
                        "documents": [],
                        "max_similarity": 0.0,
                    }

                expedientes_map[expedient_id]["documents"].append(doc)
                expedientes_map[expedient_id]["max_similarity"] = max(
                    expedientes_map[expedient_id]["max_similarity"],
                    doc.get("similarity_score", 0),
                )

        # Obtener datos básicos de expedientes
        expedient_ids = list(expedientes_map.keys())
        expedientes_basicos = await self.documento_service.obtener_expedientes_batch(
            expedient_ids, incluir_documentos=False
        )

        # Construir casos similares
        casos_similares = []
        for expediente in expedientes_basicos:
            expedient_id = expediente["expedient_id"]  # CT_Num_expediente
            similar_info = expedientes_map.get(expedient_id, {})

            # Preparar documentos coincidentes con IDs reales de BD
            documentos_coincidentes = []
            for doc in similar_info.get("documents", []):
                # Obtener IDs reales del documento desde metadatos o BD
                doc_metadata = doc.get("metadata", {})

                documentos_coincidentes.append(
                    {
                        "CN_Id_documento": doc_metadata.get("id_documento")
                        or doc_metadata.get("CN_Id_documento"),  # ID real de BD
                        "CT_Nombre_archivo": doc.get("document_name"),
                        "puntuacion_similitud": doc.get("similarity_score"),
                        "url_descarga": f"/api/documents/{expedient_id}/{doc.get('document_name')}",
                        "CT_Ruta_archivo": f"/uploads/{expedient_id}/{doc.get('document_name')}",
                    }
                )

            # Ordenar por puntuacion_similitud
            documentos_coincidentes.sort(
                key=lambda x: x.get("puntuacion_similitud", 0), reverse=True
            )

            caso_similar = {
                "expediente_id": expedient_id,  # CT_Num_expediente
                "CN_Id_expediente": expediente.get("CN_Id_expediente"),  # ID real de BD
                "CT_Num_expediente": expedient_id,  # CT_Num_expediente (más claro)
                "puntuacion_similitud": similar_info.get("max_similarity", 0),
                "documentos_coincidentes": documentos_coincidentes,
                "total_documentos": len(documentos_coincidentes),
            }

            casos_similares.append(caso_similar)

        # Ordenar por puntuacion_similitud
        casos_similares.sort(
            key=lambda x: x.get("puntuacion_similitud", 0), reverse=True
        )

        return casos_similares
