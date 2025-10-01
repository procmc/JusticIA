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
)

# Importar las tareas para registrarlas en el worker
# IMPORTANTE: Esta importación debe estar DESPUÉS de la configuración de celery_app
from app.services.ingesta.async_processing import celery_tasks