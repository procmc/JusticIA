"""
Servicio de seguimiento de progreso para tareas de larga duración.
Permite reportar progreso granular y manejar errores de forma robusta.
"""
import logging
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Estados posibles de una tarea."""
    PENDING = "pending"          # Esperando inicio
    INITIALIZING = "initializing" # Inicializando recursos
    PROCESSING = "processing"    # En proceso
    COMPLETED = "completed"      # Completado exitosamente
    FAILED = "failed"           # Falló con error
    CANCELLED = "cancelled"     # Cancelado por usuario

class ProgressTracker:
    """
    Tracker de progreso granular para tareas de procesamiento.
    Permite reportar progreso detallado en tiempo real.
    """
    
    def __init__(self, task_id: str, total_steps: int = 100):
        self.task_id = task_id
        self.total_steps = total_steps
        self.current_step = 0
        self.status = TaskStatus.PENDING
        self.message = "Tarea iniciada"
        self.start_time = datetime.now()
        self.end_time = None
        self.error_details = None
        self.progress_history = []
        self.metadata = {}
        
    def update_progress(self, step: int, message: str, metadata: Optional[Dict] = None):
        """Actualiza el progreso de la tarea."""
        self.current_step = min(step, self.total_steps)
        self.message = message
        self.status = TaskStatus.PROCESSING
        
        if metadata:
            self.metadata.update(metadata)
            
        # Guardar historial
        progress_entry = {
            "step": self.current_step,
            "percentage": self.get_percentage(),
            "message": message,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }
        self.progress_history.append(progress_entry)
        
        logger.info(f"[{self.task_id}] Progreso: {self.get_percentage():.1f}% - {message}")
        
    def set_status(self, status: TaskStatus, message: Optional[str] = None, error_details: Optional[str] = None):
        """Establece el estado de la tarea."""
        self.status = status
        if message:
            self.message = message
        if error_details:
            self.error_details = error_details
            
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            self.end_time = datetime.now()
            
        logger.info(f"[{self.task_id}] Estado: {status.value} - {self.message}")
        
    def mark_completed(self, message: str = "Tarea completada exitosamente"):
        """Marca la tarea como completada."""
        self.current_step = self.total_steps
        self.set_status(TaskStatus.COMPLETED, message)
        
    def mark_failed(self, error_message: str, error_details: Optional[str] = None):
        """Marca la tarea como fallida."""
        self.set_status(TaskStatus.FAILED, error_message, error_details)
        
    def mark_cancelled(self, message: str = "Tarea cancelada por el usuario"):
        """Marca la tarea como cancelada."""
        self.set_status(TaskStatus.CANCELLED, message)
        
    def is_cancelled(self) -> bool:
        """Verifica si la tarea ha sido cancelada."""
        return self.status == TaskStatus.CANCELLED
        
    def should_continue(self) -> bool:
        """Verifica si la tarea debe continuar procesando."""
        return self.status not in [TaskStatus.CANCELLED, TaskStatus.FAILED, TaskStatus.COMPLETED]
        
    def get_percentage(self) -> float:
        """Obtiene el porcentaje de progreso actual."""
        if self.total_steps == 0:
            return 0.0
        return (self.current_step / self.total_steps) * 100
        
    def get_elapsed_time(self) -> float:
        """Obtiene el tiempo transcurrido en segundos."""
        end_time = self.end_time or datetime.now()
        return (end_time - self.start_time).total_seconds()
        
    def get_status_dict(self) -> Dict[str, Any]:
        """Obtiene el estado completo como diccionario."""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "progress": self.get_percentage(),
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "message": self.message,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "elapsed_seconds": self.get_elapsed_time(),
            "error_details": self.error_details,
            "metadata": self.metadata,
            "is_complete": self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
        }

class ProgressManager:
    """
    Gestor global de progreso para múltiples tareas.
    Almacena y gestiona el progreso de todas las tareas activas.
    """
    
    def __init__(self):
        self.tasks: Dict[str, ProgressTracker] = {}
        self.completed_task_history: Dict[str, Dict] = {}  # 🆕 Historial de tareas completadas
        self.max_history_size = 100  # 🆕 Límite más conservador
        self.history_cleanup_threshold = 120  # 🆕 Limpiar cuando llegue a 120
        
    def create_tracker(self, task_id: str, total_steps: int = 100) -> ProgressTracker:
        """Crea un nuevo tracker de progreso."""
        tracker = ProgressTracker(task_id, total_steps)
        self.tasks[task_id] = tracker
        logger.info(f"Creado tracker para tarea {task_id} con {total_steps} pasos")
        return tracker
        
    def get_tracker(self, task_id: str) -> Optional[ProgressTracker]:
        """Obtiene un tracker existente."""
        return self.tasks.get(task_id)
        
    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el estado de una tarea."""
        # Primero buscar en tareas activas
        tracker = self.get_tracker(task_id)
        if tracker:
            return tracker.get_status_dict()
            
        # 🆕 Si no está activa, buscar en historial de completadas
        if task_id in self.completed_task_history:
            entry = self.completed_task_history[task_id]
            
            # Expandir datos compactos
            status_map = {'c': 'completed', 'f': 'failed', 'p': 'processing'}
            full_status = status_map.get(entry["s"], entry["s"])
            
            return {
                "task_id": task_id,
                "status": full_status,
                "progress": 100 if entry["ok"] else 0,
                "message": entry["msg"],
                "is_complete": True,
                "was_auto_cleaned": True,
                "auto_cleaned_at": datetime.fromtimestamp(entry["at"]).isoformat()
            }
            
        # Si no está ni activa ni en historial, realmente no existe
        return None
        
    def remove_completed_tasks(self, max_age_hours: int = 24):
        """Limpia tareas completadas antiguas."""
        current_time = datetime.now()
        to_remove = []
        
        for task_id, tracker in self.tasks.items():
            if (tracker.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] and 
                tracker.end_time and 
                (current_time - tracker.end_time).total_seconds() > max_age_hours * 3600):
                to_remove.append(task_id)
                
        for task_id in to_remove:
            del self.tasks[task_id]
            logger.info(f"Removida tarea completada: {task_id}")
            
    def schedule_task_cleanup(self, task_id: str, delay_minutes: int = 5):
        """
        Programa la eliminación automática de una tarea después de completarse.
        
        Args:
            task_id: ID de la tarea a limpiar
            delay_minutes: Minutos a esperar antes de limpiar
        """
        import threading
        import time
        
        def delayed_cleanup():
            time.sleep(delay_minutes * 60)  # Convertir minutos a segundos
            if task_id in self.tasks:
                tracker = self.tasks[task_id]
                if tracker.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    # 🆕 Guardar resumen MÍNIMO en historial antes de eliminar
                    self.completed_task_history[task_id] = {
                        "s": tracker.status.value[:1],  # Solo primera letra: 'c', 'f', etc.
                        "ok": tracker.status == TaskStatus.COMPLETED,  # Boolean más eficiente
                        "msg": tracker.message[:50] if tracker.message else "",  # Máximo 50 chars
                        "at": int(datetime.now().timestamp())  # Timestamp entero más eficiente
                    }
                    
                    # 🆕 Limpieza inteligente del historial
                    self._cleanup_history_if_needed()
                    
                    del self.tasks[task_id]
                    logger.info(f"Auto-limpieza: Removida tarea {task_id} después de {delay_minutes} minutos")
        
        # Ejecutar limpieza en hilo separado para no bloquear
        cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
        cleanup_thread.start()
        
    def _cleanup_history_if_needed(self):
        """
        Limpia el historial cuando excede el umbral para mantener memoria controlada.
        """
        if len(self.completed_task_history) >= self.history_cleanup_threshold:
            current_time = int(datetime.now().timestamp())
            
            # Ordenar por timestamp (más antiguos primero)
            sorted_items = sorted(
                self.completed_task_history.items(), 
                key=lambda x: x[1]["at"]
            )
            
            # Eliminar los más antiguos, dejando solo max_history_size
            items_to_remove = len(sorted_items) - self.max_history_size
            if items_to_remove > 0:
                for task_id, _ in sorted_items[:items_to_remove]:
                    del self.completed_task_history[task_id]
                
                logger.info(f"Limpieza de historial: Eliminadas {items_to_remove} entradas antiguas. "
                           f"Historial actual: {len(self.completed_task_history)} entradas")
                           
    def _cleanup_old_history_entries(self, max_age_hours: int = 1):
        """
        Limpia entradas del historial más antiguas que X horas.
        """
        current_time = int(datetime.now().timestamp())
        max_age_seconds = max_age_hours * 3600
        
        to_remove = []
        for task_id, entry in self.completed_task_history.items():
            if current_time - entry["at"] > max_age_seconds:
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.completed_task_history[task_id]
            
        if to_remove:
            logger.info(f"Limpieza por edad: Eliminadas {len(to_remove)} entradas antiguas del historial")
        
    def remove_task_immediately(self, task_id: str):
        """
        Elimina una tarea inmediatamente del almacén.
        
        Args:
            task_id: ID de la tarea a eliminar
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"Tarea eliminada inmediatamente: {task_id}")
            
    def get_task_count(self) -> Dict[str, int]:
        """
        Obtiene estadísticas de tareas en memoria.
        
        Returns:
            Diccionario con conteos por estado
        """
        stats = {
            "total_active": len(self.tasks),
            "total_in_history": len(self.completed_task_history),
            "history_limit": self.max_history_size,
            "history_usage_percent": round((len(self.completed_task_history) / self.max_history_size) * 100, 1),
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0
        }
        
        # Contar tareas activas
        for tracker in self.tasks.values():
            stats[tracker.status.value] += 1
            
        return stats
        
    def start_periodic_cleanup(self):
        """
        Inicia limpieza periódica del historial cada 30 minutos.
        """
        import threading
        import time
        
        def periodic_cleanup():
            while True:
                time.sleep(30 * 60)  # 30 minutos
                try:
                    self._cleanup_old_history_entries(max_age_hours=1)
                except Exception as e:
                    logger.error(f"Error en limpieza periódica: {e}")
        
        cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
        cleanup_thread.start()
        logger.info("Limpieza periódica del historial iniciada (cada 30 minutos)")

# Instancia global del gestor de progreso
progress_manager = ProgressManager()

# 🆕 Iniciar limpieza periódica al importar el módulo
progress_manager.start_periodic_cleanup()
