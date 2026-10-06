"""Pruebas de la herramienta de evaluación de texto impreso (spec 001)."""

from __future__ import annotations

import fnmatch
import logging
import os
import re
import shutil
import socket
import subprocess
from importlib.metadata import version
from pathlib import Path

import pytest
from PIL import Image

from evaluar_impreso import (
    HOSTS_LOCALES,
    MINIMO_IMAGENES,
    MINIMO_LINEAS,
    GpuNoLista,
    RedBloqueada,
    SetInsuficiente,
    _destino_permitido,
    cargar_set,
    comprobar_gpu_libre,
    construir_parser,
    ejecutar,
    preparar,
    sin_red,
)

RAIZ_HTR = Path(__file__).resolve().parent.parent
CARPETA_PRUEBAS = Path(__file__).resolve().parent


def test_version_doctr_instalada_igual_a_la_fijada():
    """N-4: la versión de docTR instalada es la que fija el Dockerfile con ==."""
    dockerfile = (RAIZ_HTR / "Dockerfile").read_text(encoding="utf-8")
    fijadas = re.findall(r'"python-doctr==([0-9][^"\s]*)"', dockerfile)

    assert len(fijadas) == 1, (
        "El Dockerfile debe fijar python-doctr exactamente una vez con =="
    )
    assert version("python-doctr") == fijadas[0]


def test_ninguna_prueba_usa_el_set_real():
    """N-11: ninguna prueba lee el set real; usan imágenes que generan ellas."""
    # La ruta se arma por partes para que este archivo no se detecte a sí mismo.
    prohibida = "data" + "set"
    usos = [
        f"{archivo.name}:{numero}"
        for archivo in sorted(CARPETA_PRUEBAS.rglob("*.py"))
        for numero, linea in enumerate(
            archivo.read_text(encoding="utf-8").splitlines(), start=1
        )
        if prohibida in linea.lower()
    ]

    assert usos == [], f"Pruebas que mencionan la carpeta del set real: {usos}"


# ===========================================================================
# Carga y preparación del set (N-1, N-2, N-3 y N-10)
# Todas las imágenes se generan aquí, en tmp_path (N-11).
# ===========================================================================


def _imagen(ruta: Path, tamano=(40, 20)) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", tamano, "white").save(ruta)
    return ruta


def _referencia(ruta: Path, lineas: int) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # Líneas vacías intercaladas: no cuentan para el mínimo.
    texto = "\n\n".join(f"Renglón {i} de la página" for i in range(lineas)) + "\n"
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def _crear_set(tmp_path, imagenes=10, lineas=10, junto_a_la_imagen=()):
    """Set de prueba: cada imagen con `lineas` renglones de referencia.

    Las referencias van a la carpeta de textos propios, salvo las de los
    índices de `junto_a_la_imagen`, que van al lado de la imagen (terceros).
    """
    carpeta_imagenes = tmp_path / "imagenes"
    carpeta_refs = tmp_path / "refs"
    carpeta_imagenes.mkdir(parents=True, exist_ok=True)
    carpeta_refs.mkdir(parents=True, exist_ok=True)
    for i in range(imagenes):
        _imagen(carpeta_imagenes / f"{i:02d}.png")
        destino = carpeta_imagenes if i in junto_a_la_imagen else carpeta_refs
        _referencia(destino / f"{i:02d}.txt", lineas)
    return carpeta_imagenes, carpeta_refs


# --- N-1: mínimos -----------------------------------------------------------


def test_minimos_del_set():
    """N-1 (cambio 1): al menos 10 capturas y al menos 100 líneas."""
    assert MINIMO_IMAGENES == 10
    assert MINIMO_LINEAS == 100


def test_set_de_10_capturas_y_100_lineas_se_acepta(tmp_path):
    """N-1: 10 capturas × 10 renglones no vacíos = 100 líneas."""
    imagenes, refs = _crear_set(tmp_path, imagenes=10, lineas=10)

    conjunto = cargar_set(imagenes, refs)

    assert len(conjunto.paginas) == 10
    assert conjunto.total_lineas == 100
    assert conjunto.excluidas == []
    assert conjunto.paginas[0].referencia.startswith("Renglón 0")


def test_set_con_9_capturas_aborta_con_mensaje_en_espanol(tmp_path):
    """N-1: con 9 capturas no se mide y se informa."""
    imagenes, refs = _crear_set(tmp_path, imagenes=9, lineas=20)

    with pytest.raises(SetInsuficiente, match=r"9 capturas.*mínimo 10"):
        cargar_set(imagenes, refs)


def test_set_con_99_lineas_aborta_con_mensaje_en_espanol(tmp_path):
    """N-1: 10 capturas pero 99 líneas (una página con 9) no se mide."""
    imagenes, refs = _crear_set(tmp_path, imagenes=10, lineas=10)
    _referencia(refs / "00.txt", 9)

    with pytest.raises(SetInsuficiente, match=r"99 líneas.*mínimo 100"):
        cargar_set(imagenes, refs)


def test_carpeta_del_set_inexistente_aborta(tmp_path):
    with pytest.raises(SetInsuficiente, match="No existe la carpeta"):
        cargar_set(tmp_path / "no_existe", tmp_path / "refs")


# --- N-1: dónde se busca el texto de referencia -----------------------------


def test_referencia_propia_y_de_terceros(tmp_path):
    """N-1, N-10: la referencia se busca en la carpeta de textos propios y,
    si no está ahí, junto a la imagen (textos de terceros)."""
    imagenes, refs = _crear_set(
        tmp_path, imagenes=10, lineas=10, junto_a_la_imagen={3, 7}
    )

    conjunto = cargar_set(imagenes, refs)

    origen = {p.imagen.stem: p.origen for p in conjunto.paginas}
    assert origen["03"] == "terceros"
    assert origen["07"] == "terceros"
    assert origen["00"] == "propio"
    assert len(conjunto.paginas) == 10


def test_acepta_png_jpg_y_jpeg_e_ignora_otros_archivos(tmp_path):
    imagenes, refs = _crear_set(tmp_path, imagenes=8, lineas=13)
    _imagen(imagenes / "08.jpg")
    _imagen(imagenes / "09.JPEG")
    _referencia(refs / "08.txt", 1)
    _referencia(refs / "09.txt", 1)
    (imagenes / "notas.md").write_text("no es una imagen", encoding="utf-8")

    conjunto = cargar_set(imagenes, refs)

    nombres = sorted(p.imagen.name for p in conjunto.paginas)
    assert nombres[-2:] == ["08.jpg", "09.JPEG"]
    assert len(conjunto.paginas) == 10


# --- N-2: imagen sin texto de referencia ------------------------------------


def test_imagen_sin_referencia_se_excluye_se_informa_y_sigue(tmp_path, caplog):
    """N-2: sin .txt en ninguna de las dos ubicaciones."""
    imagenes, refs = _crear_set(tmp_path, imagenes=10, lineas=10)
    _imagen(imagenes / "huerfana.png")

    with caplog.at_level(logging.WARNING, logger="evaluar_impreso"):
        conjunto = cargar_set(imagenes, refs)

    assert len(conjunto.paginas) == 10
    assert [nombre for nombre, _ in conjunto.excluidas] == ["huerfana.png"]
    assert "sin texto de referencia" in conjunto.excluidas[0][1]
    assert "huerfana.png" in caplog.text


def test_referencia_vacia_se_excluye(tmp_path):
    """N-2: un .txt vacío equivale a no tener texto de referencia."""
    imagenes, refs = _crear_set(tmp_path, imagenes=11, lineas=10)
    (refs / "10.txt").write_text(" \n\n", encoding="utf-8")

    conjunto = cargar_set(imagenes, refs)

    assert [nombre for nombre, _ in conjunto.excluidas] == ["10.png"]
    assert len(conjunto.paginas) == 10


def test_las_excluidas_no_cuentan_para_el_minimo(tmp_path):
    """N-1 y N-2: 10 imágenes, pero una sin referencia, deja 9: aborta."""
    imagenes, refs = _crear_set(tmp_path, imagenes=10, lineas=20)
    (refs / "05.txt").unlink()

    with pytest.raises(SetInsuficiente, match="9 capturas"):
        cargar_set(imagenes, refs)


# --- N-3: preparación de la imagen ------------------------------------------


def test_preparar_aplica_la_orientacion_exif(tmp_path):
    """N-3: etiqueta EXIF 6 (girar 90° a la derecha): 40×20 pasa a 20×40, y la
    marca de la esquina superior izquierda queda arriba a la derecha."""
    original = Image.new("RGB", (40, 20), "white")
    original.paste((0, 0, 0), (0, 0, 8, 8))
    exif = original.getexif()
    exif[0x0112] = 6
    ruta = tmp_path / "girada.jpg"
    original.save(ruta, exif=exif, quality=100)

    imagen = preparar(ruta)

    assert imagen.size == (20, 40)
    assert max(imagen.getpixel((17, 2))) < 60  # marca negra arriba a la derecha
    assert min(imagen.getpixel((2, 2))) > 200  # arriba a la izquierda, blanco


@pytest.mark.parametrize("modo", ["RGBA", "LA"])
def test_preparar_pone_la_transparencia_sobre_blanco(tmp_path, modo):
    """N-3: lo transparente queda blanco y lo opaco conserva su color."""
    negro_opaco = (0, 0, 0, 255) if modo == "RGBA" else (0, 255)
    transparente = (0, 0, 0, 0) if modo == "RGBA" else (0, 0)
    imagen = Image.new(modo, (10, 10), transparente)
    imagen.paste(negro_opaco, (0, 0, 5, 10))
    ruta = tmp_path / f"transparente_{modo}.png"
    imagen.save(ruta)

    resultado = preparar(ruta)

    assert resultado.mode == "RGB"
    assert resultado.getpixel((8, 5)) == (255, 255, 255)
    assert resultado.getpixel((2, 5)) == (0, 0, 0)


def test_preparar_pasa_la_escala_de_grises_a_rgb(tmp_path):
    """N-3: L pasa a RGB con el mismo gris."""
    ruta = tmp_path / "gris.png"
    Image.new("L", (10, 10), 100).save(ruta)

    resultado = preparar(ruta)

    assert resultado.mode == "RGB"
    assert resultado.getpixel((5, 5)) == (100, 100, 100)


def test_preparar_paleta_con_transparencia_sobre_blanco(tmp_path):
    """N-3: una imagen con paleta y color transparente también queda sobre blanco."""
    imagen = Image.new("P", (10, 10), 0)
    imagen.putpalette([0, 0, 0, 255, 0, 0] + [0] * 762)
    imagen.paste(1, (0, 0, 5, 10))
    ruta = tmp_path / "paleta.png"
    imagen.save(ruta, transparency=0)

    resultado = preparar(ruta)

    assert resultado.mode == "RGB"
    assert resultado.getpixel((8, 5)) == (255, 255, 255)
    assert resultado.getpixel((2, 5)) == (255, 0, 0)


# --- N-10: qué se versiona --------------------------------------------------

# La carpeta del set se nombra por partes: así la prueba de N-11 no la
# confunde con un uso del set real. Aquí no se lee nada de ella: solo se
# consulta si Git la ignora.
_SET = "data" + "set"


def _ignorado_segun_gitignore(ruta_relativa: str) -> bool:
    """Respaldo sin git: aplica los patrones de htr/.gitignore (sin negaciones)."""
    patrones = [
        linea.strip()
        for linea in (RAIZ_HTR / ".gitignore").read_text(encoding="utf-8").splitlines()
        if linea.strip() and not linea.lstrip().startswith(("#", "!"))
    ]
    partes = ruta_relativa.split("/")
    for patron in patrones:
        es_carpeta = patron.endswith("/")
        patron = patron.strip("/")
        # Un patrón de carpeta solo coincide con componentes que no son el último.
        candidatos = partes[:-1] if es_carpeta else partes
        if any(fnmatch.fnmatch(parte, patron) for parte in candidatos):
            return True
    return False


def _ignorado(ruta_relativa: str) -> bool:
    """N-10: usa `git check-ignore` si hay git y repositorio; si no, el .gitignore."""
    if shutil.which("git"):
        resultado = subprocess.run(
            ["git", "check-ignore", "-q", ruta_relativa],
            cwd=RAIZ_HTR,
            capture_output=True,
        )
        if resultado.returncode in (0, 1):
            return resultado.returncode == 0
    return _ignorado_segun_gitignore(ruta_relativa)


@pytest.mark.parametrize(
    "ruta",
    [
        f"{_SET}/impreso/capturas/01.png",
        f"{_SET}/impreso/capturas/12.txt",
        "resultados/eval_impreso_2026-10-05.json",
    ],
    ids=["imagen", "texto_de_terceros", "resultados"],
)
def test_n10_imagenes_textos_de_terceros_y_resultados_no_se_versionan(ruta):
    assert _ignorado(ruta), f"{ruta} quedaría versionado"


def test_n10_textos_propios_si_se_versionan():
    assert not _ignorado("corpus/impreso/capturas/01.txt")


# ===========================================================================
# Guardias de GPU (RT-03.1) y de red (RNF-09.1)
# /salud y la salida de nvidia-smi se simulan: estas pruebas no usan la GPU.
# La VRAM se lee con nvidia-smi porque, en WSL2, torch.cuda.mem_get_info solo
# ve la memoria del propio proceso (corrección de T8, plan decisión 5).
# ===========================================================================


def _salud(dispositivo="cpu"):
    return lambda: {"listo": True, "dispositivo": dispositivo, "idle_timeout_s": 120}


def _nvidia_smi(mib):
    """Salida de `nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits`."""
    return lambda: f"{mib}\n"


def test_gpu_libre_con_0_5_gb_ocupados_deja_medir():
    """RT-03.1: servidor en cpu y 0,5 GB ocupados (la base real): se puede medir."""
    estado = comprobar_gpu_libre(consultar_salud=_salud("cpu"), leer_nvidia_smi=_nvidia_smi(512))

    assert estado["dispositivo_servidor_htr"] == "cpu"
    assert estado["vram_en_uso_gb"] == pytest.approx(0.5)


def test_gpu_con_1_0_gb_exacto_deja_medir():
    """RT-03.1: el umbral es 1,0 GB y el valor exacto se acepta."""
    comprobar_gpu_libre(consultar_salud=_salud("cpu"), leer_nvidia_smi=_nvidia_smi(1024))


def test_no_mide_con_ollama_cargado():
    """RT-03.1: 5,7 GB ocupados con el servidor en cpu: es otro proceso (Ollama)."""
    with pytest.raises(GpuNoLista, match=r"5\.70 GB.*límite 1\.0 GB.*Ollama"):
        comprobar_gpu_libre(consultar_salud=_salud("cpu"), leer_nvidia_smi=_nvidia_smi(5837))


def test_no_mide_si_nvidia_smi_falla():
    """RT-03.1: sin nvidia-smi no se puede comprobar la GPU: no se mide."""

    def falla():
        raise FileNotFoundError("nvidia-smi")

    with pytest.raises(GpuNoLista, match="nvidia-smi"):
        comprobar_gpu_libre(consultar_salud=_salud("cpu"), leer_nvidia_smi=falla)


def test_no_mide_si_nvidia_smi_devuelve_algo_ilegible():
    with pytest.raises(GpuNoLista, match="nvidia-smi"):
        comprobar_gpu_libre(
            consultar_salud=_salud("cpu"), leer_nvidia_smi=lambda: "[N/A]\n"
        )


def test_lector_de_nvidia_smi_pide_la_memoria_usada():
    """La consulta real usa --query-gpu=memory.used en MiB y sin encabezado."""
    from evaluar_impreso import _leer_nvidia_smi

    llamadas = []

    def ejecutar(comando, **opciones):
        llamadas.append(comando)
        return subprocess.CompletedProcess(comando, 0, stdout="493\n", stderr="")

    assert _leer_nvidia_smi(ejecutar=ejecutar) == "493\n"
    assert llamadas == [
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"]
    ]


def test_no_mide_si_el_servidor_htr_tiene_el_modelo_en_la_gpu():
    """RT-03.1: /salud en cuda: no se mide e informa que es el servidor HTR."""
    with pytest.raises(GpuNoLista, match=r"servidor HTR.*cuda"):
        comprobar_gpu_libre(consultar_salud=_salud("cuda"), leer_nvidia_smi=_nvidia_smi(512))


def test_no_mide_si_salud_no_responde():
    """RT-03.1: sin /salud no se puede comprobar el servidor HTR: no se mide."""

    def caido():
        raise ConnectionRefusedError("conexión rechazada")

    with pytest.raises(GpuNoLista, match=r"/salud"):
        comprobar_gpu_libre(consultar_salud=caido, leer_nvidia_smi=_nvidia_smi(512))


# --- RNF-09.1: modo sin red -------------------------------------------------

IP_EXTERNA = "203.0.113.10"  # TEST-NET-3 (RFC 5737): nunca es un servicio real


def test_sin_red_bloquea_una_conexion_externa_con_mensaje_claro():
    with sin_red():
        with pytest.raises(RedBloqueada, match=r"sin red.*203\.0\.113\.10"):
            socket.create_connection((IP_EXTERNA, 443), timeout=1)


def test_sin_red_bloquea_la_resolucion_de_un_nombre_externo():
    """No llega ni a consultar el DNS de un host externo."""
    with sin_red():
        with pytest.raises(RedBloqueada, match="huggingface.co"):
            socket.getaddrinfo("huggingface.co", 443)


def test_sin_red_permite_localhost():
    servidor = socket.socket()
    servidor.bind(("127.0.0.1", 0))
    servidor.listen(1)
    try:
        with sin_red():
            cliente = socket.create_connection(servidor.getsockname(), timeout=2)
            cliente.close()
            cliente = socket.create_connection(("localhost", servidor.getsockname()[1]), timeout=2)
            cliente.close()
    finally:
        servidor.close()


@pytest.mark.parametrize("host", ["tika", "localhost", "127.0.0.1", "::1", "127.0.0.53"])
def test_destinos_locales_permitidos(host):
    assert _destino_permitido(host, nombres=set(HOSTS_LOCALES), ips=set())


def test_la_ip_de_tika_queda_permitida():
    """Al conectar, el destino ya es una IP: la de tika se resuelve antes de activar la guardia."""
    assert _destino_permitido("172.18.0.5", nombres=set(HOSTS_LOCALES), ips={"172.18.0.5"})
    assert not _destino_permitido("172.18.0.6", nombres=set(HOSTS_LOCALES), ips={"172.18.0.5"})


@pytest.mark.parametrize("host", ["huggingface.co", IP_EXTERNA, "8.8.8.8"])
def test_destinos_externos_bloqueados(host):
    assert not _destino_permitido(host, nombres=set(HOSTS_LOCALES), ips=set())


def test_sin_red_activa_el_modo_offline_y_lo_restaura(monkeypatch):
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "0")
    connect_original = socket.socket.connect

    with sin_red():
        assert os.environ["HF_HUB_OFFLINE"] == "1"
        assert os.environ["TRANSFORMERS_OFFLINE"] == "1"
        assert socket.socket.connect is not connect_original

    assert "HF_HUB_OFFLINE" not in os.environ
    assert os.environ["TRANSFORMERS_OFFLINE"] == "0"
    assert socket.socket.connect is connect_original


# --- RNF-09.1: --descargar es el único modo con red ------------------------


def _con_red() -> bool:
    return os.environ.get("HF_HUB_OFFLINE") != "1" and socket.getaddrinfo.__module__ == "socket"


def test_descargar_es_el_unico_modo_con_red():
    vistos = {}

    def descargar(_):
        vistos["descargar"] = _con_red()

    def medir(_):
        vistos["medir"] = _con_red()

    ejecutar(construir_parser().parse_args(["--descargar"]), descargar, medir)
    assert vistos == {"descargar": True}

    ejecutar(construir_parser().parse_args([]), descargar, medir)
    assert vistos == {"descargar": True, "medir": False}
    assert _con_red()  # al terminar, la guardia se retira


def test_la_medicion_falla_si_intenta_salir_a_la_red():
    """RNF-09.1: si medir necesita la red, falla y lo informa (no descarga)."""

    def medir(_):
        socket.getaddrinfo("huggingface.co", 443)

    with pytest.raises(RedBloqueada):
        ejecutar(construir_parser().parse_args([]), lambda _: None, medir)


# ===========================================================================
# Candidatos y corrida (N-3, N-4, N-5 y N-9)
# Unitarias con candidatos y GPU simulados. Las de integración, marcadas
# `integracion`, usan GPU, pesos y Tika: se corren con `pytest -m integracion`.
# ===========================================================================

import http.server  # noqa: E402
import json  # noqa: E402
import threading  # noqa: E402

from evaluar_impreso import (  # noqa: E402
    MAX_LINEAS,
    REPOS_TROCR,
    CandidatoTesseract,
    CandidatoTrOCR,
    armar_resultado,
    construir_candidatos,
    correr,
    guardar_resultado,
    medir,
    medir_candidato,
    revisar_vocabulario,
    tabla_markdown,
    vocabulario_faltante,
)
from metricas_impreso import Medicion, elegir  # noqa: E402


class GpuFalsa:
    def __init__(self, vram_gb=1.2):
        self.vram_gb = vram_gb
        self.llamadas = []

    def liberar(self):
        self.llamadas.append("liberar")

    def reiniciar_pico(self):
        self.llamadas.append("reiniciar_pico")

    def sincronizar(self):
        self.llamadas.append("sincronizar")

    def vram_pico_gb(self):
        return self.vram_gb


class CandidatoFalso:
    """Lee cada página devolviendo su referencia (o lo que diga `leer`)."""

    def __init__(self, numero, leer=None, falla_al_cargar=None, usa_gpu=True):
        self.numero = numero
        self.nombre = f"falso {numero}"
        self.usa_gpu = usa_gpu
        self.info = {}
        self.leer = leer
        self.falla_al_cargar = falla_al_cargar
        self.lecturas = 0
        self.liberado = False

    def cargar(self):
        if self.falla_al_cargar:
            raise self.falla_al_cargar

    def leer_pagina(self, imagen):
        self.lecturas += 1
        assert imagen.mode == "RGB"  # recibe la imagen ya preparada (N-3)
        return self.leer(imagen) if self.leer else (self.texto_actual, 3)

    def liberar(self):
        self.liberado = True


def _paginas(tmp_path, imagenes=10):
    carpeta_imagenes, carpeta_refs = _crear_set(tmp_path, imagenes=imagenes, lineas=10)
    return cargar_set(carpeta_imagenes, carpeta_refs).paginas


def _lector_perfecto(candidato, paginas):
    """Devuelve la referencia de la página que se está leyendo, en orden."""
    textos = iter([paginas[0].referencia] + [p.referencia for p in paginas])
    return lambda _imagen: (next(textos), 10)


# --- N-3: repositorios y parámetros de producción ---------------------------


def test_modelos_contiene_los_tres_repositorios_de_trocr():
    """N-3: el nombre de cada repositorio vive en evaluar_modelos.MODELOS."""
    from evaluar_modelos import MODELOS

    assert MODELOS["large_printed"] == "microsoft/trocr-large-printed"
    assert REPOS_TROCR == {
        1: "microsoft/trocr-large-handwritten",
        2: "qantev/trocr-large-spanish",
        3: "microsoft/trocr-large-printed",
    }
    assert set(REPOS_TROCR.values()) <= set(MODELOS.values())


def test_construir_candidatos_en_orden_y_sin_cargar_pesos():
    candidatos = construir_candidatos([1, 2, 3, 4, 5])

    assert [c.numero for c in candidatos] == [1, 2, 3, 4, 5]
    assert [c.usa_gpu for c in candidatos] == [True, True, True, True, False]


def test_candidatos_desconocidos_se_rechazan():
    with pytest.raises(SystemExit):
        construir_parser().parse_args(["--candidatos", "1,7"])
    assert construir_parser().parse_args(["--candidatos", "3,1"]).candidatos == [3, 1]
    assert construir_parser().parse_args([]).candidatos == [1, 2, 3, 4, 5]


def test_trocr_usa_el_localizador_con_parametros_de_produccion_y_une_renglones():
    """N-3: localizador docTR con max_lineas=60, TrOCR por renglón y unir()."""
    llamadas = {}

    def segmentar(imagen, max_lineas, detalle):
        llamadas["max_lineas"] = max_lineas
        detalle.update(bandas=2, inicios_bloque={1})
        return ["renglón A", "renglón B"]

    candidato = CandidatoTrOCR(
        1,
        REPOS_TROCR[1],
        segmentar=segmentar,
        reconocer_lineas=lambda lineas: ["Hola", "mundo."],
    )

    texto, n = candidato.leer_pagina(Image.new("RGB", (40, 20), "white"))

    assert llamadas["max_lineas"] == MAX_LINEAS == 60
    assert n == 2
    assert texto == "Hola\nmundo."  # el corte por disposición separa los párrafos


def test_trocr_sin_renglones_detectados_devuelve_texto_vacio():
    """N-5 (caso límite): 0 renglones dan texto vacío y CER 1."""

    def segmentar(imagen, max_lineas, detalle):
        detalle["bandas"] = 0
        return [imagen]  # segmentar devuelve la imagen entera si no halla nada

    candidato = CandidatoTrOCR(
        1, REPOS_TROCR[1], segmentar=segmentar, reconocer_lineas=lambda l: ["basura"]
    )

    assert candidato.leer_pagina(Image.new("RGB", (40, 20), "white")) == ("", 0)


# --- N-4: vocabulario de docTR ---------------------------------------------


def test_vocabulario_faltante_informa_los_caracteres_que_no_estan():
    assert vocabulario_faltante("abcdeéü") == ["á", "í", "ó", "ú", "ñ", "¿", "¡"]
    assert vocabulario_faltante("áéíóúñü¿¡ abc") == []


def test_revisar_vocabulario_registra_version_y_faltantes(caplog):
    """N-4: se registra la versión y lo que falta, y docTR se mide igual."""
    with caplog.at_level(logging.WARNING, logger="evaluar_impreso"):
        info = revisar_vocabulario("abcé", "1.1.0")

    assert info == {
        "version_doctr": "1.1.0",
        "vocabulario_faltante": ["á", "í", "ó", "ú", "ñ", "ü", "¿", "¡"],
    }
    assert "se mide igual" in caplog.text


# --- N-5: corrida -----------------------------------------------------------


def test_medir_candidato_calienta_y_reporta_cer_tiempo_vram_y_acierto(tmp_path):
    paginas = _paginas(tmp_path)
    candidato = CandidatoFalso(1)
    candidato.leer = _lector_perfecto(candidato, paginas)
    gpu = GpuFalsa(vram_gb=1.2)

    resultado = medir_candidato(candidato, paginas, gpu)

    assert candidato.lecturas == 11  # 1 de calentamiento + 10 páginas
    assert resultado.medicion.cer_promedio == 0.0
    assert resultado.medicion.vram_pico_gb == 1.2
    assert resultado.medicion.tiempo_promedio_s >= 0
    assert resultado.medicion.motivo_sin_medir is None
    assert len(resultado.paginas) == 10
    assert {"imagen", "origen", "cer", "tiempo_s", "lineas_detectadas", "texto"} <= set(
        resultado.paginas[0]
    )
    # «Renglón i de la página»: una ó y una á por renglón, 10 renglones, 10 páginas.
    assert resultado.acierto["total"] == {"aciertos": 200, "apariciones": 200, "proporcion": 1.0}
    assert gpu.llamadas[:2] == ["liberar", "reiniciar_pico"]
    assert candidato.liberado


def test_cero_renglones_da_texto_vacio_y_cer_1(tmp_path):
    paginas = _paginas(tmp_path)
    candidato = CandidatoFalso(3, leer=lambda _: ("algo que no cuenta", 0))

    resultado = medir_candidato(candidato, paginas, GpuFalsa())

    assert all(p["texto"] == "" for p in resultado.paginas)
    assert resultado.medicion.cer_promedio == 1.0


def test_candidato_sin_gpu_tiene_vram_cero(tmp_path):
    """N-5: Tesseract corre en CPU, su VRAM es 0."""
    paginas = _paginas(tmp_path)
    candidato = CandidatoFalso(5, usa_gpu=False)
    candidato.leer = _lector_perfecto(candidato, paginas)

    assert medir_candidato(candidato, paginas, GpuFalsa(vram_gb=3.0)).medicion.vram_pico_gb == 0.0


def test_un_fallo_deja_ese_candidato_sin_medir_y_los_demas_se_miden(tmp_path):
    """N-5 (fallos): el que falla queda «sin medir» con su motivo; la corrida sigue."""
    paginas = _paginas(tmp_path)
    roto = CandidatoFalso(2, falla_al_cargar=OSError("no están los pesos"))
    sano = CandidatoFalso(3)
    sano.leer = _lector_perfecto(sano, paginas)

    resultados = correr([roto, sano], paginas, GpuFalsa())

    assert "no están los pesos" in resultados[0].medicion.motivo_sin_medir
    assert resultados[0].medicion.cer_promedio is None
    assert roto.liberado
    assert resultados[1].medicion.cer_promedio == 0.0


def test_un_fallo_a_mitad_de_la_corrida_tambien_deja_sin_medir(tmp_path):
    paginas = _paginas(tmp_path)
    lecturas = iter(range(100))

    def leer(_):
        if next(lecturas) == 5:
            raise RuntimeError("CUDA out of memory")
        return ("texto", 1)

    resultado = medir_candidato(CandidatoFalso(1, leer=leer), paginas, GpuFalsa())

    assert "CUDA out of memory" in resultado.medicion.motivo_sin_medir


# --- Candidato 5: Tesseract por HTTP ----------------------------------------


class _TikaFalso(http.server.BaseHTTPRequestHandler):
    recibido: dict = {}

    def do_PUT(self):  # noqa: N802 - nombre impuesto por http.server
        cuerpo = self.rfile.read(int(self.headers["Content-Length"]))
        _TikaFalso.recibido = {"cuerpo": cuerpo, "accept": self.headers["Accept"]}
        respuesta = "Primera línea\n\nSegunda línea\n".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=UTF-8")
        self.send_header("Content-Length", str(len(respuesta)))
        self.end_headers()
        self.wfile.write(respuesta)

    def log_message(self, *args):
        pass


def test_tesseract_envia_la_imagen_preparada_en_png_y_lee_el_texto():
    servidor = http.server.HTTPServer(("127.0.0.1", 0), _TikaFalso)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    try:
        candidato = CandidatoTesseract(url=f"http://127.0.0.1:{servidor.server_port}/tika")
        with sin_red():
            texto, n = candidato.leer_pagina(Image.new("RGB", (40, 20), "white"))
    finally:
        servidor.shutdown()

    assert _TikaFalso.recibido["cuerpo"].startswith(b"\x89PNG")
    assert _TikaFalso.recibido["accept"] == "text/plain"
    assert texto == "Primera línea\n\nSegunda línea"
    assert n == 2


def test_con_tika_inaccesible_tesseract_queda_sin_medir(tmp_path):
    """N-5 (fallos): Tika no responde (puerto cerrado en localhost)."""
    paginas = _paginas(tmp_path)
    candidato = CandidatoTesseract(url="http://127.0.0.1:1/tika", timeout=2)

    with sin_red():
        resultado = medir_candidato(candidato, paginas, GpuFalsa())

    assert resultado.medicion.motivo_sin_medir


# --- N-9: JSON y tabla ------------------------------------------------------


def _resultados_de_ejemplo():
    paginas = [{"imagen": "01.png", "origen": "propio", "cer": 0.05}]
    acierto = {"por_caracter": {}, "total": {"aciertos": 9, "apariciones": 10, "proporcion": 0.9}}
    from evaluar_impreso import ResultadoCandidato

    return [
        ResultadoCandidato(Medicion(1, "base", 0.20, 2.0, 3.0), paginas, acierto, {}),
        ResultadoCandidato(
            Medicion(4, "docTR", 0.04, 1.0, 1.0),
            paginas,
            acierto,
            {"version_doctr": "1.1.0", "vocabulario_faltante": ["ñ"]},
        ),
        ResultadoCandidato(Medicion(5, "Tesseract", None, None, None, "Tika no responde"), [], None, {}),
    ]


def _resultado_de_ejemplo():
    resultados = _resultados_de_ejemplo()
    eleccion = elegir([r.medicion for r in resultados])
    return armar_resultado(
        resultados,
        eleccion,
        {"paginas": 10, "lineas": 120, "excluidas": []},
        {"dispositivo_servidor_htr": "cpu", "vram_en_uso_gb": 1.05},
    )


def test_el_json_trae_metricas_ganador_marcas_y_version_de_doctr():
    resultado = _resultado_de_ejemplo()

    assert {"fecha", "version_doctr", "configuracion", "set", "gpu", "candidatos", "eleccion"} <= set(
        resultado
    )
    assert resultado["version_doctr"] == "1.1.0"
    candidato = resultado["candidatos"][0]
    assert {
        "numero",
        "nombre",
        "estado",
        "motivo_sin_medir",
        "cer_promedio",
        "tiempo_promedio_s",
        "vram_pico_gb",
        "acierto",
        "paginas",
        "info",
    } <= set(candidato)
    assert resultado["candidatos"][2]["estado"] == "sin medir"
    assert resultado["eleccion"]["ganador"] == 4
    assert resultado["eleccion"]["cambio_de_requisito"] is True
    assert resultado["eleccion"]["proponer_rf09_parcial"] is True
    json.dumps(resultado)  # serializable


def test_la_tabla_trae_todas_las_columnas_el_ganador_y_docTR():
    tabla = tabla_markdown(_resultado_de_ejemplo())

    for columna in (
        "#",
        "Candidato",
        "Estado",
        "CER promedio",
        "Tiempo promedio (s/página)",
        "VRAM pico (GB)",
        "Acierto en español",
        "Elegible",
    ):
        assert columna in tabla
    assert "Ganador: 4" in tabla
    assert "listo para integrar para capturas de pantalla" in tabla
    assert "cambio de requisito" in tabla.lower()
    assert "RF-09" in tabla
    assert "docTR 1.1.0" in tabla and "ñ" in tabla
    assert "Tika no responde" in tabla
    assert "solo en su caso «captura de pantalla»" in tabla


def test_la_tabla_sin_ganador_muestra_la_brecha():
    resultados = [
        type(_resultados_de_ejemplo()[0])(Medicion(1, "base", 0.30, 3.0, 2.0), [], None, {})
    ]
    resultado = armar_resultado(resultados, elegir([r.medicion for r in resultados]), {}, {})

    tabla = tabla_markdown(resultado)

    assert "Sin ganador" in tabla
    assert "brecha" in tabla.lower() and "vram_gb" in tabla


def test_guardar_resultado_escribe_el_json(tmp_path):
    ruta = guardar_resultado(_resultado_de_ejemplo(), carpeta=tmp_path)

    assert ruta.parent == tmp_path
    assert ruta.name.startswith("eval_impreso_") and ruta.suffix == ".json"
    assert json.loads(ruta.read_text(encoding="utf-8"))["eleccion"]["ganador"] == 4


def test_medir_de_punta_a_punta_con_candidatos_simulados(tmp_path):
    """N-5, N-9: set → guardia → candidatos → elección → JSON y tabla."""
    carpeta_imagenes, carpeta_refs = _crear_set(tmp_path, imagenes=10, lineas=10)
    paginas = cargar_set(carpeta_imagenes, carpeta_refs).paginas
    construidos = []

    def construir(numeros):
        for numero in numeros:
            candidato = CandidatoFalso(numero)
            candidato.leer = _lector_perfecto(candidato, paginas)
            construidos.append(candidato)
        return construidos

    argumentos = construir_parser().parse_args(
        ["--set", str(carpeta_imagenes), "--refs", str(carpeta_refs), "--candidatos", "1,3"]
    )
    ruta = medir(
        argumentos,
        construir=construir,
        gpu=GpuFalsa(vram_gb=2.0),
        comprobar=lambda: {"dispositivo_servidor_htr": "cpu", "vram_en_uso_gb": 1.0},
        carpeta_resultados=tmp_path / "resultados",
    )

    resultado = json.loads(ruta.read_text(encoding="utf-8"))
    assert [c["numero"] for c in resultado["candidatos"]] == [1, 3]
    # Empate de CER y de VRAM: decide el tiempo, que aquí no es determinista.
    assert resultado["eleccion"]["ganador"] in (1, 3)
    assert resultado["set"]["paginas"] == 10


def test_medir_no_corre_candidatos_si_la_gpu_no_esta_libre(tmp_path):
    carpeta_imagenes, carpeta_refs = _crear_set(tmp_path, imagenes=10, lineas=10)
    argumentos = construir_parser().parse_args(
        ["--set", str(carpeta_imagenes), "--refs", str(carpeta_refs)]
    )

    def ocupada():
        raise GpuNoLista("ocupada por Ollama")

    def construir(_):
        raise AssertionError("no debía construir candidatos")

    with pytest.raises(GpuNoLista):
        medir(argumentos, construir=construir, gpu=GpuFalsa(), comprobar=ocupada,
              carpeta_resultados=tmp_path)


# --- T7: --solo-verificar-set -----------------------------------------------


def test_solo_verificar_set_informa_conteos_sin_medir(tmp_path, capsys):
    """N-1, N-2: comprueba el set real sin GPU ni red y sin correr candidatos."""
    from evaluar_impreso import main

    carpeta_imagenes, carpeta_refs = _crear_set(tmp_path, imagenes=10, lineas=10)
    _imagen(carpeta_imagenes / "sin_texto.png")

    codigo = main(
        ["--solo-verificar-set", "--set", str(carpeta_imagenes), "--refs", str(carpeta_refs)]
    )

    salida = capsys.readouterr().out
    assert codigo == 0
    assert "10 capturas" in salida and "100 líneas" in salida
    assert "sin_texto.png" in salida  # la excluida se informa


def test_solo_verificar_set_falla_si_no_alcanza_los_minimos(tmp_path):
    from evaluar_impreso import main

    carpeta_imagenes, carpeta_refs = _crear_set(tmp_path, imagenes=9, lineas=20)

    assert (
        main(["--solo-verificar-set", "--set", str(carpeta_imagenes), "--refs", str(carpeta_refs)])
        == 1
    )


# --- Integración: GPU, pesos y Tika reales (se corren en T8) ----------------


def _pagina_con_texto_conocido(tmp_path) -> Path:
    from PIL import ImageDraw, ImageFont

    imagen = Image.new("RGB", (900, 200), "white")
    dibujo = ImageDraw.Draw(imagen)
    fuente = ImageFont.load_default(size=40)
    dibujo.text((30, 30), "Prueba de lectura", fill="black", font=fuente)
    dibujo.text((30, 110), "del sistema ServIA", fill="black", font=fuente)
    ruta = tmp_path / "pagina_generada.png"
    imagen.save(ruta)
    return ruta


_TIKA_SIN_OCR = pytest.mark.xfail(
    strict=True,
    reason=(
        "Hallazgo de la spec 001 (T6): el Tika desplegado procesa image/png con "
        "EmptyParser y no hace OCR. Se corrige en una corrección de error aparte "
        "(tika-config.xml); al corregirla, esta marca debe quitarse."
    ),
)


@pytest.mark.integracion
@pytest.mark.parametrize(
    "numero", [1, 2, 3, 4, pytest.param(5, marks=_TIKA_SIN_OCR)]
)
def test_integracion_cada_candidato_lee_texto_no_vacio(tmp_path, numero):
    """N-3: cada candidato real lee una página generada con texto conocido."""
    imagen = preparar(_pagina_con_texto_conocido(tmp_path))
    (candidato,) = construir_candidatos([numero])
    with sin_red():
        candidato.cargar()
        try:
            texto, n = candidato.leer_pagina(imagen)
        finally:
            candidato.liberar()

    assert texto.strip()
    assert n > 0
