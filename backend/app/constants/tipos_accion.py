"""
Constantes para tipos de acción de bitácora.
Estos IDs corresponden a los valores insertados en la migración fd0682745253_insert_datos_iniciales.py
"""


class TiposAccion:
    """IDs de tipos de acción según catálogo en base de datos"""
    
    # Consultas y búsquedas
    CONSULTA = 1
    CARGA_DOCUMENTOS = 2
    BUSQUEDA_SIMILARES = 3
    
    # Autenticación
    LOGIN = 4
    
    # Administración de usuarios
    CREAR_USUARIO = 5
    EDITAR_USUARIO = 6
    
    # Auditoría
    CONSULTAR_BITACORA = 7
    EXPORTAR_BITACORA = 8


# Mapeo de descripciones para logging
DESCRIPCIONES_TIPOS_ACCION = {
    TiposAccion.CONSULTA: "Consulta",
    TiposAccion.CARGA_DOCUMENTOS: "Carga de Documentos",
    TiposAccion.BUSQUEDA_SIMILARES: "Búsqueda de Casos Similares",
    TiposAccion.LOGIN: "Inicio de Sesión",
    TiposAccion.CREAR_USUARIO: "Creación de Usuario",
    TiposAccion.EDITAR_USUARIO: "Edición de Usuario",
    TiposAccion.CONSULTAR_BITACORA: "Consulta de Bitácora",
    TiposAccion.EXPORTAR_BITACORA: "Exportación de Bitácora",
}
