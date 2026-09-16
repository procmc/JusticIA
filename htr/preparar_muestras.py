"""
Prepara un lote de fotos de manuscrito para transcripción.

Recorre una carpeta de fotos, recorta las líneas de cada una y genera un
`.txt` vacío por línea, más una lista de trabajo en Markdown. Convierte la
transcripción en "llenar casillas" en vez de escribir desde cero.

No usa GPU ni PyTorch: corre en el `.venv` nativo.

Uso:
    .venv/Scripts/python.exe preparar_muestras.py --carpeta dataset/muestras_propias
    .venv/Scripts/python.exe preparar_muestras.py --carpeta fotos_album --salida dataset/muestras_propias
"""

from __future__ import annotations

import argparse
from pathlib import Path

from recortar_lineas import recortar

RAIZ = Path(__file__).parent
EXTENSIONES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--carpeta", required=True,
                    help="carpeta con las fotos de página")
    ap.add_argument("--salida", default=None,
                    help="destino de las líneas (default: la misma carpeta)")
    ap.add_argument("--debug", action="store_true",
                    help="guarda la imagen de detección de cada foto")
    args = ap.parse_args()

    origen = Path(args.carpeta)
    if not origen.is_absolute():
        origen = RAIZ / origen
    if not origen.is_dir():
        raise SystemExit(f"No existe la carpeta: {origen}")

    destino = Path(args.salida) if args.salida else origen
    if not destino.is_absolute():
        destino = RAIZ / destino

    # Solo fotos de página: se excluyen las líneas ya recortadas y los debug.
    fotos = sorted(
        f for f in origen.iterdir()
        if f.suffix.lower() in EXTENSIONES
        and "_linea" not in f.stem
        and "_deteccion" not in f.stem
    )
    if not fotos:
        raise SystemExit(f"No hay fotos de página en {origen}")

    print(f"Fotos a procesar: {len(fotos)}\n")

    registro: list[tuple[str, list[Path]]] = []
    for foto in fotos:
        print(f"--- {foto.name}")
        try:
            lineas = recortar(foto, destino, debug=args.debug)
        except Exception as e:
            print(f"  [X] falló: {type(e).__name__}: {e}")
            continue

        for linea in lineas:
            txt = linea.with_suffix(".txt")
            if not txt.exists():          # nunca sobreescribir trabajo hecho
                txt.write_text("", encoding="utf-8")
        registro.append((foto.name, lineas))
        print()

    total = sum(len(l) for _, l in registro)
    pendientes = sum(
        1 for _, ls in registro for l in ls
        if not l.with_suffix(".txt").read_text(encoding="utf-8").strip()
    )

    # Lista de trabajo, para no perder la cuenta de qué falta transcribir.
    lista = destino / "TRANSCRIBIR.md"
    filas = ["# Transcripción pendiente",
             "",
             "Escribí en cada `.txt` **exactamente lo que dice la imagen**:",
             "sin corregir ortografía, sin agregar tildes que no están, sin",
             "completar signos de apertura que no se escribieron. El modelo se",
             "mide contra lo que hay en el papel.",
             "",
             "Si una línea salió mal recortada (basura, media palabra, un trozo",
             "de espiral), **borrá su `.jpg` y su `.txt`** en vez de inventarle",
             "un texto.",
             "",
             f"- Líneas totales: **{total}**",
             f"- Sin transcribir: **{pendientes}**",
             "",
             "| Foto | Línea | Transcripción |",
             "|---|---|---|"]
    for nombre, lineas in registro:
        for linea in lineas:
            hecho = linea.with_suffix(".txt").read_text(encoding="utf-8").strip()
            estado = hecho if hecho else "*(pendiente)*"
            filas.append(f"| {nombre} | `{linea.name}` | {estado} |")
    lista.write_text("\n".join(filas) + "\n", encoding="utf-8")

    print("=" * 60)
    print(f"{len(registro)} foto(s) procesada(s) -> {total} línea(s)")
    print(f"Sin transcribir: {pendientes}")
    print(f"Lista de trabajo: {lista}")
    print("\nSiguiente paso: llenar los .txt y luego correr")
    print("  docker compose -f docker-compose.htr.yml run --rm htr \\")
    print("      python evaluar_modelos.py --muestras dataset/muestras_propias \\")
    print("      --modelos base_en,large_en,base_es,large_es")


if __name__ == "__main__":
    main()
