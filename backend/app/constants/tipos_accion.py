"""
Catálogo de Tipos de Acción para Sistema de Auditoría (Bitácora).

Este módulo define constantes para los tipos de acciones auditables del sistema JusticIA.
Los IDs corresponden exactamente a los valores definidos en la tabla T_Tipo_accion de la BD.

Propósito:
    - Centralizar IDs de tipos de acción para evitar magic numbers
    - Documentar cada tipo de evento auditable
    - Facilitar mantenimiento y refactorización
    - Proporcionar descripciones legibles para logging

Categorías de acciones:
    1. Autenticación: Login, logout, cambios de contraseña
    2. Usuarios: Crear, editar, consultar usuarios
    3. Documentos: Carga, descarga, listado de archivos
    4. IA/RAG: Consultas conversacionales, generación de resúmenes, búsqueda similares
    5. Auditoría: Consultas y exportaciones de bitácora

Criticidad para GDPR y auditoría legal:
    - CONSULTA_RAG (12): Rastrea acceso a información sensible
    - DESCARGAR_ARCHIVO (10): Audita visualización de documentos judiciales
    - LISTAR_ARCHIVOS (11): Registra exploración de expedientes
    - BUSQUEDA_SIMILARES (1): Audita búsquedas de casos judiciales

Sincronización con BD:
    Los IDs deben coincidir con:
        - Migración: alembic/versions/001_base_completa.py
        - Tabla: T_Tipo_accion (CN_Id_tipo_accion)
    
    IMPORTANTE: No cambiar IDs sin actualizar la migración.

Example:
    ```python
    from app.constants.tipos_accion import TiposAccion, DESCRIPCIONES_TIPOS_ACCION
    from app.services.bitacora.bitacora_service import bitacora_service
    
    # Registrar login exitoso
    await bitacora_service.registrar(
        db=db,
        usuario_id='123456789',
        tipo_accion_id=TiposAccion.LOGIN,
        texto='Login exitoso desde IP: 192.168.1.100'
    )
    
    # Obtener descripción legible
    descripcion = DESCRIPCIONES_TIPOS_ACCION[TiposAccion.CONSULTA_RAG]
    print(descripcion)  # 'Consulta RAG'
    ```

Note:
    Agregar nuevos tipos requiere:
        1. Crear migración Alembic para insertar en T_Tipo_accion
        2. Agregar constante aquí con el mismo ID
        3. Agregar descripción en DESCRIPCIONES_TIPOS_ACCION

See Also:
    - app.services.bitacora.bitacora_service: Servicio de registro de eventos
    - app.routes.bitacora: Endpoints de consulta de auditoría
    - alembic/versions/001_base_completa.py: Definición de tabla T_Tipo_accion
"""


class TiposAccion:
    """
    IDs de tipos de acción auditables en el sistema.
    
    Cada constante corresponde a un registro en la tabla T_Tipo_accion.
    Los IDs están definidos en la migración 001_base_completa.py.
    """
    
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
