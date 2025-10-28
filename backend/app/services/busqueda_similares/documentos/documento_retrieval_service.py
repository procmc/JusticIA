"""
Servicio para procesar documentos coincidentes.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
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
                        "documents": {},  # Cambiar a dict para agrupar por nombre
                        "max_similarity": 0.0,
                    }

                # Agrupar chunks del mismo documento, manteniendo solo el de mayor similitud
                document_name = doc.get("document_name")
                current_score = doc.get("similarity_score", 0)
                
                if document_name:
                    # Si el documento ya existe, mantener solo el chunk con mayor score
                    if document_name not in expedientes_map[expedient_id]["documents"]:
                        expedientes_map[expedient_id]["documents"][document_name] = doc
                    else:
                        existing_score = expedientes_map[expedient_id]["documents"][document_name].get("similarity_score", 0)
                        if current_score > existing_score:
                            expedientes_map[expedient_id]["documents"][document_name] = doc
                    
                    # Actualizar score máximo del expediente
                    expedientes_map[expedient_id]["max_similarity"] = max(
                        expedientes_map[expedient_id]["max_similarity"],
                        current_score,
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
            # Convertir dict de documentos a lista
            documents_list = list(similar_info.get("documents", {}).values())
            
            for doc in documents_list:
                # Obtener IDs reales del documento desde metadatos o BD
                doc_metadata = doc.get("metadata", {})
                document_name = doc.get('document_name')
                
                # Obtener la ruta real del archivo desde la base de datos
                try:
                    # Intentar obtener el documento desde la BD para conseguir la ruta real
                    documento_bd = await self._obtener_documento_por_nombre(expedient_id, document_name)
                    
                    ruta_archivo = documento_bd.get("file_path") if documento_bd else None
                    
                    if not ruta_archivo:
                        # Fallback: construir ruta basada en estructura estándar
                        # Usar la misma lógica que FileManagementService para consistencia
                        backend_root = Path(__file__).resolve().parent.parent.parent.parent
                        ruta_archivo = str(backend_root / "uploads" / expedient_id / document_name)
                        
                except Exception as e:
                    # En caso de error, usar ruta de fallback
                    backend_root = Path(__file__).resolve().parent.parent.parent.parent
                    ruta_archivo = str(backend_root / "uploads" / expedient_id / document_name)
                    logger.error(f"Error obteniendo ruta de BD para {document_name}: {e}")

                documentos_coincidentes.append(
                    {
                        "CN_Id_documento": doc_metadata.get("id_documento")
                        or doc_metadata.get("CN_Id_documento"),  # ID real de BD
                        "CT_Nombre_archivo": document_name,
                        "puntuacion_similitud": doc.get("similarity_score"),
                        "CT_Ruta_archivo": ruta_archivo,
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
                "fecha_creacion": expediente.get("created_date"),  # Fecha de creación del expediente
                "documentos_coincidentes": documentos_coincidentes,
                "total_documentos": len(documentos_coincidentes),
            }

            casos_similares.append(caso_similar)

        # Ordenar por puntuacion_similitud
        casos_similares.sort(
            key=lambda x: x.get("puntuacion_similitud", 0), reverse=True
        )

        return casos_similares

    async def _obtener_documento_por_nombre(self, expedient_id: str, document_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información del documento desde la base de datos usando expediente y nombre.
        
        Args:
            expedient_id: Número del expediente
            document_name: Nombre del archivo
            
        Returns:
            Diccionario con información del documento o None si no se encuentra
        """
        try:
            # Usar el documento_service para obtener documentos del expediente
            expediente_data = await self.documento_service.obtener_expediente_completo(
                expedient_id, incluir_documentos=True
            )
            
            if not expediente_data or not expediente_data.get("documents"):
                return None
            
            # Buscar el documento específico por nombre
            for doc in expediente_data["documents"]:
                if doc.get("document_name") == document_name:
                    return doc
                    
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo documento {document_name} del expediente {expedient_id}: {e}")
            return None
