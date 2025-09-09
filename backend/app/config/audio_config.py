"""
Configuración para procesamiento de audio y transcripción con Whisper.
Sistema totalmente parametrizado para adaptarse a recursos del servidor.
"""
import os
import psutil
import torch
from typing import Dict, Any, Literal, cast
from dataclasses import dataclass

@dataclass
class AudioProcessingConfig:
    """Configuración para procesamiento de audio."""
    
    # Configuración básica de chunks
    chunk_duration_minutes: int = 10
    chunk_overlap_seconds: int = 30
    max_file_size_mb: int = 500
    
    # Configuración de paralelización
    max_parallel_chunks: int = 1
    enable_parallel_processing: bool = False
    
    # Configuración de Whisper
    whisper_model: str = "base"
    device: str = "cpu"
    
    # Configuración de memoria
    max_memory_usage_mb: int = 1024
    enable_chunking_threshold_mb: int = 100
    
    # Configuración de desarrollo vs producción
    environment: Literal["development", "production"] = "development"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la configuración a diccionario."""
        return {
            'chunk_duration_minutes': self.chunk_duration_minutes,
            'chunk_overlap_seconds': self.chunk_overlap_seconds,
            'max_file_size_mb': self.max_file_size_mb,
            'max_parallel_chunks': self.max_parallel_chunks,
            'enable_parallel_processing': self.enable_parallel_processing,
            'whisper_model': self.whisper_model,
            'device': self.device,
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
        Genera configuración óptima basada en recursos del sistema.
        Solo 2 entornos: development y production.
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
            # PRODUCCIÓN: Máximos recursos disponibles
            if resources['gpu_available'] and resources['gpu_memory_gb'] >= 4:
                # Producción con GPU
                config.device = "cuda"
                config.whisper_model = "large" if resources['gpu_memory_gb'] >= 10 else "medium"
                config.max_parallel_chunks = min(resources['gpu_count'] * 4, 16)
                config.enable_parallel_processing = True
                config.chunk_duration_minutes = 3  # Chunks pequeños para máxima paralelización
                config.max_memory_usage_mb = int(resources['gpu_memory_gb'] * 1024 * 0.8)
            else:
                # Producción solo CPU
                config.device = "cpu"
                config.whisper_model = "medium" if resources['total_ram_gb'] >= 16 else "small"
                config.max_parallel_chunks = min(resources['cpu_count_physical'], 8)
                config.enable_parallel_processing = True
                config.chunk_duration_minutes = 5
                config.max_memory_usage_mb = int(resources['available_ram_gb'] * 1024 * 0.6)
                
            # Configuración agresiva para producción
            config.enable_chunking_threshold_mb = 50
            config.max_file_size_mb = 2000
            
        else:
            # DESARROLLO: Whisper BASE mínimo, GPU si está disponible
            # Habilitar paralelismo porque el cuello de botella es RAM, no CPU
            if resources['gpu_available'] and resources['gpu_memory_gb'] >= 2:
                # Desarrollo con GPU
                config.device = "cuda"
                config.whisper_model = "base"  # BASE como mínimo
                config.max_parallel_chunks = 2
                config.enable_parallel_processing = True
                config.chunk_duration_minutes = 10
                config.max_memory_usage_mb = int(resources['gpu_memory_gb'] * 1024 * 0.5)
            else:
                # Desarrollo solo CPU - PARALELISMO HABILITADO para i5+
                config.device = "cpu"
                config.whisper_model = "base"  # BASE como mínimo
                config.max_parallel_chunks = 2  # Aprovechar múltiples cores
                config.enable_parallel_processing = True  # Habilitado para desarrollo
                config.chunk_duration_minutes = 10  # Chunks medianos para balance RAM/CPU
                config.max_memory_usage_mb = int(resources['available_ram_gb'] * 1024 * 0.4)
            
            # Configuración conservadora para desarrollo
            config.enable_chunking_threshold_mb = 50
            config.max_file_size_mb = 500
        
        # === OVERRIDE CON VARIABLES DE ENTORNO ===
        
        config.chunk_duration_minutes = int(os.getenv('AUDIO_CHUNK_DURATION_MIN', config.chunk_duration_minutes))
        config.max_parallel_chunks = int(os.getenv('AUDIO_MAX_PARALLEL_CHUNKS', config.max_parallel_chunks))
        config.whisper_model = os.getenv('WHISPER_MODEL', config.whisper_model)
        config.device = os.getenv('WHISPER_DEVICE', config.device)
        config.enable_parallel_processing = os.getenv('ENABLE_PARALLEL_AUDIO', str(config.enable_parallel_processing)).lower() == 'true'
        
        return config
    
    @staticmethod
    def print_system_info():
        """Imprime información del sistema para debugging."""
        resources = AudioConfigManager.detect_system_resources()
        config = AudioConfigManager.get_optimal_config()
        
        print("=== CONFIGURACIÓN DE AUDIO ===")
        print(f"Entorno: {config.environment}")
        print(f"Modelo Whisper: {config.whisper_model}")
        print(f"Dispositivo: {config.device}")
        print(f"Chunks paralelos: {config.max_parallel_chunks}")
        print(f"Procesamiento paralelo: {config.enable_parallel_processing}")
        print(f"Duración chunk: {config.chunk_duration_minutes} min")
        
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
