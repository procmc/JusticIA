"""
Constantes para tipos de acción de bitácora.
Estos IDs corresponden a los valores en la migración consolidada 001_base_completa.py
"""


class TiposAccion:
    """IDs de tipos de acción según catálogo en base de datos"""
    
    # Búsqueda y análisis
    BUSQUEDA_SIMILARES = 1            # Búsqueda de casos similares
    
    # Ingesta y procesamiento
    CARGA_DOCUMENTOS = 2              # Carga e ingesta de documentos
    
    # Autenticación y sesiones
    LOGIN = 3                         # Inicio de sesión
    LOGOUT = 4                        # Cierre de sesión
    CAMBIO_CONTRASENA = 5             # Cambio de contraseña
    RECUPERACION_CONTRASENA = 6       # Recuperación de contraseña
    
    # Administración de usuarios
    CREAR_USUARIO = 7                 # Creación de usuario
    EDITAR_USUARIO = 8                # Edición de usuario
    CONSULTAR_USUARIOS = 9            # Listar usuarios
    
    # Acceso a documentos (GDPR crítico)
    DESCARGAR_ARCHIVO = 10            # Descarga/visualización de archivos
    LISTAR_ARCHIVOS = 11              # Listar archivos de expediente
    
    # RAG y consultas inteligentes (CRÍTICO)
    CONSULTA_RAG = 12                 # Consultas conversacionales IA
    GENERAR_RESUMEN = 13              # Generación de resúmenes IA
    
    # Auditoría
    CONSULTAR_BITACORA = 14           # Consulta de auditoría
    EXPORTAR_BITACORA = 15            # Exportación de auditoría


# Mapeo de descripciones para logging
DESCRIPCIONES_TIPOS_ACCION = {
    TiposAccion.BUSQUEDA_SIMILARES: "Búsqueda de Casos Similares",
    TiposAccion.CARGA_DOCUMENTOS: "Carga de Documentos",
    TiposAccion.LOGIN: "Login",
    TiposAccion.LOGOUT: "Logout",
    TiposAccion.CAMBIO_CONTRASENA: "Cambio de Contraseña",
    TiposAccion.RECUPERACION_CONTRASENA: "Recuperación de Contraseña",
    TiposAccion.CREAR_USUARIO: "Crear Usuario",
    TiposAccion.EDITAR_USUARIO: "Editar Usuario",
    TiposAccion.CONSULTAR_USUARIOS: "Consultar Usuarios",
    TiposAccion.DESCARGAR_ARCHIVO: "Descargar Archivo",
    TiposAccion.LISTAR_ARCHIVOS: "Listar Archivos",
    TiposAccion.CONSULTA_RAG: "Consulta RAG",
    TiposAccion.GENERAR_RESUMEN: "Generar Resumen",
    TiposAccion.CONSULTAR_BITACORA: "Consultar Bitácora",
    TiposAccion.EXPORTAR_BITACORA: "Exportar Bitácora",
}
