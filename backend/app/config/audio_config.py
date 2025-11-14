"""
Configuración adaptativa para procesamiento de audio con Faster-Whisper.

Este módulo gestiona la configuración del sistema de transcripción de audio
utilizando Faster-Whisper (implementación optimizada de OpenAI Whisper).
Detecta automáticamente los recursos del sistema (RAM, CPU, GPU) y ajusta
los parámetros para maximizar rendimiento sin comprometer estabilidad.

Características principales:
    * Detección automática de recursos del sistema
    * Configuración diferenciada entre desarrollo y producción
    * Optimización automática según GPU/CPU disponible
    * Sistema secuencial sin paralelismo para máxima estabilidad
    * Soporte para chunks de archivos grandes (>300 MB)

Modelos Whisper soportados:
    * base: ~75M parámetros, rápido, buena precisión general
    * small: ~244M parámetros, mejor precisión
    * medium: ~769M parámetros, alta precisión
    * large-v3: ~1550M parámetros, máxima precisión (requiere GPU)

Tipos de cómputo Faster-Whisper:
    * int8: Óptimo para CPU, menor consumo de RAM
    * float16: Óptimo para GPU, mejor calidad

Variables de entorno disponibles:
    * ENVIRONMENT: "development" | "production"
    * AUDIO_CHUNK_DURATION_MIN: Duración de chunks en minutos
    * WHISPER_MODEL: Modelo de Whisper a usar
    * WHISPER_DEVICE: "cpu" | "cuda"
    * WHISPER_COMPUTE_TYPE: "int8" | "float16"
    * WHISPER_NUM_WORKERS: Threads internos de Faster-Whisper

Arquitectura:
    * AudioProcessingConfig: Dataclass con parámetros de configuración
    * AudioConfigManager: Gestor estático que detecta recursos y genera config óptima
    * AUDIO_CONFIG: Instancia global singleton de configuración

Example:
    >>> from app.config.audio_config import AUDIO_CONFIG
    >>> print(f"Modelo: {AUDIO_CONFIG.whisper_model}")
    Modelo: base
    >>> print(f"Device: {AUDIO_CONFIG.device}")
    Device: cpu
    >>> AudioConfigManager.print_system_info()
    === CONFIGURACIÓN DE AUDIO (faster-whisper) ===
    Entorno: development
    Modelo Whisper: base
    ...

Note:
    * En producción con GPU se usa modelo large-v3 o medium
    * En desarrollo siempre se usa modelo base conservador
    * Sistema secuencial (sin paralelismo) evita condiciones de carrera
    * Faster-Whisper es ~4x más rápido que Whisper original

Ver también:
    * tasks.process_audio_task: Tarea Celery que usa esta configuración
    * app.services.audio_service: Servicio de transcripción de audio

Authors:
    JusticIA Team

Version:
    1.0.0 - Migrado de Whisper original a Faster-Whisper
"""
import os
import psutil
import torch
from typing import Dict, Any, Literal, cast
from dataclasses import dataclass

@dataclass
class AudioProcessingConfig:
    """
    Configuración para procesamiento de audio secuencial con Faster-Whisper.
    
    Esta dataclass encapsula todos los parámetros de configuración para el
    procesamiento de audio, incluyendo chunking, modelo Whisper, dispositivo,
    y límites de memoria.
    
    Attributes:
        chunk_duration_minutes (int): Duración de cada chunk de audio en minutos.
            Default 10 minutos. Usado para dividir archivos grandes.
        chunk_overlap_seconds (int): Solapamiento entre chunks consecutivos en segundos.
            Default 30 segundos. Evita pérdida de contexto en los límites.
        max_file_size_mb (int): Tamaño máximo de archivo de audio soportado en MB.
            Default 500 MB en desarrollo, 2000 MB en producción.
        whisper_model (str): Modelo de Whisper a usar ("base", "small", "medium", "large-v3").
            Default "base".
        device (str): Dispositivo de cómputo ("cpu" o "cuda").
            Auto-detectado según disponibilidad de GPU.
        compute_type (str): Tipo de cómputo para Faster-Whisper ("int8" o "float16").
            "int8" óptimo para CPU, "float16" óptimo para GPU.
        num_workers (int): Threads internos de Faster-Whisper para carga de modelo.
            Default 4, ajustado según cores disponibles.
        max_memory_usage_mb (int): Límite de memoria RAM/VRAM en MB.
            Auto-calculado según recursos disponibles.
        enable_chunking_threshold_mb (int): Tamaño de archivo en MB que activa chunking.
            Default 300 MB en desarrollo, 25 MB en producción.
        environment (Literal): Entorno de ejecución ("development" o "production").
            Afecta valores por defecto de otros parámetros.
    
    Example:
        >>> config = AudioProcessingConfig(
        ...     whisper_model="medium",
        ...     device="cuda",
        ...     compute_type="float16"
        ... )
        >>> config.chunk_duration_minutes
        10
    """
    
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
        """
        Convierte la configuración a diccionario.
        
        Útil para serialización y logging de configuración.
        
        Returns:
            Dict[str, Any]: Diccionario con todos los parámetros de configuración.
        
        Example:
            >>> config = AudioProcessingConfig()
            >>> config_dict = config.to_dict()
            >>> config_dict["whisper_model"]
            'base'
        """
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
    """
    Gestor de configuración adaptativa de audio basada en recursos del sistema.
    
    Esta clase gestiona la detección automática de recursos del sistema (RAM, CPU, GPU)
    y genera configuraciones óptimas de audio según el entorno de ejecución.
    
    Todos los métodos son estáticos, no requiere instanciación.
    
    Example:
        >>> resources = AudioConfigManager.detect_system_resources()
        >>> print(resources["total_ram_gb"])
        16.0
        >>> config = AudioConfigManager.get_optimal_config()
        >>> print(config.whisper_model)
        'base'
    """
    
    @staticmethod
    def detect_system_resources() -> Dict[str, Any]:
        """
        Detecta los recursos disponibles del sistema.
        
        Utiliza psutil para RAM/CPU y torch para GPU. Detecta tanto recursos
        físicos como lógicos (hyperthreading).
        
        Returns:
            Dict[str, Any]: Diccionario con información de recursos:
                - total_ram_gb (float): RAM total en GB
                - available_ram_gb (float): RAM disponible en GB
                - cpu_count (int): Cores lógicos (con hyperthreading)
                - cpu_count_physical (int): Cores físicos
                - gpu_available (bool): Si hay GPU CUDA disponible
                - gpu_count (int): Cantidad de GPUs CUDA
                - gpu_memory_gb (float): VRAM de GPU principal en GB
        
        Example:
            >>> resources = AudioConfigManager.detect_system_resources()
            >>> if resources["gpu_available"]:
            ...     print(f"GPU: {resources['gpu_memory_gb']} GB")
            GPU: 8.0 GB
        """
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
        Genera configuración óptima para Faster-Whisper basada en recursos del sistema.
        
        Detecta automáticamente los recursos disponibles y ajusta parámetros según:
        - Entorno de ejecución (development vs production)
        - Disponibilidad de GPU y su VRAM
        - RAM disponible del sistema
        - Cantidad de cores de CPU
        
        Sistema secuencial optimizado sin paralelismo para máxima estabilidad.
        
        Lógica de selección de modelo:
        - Production + GPU ≥8GB: large-v3 (máxima calidad)
        - Production + GPU ≥4GB: medium
        - Production + CPU ≥16GB RAM: medium
        - Production + CPU <16GB RAM: small
        - Development + GPU ≥2GB: base
        - Development + CPU: base
        
        Variables de entorno soportadas (override):
        - ENVIRONMENT: "development" | "production"
        - AUDIO_CHUNK_DURATION_MIN: int (minutos)
        - WHISPER_MODEL: str
        - WHISPER_DEVICE: "cpu" | "cuda"
        - WHISPER_COMPUTE_TYPE: "int8" | "float16"
        - WHISPER_NUM_WORKERS: int
        
        Returns:
            AudioProcessingConfig: Configuración optimizada para el sistema.
        
        Example:
            >>> config = AudioConfigManager.get_optimal_config()
            >>> print(f"{config.device} - {config.whisper_model}")
            cpu - base
        
        Note:
            * En producción con GPU se prefiere float16 para máxima calidad
            * En CPU siempre se usa int8 para máxima eficiencia
            * Variables de entorno sobrescriben detección automática
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
        """
        Imprime información del sistema para debugging.
        
        Muestra configuración actual de audio y recursos detectados del sistema.
        Útil para diagnosticar problemas de rendimiento o configuración incorrecta.
        
        Imprime:
            - Configuración de audio (entorno, modelo, dispositivo, compute_type, workers)
            - Duración de chunks y tipo de procesamiento
            - Recursos detectados (RAM, CPU, GPU)
        
        Example:
            >>> AudioConfigManager.print_system_info()
            === CONFIGURACIÓN DE AUDIO (faster-whisper) ===
            Entorno: development
            Modelo Whisper: base
            Dispositivo: cpu
            Tipo de cómputo: int8
            Workers internos: 4
            Duración chunk: 10 min
            Procesamiento: SECUENCIAL OPTIMIZADO (sin paralelismo)
            
            === RECURSOS DETECTADOS ===
            RAM: 12.5/16.0 GB
            CPU: 8 cores físicos
            GPU: No disponible
        
        Note:
            Este método se ejecuta automáticamente al correr el módulo como script:
            python -m app.config.audio_config
        """
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
