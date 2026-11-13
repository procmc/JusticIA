# Plan 010 — Estudio del notebook (solo el cambio JJ1: ancho de las columnas)
La spec 010 se implementó sin plan ni tareas (decisión de Andrés, 09/11/2026). Este plan cubre **solo** el cambio JJ1 (sección G de la spec: RNF-04.123 a RNF-04.130), aprobado por Andrés el 12/11/2026. Lo demás de la 010 ya está implementado y su documentación sigue pendiente (ver `MEMORY.md`). Es solo de interfaz: sin backend, migración, bitácora, roles ni dependencias nuevas.

## 1. Archivos y responsabilidades
| Archivo | Cambio | Requisitos |
|---|---|---|
| **Nuevo** `frontend/hooks/notebooks/useAnchosDeColumnas.js` | Hook con toda la lógica: anchos de fábrica y límites (tabla de RNF-04.125), lectura y escritura en `localStorage` (`notebooks_anchos_columnas`, con `try/catch` y saneamiento), la función pura `limitarAncho` (mínimo, máximo y mínimo del chat), el ancho **efectivo** que se muestra cuando el área es angosta (RNF-04.129) y los controladores de arrastre, teclado y restablecer. | RNF-04.124 a 04.129 |
| **Nuevo** `frontend/components/notebooks/DivisorDeColumna.jsx` | La línea divisoria: `role="separator"`, `aria-orientation="vertical"`, `aria-label`, `aria-valuenow/min/max`, `tabIndex=0`, eventos de puntero con captura (mouse y dedo), teclado (flechas ±16, Mayús ±64, Inicio), doble clic, cursor `col-resize`, `touch-action: none`, solo desde `lg` (`hidden lg:block`). | RNF-04.124, 04.127, 04.128 |
| `frontend/pages/notebooks/index.js` (la lista `:547`, el `aside` de Fuentes `:644`, el del Estudio `:844`; el estado `plegados` `:86`) | Usa el hook; el ancho llega por variables CSS (`--ancho-lista`, `--ancho-fuentes`, `--ancho-estudio`) y las clases `lg:w-[var(--…)]` (hoy `w-56`, `lg:w-60`, `lg:w-64`); inserta un `DivisorDeColumna` en el borde derecho de la lista, el derecho de Fuentes y el izquierdo del Estudio, **solo si la columna no está plegada**; `data-testid` en las cuatro columnas; un `ref` en el contenedor para medir el área de contenido. El plegado existente (`plegados`, `alternarPanel`) no cambia. | RNF-04.123, 04.124, 04.129 |
| `frontend/e2e/flujos/notebooks-estudio.spec.js` | Pruebas nuevas (sección 4). | todos |
| `specs/010-estudio-del-notebook/tasks.md` | **Nuevo**: la tarea T1. | — |

## 2. Lógica y flujo
```
al cargar: anchos = leer(localStorage) → sanear (número, dentro de [mínimo, máximo]; si no, de fábrica)
área = ancho del contenedor (ResizeObserver)
efectivo(col) = ancho guardado, reducido hacia su mínimo si (lista + fuentes + estudio efectivos + 280 > área)   # no se guarda
arrastre (pointerdown en la línea):  inicio = ancho; en cada pointermove: nuevo = inicio ± dx   (Estudio: − dx)
    nuevo = limitar(nuevo): max(mínimo, min(máximo, área − 280 − otras columnas))
    se muestra al instante; al soltar (pointerup/cancel) se guarda
doble clic: ancho = de fábrica (esa columna) y se guarda
teclado:  ← → ±16 px (Mayús ±64), Inicio = de fábrica, con los mismos límites
< 1024 px: no hay líneas y los anchos guardados no se aplican (las clases `lg:` no se activan)
```
Una columna plegada conserva su riel (`w-12` / `lg:w-11`) y no tiene línea; al mostrarla vuelve a su último ancho (está guardado aparte).

## 3. Decisiones técnicas
- **D1. Variables CSS + clases `lg:w-[var(--…)]` de Tailwind.** El ancho solo se aplica desde `lg` y la vista pequeña no cambia. Alternativa descartada: `style={{ width }}` en línea (se aplicaría también a 616 px).
- **D2. Eventos de puntero con `setPointerCapture`** (mouse y dedo, y el arrastre no se pierde al salir de la línea). Alternativa descartada: `mousemove` en `window` (no cubre el dedo).
- **D3. Sin librería** (`react-resizable-panels` o similar): lo pide la regla de no sumar otra librería y son tres líneas. Alternativa descartada: la librería (dependencia nueva para algo pequeño).
- **D4. El ancho se guarda al soltar, no en cada movimiento.** Evita escribir cientos de veces en `localStorage`. Alternativa descartada: guardar en cada `pointermove`.
- **D5. El ancho reducido por un área angosta es solo de pantalla y no se guarda.** Así al ensanchar la ventana vuelve el ancho elegido (RNF-04.129). Alternativa descartada: guardar el valor reducido.
- **D6. Un solo objeto `{ lista, fuentes, estudio }` en una clave.** Como el plegado. Alternativa descartada: una clave por columna.

## 4. Pruebas (e2e, primero en rojo; solo escritorio salvo la última; datos `PRUEBA`)
En `notebooks-estudio.spec.js`, con `prepararNotebook`:
- **RNF-04.124:** arrastrar cada línea (`mouse.down/move/up` sobre el `separator` de su nombre accesible) cambia el ancho de la columna correcta en lo arrastrado (±2 px) y el chat cambia en lo contrario.
- **RNF-04.125:** arrastrar muy a la derecha o muy a la izquierda deja la columna en su máximo o mínimo, o en el ancho que deja al chat en 280 px (con ±2 px).
- **RNF-04.126:** el ancho sobrevive a una recarga; un valor dañado o fuera de límites en el almacenamiento (inyectado antes de cargar) deja los anchos de fábrica o el límite más cercano y sin errores en la consola.
- **RNF-04.127:** doble clic en la línea devuelve esa columna a su ancho de fábrica (224, 240 o 256 px).
- **RNF-04.128:** el `separator` tiene `aria-orientation`, nombre accesible, `aria-valuenow`; con el foco, `ArrowRight` suma 16, `Shift+ArrowRight` suma 64 y `Home` restablece.
- **RNF-04.129:** una columna plegada no tiene línea y, al mostrarla, vuelve a su último ancho elegido; a **616 px** (`pequena`) no hay ningún `separator` y los anchos guardados no cambian la vista.
- **RNF-04.130:** ninguna de las anteriores deja errores en la consola ni desplazamiento horizontal de la página.
- **No automatizable de forma fiable:** el uso con el dedo (Playwright simula punteros, no una pantalla táctil real) y la sensación al arrastrar; se cubren con la verificación manual.

## 5. Verificación manual (Andrés)
A 1366 px: arrastrar las tres líneas y ver que el chat toma el resto; llevarlas a los extremos; recargar y comprobar que se recuerda; doble clic en cada línea; probar con el teclado (Tab hasta una línea y flechas); plegar y mostrar una columna; reducir la ventana. A 616 px: no hay líneas y todo sigue como antes. Consola limpia.

## 6. Documentación (al cerrar) ⚠️
RNF-04 del ERS (una frase: las columnas del notebook se pliegan y su ancho se ajusta), una historia de usuario nueva; sin cambios en casos de uso, diagramas ni Modelo Relacional. Después `graphify update .` y `MEMORY.md`.
