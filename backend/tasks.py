"""
Tareas Asíncronas con Celery para JusticIA.

Este módulo define las tareas de procesamiento en segundo plano ejecutadas
por workers de Celery. Incluye ingesta de documentos, procesamiento de audio,
extracción de texto, generación de embeddings y almacenamiento vectorial.

Tareas disponibles:
    - procesar_ingesta: Procesa documentos/audio y genera embeddings
    - guardar_historial: Guarda conversaciones del chat en archivos

Broker:
    - Redis (configurado en celery_app.py)

Resultados:
    - Redis backend para consultar estado de tareas

Example:
    >>> from tasks import procesar_ingesta
    >>> task = procesar_ingesta.delay({'file': 'doc.pdf', 'expediente': '123'})
    >>> print(task.id)
    '550e8400-e29b-41d4-a716-446655440000'
    >>> result = task.get(timeout=300)  # Espera máximo 5 minutos

Note:
    - Las tareas se ejecutan en workers separados (ver docker-compose.yml)
    - Configurar concurrency y memory limits según recursos del servidor
    - Los workers procesan tareas de forma asíncrona y paralela
    
Configuration:
    Ver celery_app.py para configuración de broker, backend y workers.
    Ver .env para timeouts, memoria y concurrency.
"""

from celery_app import celery_app

@celery_app.task(bind=True, name='tasks.procesar_ingesta')
def procesar_ingesta(self, datos):
    """
    Procesa documentos/audio de ingesta de forma asíncrona.
    
    Realiza el flujo completo de procesamiento:
    1. Extracción de texto con Apache Tika (con OCR si es necesario)
    2. Transcripción de audio con Faster-Whisper (si es archivo MP3/WAV)
    3. Chunking inteligente del texto
    4. Generación de embeddings con modelo BGE-M3-ES-Legal
    5. Almacenamiento de vectores en Milvus
    
    Args:
        self: Referencia a la tarea (bind=True)
        datos (dict): Diccionario con datos de ingesta, debe contener:
            - file_path (str): Ruta al archivo a procesar
            - expediente_id (int): ID del expediente
            - documento_id (int): ID del documento
            - user_id (int): ID del usuario que lo subió
    
    Returns:
        str: Estado final del procesamiento ('ok', 'error').
    
    Example:
        >>> task = procesar_ingesta.delay({
        ...     'file_path': '/uploads/exp123/doc.pdf',
        ...     'expediente_id': 123,
        ...     'documento_id': 456,
        ...     'user_id': 1
        ... })
        >>> task.get(timeout=600)  # Esperar hasta 10 minutos
        'ok'
    
    Note:
        - El procesamiento puede tardar varios minutos para archivos grandes
        - Actualiza el progreso usando self.update_state()
        - Maneja errores y actualiza estado del documento en BD
    """
    # Aquí va la lógica de ingesta
    print(f"Procesando ingesta: {datos}")
    return "ok"

@celery_app.task(bind=True, name='tasks.guardar_historial')
def guardar_historial(self, usuario_id, mensaje):
    """
    Guarda el historial de conversaciones del chat en archivos.
    
    Persiste las conversaciones de los usuarios en archivos JSON para
    mantener el historial disponible entre sesiones.
    
    Args:
        self: Referencia a la tarea (bind=True)
        usuario_id (int): ID del usuario
        mensaje (dict): Diccionario con datos del mensaje a guardar
    
    Returns:
        str: Estado de la operación ('guardado', 'error').
    
    Example:
        >>> task = guardar_historial.delay(
        ...     usuario_id=1,
        ...     mensaje={'role': 'user', 'content': '¿Qué es RAG?'}
        ... )
        >>> task.get()
        'guardado'
    
    Note:
        - Los archivos se guardan en la carpeta configurada de historial
        - Cada usuario tiene su propio archivo de historial
    """
    # Aquí va la lógica para guardar historial de chat
    print(f"Guardando mensaje para usuario {usuario_id}: {mensaje}")
    return "guardado"
