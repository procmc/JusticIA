from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import time
import math
from collections import defaultdict
import asyncio
from sqlalchemy.orm import Session

from app.schemas.similarity_schemas import (
    SimilaritySearchRequest, 
    SimilaritySearchResponse, 
    SimilarCase, 
    DocumentMatch
)
from app.embeddings.embeddings import get_embedding
from app.vectorstore.vectorstore import search_similar_documents
from app.repositories.expediente_repository import ExpedienteRepository
from app.db.database import get_db
from app.config.config import COLLECTION_NAME
from app.llm.llm_service import consulta_simple


class SimilarityService:
    """Servicio especializado para búsqueda de casos similares"""
    
    def __init__(self):
        self.expediente_repo = ExpedienteRepository()

    async def search_similar_cases(
        self, 
        request: SimilaritySearchRequest,
        user_id: Optional[str] = None
    ) -> SimilaritySearchResponse:
        """
        Función principal para búsqueda de casos similares
        
        Args:
            request: Parámetros de búsqueda
            user_id: ID del usuario que realiza la búsqueda (para auditoría)
            
        Returns:
            SimilaritySearchResponse: Resultados de la búsqueda
        """
        start_time = time.time()
        
        try:
            # 1. Validar y obtener criterio de búsqueda
            search_criteria = self._extract_search_criteria(request)
            
            # 2. Realizar búsqueda según el modo
            if request.search_mode == "description":
                if not request.query_text:
                    raise ValueError("query_text es requerido para búsqueda por descripción")
                raw_results = await self._search_by_description(
                    request.query_text, 
                    request.limit, 
                    request.similarity_threshold
                )
            elif request.search_mode == "expedient":
                if not request.expedient_number:
                    raise ValueError("expedient_number es requerido para búsqueda por expediente")
                raw_results = await self._search_by_expedient(
                    request.expedient_number, 
                    request.limit, 
                    request.similarity_threshold
                )
            else:
                raise ValueError(f"Modo de búsqueda no válido: {request.search_mode}")
            
            # 3. Procesar y agrupar resultados por expediente
            similar_cases = await self._process_and_group_results(
                raw_results, 
                request.similarity_threshold
            )
            
            # 4. Calcular métricas
            execution_time = (time.time() - start_time) * 1000
            total_documents_analyzed = len(raw_results)
            
            # 5. Crear respuesta
            response = SimilaritySearchResponse(
                search_criteria=search_criteria,
                search_mode=request.search_mode,
                total_results=len(similar_cases),
                execution_time_ms=round(execution_time, 2),
                similarity_threshold=request.similarity_threshold,
                similar_cases=similar_cases,
                total_documents_analyzed=total_documents_analyzed
            )
            
            # TODO: Registrar en bitácora si user_id está disponible
            # await self._log_search_activity(user_id, request, response)
            
            return response
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            print(f"Error en búsqueda de similares: {str(e)}")
            
            # Retornar respuesta vacía pero válida en caso de error
            return SimilaritySearchResponse(
                search_criteria=search_criteria if 'search_criteria' in locals() else "Error",
                search_mode=request.search_mode,
                total_results=0,
                execution_time_ms=round(execution_time, 2),
                similarity_threshold=request.similarity_threshold,
                similar_cases=[],
                total_documents_analyzed=0
            )

    async def _search_by_description(
        self, 
        query_text: str, 
        limit: int, 
        threshold: float
    ) -> List[Dict[str, Any]]:
        """
        NUEVO: Búsqueda por descripción usando SOLO similitud semántica
        Eliminamos el sistema de keywords estáticas para usar búsqueda semántica pura
        """
        
        print(f"🔍 FLUJO DESCRIPCIÓN: Buscando por '{query_text[:100]}...'")
        
        # 1. Generar embedding del texto de consulta
        query_embedding = await get_embedding(query_text)
        print(f"✅ Embedding generado: {len(query_embedding)} dimensiones")
        
        # 2. Buscar documentos similares usando SOLO similitud semántica
        similar_docs = await search_similar_documents(
            query_embedding=query_embedding,
            limit=limit * 5,  # Buscar más docs para mejor agrupación
            filters=None  # Sin filtros para búsqueda general
        )
        
        print(f"📄 Documentos encontrados en vectorstore: {len(similar_docs)}")
        
        # 3. NO aplicar boost artificial - usar solo similitud semántica natural
        return similar_docs

    async def _search_by_expedient(
        self, 
        expedient_number: str, 
        limit: int, 
        threshold: float
    ) -> List[Dict[str, Any]]:
        """
        NUEVO FLUJO: Búsqueda por expediente específico
        1. Obtener TODOS los documentos del expediente
        2. Generar resumen semántico con LLM
        3. Buscar expedientes similares usando el resumen
        """
        
        print(f"🔍 FLUJO EXPEDIENTE: Analizando expediente {expedient_number}")
        
        # 1. Verificar que el expediente existe
        db = next(get_db())
        try:
            expediente_base = self.expediente_repo.obtener_por_numero(db, expedient_number)
            if not expediente_base:
                print(f"⚠️ Expediente {expedient_number} no encontrado")
                return []
            
            print(f"✅ Expediente base encontrado: ID {expediente_base.CN_Id_expediente}")
            
        finally:
            db.close()
        
        # 2. Obtener TODOS los documentos del expediente base
        expedient_docs = await self._get_expedient_documents(expedient_number)
        
        if not expedient_docs:
            print(f"⚠️ No se encontraron documentos para el expediente {expedient_number}")
            return []
        
        print(f"📄 Documentos del expediente: {len(expedient_docs)}")
        
        # 3. Generar resumen semántico del expediente completo usando LLM
        semantic_summary = await self._generate_semantic_summary(expedient_docs)
        print(f"📝 Resumen semántico generado: {len(semantic_summary)} chars")
        
        # 4. Crear embedding del resumen para búsqueda de similares
        summary_embedding = await get_embedding(semantic_summary)
        print(f"🔢 Embedding del resumen generado: {len(summary_embedding)} dimensiones")
        
        # 5. Buscar expedientes similares usando el resumen (excluyendo el mismo expediente)
        similar_docs = await search_similar_documents(
            query_embedding=summary_embedding,
            limit=1024,  # Límite máximo permitido por Milvus
            filters=None  # SIN FILTRO - evitar bug de Milvus
        )
        
        # Filtrar manualmente para excluir el expediente base
        filtered_docs = []
        for doc in similar_docs:
            entity = doc.get("entity", {})
            doc_expedient = entity.get("numero_expediente", "")
            
            if doc_expedient != expedient_number:  # Excluir el expediente base
                filtered_docs.append(doc)
        
        # Tomar solo los primeros 'limit * 4' documentos después del filtrado
        filtered_docs = filtered_docs[:limit * 4]
        
        print(f"📄 Expedientes similares encontrados (después de filtrar): {len(filtered_docs)}")
        
        return filtered_docs

    async def _get_expedient_documents(self, expedient_number: str) -> List[Dict[str, Any]]:
        """
        Obtiene todos los documentos de un expediente específico
        SOLUCIÓN TEMPORAL: Busca todos y filtra manualmente para evitar bug de Milvus
        """
        print(f"📋 Obteniendo todos los documentos del expediente {expedient_number}")
        
        # Usar un vector dummy normalizado (importante para COSINE similarity)
        dummy_embedding = [1.0 / math.sqrt(768)] * 768  # Vector unitario normalizado
        
        # Buscar todos los documentos SIN filtro para evitar el bug
        all_docs = await search_similar_documents(
            query_embedding=dummy_embedding,
            limit=1024,  # Límite máximo permitido por Milvus
            filters=None  # SIN FILTRO - evitar bug de Milvus
        )
        
        print(f"📄 Documentos totales encontrados: {len(all_docs)}")
        
        # Filtrar manualmente por expediente
        expedient_docs = []
        for doc in all_docs:
            entity = doc.get("entity", {})
            doc_expedient = entity.get("numero_expediente", "")
            
            if doc_expedient == expedient_number:
                expedient_docs.append(doc)
        
        print(f"📄 Documentos encontrados para {expedient_number}: {len(expedient_docs)}")
        
        # Ordenar por página/índice para mantener secuencia lógica
        expedient_docs_sorted = sorted(expedient_docs, key=lambda x: (
            x.get("entity", {}).get("pagina_inicio", 0),
            x.get("entity", {}).get("indice_chunk", 0)
        ))
        
        return expedient_docs_sorted

    async def _create_expedient_embedding(self, docs: List[Dict[str, Any]]) -> List[float]:
        """Crea un embedding representativo de un expediente completo"""
        
        # Estrategia: concatenar los textos más relevantes y generar un embedding
        texts = []
        for doc in docs[:10]:  # Tomar hasta 10 documentos más relevantes
            entity = doc.get("entity", {})
            texto = entity.get("texto", "")
            if texto.strip():
                texts.append(texto[:500])  # Tomar hasta 500 chars por documento
        
        if not texts:
            # Fallback: usar el número de expediente
            combined_text = f"Expediente judicial número {docs[0]['entity'].get('numero_expediente', '')}"
        else:
            combined_text = " ".join(texts)
        
        # Generar embedding del texto combinado
        return await get_embedding(combined_text)

    async def _process_and_group_results(
        self, 
        raw_results: List[Dict[str, Any]], 
        threshold: float
    ) -> List[SimilarCase]:
        """
        SIMPLIFICADO: Procesa y agrupa resultados usando SOLO similitud semántica natural
        """
        
        print(f"🔄 Procesando {len(raw_results)} documentos con similitud semántica pura...")
        
        # Agrupar documentos por expediente
        expedients_dict = defaultdict(list)
        
        for doc in raw_results:
            entity = doc.get("entity", {})
            distance = doc.get("distance", 1.0)
            
            # Con métrica COSINE, Milvus devuelve similitud directamente (0-1)
            # NO es distancia, por lo que NO necesitamos hacer 1.0 - distance
            similarity = distance  # Cambio crítico: distance es en realidad similarity con COSINE
            expedient_number = entity.get("numero_expediente", "")
            
            print(f"📏 Expediente: {expedient_number}, Similitud: {similarity:.3f}, Umbral: {threshold}")
            
            if similarity < threshold:
                print(f"❌ Expediente {expedient_number} rechazado por umbral bajo")
                continue
                
            if not expedient_number:
                continue
                
            expedients_dict[expedient_number].append({
                "document": entity,
                "similarity": similarity,
                "distance": distance
            })
        
        print(f"📊 Expedientes únicos encontrados: {len(expedients_dict)}")
        
        # Convertir a objetos SimilarCase
        similar_cases = []
        db = next(get_db())
        
        try:
            for expedient_number, docs in expedients_dict.items():
                # Obtener información del expediente desde la BD
                expediente = self.expediente_repo.obtener_por_numero(db, expedient_number)
                if not expediente:
                    continue
                
                # Calcular similitud del expediente usando métricas semánticas
                expedient_similarity = self._calculate_semantic_similarity(docs)
                
                # Crear documentos coincidentes ordenados por similitud natural
                docs_sorted = sorted(docs, key=lambda x: x["similarity"], reverse=True)
                matched_documents = []
                
                for doc_data in docs_sorted[:5]:  # Top 5 documentos por expediente
                    doc_entity = doc_data["document"]
                    matched_documents.append(DocumentMatch(
                        document_id=doc_entity.get("id_documento", 0),
                        document_name=doc_entity.get("nombre_archivo", "Documento sin nombre"),
                        similarity_score=doc_data["similarity"],
                        text_fragment=self._truncate_text(doc_entity.get("texto", ""), 300),
                        page_number=doc_entity.get("pagina_inicio")
                    ))
                
                # Crear objeto SimilarCase
                similar_case = SimilarCase(
                    expedient_id=expediente.CN_Id_expediente,
                    expedient_number=expedient_number,
                    similarity_percentage=round(expedient_similarity * 100, 1),
                    document_count=len(docs),
                    matched_documents=matched_documents,
                    creation_date=expediente.CF_Fecha_creacion,
                    matter_type=self._extract_matter_type(expedient_number)
                )
                
                similar_cases.append(similar_case)
        
        finally:
            db.close()
        
        # Ordenar por similitud semántica natural
        similar_cases.sort(key=lambda x: x.similarity_percentage, reverse=True)
        
        print(f"✅ Casos similares procesados con similitud semántica: {len(similar_cases)}")
        
        return similar_cases

    def _calculate_semantic_similarity(self, docs_data: List[Dict]) -> float:
        """
        Calcula similitud del expediente usando métricas semánticas puras
        """
        if not docs_data:
            return 0.0
        
        # 1. Similitud máxima (documento más relevante)
        max_similarity = max(d["similarity"] for d in docs_data)
        
        # 2. Similitud promedio ponderada
        similarities = [d["similarity"] for d in docs_data]
        weighted_avg = sum(s * s for s in similarities) / sum(similarities) if similarities else 0
        
        # 3. Bonus por consistencia (múltiples documentos relevantes)
        high_relevance_docs = len([d for d in docs_data if d["similarity"] > 0.7])
        consistency_bonus = min(high_relevance_docs * 0.02, 0.1)  # Máximo 10% bonus
        
        # Combinar métricas (priorizando el mejor match)
        final_similarity = (max_similarity * 0.7 + weighted_avg * 0.3) + consistency_bonus
        
        return min(final_similarity, 1.0)

    def _extract_search_criteria(self, request: SimilaritySearchRequest) -> str:
        """Extrae el criterio de búsqueda legible"""
        if request.search_mode == "description" and request.query_text:
            return request.query_text.strip()
        elif request.search_mode == "expedient" and request.expedient_number:
            return f"Expediente: {request.expedient_number}"
        return "Criterio no especificado"

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Trunca texto manteniendo palabras completas"""
        if len(text) <= max_length:
            return text
        
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:  # Si el último espacio está cerca del final
            truncated = truncated[:last_space]
        
        return truncated + "..."

    def _extract_matter_type(self, expedient_number: str) -> Optional[str]:
        """Extrae el tipo de materia del número de expediente"""
        try:
            # Patrón típico: YYYY-NNN-NN-XX donde XX es el tipo de materia
            parts = expedient_number.split('-')
            if len(parts) >= 4:
                matter_code = parts[3].upper()
                matter_types = {
                    'CI': 'Civil',
                    'PE': 'Penal',
                    'LA': 'Laboral',
                    'AD': 'Administrativo',
                    'FA': 'Familia',
                    'CO': 'Comercial',
                    'TU': 'Tutela',
                    'AM': 'Amparo'
                }
                return matter_types.get(matter_code, matter_code)
        except:
            pass
        
        return None


    async def _generate_semantic_summary(self, docs: List[Dict[str, Any]]) -> str:
        """
        Genera un resumen semántico inteligente del expediente usando LLM
        """
        print(f"🧠 Generando resumen semántico de {len(docs)} documentos...")
        
        # 1. Extraer y estructurar textos por tipo de documento
        document_texts = {
            'demandas': [],
            'sentencias': [],
            'resoluciones': [],
            'pruebas': [],
            'otros': []
        }
        
        for doc in docs:
            entity = doc.get("entity", {})
            texto = entity.get("texto", "").strip()
            tipo_doc = entity.get("tipo_documento", "").lower()
            nombre_archivo = entity.get("nombre_archivo", "").lower()
            
            if not texto:
                continue
                
            # Clasificar documento por tipo
            if any(x in tipo_doc or x in nombre_archivo for x in ['demanda', 'denuncia']):
                document_texts['demandas'].append(texto)
            elif any(x in tipo_doc or x in nombre_archivo for x in ['sentencia', 'fallo']):
                document_texts['sentencias'].append(texto)
            elif any(x in tipo_doc or x in nombre_archivo for x in ['resolución', 'auto', 'providencia']):
                document_texts['resoluciones'].append(texto)
            elif any(x in tipo_doc or x in nombre_archivo for x in ['prueba', 'testimonio', 'pericia']):
                document_texts['pruebas'].append(texto)
            else:
                document_texts['otros'].append(texto)
        
        # 2. Crear contenido estructurado para el LLM
        structured_content = self._build_structured_content(document_texts)
        
        # 3. Generar resumen usando LLM
        try:
            summary = await self._call_llm_for_summary(structured_content)
            print(f"✅ Resumen generado por LLM: {len(summary)} caracteres")
            return summary
        except Exception as e:
            print(f"⚠️ Error en LLM, usando resumen extractivo: {str(e)}")
            # Fallback: resumen extractivo
            return self._generate_extractive_summary(document_texts)

    def _build_structured_content(self, document_texts: Dict[str, List[str]]) -> str:
        """Construye contenido estructurado para el LLM"""
        content_parts = []
        
        for doc_type, texts in document_texts.items():
            if texts:
                # Tomar una muestra representativa de cada tipo
                sample_texts = texts[:3]  # Primeros 3 documentos de cada tipo
                combined_text = " ".join(sample_texts)[:2000]  # Máximo 2K chars por tipo
                
                content_parts.append(f"=== {doc_type.upper()} ===\n{combined_text}")
        
        return "\n\n".join(content_parts)

    async def _call_llm_for_summary(self, content: str) -> str:
        """
        Llama al LLM Ollama para generar resumen semántico usando consulta_simple
        """
        # Prompt optimizado para casos legales
        prompt = f"""
Analiza el siguiente expediente judicial y genera un resumen semántico de máximo 400 palabras que capture:

1. HECHOS PRINCIPALES: ¿Qué pasó? ¿Cuál es la situación central del caso?
2. PARTES INVOLUCRADAS: ¿Quiénes son las partes? (demandante, demandado, etc.)
3. PRETENSIONES: ¿Qué se está pidiendo? ¿Cuál es el objetivo del proceso?
4. MATERIA LEGAL: ¿Qué tipo de caso es? (civil, penal, laboral, etc.)
5. CONCEPTOS CLAVE: Términos y conceptos jurídicos relevantes

IMPORTANTE: Enfócate en los aspectos semánticos y conceptuales que permitirían encontrar casos similares. No incluyas números de expediente, fechas específicas o nombres propios.

CONTENIDO DEL EXPEDIENTE:
{content}

RESUMEN SEMÁNTICO:
"""
        
        try:
            # Usar consulta_simple que sabemos que funciona
            result = await consulta_simple(prompt)
            
            # Extraer la respuesta del resultado
            if isinstance(result, dict) and "respuesta" in result:
                summary = result["respuesta"]
            elif isinstance(result, dict) and "error" in result:
                raise ValueError(f"Error en LLM: {result['error']}")
            else:
                summary = str(result)
            
            # Limpiar y validar el resumen
            summary = summary.strip()
            if len(summary) < 50:  # Muy corto
                raise ValueError("Resumen demasiado corto")
                
            return summary
            
        except Exception as e:
            print(f"Error en llamada a LLM: {str(e)}")
            raise

    def _generate_extractive_summary(self, document_texts: Dict[str, List[str]]) -> str:
        """
        Fallback: Genera resumen extractivo simple
        """
        print("📝 Generando resumen extractivo como fallback...")
        
        summary_parts = []
        
        for doc_type, texts in document_texts.items():
            if texts:
                # Tomar primeras oraciones de cada documento
                first_sentences = []
                for text in texts[:2]:  # Primeros 2 docs de cada tipo
                    sentences = text.split('. ')
                    if sentences:
                        first_sentences.append(sentences[0][:200])
                
                if first_sentences:
                    summary_parts.append(f"{doc_type}: {' | '.join(first_sentences)}")
        
        return " || ".join(summary_parts)[:1000]


# Instancia singleton del servicio
similarity_service = SimilarityService()
