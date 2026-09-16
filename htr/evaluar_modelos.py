"""
Evalúa modelos HTR de la familia TrOCR sobre un set de líneas manuscritas
y reporta las cuatro métricas definidas en el doc 20: CER, WER, tiempo de
inferencia y VRAM máxima.

Acepta dos orígenes de datos:
  * carpeta de muestras: cada imagen con su .txt de igual nombre (ground truth)
  * dataset sintético:   dataset/sintetico/etiquetas.csv

ANTES DE CORRER: liberá la GPU. Ollama retiene ~5.5 GB de los 8 GB.
    docker compose stop ollama

Uso:
    .venv/Scripts/python.exe evaluar_modelos.py --muestras dataset/muestras_propias
    .venv/Scripts/python.exe evaluar_modelos.py --sintetico --limite 50
    .venv/Scripts/python.exe evaluar_modelos.py --muestras ... --modelos base_en,large_en
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).parent

# Los 4 candidatos. Los dos primeros saben manuscrito real pero no español;
# los dos de qantev saben español pero solo vieron texto renderizado.
MODELOS = {
    "base_en":    "microsoft/trocr-base-handwritten",
    "large_en":   "microsoft/trocr-large-handwritten",
    "base_es":    "qantev/trocr-base-spanish",
    "large_es":   "qantev/trocr-large-spanish",
    # Quinto candidato: ya combina las dos mitades del problema — parte de
    # trocr-base-handwritten (sabe trazo manuscrito) afinado a español.
    # Licencia MIT. Advertencia: NO declara con qué dataset se entrenó, así
    # que no se puede verificar la procedencia ni la licencia de esos datos.
    "base_es_hw": "ifesther/trocr-spanish-handwritten",
}


def cargar_muestras(carpeta: Path, limite: int | None) -> list[tuple[Path, str]]:
    """Imágenes con su .txt de igual nombre."""
    pares = []
    for img in sorted(carpeta.iterdir()):
        if img.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        if "_deteccion" in img.stem:          # imagen de debug, no es muestra
            continue
        txt = img.with_suffix(".txt")
        if not txt.exists():
            print(f"  [!] sin ground truth, se omite: {img.name}")
            continue
        pares.append((img, txt.read_text(encoding="utf-8").strip()))
    return pares[:limite] if limite else pares


def cargar_sintetico(limite: int | None) -> list[tuple[Path, str]]:
    base = RAIZ / "dataset" / "sintetico"
    with (base / "etiquetas.csv").open(encoding="utf-8") as fh:
        filas = [f for f in csv.DictReader(fh) if f["particion"] == "val"]
    pares = [(base / "imagenes" / f["archivo"], f["texto"]) for f in filas]
    return pares[:limite] if limite else pares


def evaluar(nombre_corto: str, repo: str, muestras: list[tuple[Path, str]],
            dispositivo: str) -> dict:
    import torch
    import jiwer
    from PIL import Image
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    print(f"\n{'=' * 70}\n{nombre_corto}  ({repo})\n{'=' * 70}")

    t0 = time.perf_counter()
    procesador = TrOCRProcessor.from_pretrained(repo)
    modelo = VisionEncoderDecoderModel.from_pretrained(repo).to(dispositivo).eval()
    t_carga = time.perf_counter() - t0
    parametros = sum(p.numel() for p in modelo.parameters())
    print(f"  carga: {t_carga:.1f}s | parámetros: {parametros/1e6:.0f}M")

    # Calentamiento: la PRIMERA inferencia de la sesión paga la
    # inicialización de CUDA/cuDNN y la selección de kernels. Sin esto, el
    # primer modelo evaluado aparece artificialmente lento (se midió 6.2
    # s/línea contra 0.97 s de un modelo de tamaño equivalente) y la
    # comparación de tiempos queda inservible.
    from PIL import Image as _Image
    if muestras:
        _px = procesador(images=_Image.open(muestras[0][0]).convert("RGB"),
                         return_tensors="pt").pixel_values.to(dispositivo)
        with torch.no_grad():
            modelo.generate(_px, max_new_tokens=8)
        if dispositivo == "cuda":
            torch.cuda.synchronize()
        print("  calentamiento hecho")

    if dispositivo == "cuda":
        torch.cuda.reset_peak_memory_stats()

    referencias, hipotesis, tiempos = [], [], []

    for i, (ruta, esperado) in enumerate(muestras, start=1):
        imagen = Image.open(ruta).convert("RGB")
        pixeles = procesador(images=imagen, return_tensors="pt").pixel_values.to(dispositivo)

        t1 = time.perf_counter()
        with torch.no_grad():
            ids = modelo.generate(pixeles, max_new_tokens=96)
        if dispositivo == "cuda":
            torch.cuda.synchronize()
        tiempos.append(time.perf_counter() - t1)

        obtenido = procesador.batch_decode(ids, skip_special_tokens=True)[0].strip()
        referencias.append(esperado)
        hipotesis.append(obtenido)

        if i <= 6 or len(muestras) <= 12:
            print(f"\n  [{i}] {ruta.name}")
            print(f"      esperado: {esperado}")
            print(f"      obtenido: {obtenido}")
            print(f"      CER de esta línea: {jiwer.cer(esperado, obtenido):.4f}")
        elif i % 25 == 0:
            print(f"  {i}/{len(muestras)}")

    vram = (torch.cuda.max_memory_allocated() / 1024**3) if dispositivo == "cuda" else 0.0

    # CER/WER agregados sobre el corpus completo, no promedio de promedios.
    cer = jiwer.cer(referencias, hipotesis)
    wer = jiwer.wer(referencias, hipotesis)

    del modelo, procesador
    if dispositivo == "cuda":
        torch.cuda.empty_cache()

    resultado = {
        "modelo": nombre_corto,
        "repo": repo,
        "parametros_M": round(parametros / 1e6, 1),
        "cer": round(float(cer), 4),
        "wer": round(float(wer), 4),
        "tiempo_medio_s": round(sum(tiempos) / len(tiempos), 3),
        "tiempo_carga_s": round(t_carga, 1),
        "vram_pico_GB": round(vram, 2),
        "n_muestras": len(muestras),
        "predicciones": [
            {"archivo": r.name, "esperado": e, "obtenido": h}
            for (r, e), h in zip(muestras, hipotesis)
        ],
    }
    print(f"\n  >> CER {resultado['cer']:.4f} | WER {resultado['wer']:.4f} | "
          f"{resultado['tiempo_medio_s']:.3f}s/línea | {resultado['vram_pico_GB']:.2f} GB")
    return resultado


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    origen = ap.add_mutually_exclusive_group(required=True)
    origen.add_argument("--muestras", help="carpeta con imágenes + .txt")
    origen.add_argument("--sintetico", action="store_true",
                        help="usar la partición val del dataset sintético")
    ap.add_argument("--modelos", default="base_en,large_en",
                    help=f"lista separada por comas. Opciones: {','.join(MODELOS)}")
    ap.add_argument("--limite", type=int, default=None)
    ap.add_argument("--salida", default="resultados")
    args = ap.parse_args()

    import torch
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Dispositivo: {dispositivo}")
    if dispositivo == "cuda":
        libre, total = torch.cuda.mem_get_info()
        print(f"GPU: {torch.cuda.get_device_name(0)}  "
              f"{libre/1024**3:.2f} GB libres de {total/1024**3:.2f} GB")
    else:
        print("  [!] Sin CUDA: los tiempos no son representativos y "
              "la VRAM no se puede medir.")

    if args.sintetico:
        muestras = cargar_sintetico(args.limite)
        etiqueta_origen = "sintetico(val)"
        print("\n  [!] ADVERTENCIA: medir sobre sintético NO predice el "
              "desempeño con letra humana real. Es solo una verificación "
              "de que la tubería funciona.")
    else:
        carpeta = Path(args.muestras)
        if not carpeta.is_absolute():
            carpeta = RAIZ / carpeta
        muestras = cargar_muestras(carpeta, args.limite)
        etiqueta_origen = str(carpeta.name)

    if not muestras:
        raise SystemExit("No hay muestras con ground truth para evaluar.")
    print(f"\nMuestras a evaluar: {len(muestras)}  (origen: {etiqueta_origen})")

    seleccion = [m.strip() for m in args.modelos.split(",") if m.strip()]
    desconocidos = [m for m in seleccion if m not in MODELOS]
    if desconocidos:
        raise SystemExit(f"Modelo(s) no reconocido(s): {desconocidos}. "
                         f"Opciones: {list(MODELOS)}")

    resultados = []
    for corto in seleccion:
        try:
            resultados.append(evaluar(corto, MODELOS[corto], muestras, dispositivo))
        except Exception as e:
            print(f"\n  [X] {corto} falló: {type(e).__name__}: {e}")

    if not resultados:
        raise SystemExit("Ningún modelo se pudo evaluar.")

    print(f"\n\n{'=' * 78}\nTABLA COMPARATIVA  (origen: {etiqueta_origen}, "
          f"{len(muestras)} líneas)\n{'=' * 78}")
    print(f"{'MODELO':<12}{'PARAM':>8}{'CER':>9}{'WER':>9}"
          f"{'s/LINEA':>10}{'VRAM GB':>10}")
    print("-" * 78)
    for r in sorted(resultados, key=lambda x: x["cer"]):
        print(f"{r['modelo']:<12}{r['parametros_M']:>7.0f}M{r['cer']:>9.4f}"
              f"{r['wer']:>9.4f}{r['tiempo_medio_s']:>10.3f}{r['vram_pico_GB']:>10.2f}")
    print("-" * 78)
    mejor = min(resultados, key=lambda x: x["cer"])
    print(f"Menor CER: {mejor['modelo']} ({mejor['cer']:.4f})")

    carpeta_salida = RAIZ / args.salida
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = carpeta_salida / f"eval_{etiqueta_origen}_{marca}.json"
    destino.write_text(json.dumps({
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "origen": etiqueta_origen,
        "dispositivo": dispositivo,
        "n_muestras": len(muestras),
        "resultados": resultados,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nJSON: {destino}")


if __name__ == "__main__":
    main()
