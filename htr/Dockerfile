# Contenedor para el trabajo de HTR (evaluación y fine-tuning).
#
# Existe porque Smart App Control está activado en la PC de trabajo y
# bloquea las DLL sin firma de PyTorch nativo en Windows
# (OSError WinError 4551 al cargar c10.dll). Los contenedores Linux no
# pasan por esa política, así que se corre PyTorch aquí adentro sin tocar
# la configuración de seguridad de la máquina.
#
# La imagen base ya trae torch + CUDA compilados: no hay nada que construir.
FROM pytorch/pytorch:2.14.0-cuda12.6-cudnn9-runtime

WORKDIR /htr

# transformers: TrOCR (VisionEncoderDecoderModel + TrOCRProcessor)
# jiwer:        cálculo de CER y WER
# pillow:       carga de las imágenes de línea
#
# --break-system-packages: la imagen base marca su Python como
# "externally managed" (PEP 668). Fuera de un contenedor esa protección
# tiene sentido; acá el contenedor ES el entorno y es desechable, así que
# instalar en el Python del sistema es lo correcto.
# sentencepiece + protobuf: el tokenizador de TrOCR es de tipo RoBERTa y
# transformers lo convierte a "fast tokenizer" en tiempo de carga; sin
# estos dos falla con "Couldn't instantiate the backend tokenizer".
# transformers se fija a la rama 4.x: TrOCR y sus checkpoints publicados
# (microsoft/trocr-*, qantev/trocr-*) son de esa era. Con transformers 5.x
# la carga del tokenizador falla con "Couldn't instantiate the backend
# tokenizer" incluso teniendo sentencepiece instalado.
RUN pip install --no-cache-dir --break-system-packages \
        "transformers>=4.44,<5" \
        "jiwer>=3.0" \
        "pillow>=10.0" \
        "numpy>=1.26" \
        "sentencepiece>=0.2" \
        "protobuf>=4.25" \
        "fastapi>=0.115" \
        "uvicorn[standard]>=0.30"

# docTR (Mindee, Apache 2.0): detector de texto ENTRENADO, para ubicar los
# renglones. Reemplaza el umbral global de Otsu, que sobre estas fotos
# clasificaba como tinta el 22 % de la pagina y arruinaba la ubicacion de
# las lineas. Ver deteccion_aprendida.py. Solo se usa la deteccion: el
# reconocedor de docTR es para texto impreso y el manuscrito lo sigue
# haciendo TrOCR.
#
# --no-deps es deliberado: la dependencia por omision de docTR es
# opencv-python, que arrastra bibliotecas de interfaz grafica (falla con
# "libxcb.so.1: cannot open shared object file" en una imagen sin X). Se
# instalan las dependencias a mano con la variante headless.
# La lista sale de `importlib.metadata.requires('python-doctr')`, no de
# adivinar: son sus dependencias obligatorias menos torch, torchvision,
# numpy y Pillow, que ya vienen de la imagen base o de arriba, y con
# opencv-python cambiado por su variante headless.
# python-doctr se fija con == a la version que ya estaba instalada (spec 001,
# N-4): subirla cambiaria el localizador de produccion como efecto secundario.
RUN pip install --no-cache-dir --break-system-packages \
        "opencv-python-headless>=4.10" \
        "onnx>=1.12,<3" \
        "scipy>=1.11" \
        "h5py>=3.10" \
        "pypdfium2>=4.11,<6" \
        "pyclipper>=1.3,<2" \
        "shapely>=2.0,<3" \
        "langdetect>=1.0.9,<2" \
        "rapidfuzz>=3.0,<4" \
        "anyascii>=0.3.2" \
        "validators>=0.18" \
        "tqdm>=4.30" \
    && pip install --no-cache-dir --break-system-packages --no-deps \
        "python-doctr==1.1.0"

# pytest: suite propia de las herramientas de htr/ (spec 001), que se corre
# con `docker compose exec servidor-htr pytest`. Va en su propia capa, al
# final, para no reconstruir las capas anteriores al agregarlo.
RUN pip install --no-cache-dir --break-system-packages "pytest>=8.0"

# Los pesos descargados de Hugging Face se cachean en un volumen para no
# re-bajar 1.4 GB en cada corrida. Los de docTR van a su propia cache, que
# tambien conviene montar como volumen (son ~100 MB por arquitectura).
ENV HF_HOME=/cache/huggingface
ENV DOCTR_CACHE_DIR=/cache/doctr

CMD ["python", "-c", "import torch; print('torch', torch.__version__, '| CUDA', torch.cuda.is_available())"]
