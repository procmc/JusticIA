"""
Ilustra el pipeline de reconocimiento sobre UNA foto real, paso por paso.

Es una herramienta para explicar el proceso (presentaciones, documentacion),
no parte del servicio. Usa las mismas funciones que el servidor: el
localizador entrenado (deteccion_aprendida) y el modelo de produccion, y le
pide el texto final al servidor en ejecucion.

Salida (carpeta indicada):
    p1_original.jpg    la foto tal como llega
    p2_papel.jpg       solo la hoja, sin lo que la rodea
    p3_renglones.jpg   la hoja con una caja por renglon detectado
    recortes/NN.png    cada renglon recortado
    lecturas.json      texto que TrOCR lee de cada recorte
    texto_final.txt    texto que devuelve el servidor (parrafos unidos)

Uso (dentro del contenedor servidor-htr):
    python /htr/ilustrar_pipeline.py /htr/dataset/paginas/foto.jpg /htr/dataset/paginas/ilustracion
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageOps
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

import deteccion_aprendida as da
from segmentacion import corregir_inclinacion, detectar_papel

MODELO = "microsoft/trocr-large-handwritten"
COLORES = ["#2563eb", "#16a34a", "#9333ea", "#ea580c", "#0891b2", "#dc2626"]


def main(foto: str, salida: str) -> None:
    out = Path(salida)
    (out / "recortes").mkdir(parents=True, exist_ok=True)

    crudo = Path(foto).read_bytes()
    imagen = ImageOps.exif_transpose(Image.open(foto)).convert("RGB")
    imagen.save(out / "p1_original.jpg", quality=90)

    # Los mismos pasos que deteccion_aprendida.segmentar, pero guardando lo
    # intermedio para poder mostrarlo.
    imagen, _ = corregir_inclinacion(imagen)
    gris = np.asarray(imagen.convert("L"), dtype=np.float32)
    px0, py0, px1, py1 = detectar_papel(gris)
    papel = imagen.crop((px0, py0, px1, py1))
    papel.save(out / "p2_papel.jpg", quality=90)

    cajas = da._cajas(papel)
    grupos = da.agrupar_en_renglones(cajas)
    grupos, _numeradas = da.quitar_columna_numeracion(grupos, papel.width)

    dibujo = papel.copy()
    d = ImageDraw.Draw(dibujo)
    grosor = max(3, papel.width // 300)
    for k, g in enumerate(grupos):
        color = COLORES[k % len(COLORES)]
        x0, y0 = int(g[:, 0].min()), int(g[:, 1].min())
        x1, y1 = int(g[:, 2].max()), int(g[:, 3].max())
        d.rectangle([x0 - 8, y0 - 8, x1 + 8, y1 + 8], outline=color, width=grosor)
    dibujo.save(out / "p3_renglones.jpg", quality=90)

    # Recortes y lectura: la misma segmentacion que usa el servidor.
    recortes = da.segmentar(imagen, max_lineas=60, detalle={})
    procesador = TrOCRProcessor.from_pretrained(MODELO)
    modelo = VisionEncoderDecoderModel.from_pretrained(MODELO).eval()
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    modelo.to(dispositivo)

    lecturas = []
    for k, recorte in enumerate(recortes, 1):
        recorte.save(out / "recortes" / f"{k:02d}.png")
        pix = procesador(images=recorte, return_tensors="pt").pixel_values.to(dispositivo)
        with torch.no_grad():
            ids = modelo.generate(pix, max_new_tokens=96)
        lecturas.append(procesador.batch_decode(ids, skip_special_tokens=True)[0].strip())
    (out / "lecturas.json").write_text(json.dumps(lecturas, ensure_ascii=False, indent=1), encoding="utf-8")

    # Texto final tal como lo entrega el servidor en produccion.
    peticion = urllib.request.Request("http://localhost:9100/htr", data=crudo, method="POST")
    with urllib.request.urlopen(peticion, timeout=300) as r:
        respuesta = json.loads(r.read())
    (out / "texto_final.txt").write_text(respuesta["texto"], encoding="utf-8")
    print(f"{len(grupos)} renglones; servidor: {respuesta['lineas']} lineas, "
          f"{respuesta['parrafos']} parrafos, {respuesta['segundos']} s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
