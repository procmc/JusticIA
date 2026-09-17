"""
Mide el pipeline COMPLETO sobre la foto de una hoja, de punta a punta.

QUÉ MIDE, Y EN QUÉ SE DIFERENCIA DE LO ANTERIOR
-----------------------------------------------
`evaluar_modelos.py` mide el modelo sobre líneas **ya recortadas a mano**.
Ese es el número 0.2480 del Ciclo 2: mide el reconocedor, con la
segmentación resuelta de antemano por una persona.

Acá se manda la **foto entera** al servidor y se mide lo que realmente
sale: detección de papel, remoción del encuadernado, corrección de
inclinación, segmentación en renglones, reconocimiento y unión en
párrafos. Todo automático.

La diferencia entre los dos números ES la brecha manual-vs-automática, que
es el último pendiente del Ciclo 2. Hasta ahora esa brecha se había visto
a ojo (un recorte automático perdió `¡Atenci` y `ble vence`) pero nunca se
había medido.

POR QUÉ CER DE DOCUMENTO Y NO POR LÍNEA
---------------------------------------
Con segmentación automática no se puede comparar línea contra línea: si el
servidor detecta 14 bandas donde hay 16 renglones, no hay forma de saber
qué banda corresponde a qué renglón sin decidirlo arbitrariamente, y esa
decisión inventaría o escondería error.

Así que se compara el texto completo contra el texto completo. Es más
exigente y es lo honesto: un renglón que la segmentación se comió aparece
como borrado, que es exactamente el daño que causa.

Uso (dentro del contenedor, que es donde vive el servidor):
    docker exec justicia-servidor-htr-1 python /htr/evaluar_hoja.py \
        /htr/dataset/paginas/hoja_imprenta_separadas.jpg --estilo imprenta

    # Si la hoja no trae las 16 oraciones del set, se indica el rango:
    ... --estilo imprenta --numeros 01-08
"""

from __future__ import annotations

import argparse
import difflib
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).parent
SET_PRUEBA = RAIZ / "corpus" / "set_prueba_manuscrito.txt"
PUERTO_POR_OMISION = 9100


def esperado(estilo: str | None, numeros: set[str] | None) -> list[str]:
    """Las oraciones del set de prueba que corresponden a esta hoja."""
    filas = []
    for linea in SET_PRUEBA.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        est, num, texto = linea.split("|", 2)
        if estilo and est != estilo:
            continue
        if numeros and num not in numeros:
            continue
        filas.append(texto)
    return filas


def rango(spec: str) -> set[str]:
    """`01-08` -> {01, 02, ... 08}; `01,03` -> {01, 03}."""
    salida: set[str] = set()
    for parte in spec.split(","):
        if "-" in parte:
            a, b = parte.split("-")
            salida.update(f"{n:02d}" for n in range(int(a), int(b) + 1))
        else:
            salida.add(f"{int(parte):02d}")
    return salida


def pedir(ruta: Path, puerto: int) -> dict:
    peticion = urllib.request.Request(
        f"http://localhost:{puerto}/htr", data=ruta.read_bytes(),
        headers={"Content-Type": "application/octet-stream"})
    import json
    with urllib.request.urlopen(peticion, timeout=600) as r:
        return json.load(r)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("imagen", type=Path)
    ap.add_argument("--estilo", choices=["imprenta", "cursiva"], default=None)
    ap.add_argument("--numeros", type=str, default=None,
                    help="qué oraciones trae la hoja, p. ej. 01-08")
    ap.add_argument("--puerto", type=int, default=PUERTO_POR_OMISION,
                    help="puerto del servidor HTR a consultar")
    ap.add_argument("--encabezado", type=str, default=None,
                    help="texto del encabezado manuscrito de la hoja, si "
                         "tiene uno. Sin esto se penaliza como inserción "
                         "texto que el pipeline leyó bien, solo porque no "
                         "está en el set de prueba")
    args = ap.parse_args()

    if not args.imagen.exists():
        raise SystemExit(f"No existe {args.imagen}")

    import jiwer

    referencias = esperado(args.estilo, rango(args.numeros) if args.numeros else None)
    if not referencias:
        raise SystemExit("El filtro de estilo/números no dejó ninguna oración.")
    if args.encabezado:
        referencias.insert(0, args.encabezado)

    print(f"Imagen   : {args.imagen.name}")
    print(f"Esperado : {len(referencias)} oraciones del set de prueba"
          f"{f' ({args.estilo})' if args.estilo else ''}\n")

    r = pedir(args.imagen, args.puerto)
    obtenido = r["texto"]
    parrafos = obtenido.split("\n")
    ref = "\n".join(referencias)

    print(f"  bandas detectadas : {r['lineas']}")
    print(f"  párrafos armados  : {r['parrafos']}   (esperados: {len(referencias)})")
    print(f"  segundos          : {r['segundos']}")
    print(f"  dispositivo       : {r['dispositivo']}\n")

    print("=" * 70)
    print("  TEXTO OBTENIDO")
    print("=" * 70)
    for i, p in enumerate(parrafos, start=1):
        print(f"  {i:>2}. {p}")

    print()
    print("=" * 70)
    print("  COMPARACIÓN LÍNEA POR LÍNEA (alineada por similitud)")
    print("=" * 70)
    cotejo = difflib.SequenceMatcher(None, referencias, parrafos,
                                     autojunk=False)
    for etiqueta, i1, i2, j1, j2 in cotejo.get_opcodes():
        if etiqueta == "equal":
            for k in range(i1, i2):
                print(f"  = {referencias[k]}")
            continue
        for k in range(i1, i2):
            print(f"  - esperado: {referencias[k]}")
        for k in range(j1, j2):
            print(f"  + obtenido: {parrafos[k]}")

    # CER de documento completo: ver "POR QUÉ CER DE DOCUMENTO".
    cer = jiwer.cer(ref, obtenido)
    wer = jiwer.wer(ref, obtenido)
    print()
    print("=" * 70)
    print(f"  CER automático (pipeline completo) : {cer:.4f}")
    print(f"  WER automático                     : {wer:.4f}")
    print(f"  caracteres esperados / obtenidos   : {len(ref)} / {len(obtenido)}")
    print()
    print("  Referencia: 0.2480 es el CER del MISMO modelo sobre líneas")
    print("  recortadas a mano. La diferencia con el número de arriba es la")
    print("  brecha que aporta la segmentación automática.")


if __name__ == "__main__":
    main()
