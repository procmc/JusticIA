# Tipografías — licencia y atribución

Las 21 tipografías de esta carpeta vienen de Google Fonts, repartidas en
dos licencias, **ambas permisivas y con uso comercial permitido**:

* **SIL Open Font License 1.1 (OFL)** — 17 fuentes. Exige que el aviso de
  copyright y la licencia **acompañen a los archivos de fuente**.
* **Apache License 2.0** — 4 fuentes.

El texto completo de cada licencia está en `licencias/`, tal como se
distribuye en https://github.com/google/fonts.

## SIL OFL 1.1

| Archivo | Proyecto | Licencia |
|---|---|---|
| `PatrickHand-Regular.ttf` | patrickhand | `licencias/OFL-patrickhand.txt` |
| `ArchitectsDaughter-Regular.ttf` | architectsdaughter | `licencias/OFL-architectsdaughter.txt` |
| `IndieFlower-Regular.ttf` | indieflower | `licencias/OFL-indieflower.txt` |
| `Kalam-Regular.ttf` | kalam | `licencias/OFL-kalam.txt` |
| `ShadowsIntoLight.ttf` | shadowsintolight | `licencias/OFL-shadowsintolight.txt` |
| `GloriaHallelujah.ttf` | gloriahallelujah | `licencias/OFL-gloriahallelujah.txt` |
| `CoveredByYourGrace.ttf` | coveredbyyourgrace | `licencias/OFL-coveredbyyourgrace.txt` |
| `ReenieBeanie.ttf` | reeniebeanie | `licencias/OFL-reeniebeanie.txt` |
| `CaveatBrush-Regular.ttf` | caveatbrush | `licencias/OFL-caveatbrush.txt` |
| `Sriracha-Regular.ttf` | sriracha | `licencias/OFL-sriracha.txt` |
| `Caveat[wght].ttf` | caveat | `licencias/OFL-caveat.txt` |
| `DancingScript[wght].ttf` | dancingscript | `licencias/OFL-dancingscript.txt` |
| `BadScript-Regular.ttf` | badscript | `licencias/OFL-badscript.txt` |
| `MarckScript-Regular.ttf` | marckscript | `licencias/OFL-marckscript.txt` |
| `PetitFormalScript-Regular.ttf` | petitformalscript | `licencias/OFL-petitformalscript.txt` |
| `Allura-Regular.ttf` | allura | `licencias/OFL-allura.txt` |
| `Cedarville-Cursive.ttf` | cedarvillecursive | `licencias/OFL-cedarvillecursive.txt` |

## Apache 2.0

| Archivo | Proyecto | Licencia |
|---|---|---|
| `JustAnotherHand-Regular.ttf` | justanotherhand | `licencias/APACHE-justanotherhand.txt` |
| `RockSalt-Regular.ttf` | rocksalt | `licencias/APACHE-rocksalt.txt` |
| `PermanentMarker-Regular.ttf` | permanentmarker | `licencias/APACHE-permanentmarker.txt` |
| `HomemadeApple-Regular.ttf` | homemadeapple | `licencias/APACHE-homemadeapple.txt` |

## Sobre las imágenes generadas

Ambas licencias restringen la redistribución de **los archivos de**
**fuente**, no de lo que se renderiza con ellos. Las imágenes producidas
por `generar_sintetico.py` no heredan restricción de licencia.

## Verificación de cobertura del español

`descargar_fuentes.py` revisa el `cmap` de cada fuente y **descarta** las
que no cubran `á é í ó ú ü ñ Á É Í Ó Ú Ü Ñ ¿ ¡`. Las 21 pasaron.
