"""
Módulo para parseo y validación de respuestas del LLM.
Maneja la extracción de JSON y reparación de respuestas mal formadas.
"""

import logging
import json
import re
from app.schemas.similarity_schemas import ResumenIA

logger = logging.getLogger(__name__)


class ResponseParser:
    """Parsea y valida respuestas del LLM para generar objetos ResumenIA."""
    
    def parsear_respuesta_ia(self, respuesta_raw: str) -> ResumenIA:
        """
        Parsea la respuesta del LLM y la convierte en objeto ResumenIA.
        
        Args:
            respuesta_raw: Respuesta cruda del LLM
            
        Returns:
            Objeto ResumenIA con los datos parseados
        """
        logger.debug(f"Parseando respuesta de {len(respuesta_raw)} caracteres")
        
        try:
            # Paso 1: Limpiar la respuesta
            respuesta_limpia = self._limpiar_respuesta(respuesta_raw)
            
            # Paso 2: Intentar parsear con diferentes estrategias
            datos = self._extraer_json(respuesta_limpia)
            
            if datos:
                return self._crear_resumen_desde_datos(datos, respuesta_raw)
            else:
                logger.warning("No se pudo extraer JSON válido, usando fallback")
                return self._crear_resumen_fallback(respuesta_raw)
                
        except Exception as e:
            logger.error(f"Error parseando respuesta: {e}", exc_info=True)
            return self._crear_resumen_fallback(respuesta_raw)
    
    def _limpiar_respuesta(self, respuesta: str) -> str:
        """Limpia la respuesta eliminando markdown y espacios."""
        respuesta_limpia = respuesta.strip()
        
        # Eliminar markdown code blocks si existen
        if respuesta_limpia.startswith("```"):
            lineas = respuesta_limpia.split('\n')
            respuesta_limpia = '\n'.join(lineas[1:])
            if respuesta_limpia.endswith("```"):
                respuesta_limpia = respuesta_limpia[:-3]
        
        return respuesta_limpia.strip()
    
    def _extraer_json(self, respuesta: str) -> dict:
        """
        Extrae JSON de la respuesta usando múltiples estrategias.
        
        Returns:
            Diccionario con los datos o None si falla
        """
        # Estrategia 1: Parseo directo
        try:
            return json.loads(respuesta)
        except json.JSONDecodeError:
            pass
        
        # Estrategia 2: Buscar JSON completo con regex
        pattern_completo = r'\{\s*"resumen"\s*:.*?"conclusion"\s*:.*?\}'
        match = re.search(pattern_completo, respuesta, re.DOTALL)
        
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        
        # Estrategia 3: Buscar por llaves
        inicio = respuesta.find('{')
        fin = respuesta.rfind('}')
        
        if inicio != -1 and fin != -1 and fin > inicio:
            json_str = respuesta[inicio:fin+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Estrategia 4: Intentar reparar
                json_reparado = self._reparar_json(json_str)
                if json_reparado:
                    try:
                        return json.loads(json_reparado)
                    except json.JSONDecodeError:
                        pass
        
        return None
    
    def _reparar_json(self, json_str: str) -> str:
        """
        Intenta reparar JSON incompleto o mal formado.
        
        Returns:
            JSON reparado como string o string vacío si falla
        """
        try:
            # Si ya es válido, retornar
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            pass
        
        try:
            json_limpio = json_str.strip()
            
            # Asegurar que comience con {
            if not json_limpio.startswith('{'):
                inicio = json_limpio.find('{')
                if inicio != -1:
                    json_limpio = json_limpio[inicio:]
                else:
                    return ""
            
            # Eliminar texto después de la última llave
            ultima_llave = json_limpio.rfind('}')
            if ultima_llave != -1:
                json_limpio = json_limpio[:ultima_llave + 1]
            
            # Contar llaves
            abiertas = json_limpio.count('{')
            cerradas = json_limpio.count('}')
            
            # Si faltan llaves de cierre
            if abiertas > cerradas:
                if '"resumen"' not in json_limpio:
                    return ""
                
                # Eliminar comas finales mal puestas
                json_limpio = json_limpio.rstrip().rstrip(',').rstrip()
                
                # Cerrar strings sin cerrar
                comillas = json_limpio.count('"')
                if comillas % 2 != 0:
                    json_limpio += '"'
                
                # Cerrar arrays incompletos
                json_limpio = self._cerrar_arrays_incompletos(json_limpio)
                
                # Agregar campos faltantes
                json_limpio = self._agregar_campos_faltantes(json_limpio)
                
                # Cerrar llaves faltantes
                diferencia = json_limpio.count('{') - json_limpio.count('}')
                if diferencia > 0:
                    json_limpio += '}' * diferencia
            
            # Validar el JSON reparado
            json.loads(json_limpio)
            logger.info("JSON reparado exitosamente")
            return json_limpio
            
        except Exception as e:
            logger.error(f"Error reparando JSON: {e}")
            return ""
    
    def _cerrar_arrays_incompletos(self, json_str: str) -> str:
        """Cierra arrays que quedaron abiertos."""
        if '"palabras_clave"' in json_str:
            idx = json_str.find('"palabras_clave"')
            substr = json_str[idx:]
            if substr.count('[') > substr.count(']'):
                json_str += ']'
        
        if '"factores_similitud"' in json_str:
            idx = json_str.find('"factores_similitud"')
            substr = json_str[idx:]
            if substr.count('[') > substr.count(']'):
                json_str += ']'
        
        return json_str
    
    def _agregar_campos_faltantes(self, json_str: str) -> str:
        """Agrega campos requeridos si faltan."""
        if '"palabras_clave"' not in json_str:
            if not json_str.rstrip().endswith(','):
                json_str = json_str.rstrip() + ','
            json_str += ' "palabras_clave": ["Análisis Legal", "Expediente Judicial", "Procedimiento Legal"]'
        
        if '"factores_similitud"' not in json_str:
            if not json_str.rstrip().endswith(','):
                json_str = json_str.rstrip() + ','
            json_str += ' "factores_similitud": ["Contenido del expediente legal", "Documentación procesal oficial"]'
        
        if '"conclusion"' not in json_str:
            if not json_str.rstrip().endswith(','):
                json_str = json_str.rstrip() + ','
            json_str += ' "conclusion": "Se requiere análisis manual adicional"'
        
        return json_str
    
    def _crear_resumen_desde_datos(self, datos: dict, respuesta_raw: str) -> ResumenIA:
        """Crea objeto ResumenIA desde datos parseados con validación."""
        # Validar que tenga los campos mínimos
        if not datos.get("resumen"):
            logger.warning("JSON sin campo resumen, usando fallback")
            return self._crear_resumen_fallback(respuesta_raw)
        
        # Validar que el resumen sea válido
        resumen_texto = datos.get("resumen", "").strip()
        if len(resumen_texto) < 50 or resumen_texto.startswith('{"resumen"'):
            logger.warning(f"Resumen inválido ({len(resumen_texto)} chars), usando fallback")
            return self._crear_resumen_fallback(respuesta_raw)
        
        return ResumenIA(
            resumen=resumen_texto,
            palabras_clave=datos.get("palabras_clave") or [
                "Análisis Legal", "Expediente Judicial", "Procedimiento Legal"
            ],
            factores_similitud=datos.get("factores_similitud") or [
                "Contenido del expediente legal", 
                "Documentación procesal oficial"
            ],
            conclusion=datos.get("conclusion") or "Se requiere análisis manual adicional"
        )
    
    def _crear_resumen_fallback(self, respuesta_raw: str) -> ResumenIA:
        """Crea un resumen de fallback cuando no se puede parsear JSON."""
        return ResumenIA(
            resumen=respuesta_raw[:600] if respuesta_raw else "No se pudo generar resumen automático del expediente",
            palabras_clave=[
                "Análisis Legal", "Expediente Judicial", "Procedimiento Legal"
            ],
            factores_similitud=[
                "Contenido del expediente legal", 
                "Documentación procesal oficial"
            ],
            conclusion="Se requiere análisis manual adicional"
        )
