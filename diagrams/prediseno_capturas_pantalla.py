"""
Prediseno de la lamina "Capturas de pantalla".
Cifras de specs/001-reconocimiento-texto-impreso/resultados.md (05/10/2026):
10 capturas, 155 lineas de referencia, sin red.
Es una referencia para que Andres la rehaga en su presentacion.

Ejecutar (local): py prediseno_capturas_pantalla.py
Output: output/prediseno_capturas_pantalla.png
"""

import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]
FONDO, TARJETA, BORDE = "#070716", "#12122b", "#2a2a52"
BLANCO, GRIS, TENUE = "#ffffff", "#a3a9c2", "#5b6082"
VERDE, MORADO, BARRA, ROJO, NARANJA = "#22c55e", "#a855f7", "#4b5578", "#f87171", "#fb923c"

W, H = 1920, 1080
fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=FONDO)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(H, 0)
ax.axis("off")


def tarjeta(x, y, w, h, color=TARJETA):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=22",
                                facecolor=color, edgecolor=BORDE, linewidth=1.5))


def pastilla(x, y, w, texto, color):
    ax.add_patch(FancyBboxPatch((x, y), w, 34, boxstyle="round,pad=0,rounding_size=17",
                                facecolor="none", edgecolor=color, linewidth=2))
    ax.text(x + w / 2, y + 17, texto, color=color, fontsize=12, fontweight="bold", va="center", ha="center")


# Titulo
ax.text(60, 80, "Capturas de pantalla: ¿qué modelo lee mejor?", color=BLANCO, fontsize=34, fontweight="bold", va="center")
ax.text(60, 135, "Cinco candidatos medidos sobre 10 capturas (155 líneas de referencia) · medición del 05/10/2026, sin red",
        color=GRIS, fontsize=16, va="center")

# --- Tarjeta izquierda: candidatos
tarjeta(40, 180, 1180, 560)
ax.text(75, 222, "Candidatos medidos", color=BLANCO, fontsize=20, fontweight="bold", va="center")
ax.text(1185, 222, "Error por carácter (CER) · menor es mejor", color=GRIS, fontsize=13, va="center", ha="right")

candidatos = [
    ("docTR completo 1.1.0", 0.0484, "Detector + reconocedor propios", VERDE, "MEJOR MEDIDO", 150),
    ("qantev/trocr-large-spanish", 0.0642, "TrOCR afinado en español", BARRA, None, 0),
    ("microsoft/trocr-large-handwritten", 0.1208, "TrOCR de manuscrito", MORADO, "USADO HOY", 120),
    ("microsoft/trocr-large-printed", 0.8401, "TrOCR de texto impreso", BARRA, None, 0),
    ("Tesseract (vía Tika)", 1.0000, "Sin OCR de imágenes en el Tika desplegado*", ROJO, None, 0),
]
x_barra, escala, y0, paso, alto = 560, 520, 290, 86, 50
for i, (nombre, cer, detalle, color, etiqueta, ancho_pastilla) in enumerate(candidatos):
    y = y0 + i * paso
    ax.text(x_barra - 20, y + 14, nombre, color=BLANCO if color in (VERDE, MORADO) else "#d5d9ec", fontsize=15,
            fontweight="bold" if color in (VERDE, MORADO) else "normal", va="center", ha="right")
    ax.text(x_barra - 20, y + 39, detalle, color=TENUE, fontsize=11.5, va="center", ha="right")
    ax.add_patch(FancyBboxPatch((x_barra, y), max(cer * escala, 14), alto, boxstyle="round,pad=0,rounding_size=8",
                                facecolor=color, edgecolor="none"))
    x_valor = max(x_barra + max(cer * escala, 14) + 16, x_barra + 0.10 * escala + 16)
    ax.text(x_valor, y + alto / 2, f"{cer:.4f}".replace(".", ","), color=BLANCO,
            fontsize=16, fontweight="bold", va="center")
    if etiqueta:
        pastilla(x_valor + 95, y + 8, ancho_pastilla, etiqueta, color)

# Linea del criterio
xc = x_barra + 0.10 * escala
ax.plot([xc, xc], [270, 700], color=NARANJA, linewidth=2, linestyle=(0, (5, 4)))
ax.text(xc + 8, 262, "Criterio: CER ≤ 0,10", color=NARANJA, fontsize=12.5, va="center")
ax.text(75, 715, "*El CER de Tesseract refleja una configuración de Tika, no la calidad de Tesseract.", color=TENUE,
        fontsize=11.5, va="center")

# --- Tarjeta derecha: hallazgos
tarjeta(1250, 180, 630, 560)
ax.text(1285, 222, "Qué encontramos", color=BLANCO, fontsize=20, fontweight="bold", va="center")
hallazgos = [
    "El texto de imprenta o de pantalla se lee bien con el modelo actual: CER 0,12.",
    "docTR midió mejor: CER 0,048 y 0,31 s por página.",
    "Pero docTR pierde las tildes y la ñ.",
    "qantev las conserva (88,8 % de acierto), pero tarda 10 s por página.",
]
y = 285
for r in hallazgos:
    ax.add_patch(Rectangle((1285, y - 8), 6, 6, facecolor=VERDE, edgecolor="none"))
    lineas = textwrap.wrap(r, 44)
    for k, linea in enumerate(lineas):
        ax.text(1308, y + k * 27, linea, color="#e5e8f5", fontsize=15, va="center")
    y += len(lineas) * 27 + 30
ax.add_patch(FancyBboxPatch((1285, 612), 560, 100, boxstyle="round,pad=0,rounding_size=14",
                            facecolor="#0c0c22", edgecolor=BORDE, linewidth=1.2))
ax.text(1305, 640, "Estado", color=NARANJA, fontsize=14, fontweight="bold", va="center")
ax.text(1305, 677, "ServIA usa hoy el modelo actual. Integrar docTR\nqueda como mejora (cambio de requisito).",
        color=GRIS, fontsize=13, va="center", linespacing=1.5)

# --- Franja inferior: comparacion de los tres que importan
tarjeta(40, 770, 1840, 260)
ax.text(75, 808, "Los tres que importan", color=BLANCO, fontsize=20, fontweight="bold", va="center")
filas = ["Tiempo por página", "Memoria de GPU", "Acierto en tildes y ñ"]
cols = [
    ("docTR completo", VERDE, ["0,31 s", "0,71 GB", "14,2 %"]),
    ("qantev/trocr-large-spanish", GRIS, ["10,25 s", "2,35 GB", "88,8 %"]),
    ("trocr-large-handwritten (actual)", MORADO, ["8,52 s", "2,15 GB", "0 %"]),
]
x_fila, ancho_col = 75, 400
for r, fila in enumerate(filas):
    ax.text(x_fila, 893 + r * 48, fila, color=GRIS, fontsize=14.5, va="center")
for c, (nombre, color, valores) in enumerate(cols):
    x = 500 + c * 450
    ax.text(x, 843, nombre, color=color, fontsize=15.5, fontweight="bold", va="center")
    for r, v in enumerate(valores):
        ax.text(x, 893 + r * 48, v, color=BLANCO, fontsize=20, fontweight="bold", va="center")
ax.plot([480, 480], [830, 1005], color=BORDE, linewidth=1.5)

ax.text(1880, 1060, "Prediseño de referencia · cifras de specs/001-reconocimiento-texto-impreso", color=TENUE,
        fontsize=10.5, va="center", ha="right")
fig.savefig("output/prediseno_capturas_pantalla.png", facecolor=FONDO)
print("Generado: output/prediseno_capturas_pantalla.png")
