from celery import Celery
from app.config.config import REDIS_URL

celery_app = Celery(
    'justicia_backend',
    broker=f'{REDIS_URL}/0',
    backend=f'{REDIS_URL}/1',
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Configuración para tareas largas de procesamiento
    task_acks_late=True,  # Reconocer después de completar (permite retry en fallos)
    task_reject_on_worker_lost=False,  # SÍ reintentar si worker muere inesperadamente
    worker_prefetch_multiplier=1,  # Una tarea a la vez
    task_track_started=True,  # Trackear inicio
    
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