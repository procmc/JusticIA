import re
from typing import Optional, Dict, Any

def validar_expediente(numero_expediente: str) -> bool:
    """
    Valida el formato de un número de expediente del Poder Judicial.
    Formato: AA-CCCCCC-OOOO-MM
    
    Donde:
    - AA: Año (2 dígitos)
    - CCCCCC: Consecutivo (6 dígitos)
    - OOOO: Oficina (4 dígitos)
    - MM: Materia (2 caracteres alfabéticos)
    """
    if not numero_expediente:
        return False
    
    # Limpiar espacios y convertir a mayúsculas
    numero_limpio = numero_expediente.strip().upper()
    
    # Patrón regex: 2 dígitos - 6 dígitos - 4 dígitos - 2 letras
    patron = r'^\d{2}-\d{6}-\d{4}-[A-Z]{2}$'
    
    return bool(re.match(patron, numero_limpio))


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
