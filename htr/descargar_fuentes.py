"""
Descarga tipografías manuscritas de Google Fonts (todas licencia SIL OFL)
y verifica que cubran los caracteres del español.

La OFL permite uso comercial y redistribución, por lo que las imágenes
generadas con estas fuentes no tienen restricción de licencia para el
proyecto.

Uso:
    .venv/Scripts/python.exe descargar_fuentes.py
"""

import urllib.request
import urllib.error
from pathlib import Path

# Google Fonts reparte las tipografías en dos carpetas según su licencia.
# Ambas son permisivas: OFL permite uso comercial, Apache 2.0 también.
BASES = {
    "ofl": "https://raw.githubusercontent.com/google/fonts/main/ofl",
    "apache": "https://raw.githubusercontent.com/google/fonts/main/apache",
}
DESTINO = Path(__file__).parent / "fuentes"

# Caracteres que el español necesita y que muchas fuentes manuscritas omiten.
CARACTERES_ESPANOL = "áéíóúüñÁÉÍÓÚÜÑ¿¡"

# Mezcla deliberada de estilos: imprenta a mano, cursiva ligada y trazo grueso.
# (licencia, carpeta, archivo, estilo)
#
# NOTA DE DOMINIO (dato del encargado, 15/09/2026): en Costa Rica la
# cursiva ligada ya no se enseña en las escuelas y no se usa a nivel
# general. El caso real del proyecto es LETRA DE IMPRENTA A MANO. Las
# cursivas se conservan con peso bajo (ver generar_sintetico.py) por si
# aparecen documentos de archivo escritos por personas de generaciones
# anteriores, pero no son el objetivo.
CANDIDATAS = [
    # --- imprenta a mano: el estilo objetivo ---
    ("ofl",    "patrickhand",        "PatrickHand-Regular.ttf",        "imprenta"),
    ("ofl",    "architectsdaughter", "ArchitectsDaughter-Regular.ttf", "imprenta"),
    ("ofl",    "indieflower",        "IndieFlower-Regular.ttf",        "imprenta"),
    ("ofl",    "kalam",              "Kalam-Regular.ttf",              "imprenta"),
    ("ofl",    "shadowsintolight",   "ShadowsIntoLight.ttf",           "imprenta"),
    ("ofl",    "gloriahallelujah",   "GloriaHallelujah.ttf",           "imprenta"),
    ("ofl",    "coveredbyyourgrace", "CoveredByYourGrace.ttf",         "imprenta"),
    ("ofl",    "reeniebeanie",       "ReenieBeanie.ttf",               "imprenta"),
    ("apache", "justanotherhand",    "JustAnotherHand-Regular.ttf",    "imprenta"),
    # --- trazo grueso: también letras separadas ---
    ("ofl",    "caveatbrush",        "CaveatBrush-Regular.ttf",        "trazo grueso"),
    ("ofl",    "sriracha",           "Sriracha-Regular.ttf",           "trazo grueso"),
    ("apache", "rocksalt",           "RockSalt-Regular.ttf",           "trazo grueso"),
    ("apache", "permanentmarker",    "PermanentMarker-Regular.ttf",    "trazo grueso"),
    # --- cursiva ligada: peso bajo, no es el objetivo ---
    ("ofl",    "caveat",             "Caveat%5Bwght%5D.ttf",           "cursiva"),
    ("ofl",    "dancingscript",      "DancingScript%5Bwght%5D.ttf",    "cursiva"),
    ("ofl",    "badscript",          "BadScript-Regular.ttf",          "cursiva"),
    ("ofl",    "marckscript",        "MarckScript-Regular.ttf",        "cursiva"),
    ("ofl",    "petitformalscript",  "PetitFormalScript-Regular.ttf",  "cursiva"),
    ("ofl",    "allura",             "Allura-Regular.ttf",             "cursiva"),
    ("ofl",    "cedarvillecursive",  "Cedarville-Cursive.ttf",         "cursiva"),
    ("apache", "homemadeapple",      "HomemadeApple-Regular.ttf",      "cursiva"),
]


def descargar(licencia: str, carpeta: str, archivo: str) -> bytes | None:
    """Baja un .ttf de google/fonts. Devuelve None si no existe."""
    url = f"{BASES[licencia]}/{carpeta}/{archivo}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.read()
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None


def cobertura_espanol(ruta: Path) -> tuple[bool, str]:
    """Revisa en el cmap de la fuente si están los caracteres del español."""
    from fontTools.ttLib import TTFont

    try:
        fuente = TTFont(ruta, fontNumber=0, lazy=True)
        disponibles: set[int] = set()
        for tabla in fuente["cmap"].tables:
            disponibles.update(tabla.cmap.keys())
        fuente.close()
    except Exception as e:
        return False, f"ilegible ({type(e).__name__})"

    faltantes = [c for c in CARACTERES_ESPANOL if ord(c) not in disponibles]
    if faltantes:
        return False, "faltan " + "".join(faltantes)
    return True, "completo"


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)

    print(f"Descargando {len(CANDIDATAS)} candidatas a {DESTINO}\n")
    print(f"{'FUENTE':<24} {'ESTILO':<14} {'KB':>6}  ESPAÑOL")
    print("-" * 68)

    aptas, descartadas, sin_descarga = [], [], []

    for licencia, carpeta, archivo, estilo in CANDIDATAS:
        datos = descargar(licencia, carpeta, archivo)
        if datos is None:
            print(f"{carpeta:<24} {estilo:<14} {'--':>6}  no encontrada en el repo")
            sin_descarga.append(carpeta)
            continue

        ruta = DESTINO / archivo.replace("%5B", "[").replace("%5D", "]")
        ruta.write_bytes(datos)

        ok, detalle = cobertura_espanol(ruta)
        print(f"{carpeta:<24} {estilo:<14} {len(datos)//1024:>6}  "
              f"{'OK' if ok else 'DESCARTADA'} - {detalle}")

        if ok:
            aptas.append((ruta.name, estilo))
        else:
            ruta.unlink()          # no sirve: la borramos para no usarla por error
            descartadas.append(carpeta)

    print("-" * 68)
    print(f"\nAPTAS: {len(aptas)}   descartadas por charset: {len(descartadas)}   "
          f"no encontradas: {len(sin_descarga)}")

    if aptas:
        print("\nFuentes utilizables por estilo:")
        for estilo in ("imprenta", "cursiva", "trazo grueso"):
            nombres = [n for n, e in aptas if e == estilo]
            print(f"  {estilo:<14} ({len(nombres)}): {', '.join(nombres) or '-'}")


if __name__ == "__main__":
    main()
