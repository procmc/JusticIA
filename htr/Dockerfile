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

# Los pesos descargados de Hugging Face se cachean en un volumen para no
# re-bajar 1.4 GB en cada corrida.
ENV HF_HOME=/cache/huggingface

CMD ["python", "-c", "import torch; print('torch', torch.__version__, '| CUDA', torch.cuda.is_available())"]
