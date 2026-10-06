"""Evaluación de reconocedores de texto impreso sobre capturas de pantalla (spec 001).

Se ejecuta a mano dentro del contenedor:

    docker compose exec servidor-htr python evaluar_impreso.py

Este módulo reúne la carga del set y la preparación de cada imagen (N-1, N-2,
N-3). Las guardias, los candidatos y la corrida se agregan en las tareas
siguientes de la spec. La lógica pura de métricas y elección está en
`metricas_impreso.py`, para poder probarla sin GPU.

Set (cambio 1 de la spec: solo capturas de pantalla):

* imágenes: `dataset/impreso/capturas/<nombre>.{png,jpg,jpeg}`, sin versionar;
* texto de referencia `<nombre>.txt` en UTF-8, que se busca primero en
  `corpus/impreso/capturas/` (textos propios del proyecto, versionados) y,
  si no está ahí, junto a la imagen (textos de terceros, sin versionar, N-10).
"""

from __future__ import annotations

import argparse
import gc
import io
import ipaddress
import json
import logging
import os
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps

from evaluar_modelos import MODELOS
from metricas_impreso import (
    CARACTERES_ESPANOL,
    LIMITE_CER,
    LIMITE_TIEMPO_S,
    LIMITE_VRAM_GB,
    Eleccion,
    Medicion,
    acierto_espanol,
    cer_pagina,
    cer_promedio,
    elegir,
    sumar_aciertos,
)

log = logging.getLogger("evaluar_impreso")

RAIZ = Path(__file__).resolve().parent
CARPETA_SET = RAIZ / "dataset" / "impreso" / "capturas"
CARPETA_REFERENCIAS = RAIZ / "corpus" / "impreso" / "capturas"

MINIMO_IMAGENES = 10
MINIMO_LINEAS = 100
EXTENSIONES_IMAGEN = frozenset({".png", ".jpg", ".jpeg"})


class SetInsuficiente(Exception):
    """El set no cumple los mínimos de N-1: no se mide."""


@dataclass(frozen=True)
class Pagina:
    imagen: Path
    referencia: str
    origen: str  # "propio" (corpus/) o "terceros" (junto a la imagen)
    lineas: int


@dataclass
class SetCapturas:
    paginas: list[Pagina] = field(default_factory=list)
    # (nombre de la imagen, motivo) de cada imagen que no entra en la medición.
    excluidas: list[tuple[str, str]] = field(default_factory=list)

    @property
    def total_lineas(self) -> int:
        return sum(p.lineas for p in self.paginas)


def _contar_lineas(texto: str) -> int:
    """Líneas no vacías del texto de referencia."""
    return sum(1 for linea in texto.splitlines() if linea.strip())


def _buscar_referencia(imagen: Path, carpeta_referencias: Path) -> tuple[Path, str] | None:
    propia = carpeta_referencias / f"{imagen.stem}.txt"
    if propia.is_file():
        return propia, "propio"
    de_terceros = imagen.with_suffix(".txt")
    if de_terceros.is_file():
        return de_terceros, "terceros"
    return None


def cargar_set(
    carpeta_set: Path = CARPETA_SET,
    carpeta_referencias: Path = CARPETA_REFERENCIAS,
) -> SetCapturas:
    """Empareja cada captura con su texto de referencia y comprueba los mínimos.

    N-2: una imagen sin texto de referencia (o con uno vacío) se excluye y se
    informa, y la carga sigue. N-1: si las capturas válidas no llegan a 10 o
    sus referencias a 100 líneas no vacías, lanza SetInsuficiente.
    """
    carpeta_set = Path(carpeta_set)
    carpeta_referencias = Path(carpeta_referencias)
    if not carpeta_set.is_dir():
        raise SetInsuficiente(f"No existe la carpeta del set: {carpeta_set}")

    conjunto = SetCapturas()
    imagenes = sorted(
        ruta
        for ruta in carpeta_set.iterdir()
        if ruta.is_file() and ruta.suffix.lower() in EXTENSIONES_IMAGEN
    )
    for imagen in imagenes:
        encontrada = _buscar_referencia(imagen, carpeta_referencias)
        if encontrada is None:
            motivo = (
                f"sin texto de referencia: no hay {imagen.stem}.txt en "
                f"{carpeta_referencias} ni junto a la imagen"
            )
        else:
            ruta_txt, origen = encontrada
            texto = ruta_txt.read_text(encoding="utf-8")
            lineas = _contar_lineas(texto)
            if lineas:
                conjunto.paginas.append(Pagina(imagen, texto, origen, lineas))
                continue
            motivo = f"sin texto de referencia: {ruta_txt.name} está vacío"
        conjunto.excluidas.append((imagen.name, motivo))
        log.warning("Se excluye %s: %s", imagen.name, motivo)

    faltas = []
    if len(conjunto.paginas) < MINIMO_IMAGENES:
        faltas.append(
            f"hay {len(conjunto.paginas)} capturas con texto de referencia "
            f"(mínimo {MINIMO_IMAGENES})"
        )
    if conjunto.total_lineas < MINIMO_LINEAS:
        faltas.append(
            f"sus referencias suman {conjunto.total_lineas} líneas "
            f"(mínimo {MINIMO_LINEAS})"
        )
    if faltas:
        raise SetInsuficiente(
            "El set no alcanza los mínimos y no se mide: " + "; ".join(faltas) + "."
        )
    return conjunto


def preparar(ruta: Path) -> Image.Image:
    """Abre una imagen tal como la recibirán todos los candidatos (N-3).

    Aplica la orientación EXIF, pone lo transparente sobre fondo blanco y
    entrega siempre RGB (la escala de grises también pasa a RGB).
    """
    with Image.open(ruta) as abierta:
        imagen = ImageOps.exif_transpose(abierta)
        imagen.load()

    if imagen.mode == "P" and "transparency" in imagen.info:
        imagen = imagen.convert("RGBA")
    if imagen.mode in ("RGBA", "LA", "PA"):
        imagen = imagen.convert("RGBA")
        fondo = Image.new("RGB", imagen.size, (255, 255, 255))
        fondo.paste(imagen, mask=imagen.getchannel("A"))
        return fondo
    return imagen.convert("RGB")


# ---------------------------------------------------------------------------
# Guardia de GPU (RT-03.1)
# ---------------------------------------------------------------------------

URL_SALUD = "http://localhost:9100/salud"
# La VRAM ocupada se lee con nvidia-smi, que ve todos los procesos. En WSL2,
# torch.cuda.mem_get_info solo ve la memoria del propio proceso: con Ollama
# cargado decía 1,05 GB en uso mientras nvidia-smi marcaba 5713 MiB (T8).
# Sin modelos, nvidia-smi marca 493–522 MiB; un modelo cargado ocupa ≥ 2 GB el
# HTR y ~5,6 GB Ollama (plan, decisión 5).
LIMITE_VRAM_EN_USO_GB = 1.0
_GB = 1024**3
_COMANDO_NVIDIA_SMI = ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"]


class GpuNoLista(Exception):
    """Otro proceso tiene un modelo en la GPU, o no se pudo comprobar: no se mide."""


def _consultar_salud() -> dict:
    with urllib.request.urlopen(URL_SALUD, timeout=5) as respuesta:
        return json.load(respuesta)


def _leer_nvidia_smi(ejecutar=subprocess.run) -> str:
    """Salida de nvidia-smi con la memoria usada de cada GPU, en MiB."""
    return ejecutar(
        _COMANDO_NVIDIA_SMI, capture_output=True, text=True, check=True, timeout=30
    ).stdout


def _vram_ocupada_gb(leer_nvidia_smi) -> float:
    try:
        salida = leer_nvidia_smi()
        # Una línea por GPU; se usa la primera, que es la que usa PyTorch (cuda:0).
        mib = float(salida.strip().splitlines()[0])
    except Exception as error:  # noqa: BLE001 - sin la lectura no se puede comprobar
        raise GpuNoLista(
            f"No se pudo leer la VRAM ocupada con nvidia-smi ({error}). "
            "Sin esa comprobación no se mide."
        ) from error
    return mib / 1024


def comprobar_gpu_libre(consultar_salud=_consultar_salud, leer_nvidia_smi=_leer_nvidia_smi) -> dict:
    """Comprueba antes de medir que ningún otro proceso tenga un modelo en la GPU.

    Pide dos cosas: que /salud del servidor HTR de producción diga
    dispositivo «cpu» (su modelo fuera de la GPU) y que la VRAM ocupada según
    nvidia-smi no pase de 1,0 GB. Si algo falla o no se puede comprobar, lanza
    GpuNoLista diciendo el motivo. Devuelve el estado para el JSON.
    """
    try:
        salud = consultar_salud()
    except GpuNoLista:
        raise
    except Exception as error:  # noqa: BLE001 - cualquier fallo impide comprobar
        raise GpuNoLista(
            f"No se pudo consultar /salud del servidor HTR ({URL_SALUD}): {error}. "
            "Sin esa comprobación no se mide."
        ) from error

    en_uso_gb = _vram_ocupada_gb(leer_nvidia_smi)
    dispositivo = salud.get("dispositivo")

    motivos = []
    if dispositivo != "cpu":
        espera = salud.get("idle_timeout_s", 120)
        motivos.append(
            f"el servidor HTR de producción tiene su modelo en la GPU (dispositivo "
            f"«{dispositivo}»); espere unos {espera} s sin uso a que pase a «cpu»"
        )
    if en_uso_gb > LIMITE_VRAM_EN_USO_GB + 1e-9:
        if dispositivo == "cpu":
            quien = (
                "otro proceso tiene un modelo cargado, probablemente Ollama "
                "(deténgalo con «docker compose stop ollama»)"
            )
        else:
            quien = "al menos una parte es del servidor HTR"
        motivos.append(
            f"hay {en_uso_gb:.2f} GB de VRAM ocupada según nvidia-smi (límite "
            f"{LIMITE_VRAM_EN_USO_GB:.1f} GB): {quien}"
        )
    if motivos:
        raise GpuNoLista("La GPU no está libre y no se mide: " + "; ".join(motivos) + ".")

    return {"dispositivo_servidor_htr": dispositivo, "vram_en_uso_gb": round(en_uso_gb, 3)}


# ---------------------------------------------------------------------------
# Modo sin red (RNF-09.1)
# ---------------------------------------------------------------------------

HOSTS_LOCALES = ("localhost", "127.0.0.1", "::1", "tika")
_VARIABLES_SIN_RED = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")


class RedBloqueada(ConnectionError):
    """Se intentó salir a la red durante la medición."""


def _resolver(host: str) -> set[str]:
    try:
        return {info[4][0] for info in socket.getaddrinfo(host, None)}
    except OSError:
        return set()


def _destino_permitido(host, nombres: set[str], ips: set[str]) -> bool:
    """Solo los servicios locales: los nombres permitidos, sus IP y loopback."""
    if host in (None, b"", ""):
        return True  # sin host: dirección local
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    host = str(host).split("%")[0]  # quita el ámbito de una IPv6 (fe80::1%eth0)
    if host in nombres or host in ips:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


@contextmanager
def sin_red(hosts: tuple[str, ...] = HOSTS_LOCALES):
    """Bloquea toda conexión que no sea a un servicio local mientras dura el bloque.

    Activa el modo sin conexión de Hugging Face (HF_HUB_OFFLINE y
    TRANSFORMERS_OFFLINE, que deben estar puestos antes de importar
    transformers) y una guardia sobre la resolución de nombres y la conexión
    de sockets. Al salir, deja todo como estaba.
    """
    nombres = set(hosts)
    # Las IP se resuelven antes de activar la guardia: al conectar, el destino
    # ya es una IP (por ejemplo, la de tika en la red de compose).
    ips = set().union(*(_resolver(h) for h in hosts))

    def comprobar(host, puerto):
        if not _destino_permitido(host, nombres, ips):
            raise RedBloqueada(
                f"Modo sin red (RNF-09.1): se bloqueó una conexión a {host}:{puerto}. "
                "La medición solo habla con servicios locales; si faltan pesos, "
                "descárguelos antes con --descargar."
            )

    getaddrinfo_original = socket.getaddrinfo
    connect_original = socket.socket.connect
    connect_ex_original = socket.socket.connect_ex

    def getaddrinfo(host, port, *args, **kwargs):
        comprobar(host, port)
        return getaddrinfo_original(host, port, *args, **kwargs)

    def _destino(sock, direccion):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            comprobar(direccion[0], direccion[1])

    def connect(self, direccion):
        _destino(self, direccion)
        return connect_original(self, direccion)

    def connect_ex(self, direccion):
        _destino(self, direccion)
        return connect_ex_original(self, direccion)

    entorno_previo = {v: os.environ.get(v) for v in _VARIABLES_SIN_RED}
    for variable in _VARIABLES_SIN_RED:
        os.environ[variable] = "1"
    socket.getaddrinfo = getaddrinfo
    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    try:
        yield
    finally:
        socket.getaddrinfo = getaddrinfo_original
        socket.socket.connect = connect_original
        socket.socket.connect_ex = connect_ex_original
        for variable, valor in entorno_previo.items():
            if valor is None:
                os.environ.pop(variable, None)
            else:
                os.environ[variable] = valor


# ---------------------------------------------------------------------------
# Candidatos (N-3, N-4)
#
# Todos cumplen la misma interfaz: cargar(), leer_pagina(imagen) ->
# (texto, renglones_detectados) y liberar(). torch, transformers y docTR se
# importan dentro de cargar(), después de activar el modo sin red.
# ---------------------------------------------------------------------------

# Parámetros de producción (servidor_htr.py: HTR_MAX_LINEAS y HTR_MAX_TOKENS).
MAX_LINEAS = 60
MAX_TOKENS = 96

REPOS_TROCR = {
    1: MODELOS["large_en"],  # línea base: el modelo de producción
    2: MODELOS["large_es"],
    3: MODELOS["large_printed"],
}
CANDIDATOS = (1, 2, 3, 4, 5)
URL_TIKA = os.getenv("TIKA_SERVER_URL", "http://tika:9998").rstrip("/") + "/tika"


def _dispositivo() -> str:
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


class CandidatoTrOCR:
    """Candidatos 1 a 3: localizador docTR de producción + TrOCR por renglón + unir."""

    usa_gpu = True

    def __init__(self, numero: int, repo: str, segmentar=None, reconocer_lineas=None):
        self.numero = numero
        self.nombre = repo
        self.repo = repo
        self.info: dict = {"repositorio": repo}
        self._segmentar = segmentar
        self._reconocer_inyectado = reconocer_lineas
        self._procesador = None
        self._modelo = None

    def cargar(self) -> None:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        if self._segmentar is None:
            from deteccion_aprendida import segmentar

            self._segmentar = segmentar
        self._dispositivo = _dispositivo()
        self._procesador = TrOCRProcessor.from_pretrained(self.repo)
        self._modelo = VisionEncoderDecoderModel.from_pretrained(self.repo).eval()
        self._modelo.to(self._dispositivo)

    def _reconocer_lineas(self, lineas: list[Image.Image]) -> list[str]:
        if self._reconocer_inyectado is not None:
            return self._reconocer_inyectado(lineas)
        import torch

        textos = []
        for linea in lineas:
            pixeles = self._procesador(images=linea, return_tensors="pt").pixel_values
            with torch.no_grad():
                ids = self._modelo.generate(
                    pixeles.to(self._dispositivo), max_new_tokens=MAX_TOKENS
                )
            textos.append(self._procesador.batch_decode(ids, skip_special_tokens=True)[0].strip())
        return textos

    def leer_pagina(self, imagen: Image.Image) -> tuple[str, int]:
        from unir_lineas import unir

        detalle: dict = {}
        lineas = self._segmentar(imagen, max_lineas=MAX_LINEAS, detalle=detalle)
        renglones = detalle.get("bandas", len(lineas))
        if not renglones:
            return "", 0
        textos = self._reconocer_lineas(lineas)
        return "\n".join(unir(textos, cortes=detalle.get("inicios_bloque"))), renglones

    def liberar(self) -> None:
        self._modelo = None
        self._procesador = None


def vocabulario_faltante(vocabulario: str) -> list[str]:
    """Caracteres del español (N-4) que el reconocedor no puede producir."""
    return [c for c in CARACTERES_ESPANOL if c not in vocabulario]


def revisar_vocabulario(vocabulario: str, version: str) -> dict:
    """N-4: registra la versión de docTR y los caracteres que le faltan."""
    faltantes = vocabulario_faltante(vocabulario)
    if faltantes:
        log.warning(
            "El vocabulario de docTR %s no incluye %s: se documenta como límite y "
            "docTR se mide igual.",
            version,
            " ".join(faltantes),
        )
    return {"version_doctr": version, "vocabulario_faltante": faltantes}


class CandidatoDocTR:
    """Candidato 4: docTR completo, con su detector y reconocedor predeterminados."""

    usa_gpu = True

    def __init__(self, numero: int = 4):
        self.numero = numero
        self.nombre = "docTR completo (predeterminado)"
        self.info: dict = {}
        self._predictor = None

    def cargar(self) -> None:
        import doctr
        import deteccion_aprendida
        from doctr.models import ocr_predictor

        # Plan: anular el detector en caché del localizador de producción
        # antes de cargar docTR, para no arrastrarlo a esta medición.
        deteccion_aprendida._detector = None
        gc.collect()
        self._predictor = ocr_predictor(pretrained=True).to(_dispositivo()).eval()
        self.info = revisar_vocabulario(
            self._predictor.reco_predictor.model.vocab, doctr.__version__.lstrip("v")
        )
        self.info["arquitecturas"] = {
            "deteccion": type(self._predictor.det_predictor.model).__name__,
            "reconocimiento": type(self._predictor.reco_predictor.model).__name__,
        }

    def leer_pagina(self, imagen: Image.Image) -> tuple[str, int]:
        import numpy as np
        import torch

        with torch.no_grad():
            documento = self._predictor([np.asarray(imagen)])
        renglones = sum(len(b.lines) for p in documento.pages for b in p.blocks)
        return documento.render().strip(), renglones

    def liberar(self) -> None:
        self._predictor = None


class CandidatoTesseract:
    """Candidato 5: Tesseract tal como está desplegado en Tika (spa+eng, CPU)."""

    usa_gpu = False

    def __init__(self, numero: int = 5, url: str = URL_TIKA, timeout: float = 120):
        self.numero = numero
        self.nombre = "Tesseract (servicio de extracción)"
        self.url = url
        self.timeout = timeout
        self.info: dict = {"url": url}

    def cargar(self) -> None:
        pass

    def leer_pagina(self, imagen: Image.Image) -> tuple[str, int]:
        buffer = io.BytesIO()
        imagen.save(buffer, format="PNG")
        peticion = urllib.request.Request(
            self.url,
            data=buffer.getvalue(),
            method="PUT",
            headers={"Content-Type": "image/png", "Accept": "text/plain"},
        )
        with urllib.request.urlopen(peticion, timeout=self.timeout) as respuesta:
            texto = respuesta.read().decode("utf-8").strip()
        return texto, sum(1 for linea in texto.splitlines() if linea.strip())

    def liberar(self) -> None:
        pass


def construir_candidatos(numeros) -> list:
    """Construye los candidatos pedidos, en el orden recibido, sin cargar pesos."""
    candidatos = []
    for numero in numeros:
        if numero in REPOS_TROCR:
            candidatos.append(CandidatoTrOCR(numero, REPOS_TROCR[numero]))
        elif numero == 4:
            candidatos.append(CandidatoDocTR())
        elif numero == 5:
            candidatos.append(CandidatoTesseract())
        else:
            raise ValueError(f"Candidato desconocido: {numero}")
    return candidatos


# ---------------------------------------------------------------------------
# Corrida (N-5)
# ---------------------------------------------------------------------------


class GpuTorch:
    """Operaciones de GPU de la corrida; las pruebas usan una versión simulada."""

    def liberar(self) -> None:
        import torch

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def reiniciar_pico(self) -> None:
        import torch

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

    def sincronizar(self) -> None:
        import torch

        if torch.cuda.is_available():
            torch.cuda.synchronize()

    def vram_pico_gb(self) -> float:
        import torch

        return torch.cuda.max_memory_reserved() / _GB if torch.cuda.is_available() else 0.0


@dataclass
class ResultadoCandidato:
    medicion: Medicion
    paginas: list[dict]
    acierto: dict | None
    info: dict


def medir_candidato(candidato, paginas: list[Pagina], gpu) -> ResultadoCandidato:
    """Mide un candidato sobre todo el set. Si algo falla, queda «sin medir»."""
    detalle_paginas: list[dict] = []
    try:
        gpu.liberar()
        gpu.reiniciar_pico()
        candidato.cargar()
        # Calentamiento: la primera inferencia paga la inicialización de CUDA.
        candidato.leer_pagina(preparar(paginas[0].imagen))
        gpu.sincronizar()

        aciertos = []
        for pagina in paginas:
            imagen = preparar(pagina.imagen)
            inicio = time.perf_counter()
            texto, renglones = candidato.leer_pagina(imagen)
            gpu.sincronizar()
            segundos = time.perf_counter() - inicio
            if renglones == 0:
                texto = ""  # caso límite: sin renglones, CER = 1
            acierto = acierto_espanol(pagina.referencia, texto)
            aciertos.append(acierto)
            detalle_paginas.append(
                {
                    "imagen": pagina.imagen.name,
                    "origen": pagina.origen,
                    "lineas_referencia": pagina.lineas,
                    "lineas_detectadas": renglones,
                    "cer": cer_pagina(pagina.referencia, texto),
                    "tiempo_s": segundos,
                    "acierto": acierto["total"],
                    "texto": texto,
                }
            )

        medicion = Medicion(
            numero=candidato.numero,
            nombre=candidato.nombre,
            cer_promedio=cer_promedio([p["cer"] for p in detalle_paginas]),
            vram_pico_gb=gpu.vram_pico_gb() if candidato.usa_gpu else 0.0,
            tiempo_promedio_s=sum(p["tiempo_s"] for p in detalle_paginas) / len(detalle_paginas),
        )
        return ResultadoCandidato(medicion, detalle_paginas, sumar_aciertos(aciertos), candidato.info)
    except Exception as error:  # noqa: BLE001 - N-5: un fallo no detiene la corrida
        motivo = f"{type(error).__name__}: {error}"
        log.error("Candidato %s sin medir: %s", candidato.numero, motivo)
        medicion = Medicion(candidato.numero, candidato.nombre, None, None, None, motivo)
        return ResultadoCandidato(medicion, detalle_paginas, None, candidato.info)
    finally:
        candidato.liberar()
        gpu.liberar()


def correr(candidatos, paginas: list[Pagina], gpu) -> list[ResultadoCandidato]:
    resultados = []
    for candidato in candidatos:
        log.info("Midiendo el candidato %s: %s", candidato.numero, candidato.nombre)
        resultados.append(medir_candidato(candidato, paginas, gpu))
    return resultados


# ---------------------------------------------------------------------------
# Resultados: JSON y tabla Markdown (N-9)
# ---------------------------------------------------------------------------

CARPETA_RESULTADOS = RAIZ / "resultados"


def armar_resultado(
    resultados: list[ResultadoCandidato],
    eleccion: Eleccion,
    conjunto: dict,
    estado_gpu: dict,
    fecha: datetime | None = None,
) -> dict:
    fecha = fecha or datetime.now()
    info_doctr = next((r.info for r in resultados if "version_doctr" in r.info), {})
    return {
        "fecha": fecha.isoformat(timespec="seconds"),
        "version_doctr": info_doctr.get("version_doctr"),
        "vocabulario_faltante_doctr": info_doctr.get("vocabulario_faltante"),
        "configuracion": {
            "candidatos": [r.medicion.numero for r in resultados],
            "repositorios_trocr": REPOS_TROCR,
            "max_lineas": MAX_LINEAS,
            "max_tokens": MAX_TOKENS,
            "url_tika": URL_TIKA,
            "limites": {
                "cer": LIMITE_CER,
                "vram_gb": LIMITE_VRAM_GB,
                "tiempo_s": LIMITE_TIEMPO_S,
            },
        },
        "set": conjunto,
        "gpu": estado_gpu,
        "candidatos": [
            {
                **asdict(r.medicion),
                "estado": "medido" if r.medicion.medido else "sin medir",
                "acierto": r.acierto,
                "paginas": r.paginas,
                "info": r.info,
            }
            for r in resultados
        ],
        "eleccion": {
            "ganador": eleccion.ganador.numero if eleccion.ganador else None,
            "listo_para_integrar": eleccion.listo_para_integrar,
            "brechas": eleccion.brechas,
            "excluidos": eleccion.excluidos,
            "proponer_rf09_parcial": eleccion.proponer_rf09_parcial,
            "cambio_de_requisito": eleccion.cambio_de_requisito,
        },
    }


def _numero(valor, decimales: int) -> str:
    return "—" if valor is None else f"{valor:.{decimales}f}"


def _acierto_texto(acierto: dict | None) -> str:
    if not acierto or acierto["total"]["proporcion"] is None:
        return "—"
    total = acierto["total"]
    return f"{total['proporcion'] * 100:.1f} % ({total['aciertos']}/{total['apariciones']})"


def tabla_markdown(resultado: dict) -> str:
    """Tabla comparativa y conclusión, a partir del JSON (se puede regenerar)."""
    eleccion = resultado["eleccion"]
    excluidos = {int(k): v for k, v in eleccion.get("excluidos", {}).items()}
    brechas = {int(k): v for k, v in eleccion.get("brechas", {}).items()}

    filas = [
        "| # | Candidato | Estado | CER promedio | Tiempo promedio (s/página) "
        "| VRAM pico (GB) | Acierto en español | Elegible |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for c in resultado["candidatos"]:
        estado = c["estado"] if c["estado"] == "medido" else f"sin medir: {c['motivo_sin_medir']}"
        elegible = "no: " + excluidos[c["numero"]] if c["numero"] in excluidos else "sí"
        if c["estado"] != "medido":
            elegible = "no"
        filas.append(
            f"| {c['numero']} | {c['nombre']} | {estado} | {_numero(c['cer_promedio'], 4)} "
            f"| {_numero(c['tiempo_promedio_s'], 2)} | {_numero(c['vram_pico_gb'], 2)} "
            f"| {_acierto_texto(c['acierto'])} | {elegible} |"
        )

    lineas = ["\n".join(filas), ""]
    ganador = eleccion["ganador"]
    if ganador is None:
        lineas.append("**Sin ganador**: ningún candidato cumple los límites de VRAM y tiempo.")
    else:
        nombre = next(c["nombre"] for c in resultado["candidatos"] if c["numero"] == ganador)
        marca = (
            "listo para integrar para capturas de pantalla"
            if eleccion["listo_para_integrar"]
            else "no queda listo para integrar"
        )
        lineas.append(f"**Ganador: {ganador}** ({nombre}): {marca}.")
    if brechas:
        detalle = "; ".join(
            f"{numero}: " + ", ".join(f"{k} +{v:.4g}" for k, v in brecha.items())
            for numero, brecha in sorted(brechas.items())
        )
        lineas.append(f"**Brecha** (cuánto supera cada límite): {detalle}.")
    if eleccion["proponer_rf09_parcial"]:
        lineas.append(
            "**N-7**: la línea base no cumple el criterio: proponer RF-09 «Parcial» en el ERS."
        )
    if eleccion["cambio_de_requisito"]:
        lineas.append(
            "**N-8**: gana docTR o Tesseract: la elección es un **cambio de requisito** "
            "(RF-09, HU-09, CU-08 y FH-01)."
        )
    if resultado.get("version_doctr"):
        faltan = resultado.get("vocabulario_faltante_doctr") or []
        lineas.append(
            f"Versión: docTR {resultado['version_doctr']}; su vocabulario "
            + (f"no incluye {' '.join(faltan)}." if faltan else "incluye todos los caracteres del español medidos.")
        )
    lineas.append(
        "Límite: RF-09 quedó medido solo en su caso «captura de pantalla»; "
        "no hay evidencia sobre fotos con celular ni escaneos."
    )
    return "\n".join(lineas)


def guardar_resultado(resultado: dict, carpeta: Path = CARPETA_RESULTADOS) -> Path:
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    marca = datetime.fromisoformat(resultado["fecha"]).strftime("%Y-%m-%d_%H%M%S")
    ruta = carpeta / f"eval_impreso_{marca}.json"
    ruta.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------


def _lista_candidatos(texto: str) -> list[int]:
    try:
        numeros = [int(parte) for parte in texto.split(",") if parte.strip()]
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"lista de candidatos inválida: {texto}") from error
    desconocidos = [n for n in numeros if n not in CANDIDATOS]
    if desconocidos or not numeros:
        raise argparse.ArgumentTypeError(
            f"candidatos desconocidos: {desconocidos or texto}; las opciones son 1 a 5"
        )
    return numeros


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evalúa reconocedores de texto impreso sobre capturas de pantalla (spec 001)."
    )
    parser.add_argument("--set", type=Path, default=CARPETA_SET, help="carpeta de las capturas")
    parser.add_argument(
        "--refs", type=Path, default=CARPETA_REFERENCIAS, help="carpeta de los textos propios"
    )
    parser.add_argument(
        "--descargar",
        action="store_true",
        help="solo descarga los pesos a las cachés; es el único modo con red",
    )
    parser.add_argument(
        "--solo-verificar-set",
        action="store_true",
        help="solo comprueba el set (mínimos y textos de referencia), sin GPU ni candidatos",
    )
    parser.add_argument(
        "--candidatos",
        type=_lista_candidatos,
        default=list(CANDIDATOS),
        help="números separados por comas (1 a 5); por omisión, todos",
    )
    return parser


def ejecutar(argumentos: argparse.Namespace, descargar, medir):
    """RNF-09.1: con --descargar se permite la red; si no, se mide sin red."""
    if argumentos.descargar:
        return descargar(argumentos)
    with sin_red():
        return medir(argumentos)


def descargar_pesos(argumentos: argparse.Namespace) -> None:
    """Único paso con red: baja los pesos de los candidatos 1 a 4 a las cachés.

    Se cargan en CPU y se descartan: solo interesa que queden en caché. Tesseract
    no tiene pesos propios (corre en el servicio de extracción).
    """
    for numero in argumentos.candidatos:
        if numero in REPOS_TROCR:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel

            repo = REPOS_TROCR[numero]
            log.info("Descargando %s ...", repo)
            TrOCRProcessor.from_pretrained(repo)
            VisionEncoderDecoderModel.from_pretrained(repo)
        elif numero == 4:
            import deteccion_aprendida
            from doctr.models import ocr_predictor

            log.info("Descargando docTR (predictor completo y localizador de producción) ...")
            ocr_predictor(pretrained=True)
            deteccion_aprendida._cargar()
        gc.collect()
    log.info("Pesos en caché.")


def medir(
    argumentos: argparse.Namespace,
    construir=construir_candidatos,
    gpu=None,
    comprobar=comprobar_gpu_libre,
    carpeta_resultados: Path = CARPETA_RESULTADOS,
) -> Path:
    """Flujo completo del plan: set → guardia de GPU → candidatos → elección → JSON."""
    conjunto = cargar_set(argumentos.set, argumentos.refs)
    log.info(
        "Set: %d capturas, %d líneas, %d excluidas.",
        len(conjunto.paginas),
        conjunto.total_lineas,
        len(conjunto.excluidas),
    )
    estado_gpu = comprobar()
    log.info("GPU libre: %s", estado_gpu)

    resultados = correr(construir(argumentos.candidatos), conjunto.paginas, gpu or GpuTorch())
    eleccion = elegir([r.medicion for r in resultados])
    resultado = armar_resultado(
        resultados,
        eleccion,
        {
            "paginas": len(conjunto.paginas),
            "lineas": conjunto.total_lineas,
            "excluidas": conjunto.excluidas,
            "origen": {
                origen: sum(1 for p in conjunto.paginas if p.origen == origen)
                for origen in ("propio", "terceros")
            },
        },
        estado_gpu,
    )
    ruta = guardar_resultado(resultado, carpeta_resultados)
    print(tabla_markdown(resultado))
    log.info("Resultados guardados en %s", ruta)
    return ruta


def verificar_set(argumentos: argparse.Namespace) -> SetCapturas:
    """T7: carga el set y resume lo que encontró, sin GPU ni candidatos."""
    conjunto = cargar_set(argumentos.set, argumentos.refs)
    por_origen = {
        origen: sum(1 for p in conjunto.paginas if p.origen == origen)
        for origen in ("propio", "terceros")
    }
    print(
        f"Set válido: {len(conjunto.paginas)} capturas y {conjunto.total_lineas} líneas "
        f"(mínimos {MINIMO_IMAGENES} y {MINIMO_LINEAS}); textos propios: "
        f"{por_origen['propio']}, de terceros: {por_origen['terceros']}."
    )
    for pagina in conjunto.paginas:
        print(f"  {pagina.imagen.name}: {pagina.lineas} líneas ({pagina.origen})")
    for nombre, motivo in conjunto.excluidas:
        print(f"  Excluida {nombre}: {motivo}")
    return conjunto


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    argumentos = construir_parser().parse_args(argv)
    try:
        if argumentos.solo_verificar_set:
            with sin_red():
                verificar_set(argumentos)
            return 0
        ejecutar(argumentos, descargar_pesos, medir)
    except (SetInsuficiente, GpuNoLista, RedBloqueada) as error:
        log.error("%s", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
