"""
Configuración de Celery para tareas asíncronas de JusticIA.

Este módulo configura la instancia de Celery para procesar tareas en
segundo plano, especialmente tareas largas de procesamiento de documentos
y audio que pueden tardar varios minutos.

Arquitectura:
    * Broker: Redis (DB 0) - Cola de tareas pendientes
    * Backend: Redis (DB 1) - Almacenamiento de resultados
    * Workers: Procesos separados que ejecutan tareas
    * Tasks: Definidas en app.services.ingesta.async_processing.celery_tasks

Características de configuración:
    * Tareas largas: Hasta 2 horas de ejecución
    * ACK tardío: Reconocimiento después de completar (permite retry)
    * Worker prefetch: 1 tarea a la vez (evita memory overflow)
    * Tracking: Estado de inicio/progreso/finalización
    * Timeouts: Configurados para tareas de procesamiento pesado

Tareas soportadas:
    * Procesamiento de PDF con OCR (Apache Tika + Tesseract)
    * Transcripción de audio (Faster-Whisper)
    * Generación de embeddings (BGE-M3)
    * Almacenamiento vectorial (Milvus)

Ejecución de workers:
    Desarrollo:
        celery -A celery_app worker --loglevel=info --concurrency=2
    
    Producción:
        celery -A celery_app worker --loglevel=info --concurrency=4 \
               --max-memory-per-child=2000000  # 2GB por worker

Monitoreo:
    # Ver tareas activas
    celery -A celery_app inspect active
    
    # Ver estado de worker
    celery -A celery_app inspect stats
    
    # Flower (dashboard web)
    celery -A celery_app flower --port=5555

Variables de entorno:
    * REDIS_URL: URL de conexión a Redis (default: redis://localhost:6379)

Timeouts configurados:
    * task_time_limit: 7200s (2h) - Hard limit
    * task_soft_time_limit: 6600s (1h50m) - Soft limit (permite limpieza)
    * visibility_timeout: 7200s - Tiempo máximo esperando ACK
    * socket_timeout: 300s - Timeout de conexión

Example:
    >>> # En otro módulo, usar las tareas
    >>> from celery_app import celery_app
    >>> 
    >>> @celery_app.task
    >>> def mi_tarea(datos):
    ...     return procesar(datos)
    >>> 
    >>> # Ejecutar tarea asíncrona
    >>> task = mi_tarea.delay({'file': 'doc.pdf'})
    >>> print(task.id)  # UUID de la tarea
    >>> result = task.get(timeout=600)  # Esperar resultado

Note:
    * Los workers deben iniciarse DESPUÉS de que Redis esté corriendo
    * Configurar max-memory-per-child para evitar memory leaks
    * Usar visibility_timeout >= task_time_limit
    * Las tareas DEBEN ser idempotentes para soportar retries

Ver también:
    * tasks.py: Tareas registradas
    * app.services.ingesta.async_processing.celery_tasks: Tareas de ingesta
    * docker-compose.yml: Configuración de workers en Docker

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    1.0.0
"""
from celery import Celery
from app.config.config import REDIS_URL

# Crear instancia de Celery
celery_app = Celery(
    'justicia_backend',
    broker=f'{REDIS_URL}/0',  # Redis DB 0 para cola de tareas
    backend=f'{REDIS_URL}/1',  # Redis DB 1 para resultados
)

# Configuración optimizada para tareas largas de procesamiento
celery_app.conf.update(
    # Serialización JSON para compatibilidad y seguridad
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Configuración para tareas largas de procesamiento
    task_acks_late=True,  # Reconocer después de completar (permite retry en fallos)
    task_reject_on_worker_lost=False,  # SÍ reintentar si worker muere inesperadamente
    worker_prefetch_multiplier=1,  # Una tarea a la vez (evita memory overflow)
    task_track_started=True,  # Trackear inicio de ejecución
    
    # CLAVE: Aumentar timeout de ACK para tareas largas (2 horas)
    broker_transport_options={
        'visibility_timeout': 7200,  # 2 horas - tiempo máximo esperando ACK
        'socket_timeout': 300,  # 5 minutos - timeout de conexión socket
        'socket_keepalive': True,  # Mantener conexión viva
    },
    
    # Configuración de resultados
    result_backend_transport_options={
        'socket_timeout': 300,
        'socket_keepalive': True,
    },
    
    # Timeouts de tarea
    task_time_limit=7200,  # 2 horas hard limit
    task_soft_time_limit=6600,  # 1h50m soft limit
)

# Importar las tareas para registrarlas en el worker
# IMPORTANTE: Esta importación debe estar DESPUÉS de la configuración de celery_app
from app.services.ingesta.async_processing import celery_tasks