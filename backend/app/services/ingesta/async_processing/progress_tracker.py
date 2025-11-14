"""
Sistema de tracking de progreso en Redis compartido entre procesos.

Proporciona tracking de progreso para tareas de procesamiento de archivos,
compartido entre backend (FastAPI) y celery-worker.

Características:
    * Almacenamiento Redis: TTL 3600s (1 hora)
    * Estados: PENDIENTE, PROCESANDO, COMPLETADO, FALLIDO, CANCELADO
    * Compartido: Accesible desde múltiples procesos
    * Progress: Porcentaje (0-100) con mensaje descriptivo
    * Cancelación: Flag persistent para verificación
    * ProgressManager: Gestor global de múltiples tareas

Estructura Redis:
    Key: "task_progress:{task_id}"
    Value: JSON {
        "status": "procesando",
        "progress": 45,
        "message": "Procesando archivo 3 de 10",
        "timestamp": "2024-01-15T10:30:00",
        "error": null
    }
    TTL: 3600 segundos

Estados (EstadoTarea):
    * PENDIENTE: Tarea creada pero no iniciada
    * PROCESANDO: En ejecución activa
    * COMPLETADO: Finalizada exitosamente
    * FALLIDO: Error durante procesamiento
    * CANCELADO: Cancelada por usuario

Example:
    >>> from app.services.ingesta.async_processing.progress_tracker import ProgressTracker, EstadoTarea
    >>> 
    >>> # Crear tracker
    >>> tracker = ProgressTracker(task_id="task_123")
    >>> 
    >>> # Actualizar progreso
    >>> tracker.update_progress(
    ...     progress=25,
    ...     message="Procesando archivo 1 de 4",
    ...     status=EstadoTarea.PROCESANDO
    ... )
    >>> 
    >>> # Verificar cancelación
    >>> if tracker.is_cancelled():
    ...     print("Tarea cancelada por usuario")
    >>> 
    >>> # Marcar completado
    >>> tracker.mark_completed(message="4 archivos procesados exitosamente")
    >>> 
    >>> # Obtener estado
    >>> data = tracker.get_progress()
    >>> print(f"Progreso: {data['progress']}%")

ProgressManager:
    >>> from app.services.ingesta.async_processing.progress_tracker import progress_manager
    >>> 
    >>> # Obtener tracker existente
    >>> tracker = progress_manager.get_tracker("task_123")
    >>> 
    >>> # Cancelar tarea
    >>> progress_manager.cancel_task("task_123")
    >>> 
    >>> # Limpiar tracker
    >>> progress_manager.cleanup_tracker("task_123")

Note:
    * Redis debe estar disponible (falla silenciosamente si no)
    * TTL automático previene acumulación de datos
    * ProgressManager es singleton (importar progress_manager)
    * Usado en document_processor y celery_tasks
    * Compatible con multiprocessing (Redis compartido)

Ver también:
    * app.services.ingesta.celery_tasks: Usa ProgressTracker
    * app.services.ingesta.document_processor: Actualiza progreso
    * app.db.redis_client: Cliente Redis singleton
    * app.routes.expedientes: Endpoints de progreso

Authors:
    JusticIA Team

Version:
    1.0.0 - Sistema de tracking en Redis
"""
import logging
import json
import redis
import os
from typing import Dict, Optional, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Obtener URL de Redis desde variable de entorno (compatible con Docker)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Conexión Redis compartida (mismo Redis que usa Celery)
redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True  # Decodificar strings automáticamente
)

class EstadoTarea(Enum):
    """Estados posibles de una tarea.
    
    Attributes:
        PENDIENTE: Tarea creada pero no iniciada.
        PROCESANDO: En ejecución activa.
        COMPLETADO: Finalizada exitosamente.
        FALLIDO: Error durante procesamiento.
        CANCELADO: Cancelada por usuario.
    """
    PENDIENTE = "pendiente"
    PROCESANDO = "procesando"
    COMPLETADO = "completado"
    FALLIDO = "fallido"
    CANCELADO = "cancelado"


class ProgressTracker:
    """
    Tracker de progreso granular para tareas de procesamiento.
    Almacena progreso en Redis para compartir entre procesos (backend y celery-worker).
    """
    
    def __init__(self, task_id: str, total_steps: int = 100):
        self.task_id = task_id
        self.total_steps = total_steps
        self.redis_key = f"task_progress:{task_id}"
        
        # Inicializar estado en Redis
        initial_state = {
            "task_id": task_id,
            "total_steps": total_steps,
            "current_step": 0,
            "status": EstadoTarea.PENDIENTE.value,
            "message": "Iniciando...",
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "error_details": None
        }
        redis_client.setex(
            self.redis_key,
            3600,  # TTL de 1 hora
            json.dumps(initial_state)
        )
        logger.info(f"[{self.task_id}] Tracker creado en Redis")
    
    def _get_state(self) -> Dict[str, Any]:
        """Obtiene el estado actual desde Redis."""
        data = redis_client.get(self.redis_key)
        if data:
            return json.loads(data)
        # Si no existe, retornar estado por defecto
        return {
            "task_id": self.task_id,
            "total_steps": self.total_steps,
            "current_step": 0,
            "status": EstadoTarea.PENDIENTE.value,
            "message": "Iniciando...",
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "error_details": None
        }
    
    def _save_state(self, state: Dict[str, Any]):
        """Guarda el estado en Redis."""
        redis_client.setex(
            self.redis_key,
            3600,  # TTL de 1 hora
            json.dumps(state)
        )
        
    def update_progress(self, step: int, message: str):
        """Actualiza el progreso de la tarea en Redis."""
        state = self._get_state()
        state["current_step"] = min(step, self.total_steps)
        state["message"] = message
        state["status"] = EstadoTarea.PROCESANDO.value
        self._save_state(state)
        
        progress = (state["current_step"] / self.total_steps) * 100
        logger.info(f"[{self.task_id}] Progreso: {progress:.1f}% - {message}")
        
    def mark_completed(self, message: str = "Tarea completada exitosamente"):
        """Marca la tarea como completada en Redis."""
        state = self._get_state()
        state["current_step"] = self.total_steps
        state["status"] = EstadoTarea.COMPLETADO.value
        state["message"] = message
        state["end_time"] = datetime.now().isoformat()
        self._save_state(state)
        logger.info(f"[{self.task_id}] Estado: {state['status']} - {message}")
        
    def mark_failed(self, error_message: str, error_details: Optional[str] = None):
        """Marca la tarea como fallida en Redis."""
        state = self._get_state()
        state["status"] = EstadoTarea.FALLIDO.value
        state["message"] = error_message
        state["error_details"] = error_details
        state["end_time"] = datetime.now().isoformat()
        self._save_state(state)
        logger.error(f"[{self.task_id}] Error: {error_message}")
        
    def mark_cancelled(self, message: str = "Tarea cancelada por el usuario"):
        """Marca la tarea como cancelada en Redis."""
        state = self._get_state()
        state["status"] = EstadoTarea.CANCELADO.value
        state["message"] = message
        state["end_time"] = datetime.now().isoformat()
        self._save_state(state)
        logger.info(f"[{self.task_id}] Cancelado: {message}")
        
    def get_percentage(self) -> float:
        """Obtiene el porcentaje de progreso actual desde Redis."""
        state = self._get_state()
        if state["total_steps"] == 0:
            return 0.0
        return (state["current_step"] / state["total_steps"]) * 100
        
    def get_elapsed_time(self) -> float:
        """Obtiene el tiempo transcurrido en segundos desde Redis."""
        state = self._get_state()
        start_time = datetime.fromisoformat(state["start_time"])
        if state["end_time"]:
            end_time = datetime.fromisoformat(state["end_time"])
        else:
            end_time = datetime.now()
        return (end_time - start_time).total_seconds()
        
    def is_finished(self) -> bool:
        """Verifica si la tarea ha finalizado."""
        state = self._get_state()
        return state["status"] in [EstadoTarea.COMPLETADO.value, EstadoTarea.FALLIDO.value, EstadoTarea.CANCELADO.value]
        
    def get_status_dict(self) -> Dict[str, Any]:
        """Obtiene el estado completo como diccionario desde Redis."""
        state = self._get_state()
        return {
            "task_id": state["task_id"],
            "status": state["status"],
            "progress": round((state["current_step"] / state["total_steps"]) * 100, 1),
            "message": state["message"],
            "error_details": state["error_details"],
            "elapsed_seconds": round(self.get_elapsed_time(), 2),
            "is_finished": self.is_finished()
        }


class ProgressManager:
    """
    Gestor global de progreso para múltiples tareas.
    Consulta Redis directamente para obtener estado compartido entre procesos.
    """
    
    def __init__(self, ttl_seconds: int = 10800):  # 3 horas por defecto
        """
        Inicializa el gestor de progreso.
        
        Args:
            ttl_seconds: Tiempo de vida (TTL) para los datos en Redis (por defecto 3 horas)
        """
        self.ttl_seconds = ttl_seconds
    
    def create_tracker(self, task_id: str, total_steps: int = 100) -> ProgressTracker:
        """Crea un nuevo tracker de progreso (se guarda en Redis)."""
        tracker = ProgressTracker(task_id, total_steps)
        logger.info(f"Creado tracker para tarea {task_id} con {total_steps} pasos")
        return tracker
        
    def get_tracker(self, task_id: str) -> Optional[ProgressTracker]:
        """
        Obtiene un tracker existente.
        Crea una instancia que leerá desde Redis.
        """
        redis_key = f"task_progress:{task_id}"
        if redis_client.exists(redis_key):
            # Crear instancia que apuntará a los datos en Redis
            tracker = ProgressTracker.__new__(ProgressTracker)
            tracker.task_id = task_id
            tracker.redis_key = redis_key
            # Obtener total_steps desde Redis
            state = json.loads(redis_client.get(redis_key))
            tracker.total_steps = state.get("total_steps", 100)
            return tracker
        return None
        
    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el estado de una tarea directamente desde Redis."""
        redis_key = f"task_progress:{task_id}"
        data = redis_client.get(redis_key)
        if data:
            state = json.loads(data)
            # Calcular progreso
            progress = 0.0
            if state.get("total_steps", 0) > 0:
                progress = (state.get("current_step", 0) / state["total_steps"]) * 100
            
            # Calcular tiempo transcurrido
            start_time = datetime.fromisoformat(state["start_time"])
            if state.get("end_time"):
                end_time = datetime.fromisoformat(state["end_time"])
            else:
                end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            
            return {
                "task_id": state["task_id"],
                "status": state["status"],
                "progress": round(progress, 1),
                "message": state["message"],
                "error_details": state.get("error_details"),
                "elapsed_seconds": round(elapsed, 2),
                "is_finished": state["status"] in ["completado", "fallido", "cancelado"]
            }
        return None
        
    def mark_task_cancelled(self, task_id: str, message: str = "Cancelado por el usuario"):
        """
        Marca una tarea como cancelada en Redis.
        Útil para cancelaciones externas (por endpoint o usuario).
        """
        redis_key = f"task_progress:{task_id}"
        data = redis_client.get(redis_key)
        
        if data:
            state = json.loads(data)
            state["status"] = EstadoTarea.CANCELADO.value
            state["message"] = message
            state["end_time"] = datetime.now().isoformat()
            
            # Guardar estado actualizado en Redis con TTL
            redis_client.setex(
                redis_key,
                self.ttl_seconds,
                json.dumps(state)
            )
            logger.info(f"Tarea {task_id} marcada como cancelada: {message}")
            return True
        else:
            logger.warning(f"No se pudo marcar como cancelada, tarea no encontrada: {task_id}")
            return False
    
    def remove_task(self, task_id: str):
        """Elimina una tarea de Redis."""
        redis_key = f"task_progress:{task_id}"
        redis_client.delete(redis_key)
        logger.info(f"Tarea eliminada de Redis: {task_id}")
            
    def schedule_task_cleanup(self, task_id: str, delay_minutes: int = 5):
        """
        Programa la eliminación automática de una tarea después de N minutos.
        Como usamos TTL en Redis, esto es opcional pero útil para limpieza temprana.
        """
        import threading
        import time
        
        def delayed_cleanup():
            time.sleep(delay_minutes * 60)
            self.remove_task(task_id)
        
        cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
        cleanup_thread.start()
        
    def get_task_count(self) -> Dict[str, int]:
        """
        Obtiene estadísticas de tareas activas en Redis.
        """
        # Buscar todas las claves de tareas
        keys = redis_client.keys("task_progress:*")
        
        stats = {
            "total_activas": len(keys),
            "pendiente": 0,
            "procesando": 0,
            "completado": 0,
            "fallido": 0,
            "cancelado": 0
        }
        
        for key in keys:
            data = redis_client.get(key)
            if data:
                state = json.loads(data)
                estado = state.get("status", "pendiente")
                if estado in stats:
                    stats[estado] += 1
            
        return stats


# Instancia global del gestor de progreso
progress_manager = ProgressManager()

