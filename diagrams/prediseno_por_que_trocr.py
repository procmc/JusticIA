"""
Prediseno de la lamina "Por que elegimos TrOCR large-handwritten".
Cifras de htr/README.md (Ciclo 1): 18 lineas de letra humana real.
Es una referencia para que Andres la rehaga en su presentacion.

Ejecutar (local): py prediseno_por_que_trocr.py
Output: output/prediseno_por_que_trocr.png
"""

import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]
FONDO, TARJETA, BORDE = "#070716", "#12122b", "#2a2a52"
BLANCO, GRIS, TENUE = "#ffffff", "#a3a9c2", "#5b6082"
VERDE, BARRA, ROJO, AMBAR = "#22c55e", "#4b5578", "#f87171", "#fbbf24"

W, H = 1920, 1080
fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=FONDO)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(H, 0)
ax.axis("off")


def tarjeta(x, y, w, h, color=TARJETA):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=22",
                                facecolor=color, edgecolor=BORDE, linewidth=1.5))


# Titulo
ax.text(60, 80, "¿Por qué elegimos TrOCR large-handwritten?", color=BLANCO, fontsize=34, fontweight="bold", va="center")
ax.text(60, 135, "Cinco modelos medidos sobre 18 líneas de letra humana real (imprenta a mano, foto de celular)",
        color=GRIS, fontsize=16, va="center")

# --- Tarjeta izquierda: los candidatos
tarjeta(40, 180, 1180, 590)
ax.text(75, 222, "Candidatos medidos", color=BLANCO, fontsize=20, fontweight="bold", va="center")
ax.text(1185, 222, "Error por carácter (CER) · menor es mejor", color=GRIS, fontsize=13, va="center", ha="right")

candidatos = [
    ("microsoft/trocr-large-handwritten", 0.2771, "558 M parámetros · 2,12 GB de VRAM", VERDE),
    ("microsoft/trocr-base-handwritten", 0.3934, "334 M parámetros · 1,29 GB de VRAM", BARRA),
    ("qantev/trocr-large-spanish", 0.4031, "609 M parámetros · 2,32 GB de VRAM", BARRA),
    ("qantev/trocr-base-spanish", 0.6260, "385 M parámetros · 1,49 GB de VRAM", BARRA),
    ("ifesther/trocr-spanish-handwritten", 0.6570, "334 M parámetros · 1,29 GB de VRAM", BARRA),
]
x_barra, escala, y0, paso, alto = 560, 850, 290, 94, 54
for i, (nombre, cer, detalle, color) in enumerate(candidatos):
    y = y0 + i * paso
    ax.text(x_barra - 20, y + 15, nombre, color=BLANCO if i == 0 else "#d5d9ec", fontsize=15, fontweight="bold" if i == 0 else "normal",
            va="center", ha="right")
    ax.text(x_barra - 20, y + 42, detalle, color=TENUE, fontsize=11.5, va="center", ha="right")
    ax.add_patch(FancyBboxPatch((x_barra, y), cer * escala, alto, boxstyle="round,pad=0,rounding_size=8",
                                facecolor=color, edgecolor="none"))
    ax.text(x_barra + cer * escala + 16, y + alto / 2, f"{cer:.3f}".replace(".", ","), color=BLANCO, fontsize=17,
            fontweight="bold", va="center")
    if i == 0:
        ax.add_patch(FancyBboxPatch((x_barra + cer * escala + 100, y + 10), 130, 34, boxstyle="round,pad=0,rounding_size=17",
                                    facecolor="none", edgecolor=VERDE, linewidth=2))
        ax.text(x_barra + cer * escala + 165, y + 27, "ELEGIDO", color=VERDE, fontsize=12.5, fontweight="bold",
                va="center", ha="center")
ax.text(75, 745, "Los cinco tienen licencia MIT.", color=TENUE, fontsize=12.5, va="center")

# --- Tarjeta derecha: razones
tarjeta(1250, 180, 630, 590)
ax.text(1285, 222, "Por qué ganó", color=BLANCO, fontsize=20, fontweight="bold", va="center")
razones = [
    "Menor error en letra real: 0,277 frente a 0,393–0,657.",
    "El resultado se repitió en dos escrituras independientes del mismo texto.",
    "Con solo 2 líneas ganaba otro modelo; con 18 el orden se invirtió. Por eso se midió con más muestra.",
    "El modelo en español (qantev) quedó 3.º: su falla está en el decoder, no en leer trazos, y se corrige con LoRA.",
]
y = 285
for r in razones:
    ax.add_patch(Rectangle((1285, y - 8), 6, 6, facecolor=VERDE, edgecolor="none"))
    lineas = textwrap.wrap(r, 44)
    for k, linea in enumerate(lineas):
        ax.text(1308, y + k * 27, linea, color="#e5e8f5", fontsize=15, va="center")
    y += len(lineas) * 27 + 34

# --- Franja inferior: descartados
tarjeta(40, 800, 1840, 230)
ax.text(75, 838, "Descartados antes de medir", color=BLANCO, fontsize=20, fontweight="bold", va="center")
descartados = [
    ("Surya", "Licencia restrictiva:\nlibre solo para investigación"),
    ("Donut", "Comprende documentos,\npero no transcribe manuscrito"),
    ("PaddleOCR · Qwen2.5-VL", "Excluidos por política\ninstitucional (origen chino)"),
    ("Corrección con un LLM", "Empeoró el CER 10–14 %\ny destruye nombres propios"),
]
ancho_col = 430
for i, (nombre, motivo) in enumerate(descartados):
    x = 75 + i * (ancho_col + 20)
    ax.add_patch(FancyBboxPatch((x, 868), ancho_col, 135, boxstyle="round,pad=0,rounding_size=14",
                                facecolor="#0c0c22", edgecolor=BORDE, linewidth=1.2))
    ax.text(x + 22, 898, nombre, color=ROJO, fontsize=16.5, fontweight="bold", va="center")
    ax.text(x + 22, 957, motivo, color=GRIS, fontsize=13.5, va="center", linespacing=1.5)

ax.text(1880, 1060, "Prediseño de referencia · cifras de htr/README.md", color=TENUE, fontsize=10.5, va="center", ha="right")
fig.savefig("output/prediseno_por_que_trocr.png", facecolor=FONDO)
print("Generado: output/prediseno_por_que_trocr.png")
