"""
Mide el modelo sobre las líneas compuestas de UJIpenchars2.

PARA QUÉ
--------
Dos preguntas distintas, y conviene no confundirlas:

  1. **¿Son legibles estas líneas?** Si el CER saliera cerca de 0, el
     corpus sería demasiado fácil y entrenar con él no enseñaría nada. Si
     saliera cerca de 1, sería ruido y tampoco. Lo útil es que quede en el
     orden del CER sobre manuscrito real (0.2480, medido el 17/09/2026).

  2. **¿Reproduce el fallo del español?** Sobre caracteres aislados el
     modelo acertó 0 de 45 en `ñ` y vocales acentuadas, con un patrón
     claro: `ñ` -> `n.` y `é` -> `e '`. El codificador ve la tinta de la
     tilde, pero el decodificador no sabe que la marca y la letra de abajo
     son un solo carácter. Si ese fallo reaparece acá, este corpus sirve
     para corregirlo con LoRA en el Ciclo 4; y esta medición queda como la
     línea base contra la cual comparar después.

CÓMO SE MIDE LA RECUPERACIÓN POR CARÁCTER
-----------------------------------------
No alcanza con contar cuántas `ñ` salieron: el modelo podría poner una `ñ`
en el lugar equivocado y el conteo daría bien. Se alinea cada referencia
con su hipótesis (`difflib`) y solo se cuentan las `ñ` que caen dentro de
un tramo que coincide. Eso sí es recuperación real del carácter.

SOLO ESCRITORES RESERVADOS
--------------------------
Se evalúa únicamente la partición `val`, que son manos que no van a estar
en el entrenamiento. Medir sobre escritores de entrenamiento daría un
número más bonito y sin ningún valor.

Se corre DENTRO del contenedor, porque PyTorch nativo está bloqueado en
Windows por Smart App Control:

    docker exec justicia-servidor-htr-1 python /htr/evaluar_uji.py
    docker exec justicia-servidor-htr-1 python /htr/evaluar_uji.py --limite 60
"""

from __future__ import annotations

import argparse
import csv
import difflib
import time
import unicodedata
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).parent
DATOS = RAIZ / "dataset" / "uji_lineas"

# Los caracteres que el modelo base nunca vio: el dataset IAM es inglés.
ESPANOL = "ñÑáéíóúÁÉÍÓÚüÜ¿¡"


def cargar(particion: str, limite: int | None) -> list[tuple[Path, str]]:
    with (DATOS / "etiquetas.csv").open(encoding="utf-8") as fh:
        filas = [f for f in csv.DictReader(fh) if f["particion"] == particion]
    pares = [(DATOS / "imagenes" / f["archivo"], f["texto"]) for f in filas]
    return pares[:limite] if limite else pares


def recuperacion(referencias: list[str], hipotesis: list[str]
                 ) -> dict[str, tuple[int, int]]:
    """
    Por cada carácter, `(aciertos, total)` contando solo los que caen en un
    tramo alineado. Ver "CÓMO SE MIDE LA RECUPERACIÓN POR CARÁCTER".
    """
    total: Counter[str] = Counter()
    ok: Counter[str] = Counter()
    for ref, hip in zip(referencias, hipotesis):
        total.update(ref)
        cotejo = difflib.SequenceMatcher(None, ref, hip, autojunk=False)
        for etiqueta, i1, i2, _, _ in cotejo.get_opcodes():
            if etiqueta == "equal":
                ok.update(ref[i1:i2])
    return {c: (ok[c], total[c]) for c in total}


def confusiones(referencias: list[str], hipotesis: list[str],
                objetivo: str) -> Counter[str]:
    """Con qué reemplazó el modelo cada aparición de `objetivo`."""
    salida: Counter[str] = Counter()
    for ref, hip in zip(referencias, hipotesis):
        cotejo = difflib.SequenceMatcher(None, ref, hip, autojunk=False)
        for etiqueta, i1, i2, j1, j2 in cotejo.get_opcodes():
            if etiqueta == "equal":
                continue
            for k in range(i1, i2):
                if ref[k] in objetivo:
                    salida[f"{ref[k]} -> {hip[j1:j2][:4]!r}"] += 1
    return salida


def desacentuar(texto: str) -> str:
    """Quita tildes y diéresis dejando la letra base; la `ñ` se conserva."""
    VIRGULILLA = "̃"
    salida = [c for c in unicodedata.normalize("NFD", texto)
              if not unicodedata.combining(c) or c == VIRGULILLA]
    return unicodedata.normalize("NFC", "".join(salida))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--modelo", default="microsoft/trocr-large-handwritten")
    ap.add_argument("--particion", default="val", choices=["val", "train"])
    ap.add_argument("--limite", type=int, default=None)
    args = ap.parse_args()

    import jiwer
    import torch
    from PIL import Image
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    from unir_lineas import normalizar

    muestras = cargar(args.particion, args.limite)
    if not muestras:
        raise SystemExit(f"Sin muestras en la partición {args.particion}. "
                         f"Corré primero: python generar_uji.py")

    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Modelo     : {args.modelo}")
    print(f"Muestras   : {len(muestras)} ({args.particion}, escritores reservados)")
    print(f"Dispositivo: {dispositivo}\n")

    procesador = TrOCRProcessor.from_pretrained(args.modelo)
    modelo = VisionEncoderDecoderModel.from_pretrained(args.modelo).to(dispositivo).eval()

    # Calentamiento: la primera inferencia paga la inicialización de CUDA y
    # falsearía el tiempo por línea (medido el 15/09: 6.22 s contra 0.263 s,
    # un error de 24 veces).
    px = procesador(images=Image.new("RGB", (384, 96), (250, 250, 248)),
                    return_tensors="pt").pixel_values.to(dispositivo)
    with torch.no_grad():
        modelo.generate(px, max_new_tokens=4)
    if dispositivo == "cuda":
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    print("  calentamiento hecho\n")

    refs, hips, tiempos = [], [], []
    for i, (ruta, esperado) in enumerate(muestras, start=1):
        imagen = Image.open(ruta).convert("RGB")
        px = procesador(images=imagen, return_tensors="pt").pixel_values.to(dispositivo)
        t0 = time.perf_counter()
        with torch.no_grad():
            ids = modelo.generate(px, max_new_tokens=96)
        if dispositivo == "cuda":
            torch.cuda.synchronize()
        tiempos.append(time.perf_counter() - t0)
        refs.append(esperado)
        hips.append(procesador.batch_decode(ids, skip_special_tokens=True)[0].strip())

        if i <= 6:
            print(f"  [{i}] {ruta.name}")
            print(f"      esperado: {esperado}")
            print(f"      obtenido: {hips[-1]}")
            print(f"      CER: {jiwer.cer(esperado, hips[-1]):.4f}")
        elif i % 25 == 0:
            print(f"  {i}/{len(muestras)}")

    normalizadas = [normalizar(h) for h in hips]

    # Dos problemas distintos se suman dentro del mismo CER, y conviene
    # separarlos porque se arreglan de maneras diferentes:
    #
    #   (a) el modelo no emite tildes ni eñes, y
    #   (b) el decodificador es un modelo de lenguaje INGLÉS, que jala las
    #       palabras hacia su ortografía (administrativa -> administrative,
    #       admisible -> admissible, institucional -> institutional).
    #
    # Midiendo contra referencias sin tilde se anula (a) y queda a la vista
    # cuánto pesa (b). Este número NO es un resultado para reportar: es un
    # diagnóstico, porque en el texto final las tildes sí hacen falta.
    cer_norm = jiwer.cer(refs, normalizadas)
    cer_sin_tilde = jiwer.cer([desacentuar(r) for r in refs],
                              [desacentuar(h) for h in normalizadas])

    print(f"\n{'='*66}")
    print(f"  CER crudo        {jiwer.cer(refs, hips):.4f}")
    print(f"  CER normalizado  {cer_norm:.4f}"
          "   (misma normalización que el servidor)")
    print(f"  CER sin tildes   {cer_sin_tilde:.4f}"
          f"   (diagnóstico: las tildes son el "
          f"{1 - cer_sin_tilde / cer_norm:.0%} del error)")
    print(f"  WER normalizado  {jiwer.wer(refs, normalizadas):.4f}")
    print(f"  Segundos/línea   {sum(tiempos)/len(tiempos):.3f}")
    if dispositivo == "cuda":
        print(f"  VRAM pico        {torch.cuda.max_memory_allocated()/1024**3:.2f} GB")

    rec = recuperacion(refs, normalizadas)
    print(f"\n{'='*66}")
    print("  Recuperación por carácter del español")
    print(f"  {'car':<5}{'aciertos':>10}{'total':>8}{'tasa':>8}")
    acc = tot = 0
    for c in ESPANOL:
        ok, n = rec.get(c, (0, 0))
        if not n:
            continue
        acc += ok
        tot += n
        print(f"  {c:<5}{ok:>10}{n:>8}{ok/n:>8.1%}")
    if tot:
        print(f"  {'TODOS':<5}{acc:>10}{tot:>8}{acc/tot:>8.1%}")

    # Comparación: los mismos caracteres, pero los que el modelo sí conoce.
    ascii_ok = sum(v[0] for k, v in rec.items() if k.isalpha() and k.isascii())
    ascii_tot = sum(v[1] for k, v in rec.items() if k.isalpha() and k.isascii())
    if ascii_tot:
        print(f"  {'a-z':<5}{ascii_ok:>10}{ascii_tot:>8}{ascii_ok/ascii_tot:>8.1%}"
              "   (referencia: letras que el modelo sí vio en IAM)")

    # Se guardan las predicciones: cualquier análisis posterior sale de acá
    # sin volver a pagar la inferencia.
    volcado = DATOS / f"predicciones_{args.particion}.csv"
    with volcado.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["archivo", "esperado", "obtenido", "cer"])
        for (ruta, esperado), hip in zip(muestras, normalizadas):
            w.writerow([ruta.name, esperado, hip,
                        f"{jiwer.cer(esperado, hip):.4f}"])
    print(f"\n  Predicciones guardadas en {volcado}")

    conf = confusiones(refs, normalizadas, ESPANOL)
    if conf:
        print(f"\n{'='*66}")
        print("  Con qué los reemplaza (10 más frecuentes)")
        for caso, n in conf.most_common(10):
            print(f"  {n:>5}x  {caso}")


if __name__ == "__main__":
    main()
