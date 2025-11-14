"""
Utilidades de Validación y Formateo de Números de Expediente Judicial.

Este módulo proporciona funciones especializadas para validar, extraer componentes,
y formatear números de expediente del Poder Judicial de Costa Rica.

Formato de expediente costarricense:
    YY-NNNNNN-NNNN-XX o YYYY-NNNNNN-NNNN-XX
    
    Componentes:
        - YY/YYYY: Año (2 o 4 dígitos)
        - NNNNNN: Número consecutivo (6 dígitos)
        - NNNN: Código de oficina (4 dígitos)
        - XX: Código de materia (2 letras mayúsculas)
    
    Ejemplos válidos:
        - 02-000744-0164-CI (civil)
        - 2022-063557-6597-LA (laboral)
        - 01-003287-0166-FA (familia)
        - 2023-123456-7890-PE (penal)

Códigos de materia comunes:
    - CI: Civil
    - LA: Laboral
    - FA: Familia
    - PE: Penal
    - CO: Cobro judicial
    - CA: Contencioso administrativo
    - TP: Tránsito y pensiones

Funciones principales:
    - validar_expediente: Valida formato con regex estricto
    - extraer_componentes_expediente: Descompone en partes individuales
    - formatear_expediente: Normaliza formato (trim + uppercase)

Validación multi-nivel:
    1. Validación específica: Patrón exacto del Poder Judicial
    2. Validación genérica: Fallback para casos edge (17-20 caracteres)

Example:
    ```python
    from app.utils.expediente_validator import (
        validar_expediente, 
        extraer_componentes_expediente,
        formatear_expediente
    )
    
    # Validar formato
    es_valido = validar_expediente('02-000744-0164-CI')
    print(es_valido)  # True
    
    # Extraer componentes
    componentes = extraer_componentes_expediente('2022-063557-6597-LA')
    print(componentes)
    # {'año': '2022', 'consecutivo': '063557', 'oficina': '6597', 'materia': 'LA'}
    
    # Formatear (limpia y normaliza)
    formateado = formatear_expediente(' 02-000744-0164-ci ')
    print(formateado)  # '02-000744-0164-CI'
    ```

Note:
    Todas las funciones son tolerantes a espacios en blanco y mayúsculas/minúsculas.
    La validación genérica permite formatos ligeramente diferentes para casos edge.

See Also:
    - frontend/utils/validation/expedienteValidator.js: Validación en frontend
    - app.routes.archivos: Usa validación antes de servir archivos
    - app.services.expediente_service: Usa validación en creación
"""

import re
from typing import Optional, Dict, Any

def validar_expediente(numero_expediente: str) -> bool:
    """
    Valida el formato de un número de expediente del Poder Judicial de Costa Rica.
    
    Formatos aceptados:
    - YY-NNNNNN-NNNN-XX  (17 caracteres, ej: 02-000744-0164-CI)
    - YYYY-NNNNNN-NNNN-XX (19 caracteres, ej: 2022-063557-6597-LA)
    
    Donde:
    - YY/YYYY: Año (2 o 4 dígitos)
    - NNNNNN: 6 dígitos (consecutivo)
    - NNNN: 4 dígitos (oficina)
    - XX: 2 letras mayúsculas (código de materia: CI, LA, FA, etc.)
    
    Args:
        numero_expediente: Número de expediente a validar
        
    Returns:
        True si el formato es válido, False en caso contrario
    """
    if not numero_expediente:
        return False
    
    # Limpiar espacios
    numero_limpio = numero_expediente.strip()
    
    # Patrón específico del Poder Judicial: YY-NNNNNN-NNNN-XX o YYYY-NNNNNN-NNNN-XX
    # Acepta longitud de 17 (YY) o 19 (YYYY) caracteres
    patron_especifico = r'^\d{2,4}-\d{6}-\d{4}-[A-Z]{2}$'
    
    # Validación específica primero
    if re.match(patron_especifico, numero_limpio.upper()):
        return True
    
    # Fallback: validación genérica (17-20 caracteres alfanuméricos con guiones)
    # Para casos edge con formatos ligeramente diferentes
    patron_generico = r'^[A-Za-z0-9\-]{17,20}$'
    
    return bool(re.match(patron_generico, numero_limpio))


def extraer_componentes_expediente(numero_expediente: str) -> Optional[Dict[str, str]]:
    """
    Extrae los componentes de un número de expediente válido.
    """
    if not validar_expediente(numero_expediente):
        return None
    
    # Limpiar y dividir por guiones
    numero_limpio = numero_expediente.strip().upper()
    partes = numero_limpio.split('-')
    
    return {
        'año': partes[0],
        'consecutivo': partes[1],
        'oficina': partes[2],
        'materia': partes[3]
    }


def formatear_expediente(numero_expediente: str) -> Optional[str]:
    """
    Formatea un número de expediente limpiando espacios.
    """
    if not validar_expediente(numero_expediente):
        return None
    
    return numero_expediente.strip().upper()
