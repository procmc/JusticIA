import re
from typing import Optional, Dict, Any

def validar_expediente(numero_expediente: str) -> bool:
    """
    Valida el formato de un número de expediente.
    Formato: entre 17 y 20 caracteres alfanuméricos (incluyendo guiones)
    """
    if not numero_expediente:
        return False
    
    # Limpiar espacios
    numero_limpio = numero_expediente.strip()
    
    # Patrón regex: entre 17 y 20 caracteres alfanuméricos (incluyendo guiones)
    patron = r'^[A-Za-z0-9\-]{17,20}$'
    
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
