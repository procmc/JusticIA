# CLAUDE.md — ServIA

Asistente de inteligencia artificial para el Sector Público de Costa Rica: carga documentos (texto, audio e imagen), responde en lenguaje natural citando la fuente y busca temas similares. Todo corre en infraestructura local, sin servicios de IA en la nube. Nació como JusticIA (Poder Judicial, 2025) y hoy lo conduce el MICITT — Dirección de Gobernanza. Lo desarrolla un único practicante.

## Stack y estructura

- **Backend** (`backend/`): FastAPI (Python 3.11), SQLAlchemy + Alembic sobre SQL Server 2022, Celery + Redis, LangChain con Ollama (`llama3.1:8b`), embeddings `intfloat/multilingual-e5-large` (1024 dimensiones) y Qdrant. Monolito modular: `app/routes` → `app/services` → `app/repositories` → `app/db/models`.
- **Worker** (`celery-worker`): el mismo código del backend en otro proceso; procesa la ingesta (Tika, faster-whisper, servidor HTR → fragmentos → Qdrant).
- **Frontend** (`frontend/`): Next.js 15 (pages router), React 18, NextAuth, HeroUI y Tailwind. Las llamadas a la API pasan por `services/httpService.js`; el acceso por rol, por `middleware.js` (`ROUTE_PERMISSIONS`).
- **`htr/`**: servidor de reconocimiento de texto en imagen (docTR + TrOCR, GPU) y herramientas de investigación. No es código del backend.
- **`diagrams/`**: generador de diagramas técnicos en Python (servicio `diagrams`, perfil `tools`).
- **`Documentacion/Documentacion_ServIA_2026/`**: Visión, StakeHolder, ERS, Historias de Usuario, Casos de Uso, Modelo de Dominio, Procesos, Arquitectura C4 y Modelo Relacional; el código PlantUML está en `Diagramas/<sección>/`. `Documentacion_JusticIA_2025/` es la del proyecto original.
- `docker-compose.yml` levanta 8 servicios; el frontend se ejecuta aparte con npm.

## Comandos

Desde la raíz del proyecto:

- Levantar: `docker compose up -d` · estado: `docker compose ps` · logs: `docker compose logs -f backend` (o `celery-worker`, `tika`).
- Aplicar cambios del backend: `docker compose restart backend celery-worker`. Si cambió `requirements.txt` o un Dockerfile: `docker compose build backend` y `docker compose up -d backend celery-worker`.
- Frontend: `cd frontend`, `npm install` (la primera vez o si cambió `package.json`), `npm run dev` → http://localhost:3000. Compilación de prueba: `npm run build`; estilo: `npm run lint`.
- Migraciones: el backend aplica `alembic upgrade head` al iniciar. Nueva migración: `docker compose exec backend alembic revision --autogenerate -m "..."`, y revisar el archivo generado antes de aplicarlo. Estado: `docker compose exec backend alembic current`.
- Salud: `curl http://localhost:8000/` (API), `curl http://localhost:6333/collections` (Qdrant), `docker compose exec ollama ollama list` (modelos).
- Diagramas: `docker run --rm -v "<carpeta>:/data" plantuml/plantuml -tpng "/data/*.puml"`.
- Herramientas locales de Claude Code: Poppler (`pdftoppm`), para leer los PDF de más de 10 páginas (`winget install oschwartz10612.Poppler`); el navegador para verificar la interfaz es el MCP `chrome-devtools` de `.mcp.json`.

## Convenciones

- Interfaz, respuestas del asistente, documentación y comentarios nuevos en español (RT-07).
- Vocabulario gubernamental: **tema**, no "expediente"; **Usuario Gubernamental**, no "Usuario Judicial". El código y la base de datos todavía conservan los nombres heredados (RT-06): el código nuevo usa el vocabulario nuevo, pero los nombres existentes no se renombran por cuenta propia.
- Backend: cada módulo sigue router → servicio → repositorio, y accede a SQL Server, Qdrant, Ollama y archivos solo a través del núcleo (`db`, `repositories`, `vectorstore`, `llm`, `services/documentos`).
- Base de datos: tablas `T_`; columnas `CN_` (número o identificador), `CT_` (texto) y `CF_` (fecha). Todo cambio de esquema va en una migración de Alembic.
- Toda acción relevante del usuario se registra en la bitácora mediante el servicio de auditoría de su módulo (`services/bitacora/`); si el registro falla, la acción continúa (RF-21).
- Frontend: una página nueva va también en `ROUTE_PERMISSIONS` (`middleware.js`) —si no, el middleware la bloquea— y en la navegación (`data/menuitems.js` y las tarjetas de `pages/index.js`).
- Diagramas: PlantUML con `!pragma layout elk` (líneas rectas, no curvas).

## Reglas de dominio / trampas conocidas

**Fuente de verdad**: los documentos de `Documentacion/Documentacion_ServIA_2026/` son de planificación: definen cómo debe comportarse el sistema y el código se ajusta a ellos. Donde el sistema todavía difiere, el ERS lo señala en un párrafo «Estado actual».

**LLM y RAG**:
- Los parámetros de `ChatOllama` (`num_ctx`, `num_predict`, `top_k`…) van como argumentos directos del constructor, no dentro de `model_kwargs`, donde se ignoran en silencio.
- Mantener `OLLAMA_NUM_PARALLEL=1`: con más ranuras, Ollama reparte el `num_ctx` entre ellas y trunca el contexto.
- Los modelos E5 necesitan el prefijo `query: ` (consultas) o `passage: ` (documentos); `embeddings.py` ya lo agrega. Documentos y consultas se vectorizan siempre con el mismo modelo.
- Filtros de Qdrant: LangChain anida los metadatos, así que la clave es `metadata.<campo>` (p. ej. `metadata.numero_expediente`), no `<campo>`.
- El nombre de archivo en los metadatos es `nombre_archivo`, no `archivo`; conservar el respaldo de `chunk_context_builder.py`.

**Ingesta**:
- En `extract_text_from_file()`, las imágenes van al servidor HTR antes que a Tika, porque Tika las leería con OCR de texto impreso.
- El manuscrito es una limitación aceptada (RF-10): corregir el texto con el LLM ya se probó y empeora el resultado.
- Límite de 1 GB por archivo, igual en frontend y backend; sin límite de cantidad.

**Datos**:
- `T_Documento` se une a los temas por la tabla intermedia `T_Expediente_Documento`; la columna `T_Documento.CN_Id_expediente` no existe.
- Un notebook usa como tema su clave interna `NB-<id>` (`clave_interna`).
- `CF_Ultimo_acceso = NULL` obliga a cambiar la contraseña temporal al iniciar sesión.
- Ningún registro se elimina físicamente (RN-01, RNF-10); la única excepción es quitar un documento de un notebook, que borra sus fragmentos en Qdrant, el archivo y la fila.

**Infraestructura**:
- El LLM y el HTR comparten una GPU de 8 GB, y cada uno libera la memoria de video tras 2 minutos sin uso. Antes de experimentos de GPU en `htr/`, detener Ollama.
- WSL2 necesita `memory=12GB` en `.wslconfig`. Si Docker Desktop deja de responder, se reinicia: los contenedores vuelven solos.
- En Git Bash, `docker run -v` con rutas de Windows requiere `MSYS_NO_PATHCONV=1`.
- No hay cuenta de correo configurada: los envíos de notificaciones fallan en silencio (pendiente institucional).

## Memoria

- Al empezar, lee `MEMORY.md` para conocer el estado del proyecto y las decisiones tomadas.
- Al terminar una tarea, actualízalo: estado actual, decisiones importantes (con su porqué) y errores a evitar.
- Máximo 200 líneas, sin pasarse de ese límite: resume o elimina lo que ya no aporte.
- Si algo se convierte en una regla permanente, propón moverlo a `CLAUDE.md` en lugar de dejarlo en la memoria.
- No guardes nunca datos sensibles (claves, contraseñas, tokens, datos personales): el repositorio es público.
- La bitácora de la práctica es aparte y privada; no se mezcla con `MEMORY.md`.

## Reglas

- Antes de tocar código, lee la constitución del proyecto (`docs/constitution.md`) y la spec activa (`specs/NNN-*/`), junto con los RF/RNF del ERS y los casos de uso que esa spec referencia.

## Forma de trabajar

Cambios pequeños y enfocados; no reescribas lo que ya funciona. Al terminar, resume qué cambió, qué requisitos (RF/RNF) toca y qué decisiones debe revisar el desarrollador.

- ✅ **Siempre**: textos en español y vocabulario «tema»; verificar contra el código real antes de afirmar algo; registrar en la bitácora las acciones nuevas de los usuarios.
- ✅ **Siempre**: escribir primero las pruebas del requisito y, al corregir un error, su prueba de regresión.
- ✅ **Siempre**: actualizar `MEMORY.md` al terminar cada tarea.
- ⚠️ **Pregunta antes**: crear archivos nuevos; cambiar el esquema de la base de datos o crear migraciones; renombrar "expediente" a "tema" en el código o la base de datos (requiere la confirmación del tutor); cambiar prompts, modelos de IA o el `docker-compose.yml`; hacer commit o push; borrar datos de SQL Server, Qdrant o `uploads/`.
- ❌ **Nunca**: subir credenciales, `.env`, documentos cargados o datos personales (el repositorio `procmc/JusticIA` es público); usar servicios de IA en la nube (RNF-09); incorporar modelos de origen chino (RT-04); `git push --force` ni reescribir el historial.

## Verificación

Cada requisito se aprueba con pruebas automatizadas (unitarias, de integración y de extremo a extremo) y, además, con la verificación manual de punta a punta (principio 4 de la constitución). El código heredado todavía no tiene pruebas (RA-02): se cubre con specs retroactivas, en el orden de `.claude/rules/testing.md`. Los comandos de las pruebas se agregan a «Comandos» al cerrar la spec de infraestructura de pruebas.

- Pruebas: la suite completa pasa; las pruebas usan un entorno aislado y nunca datos reales.
- Backend: `docker compose ps` sin reinicios, `curl http://localhost:8000/` responde y `docker compose logs backend celery-worker` no muestra errores.
- Ingesta: cargar un archivo de prueba no sensible y confirmar que queda Procesado y con sus fragmentos en Qdrant.
- Interfaz: con el navegador (Claude in Chrome o Chrome DevTools MCP) en http://localhost:3000, probar el flujo con los dos roles y revisar la consola. Las credenciales de prueba no se guardan en el repositorio.
- Frontend: `npm run build` sin errores.
- Al terminar, limpiar los datos de prueba (documento, fragmentos y archivo).
