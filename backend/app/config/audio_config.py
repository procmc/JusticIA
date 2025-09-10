"""
Configuración simplificada para procesamiento de audio con faster-whisper.
Sistema secuencial optimizado para máximo rendimiento sin paralelismo.
"""
import os
import psutil
import torch
from typing import Dict, Any, Literal, cast
from dataclasses import dataclass

@dataclass
class AudioProcessingConfig:
    """Configuración para procesamiento de audio secuencial con faster-whisper."""
    
    # Configuración básica de chunks
    chunk_duration_minutes: int = 10
    chunk_overlap_seconds: int = 30
    max_file_size_mb: int = 500
    
    # Configuración de faster-whisper
    whisper_model: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"  # Optimización para faster-whisper
    num_workers: int = 4        # Threads internos de faster-whisper
    
    # Configuración de memoria optimizada para faster-whisper
    max_memory_usage_mb: int = 2048
    enable_chunking_threshold_mb: int = 300  # Aumentado de 100 a 300 MB
    
    # Configuración de desarrollo vs producción
    environment: Literal["development", "production"] = "development"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la configuración a diccionario."""
        return {
            'chunk_duration_minutes': self.chunk_duration_minutes,
            'chunk_overlap_seconds': self.chunk_overlap_seconds,
            'max_file_size_mb': self.max_file_size_mb,
            'whisper_model': self.whisper_model,
            'device': self.device,
            'compute_type': self.compute_type,
            'num_workers': self.num_workers,
            'max_memory_usage_mb': self.max_memory_usage_mb,
            'enable_chunking_threshold_mb': self.enable_chunking_threshold_mb,
            'environment': self.environment
        }

class AudioConfigManager:
    """Gestor de configuración adaptativa de audio basada en recursos del sistema."""
    
    @staticmethod
    def detect_system_resources() -> Dict[str, Any]:
        """Detecta los recursos disponibles del sistema."""
        # Memoria RAM
        memory = psutil.virtual_memory()
        total_ram_gb = memory.total / (1024**3)
        available_ram_gb = memory.available / (1024**3)
        
        # CPU
        cpu_count = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        
        # GPU (si está disponible)
        gpu_available = torch.cuda.is_available()
        gpu_count = torch.cuda.device_count() if gpu_available else 0
        gpu_memory_gb = 0
        
        if gpu_available and gpu_count > 0:
            gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        
        return {
            'total_ram_gb': total_ram_gb,
            'available_ram_gb': available_ram_gb,
            'cpu_count': cpu_count,
            'cpu_count_physical': cpu_count_physical,
            'gpu_available': gpu_available,
            'gpu_count': gpu_count,
            'gpu_memory_gb': gpu_memory_gb
        }
    
    @staticmethod
    def get_optimal_config() -> AudioProcessingConfig:
        """
        Genera configuración óptima para faster-whisper basada en recursos del sistema.
        Sistema secuencial optimizado sin paralelismo.
        """
        resources = AudioConfigManager.detect_system_resources()
        environment = os.getenv('ENVIRONMENT', 'development')
        
        # Configuración base
        config = AudioProcessingConfig()
        
        # Validar entorno
        if environment not in ['development', 'production']:
            environment = 'development'
        config.environment = cast(Literal['development', 'production'], environment)
        
        # === CONFIGURACIÓN POR ENTORNO ===
        
        if environment == "production":
            # PRODUCCIÓN: Mejor modelo y optimizaciones según recursos
            if resources['gpu_available'] and resources['gpu_memory_gb'] >= 8:
                # Producción con GPU grande
                config.device = "cuda"
                config.whisper_model = "large-v3"
                config.compute_type = "float16"  # Mejor calidad con GPU
                config.num_workers = min(8, resources['gpu_count'] * 2)
                config.chunk_duration_minutes = 15  # Chunks más grandes para eficiencia
                config.max_memory_usage_mb = int(resources['gpu_memory_gb'] * 1024 * 0.8)
            elif resources['gpu_available'] and resources['gpu_memory_gb'] >= 4:
                # Producción con GPU mediana
                config.device = "cuda"
                config.whisper_model = "medium"
                config.compute_type = "float16"
                config.num_workers = min(6, resources['gpu_count'] * 2)
                config.chunk_duration_minutes = 12
                config.max_memory_usage_mb = int(resources['gpu_memory_gb'] * 1024 * 0.7)
            else:
                # Producción solo CPU - optimizado para servidor
                config.device = "cpu"
                config.whisper_model = "medium" if resources['total_ram_gb'] >= 16 else "small"
                config.compute_type = "int8"  # Máxima eficiencia en CPU
                config.num_workers = min(resources['cpu_count_physical'], 8)
                config.chunk_duration_minutes = 10
                config.max_memory_usage_mb = int(resources['available_ram_gb'] * 1024 * 0.6)
                
            # Configuración agresiva para producción
            config.enable_chunking_threshold_mb = 25  # Chunk archivos más pequeños
            config.max_file_size_mb = 2000
            
        else:
            # DESARROLLO: faster-whisper base conservador
            if resources['gpu_available'] and resources['gpu_memory_gb'] >= 2:
                # Desarrollo con GPU
                config.device = "cuda"
                config.whisper_model = "base"
                config.compute_type = "float16"
                config.num_workers = 4
                config.chunk_duration_minutes = 10
                config.max_memory_usage_mb = int(resources['gpu_memory_gb'] * 1024 * 0.5)
            else:
                # Desarrollo solo CPU
                config.device = "cpu"
                config.whisper_model = "base"
                config.compute_type = "int8"  # Óptimo para CPU
                config.num_workers = min(resources['cpu_count_physical'], 4)
                config.chunk_duration_minutes = 10
                config.max_memory_usage_mb = int(resources['available_ram_gb'] * 1024 * 0.4)
            
            # Configuración conservadora para desarrollo
            config.enable_chunking_threshold_mb = 50
            config.max_file_size_mb = 500
        
        # === OVERRIDE CON VARIABLES DE ENTORNO ===
        
        config.chunk_duration_minutes = int(os.getenv('AUDIO_CHUNK_DURATION_MIN', config.chunk_duration_minutes))
        config.whisper_model = os.getenv('WHISPER_MODEL', config.whisper_model)
        config.device = os.getenv('WHISPER_DEVICE', config.device)
        
        # Nuevas configuraciones para faster-whisper
        if 'WHISPER_COMPUTE_TYPE' in os.environ:
            config.compute_type = os.getenv('WHISPER_COMPUTE_TYPE', config.compute_type)
        if 'WHISPER_NUM_WORKERS' in os.environ:
            config.num_workers = int(os.getenv('WHISPER_NUM_WORKERS', config.num_workers))
        
        return config
    
    @staticmethod
    def print_system_info():
        """Imprime información del sistema para debugging."""
        resources = AudioConfigManager.detect_system_resources()
        config = AudioConfigManager.get_optimal_config()
        
        print("=== CONFIGURACIÓN DE AUDIO (faster-whisper) ===")
        print(f"Entorno: {config.environment}")
        print(f"Modelo Whisper: {config.whisper_model}")
        print(f"Dispositivo: {config.device}")
        print(f"Tipo de cómputo: {config.compute_type}")
        print(f"Workers internos: {config.num_workers}")
        print(f"Duración chunk: {config.chunk_duration_minutes} min")
        print(f"Procesamiento: SECUENCIAL OPTIMIZADO (sin paralelismo)")
        
        print(f"\n=== RECURSOS DETECTADOS ===")
        print(f"RAM: {resources['available_ram_gb']:.1f}/{resources['total_ram_gb']:.1f} GB")
        print(f"CPU: {resources['cpu_count_physical']} cores físicos")
        if resources['gpu_available']:
            print(f"GPU: {resources['gpu_count']} dispositivos, {resources['gpu_memory_gb']:.1f} GB")
        else:
            print("GPU: No disponible")

# Instancia global de configuración
AUDIO_CONFIG = AudioConfigManager.get_optimal_config()

# Para debugging en desarrollo
if __name__ == "__main__":
    AudioConfigManager.print_system_info()
