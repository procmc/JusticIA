"""
Graficas del reconocimiento de texto en imagenes (HTR) de ServIA.
Cifras tomadas de htr/README.md (Ciclo 1 y Ciclo de texto impreso, spec 001).

Ejecutar (local, con matplotlib): py graficas_htr.py
Output: output/htr_modelos_manuscrito.png
        output/htr_modelos_impreso.png
        output/htr_gpu_compartida.png
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch

plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]
AZUL, VERDE, MORADO, NARANJA, GRIS, ROJO = "#2563eb", "#16a34a", "#9333ea", "#ea580c", "#cbd5e1", "#dc2626"
TEXTO = "#1f2937"


def estilo(ax):
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(axis="y", length=0, labelsize=12, colors=TEXTO)
    ax.tick_params(axis="x", labelsize=11, colors="#6b7280")
    ax.xaxis.grid(True, color="#e5e7eb")
    ax.set_axisbelow(True)


# ---------------------------------------------------------------- manuscrito
modelos = [
    ("trocr-large-handwritten", 0.2771, 2.12, 0.271),
    ("trocr-base-handwritten", 0.3934, 1.29, 0.199),
    ("qantev/trocr-large-spanish", 0.4031, 2.32, 0.324),
    ("qantev/trocr-base-spanish", 0.6260, 1.49, 0.298),
    ("ifesther/trocr-spanish-handwritten", 0.6570, 1.29, 0.365),
]
fig, ax = plt.subplots(figsize=(11, 5.2), dpi=150)
y = list(range(len(modelos)))[::-1]
colores = [VERDE] + [GRIS] * 4
ax.barh(y, [m[1] for m in modelos], color=colores, height=0.62)
ax.set_yticks(y)
ax.set_yticklabels([m[0] for m in modelos])
for yi, m in zip(y, modelos):
    ax.text(m[1] + 0.012, yi, f"{m[1]:.3f}".replace(".", ","), va="center", fontsize=12, fontweight="bold", color=TEXTO)
    ax.text(1.02, yi, f"{m[2]:.2f} GB · {m[3]:.2f} s/línea".replace(".", ","), va="center", ha="right", fontsize=10.5, color="#6b7280")
ax.set_xlim(0, 1.03)
ax.set_xticks([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7])
ax.set_xticklabels(["0", "0,1", "0,2", "0,3", "0,4", "0,5", "0,6", "0,7"])
ax.set_xlabel("Tasa de error por carácter (CER) · menor es mejor", fontsize=11, color="#6b7280")
ax.set_title("Manuscrito: los cinco modelos evaluados", loc="left", fontsize=16, fontweight="bold", color=TEXTO, pad=34)
ax.text(0, 1.04, "18 líneas de letra humana real (imprenta a mano, foto de celular) · GPU liberada de Ollama",
        transform=ax.transAxes, fontsize=11, color="#6b7280")
estilo(ax)
fig.tight_layout()
fig.savefig("output/htr_modelos_manuscrito.png", facecolor="white")
plt.close(fig)

# ------------------------------------------------------------------- impreso
cands = [
    ("docTR completo 1.1.0", 0.0484, 0.31, 0.71, VERDE),
    ("trocr-large-spanish (qantev)", 0.0642, 10.25, 2.35, GRIS),
    ("trocr-large-handwritten\n(en producción)", 0.1208, 8.52, 2.15, MORADO),
    ("trocr-large-printed", 0.8401, 11.72, 2.35, GRIS),
    ("Tesseract (vía Tika)", 1.0000, 0.03, 0.0, ROJO),
]
fig, ax = plt.subplots(figsize=(11, 5.6), dpi=150)
y = list(range(len(cands)))[::-1]
ax.barh(y, [c[1] for c in cands], color=[c[4] for c in cands], height=0.62)
ax.set_yticks(y)
ax.set_yticklabels([c[0] for c in cands])
for yi, c in zip(y, cands):
    ax.text(min(c[1], 0.78) + 0.012, yi, f"{c[1]:.4f}".replace(".", ","), va="center", fontsize=12,
            fontweight="bold", color=TEXTO, bbox=dict(facecolor="white", edgecolor="none", pad=1.5))
    ax.text(1.27, yi, f"{c[2]:.2f} s/página · {c[3]:.2f} GB".replace(".", ","), va="center", ha="right",
            fontsize=10.5, color="#6b7280")
ax.axvline(0.10, color=NARANJA, linestyle="--", linewidth=1.5)
ax.text(0.108, 4.42, "Criterio: CER ≤ 0,10", color=NARANJA, fontsize=10.5, va="bottom")
ax.set_xlim(0, 1.28)
ax.set_ylim(-0.6, 4.9)
ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2])
ax.set_xticklabels(["0", "0,2", "0,4", "0,6", "0,8", "1,0", "1,2"])
ax.set_xlabel("Tasa de error por carácter (CER) · menor es mejor", fontsize=11, color="#6b7280")
ax.set_title("Capturas de pantalla: cinco candidatos", loc="left", fontsize=16, fontweight="bold", color=TEXTO, pad=34)
ax.text(0, 1.04, "10 capturas, 155 líneas de referencia · medición del 05/10/2026, sin red",
        transform=ax.transAxes, fontsize=11, color="#6b7280")
ax.legend(handles=[Patch(color=VERDE, label="Mejor medido"), Patch(color=MORADO, label="Usado hoy en ServIA"),
                   Patch(color=ROJO, label="Sin OCR de imágenes (error de configuración)")],
          loc="upper center", frameon=False, fontsize=10.5, ncol=3, bbox_to_anchor=(0.45, -0.14))
estilo(ax)
fig.tight_layout()
fig.savefig("output/htr_modelos_impreso.png", facecolor="white")
plt.close(fig)

# --------------------------------------------------------------- GPU compartida
fig = plt.figure(figsize=(12, 5.4), dpi=150)
gs = fig.add_gridspec(1, 2, width_ratios=[1, 2.1], wspace=0.18)

# Izquierda: la VRAM no alcanza con holgura
ax1 = fig.add_subplot(gs[0])
ax1.bar(0, 5.5, color=AZUL, width=0.55)
ax1.bar(0, 2.1, bottom=5.5, color=MORADO, width=0.55)
ax1.bar(0, 0.4, bottom=7.6, color="#e5e7eb", width=0.55)
ax1.axhline(8, color=ROJO, linewidth=1.6, linestyle="--")
ax1.text(0.33, 8.08, "Límite de la GPU: 8 GB", color=ROJO, fontsize=10.5, va="bottom", ha="center")
ax1.text(0, 2.75, "Ollama\nllama3.1:8b\n5,5 GB", ha="center", va="center", color="white", fontsize=11.5, fontweight="bold")
ax1.text(0, 6.55, "Servidor HTR\n2,1 GB", ha="center", va="center", color="white", fontsize=10.5, fontweight="bold")
ax1.text(0.37, 7.8, "0,4 GB libres", ha="left", va="center", fontsize=9.5, color="#6b7280")
ax1.set_xlim(-0.5, 1.05)
ax1.set_ylim(0, 9)
ax1.set_xticks([])
ax1.set_ylabel("Memoria de la GPU (GB)", fontsize=11, color="#6b7280")
ax1.set_title("Los dos juntos: 7,6 de 8 GB", fontsize=13, fontweight="bold", color=TEXTO, loc="left")
for lado in ("top", "right"):
    ax1.spines[lado].set_visible(False)

# Derecha: la solucion es repartir la GPU en el tiempo
ax2 = fig.add_subplot(gs[1])
ax2.set_xlim(0, 100)
ax2.set_ylim(0, 3)
ax2.axis("off")
ax2.set_title("La solución: turnarse la GPU en el tiempo", fontsize=13, fontweight="bold", color=TEXTO, loc="left")


def bloque(x0, x1, fila, color, texto=""):
    ax2.add_patch(FancyBboxPatch((x0, fila + 0.12), x1 - x0, 0.76, boxstyle="round,pad=0,rounding_size=0.15",
                                 facecolor=color, edgecolor="none"))
    if texto:
        ax2.text((x0 + x1) / 2, fila + 0.5, texto, ha="center", va="center", color="white", fontsize=10.5,
                 fontweight="bold")


ax2.text(-1, 2.5, "Ollama\n(chat)", ha="right", va="center", fontsize=11.5, color=TEXTO, fontweight="bold")
ax2.text(-1, 0.5, "Servidor HTR\n(imágenes)", ha="right", va="center", fontsize=11.5, color=TEXTO, fontweight="bold")
bloque(0, 24, 2, AZUL, "En GPU")
bloque(24, 44, 2, GRIS)
ax2.text(34, 2.5, "libera tras\n2 min sin uso", ha="center", va="center", fontsize=9.5, color="#6b7280")
bloque(44, 100, 2, GRIS)
bloque(0, 44, 0, GRIS)
bloque(44, 70, 0, MORADO, "En GPU")
bloque(70, 100, 0, GRIS)
ax2.text(85, 0.5, "libera a los 120 s\nsin peticiones", ha="center", va="center", fontsize=9.5, color="#6b7280")
ax2.annotate("", xy=(100, 1.5), xytext=(0, 1.5), arrowprops=dict(arrowstyle="->", color="#6b7280", lw=1.3))
ax2.text(50, 1.62, "tiempo", ha="center", va="bottom", fontsize=10, color="#6b7280")
ax2.text(45.5, 1.2, "El usuario sube\nuna imagen", ha="left", va="center", fontsize=9.5, color=MORADO, fontweight="bold")
ax2.plot([44, 44], [1.5, 0.88], color=MORADO, linewidth=1.3)

fig.text(0.02, 0.01, "Costo: la primera petición tras un período inactivo paga unos segundos de traslado. "
         "Nunca están los dos en la GPU a la vez (esquema ilustrativo).", fontsize=10.5, color="#6b7280")
fig.subplots_adjust(left=0.07, right=0.98, top=0.88, bottom=0.12)
fig.savefig("output/htr_gpu_compartida.png", facecolor="white")
plt.close(fig)
print("Graficas generadas en output/")
