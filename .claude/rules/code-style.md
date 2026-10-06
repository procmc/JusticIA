---
paths:
  - "backend/**/*.py"
  - "frontend/**/*.{js,jsx}"
---

# Estilo de código

## General

- Nombres del dominio en español, como el código existente: funciones con verbo (`crear_notebook`, `listar_notebooks_usuario`; `crearNotebook`, `listarNotebooks`) y «tema» en lo nuevo. Los términos técnicos (`router`, `service`, `chunk`) pueden quedar en inglés.
- Comentarios y docstrings nuevos en español, explicando el porqué, no el qué.
- No hay formateador automático (ni black/ruff ni prettier): respeta el formato del archivo y no reformatees líneas que no cambias, para que el diff muestre solo el cambio.
- Nada de URLs, puertos, rutas ni claves en el código: van en variables de entorno (`backend/app/config/config.py`; `NEXT_PUBLIC_*` en el frontend).
- No dejes código comentado, `print` ni `console.log` de depuración.

## Python (backend)

- PEP 8, 4 espacios y tipos en las firmas públicas (`def obtener_por_numero(self, db: Session, numero_expediente: str) -> Optional[T_Expediente]`).
- Cada módulo empieza con un docstring que dice qué hace y con qué se relaciona («Ver también»).
- Logging con `logger = logging.getLogger(__name__)`; dentro de un `except`, `logger.exception(...)` para conservar la traza.
- Repositorios: una clase por tabla en `app/repositories/`, con `db: Session` como primer argumento de cada método.
- Modelos: `app/db/models/<entidad>.py`, tabla `T_<Entidad>`, columnas `CN_`/`CT_`/`CF_`.
- Tipos de acción de la bitácora: desde `TiposAccion`, no como texto suelto.
- **Trampa:** no uses `MetadataFields` de `app/constants/metadata_fields.py`. Sus valores (`expediente_numero`, `archivo`) no coinciden con las claves que de verdad se guardan en Qdrant (`numero_expediente`, `nombre_archivo`; ver `vectorstore/storage.py`).

## JavaScript (frontend)

- Componentes funcionales con hooks, en `.jsx` y PascalCase (`DropZone.jsx`), agrupados por sección en `components/<seccion>/`; hooks propios `useAlgo.js` en `hooks/<seccion>/`; páginas en `pages/<seccion>/index.js(x)`.
- Interfaz con `@heroui/react` y clases de Tailwind; no agregues otra librería de componentes ni CSS suelto. Reutiliza `components/ui/` (`ConfirmModal` para confirmar, `CustomAlert` para avisos), `addToast` para notificaciones y los íconos de `components/icons/` (exportados en su `index.js`).
- Hay tema claro y oscuro: todo color lleva su variante `dark:` o usa las clases de HeroUI que ya cambian con el tema (`text-default-700`, `bg-default-50`).
- La interfaz se adapta a pantallas más pequeñas que la de escritorio (RNF-04).
- `npm run lint` (`next/core-web-vitals`) sin errores ni advertencias nuevas.
