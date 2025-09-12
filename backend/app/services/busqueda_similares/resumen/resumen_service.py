"""
Servicio de generación de resúmenes semánticos.

Este módulo maneja la generación de resúmenes estructurados de expedientes
utilizando LLM y prompts externalizados.
"""

import logging
import os
from typing import Optional, Dict, Any
from app.llm.llm_service import get_llm

logger = logging.getLogger(__name__)


class ResumenSemanticoService:
    """Servicio para generar resúmenes semánticos estructurados."""
    
    def __init__(self):
        self.llm_service = None
        self.prompts_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "prompts")
    
    async def _get_llm_service(self):
        """Obtiene el servicio LLM de forma lazy."""
        if self.llm_service is None:
            self.llm_service = await get_llm()
        return self.llm_service
    
    def _load_prompt(self, prompt_name: str) -> str:
        """
        Carga un prompt desde archivo .md.
        
        Args:
            prompt_name: Nombre del archivo de prompt (sin extensión)
            
        Returns:
            Contenido del prompt como string
        """
        try:
            prompt_file = os.path.join(self.prompts_path, f"{prompt_name}.md")
            
            if os.path.exists(prompt_file):
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            else:
                logger.warning(f"Prompt {prompt_name}.md no encontrado")
                return self._get_fallback_prompt()
                
        except Exception as e:
            logger.error(f"Error cargando prompt {prompt_name}: {e}")
            return self._get_fallback_prompt()
    
    def _get_fallback_prompt(self) -> str:
        """
        Retorna un prompt de respaldo si no se puede cargar el archivo.
        
        Returns:
            Prompt básico de respaldo
        """
        try:
            return self._load_prompt("expediente_summary_fallback")
        except:
            return """
            Analiza el siguiente expediente legal y proporciona un resumen estructurado en 5 puntos principales:
            
            1. Tipo de caso
            2. Partes involucradas
            3. Hechos principales
            4. Estado procesal
            5. Elementos relevantes
            
            Expediente: {expedient_data}
            """
    
    async def generar_resumen_expediente(
        self,
        expedient_data: Dict[str, Any],
        usar_prompt_principal: bool = True
    ) -> str:
        """
        Genera un resumen semántico estructurado de un expediente.
        
        Args:
            expedient_data: Datos del expediente incluyendo metadatos y documentos
            usar_prompt_principal: Si usar el prompt principal o el de respaldo
            
        Returns:
            Resumen semántico estructurado
        """
        try:
            # Cargar prompt apropiado
            prompt_name = "expediente_summary" if usar_prompt_principal else "expediente_summary_fallback"
            prompt_template = self._load_prompt(prompt_name)
            
            # Preparar datos del expediente
            expedient_text = self._preparar_datos_expediente(expedient_data)
            
            # Formatear prompt con datos
            prompt = prompt_template.format(expedient_data=expedient_text)
            
            # Generar resumen usando LLM
            llm_service = await self._get_llm_service()
            response = await llm_service.ainvoke(prompt)
            
            # Extraer contenido de la respuesta
            resumen = getattr(response, "content", str(response))
            
            if not resumen or not resumen.strip():
                logger.warning("LLM retornó resumen vacío, intentando con prompt de respaldo")
                if usar_prompt_principal:
                    return await self.generar_resumen_expediente(expedient_data, False)
                else:
                    raise ValueError("No se pudo generar resumen")
            
            logger.info("Resumen semántico generado exitosamente")
            return resumen.strip()
            
        except Exception as e:
            logger.error(f"Error generando resumen semántico: {e}")
            raise
    
    def _preparar_datos_expediente(self, expedient_data: Dict[str, Any]) -> str:
        """
        Prepara los datos del expediente para el prompt.
        
        Args:
            expedient_data: Datos completos del expediente
            
        Returns:
            Texto formateado con los datos del expediente
        """
        try:
            lines = []
            
            # Información básica del expediente
            if expedient_data.get("expedient_id"):
                lines.append(f"ID Expediente: {expedient_data['expedient_id']}")
            
            if expedient_data.get("expedient_name"):
                lines.append(f"Nombre: {expedient_data['expedient_name']}")
            
            if expedient_data.get("created_date"):
                lines.append(f"Fecha Creación: {expedient_data['created_date']}")
            
            if expedient_data.get("status"):
                lines.append(f"Estado: {expedient_data['status']}")
            
            # Documentos del expediente
            documents = expedient_data.get("documents", [])
            if documents:
                lines.append("\nDocumentos:")
                for i, doc in enumerate(documents[:10], 1):  # Limitar a 10 documentos
                    doc_info = f"{i}. {doc.get('document_name', 'Sin nombre')}"
                    if doc.get('content_preview'):
                        preview = doc['content_preview'][:200] + "..." if len(doc['content_preview']) > 200 else doc['content_preview']
                        doc_info += f"\n   Contenido: {preview}"
                    lines.append(doc_info)
            
            return "\n".join(lines) if lines else "No hay datos disponibles del expediente"
            
        except Exception as e:
            logger.error(f"Error preparando datos del expediente: {e}")
            return "Error procesando datos del expediente"
    
    async def validar_resumen(self, resumen: str) -> bool:
        """
        Valida que el resumen generado tenga el formato esperado.
        
        Args:
            resumen: Resumen a validar
            
        Returns:
            True si el resumen es válido, False en caso contrario
        """
        try:
            if not resumen or len(resumen.strip()) < 50:
                return False
            
            # Verificar que contenga puntos estructurados
            lines = resumen.strip().split('\n')
            bullet_count = sum(1 for line in lines if line.strip().startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.')))
            
            return bullet_count >= 3  # Al menos 3 puntos estructurados
            
        except Exception as e:
            logger.error(f"Error validando resumen: {e}")
            return False
