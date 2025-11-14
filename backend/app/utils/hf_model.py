"""
Utilidad de Gestión y Descarga de Modelos de HuggingFace.

Este módulo proporciona funciones para verificar la disponibilidad de modelos
de embeddings desde HuggingFace Hub y descargarlos automáticamente si no están presentes.

Flujo de descarga:
    1. Verifica si el modelo ya existe en disco (busca .safetensors o .bin)
    2. Si no existe, descarga usando huggingface_hub.snapshot_download
    3. Muestra progreso con tqdm automáticamente
    4. Copia el snapshot al directorio final con nombre sanitizado

Directorio de modelos:
    Por defecto: backend/models/
    Estructura: models/{author}__{model-name}/
    
    Ejemplo:
        - model_id: 'Dariolopez/bge-m3-es-legal-tmp-6'
        - destino: models/Dariolopez__bge-m3-es-legal-tmp-6/

Detección de modelos existentes:
    Considera el modelo disponible si encuentra archivos:
        - *.safetensors (formato preferido, más rápido)
        - *.bin (formato PyTorch clásico)

Dependencias:
    - huggingface_hub: Para snapshot_download
    - tqdm: Para mostrar progreso (incluido en huggingface_hub)

Tamaño típico de modelos:
    - BGE-M3: ~2.5 GB
    - BERT-base: ~500 MB
    - Modelos grandes (>7B params): 10-50 GB

Example:
    ```python
    from app.utils.hf_model import ensure_model_available
    
    # Verificar/descargar modelo de embeddings
    model_id = 'Dariolopez/bge-m3-es-legal-tmp-6'
    disponible = ensure_model_available(model_id, dest_root='models')
    
    if disponible:
        print(f'Modelo {model_id} listo para usar')
        # Cargar con sentence-transformers u otro framework
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('models/Dariolopez__bge-m3-es-legal-tmp-6')
    else:
        print('Error: No se pudo descargar el modelo')
    ```

Note:
    La descarga muestra progreso automáticamente con tqdm.
    En caso de error de red, snapshot_download reintenta automáticamente.

See Also:
    - app.embeddings: Usa esta función para garantizar disponibilidad de modelos
    - tasks.procesar_ingesta: Verifica modelo antes de generar embeddings
"""

from pathlib import Path
import os
import shutil


def ensure_model_available(model_id: str, dest_root: str = "models") -> bool:
    """
    Verifica disponibilidad del modelo y lo descarga si es necesario.
    
    Busca archivos .safetensors o .bin en el directorio del modelo.
    Si no existen, descarga el modelo completo desde HuggingFace Hub
    mostrando progreso con tqdm.

    Retorna True si el modelo ya estaba o se descargó correctamente, False si no se pudo asegurar.
    """
    if not model_id:
        return False

    sanitized = model_id.replace('/', '__')
    final_dir = Path(dest_root) / sanitized

    # Si ya hay pesos comunes, consideramos el modelo presente
    if final_dir.exists() and (any(final_dir.glob('*.safetensors')) or any(final_dir.glob('*.bin'))):
        print(f"Modelo '{model_id}' disponible")
        return True
    
    print(f"Descargando modelo: {model_id} (~2.5GB)")

    try:
        # import aquí para no requerir la dependencia si no se usa
        from huggingface_hub import snapshot_download
        import sys
    except Exception as e:
        print(f"huggingface_hub no disponible: {e}")
        return False

    try:
        # Forzar que tqdm muestre el progreso en stdout/stderr
        sys.stdout.flush()
        sys.stderr.flush()
        
        # snapshot_download mostrará automáticamente el progreso con tqdm
        # (resume_download ya no es necesario, ahora siempre reintenta automáticamente)
        snapshot_path = snapshot_download(
            repo_id=model_id
        )
        snapshot_path = Path(snapshot_path)
        
        # Copiar a directorio final
        if final_dir.exists():
            shutil.rmtree(final_dir)
        shutil.copytree(snapshot_path, final_dir)
        
        print(f"Modelo '{model_id}' descargado")
        return True
    except Exception as e:
        print(f"Error descarga: {e}")
        return False
