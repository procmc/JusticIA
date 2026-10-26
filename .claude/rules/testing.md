---
paths:
  - "backend/**/*"
  - "frontend/**/*"
  - "specs/**/*.md"
  - "docs/constitution.md"
---

# Pruebas y verificación

Principio 4 de la constitución: cada requisito se cubre con pruebas automatizadas escritas antes del código y, además, con la verificación manual de punta a punta. Ninguna spec ni requisito se aprueba solo con verificación manual.

## Orden de trabajo

El código heredado no tiene pruebas (RA-02). Se cubre en este orden, cada paso como una spec:

1. **Infraestructura de pruebas del backend**: pytest dentro del contenedor del backend y un entorno aislado (base de datos y colección de Qdrant solo para pruebas). Playwright y el extremo a extremo llegan con el paso 2.
2. **Red de seguridad de los flujos críticos**: inicio de sesión y acceso por rol, subir un archivo → Procesado → el chat lo cita, y NotebookServIA, y la infraestructura de extremo a extremo. Hechos (specs 005a y 005b): la infraestructura de extremo a extremo, el acceso, la carga con la cita en el chat general y NotebookServIA; el resto del chat y la bitácora en el navegador, a la spec de su módulo.
3. **Cada spec prueba el módulo que toca** (sustituye a las specs retroactivas por módulo; decisión de Andrés, 22/10/2026): toda spec nueva o corrección escribe primero las pruebas de lo que cambia y de los requisitos existentes del módulo que modifica, contra el ERS; lo que el código no cumple, como fallo esperado con su referencia. Lo que ninguna spec toque queda como trabajo futuro documentado (su «Estado actual» en el ERS y una línea en `MEMORY.md`).
4. Con el paso 2 cerrado (spec 005b), empiezan las funciones nuevas y los «Estado actual» del ERS, cada una con sus pruebas desde el inicio según el paso 3.

- No crees pruebas ni dependencias de pruebas por fuera de la spec del paso 1 mientras esta no esté cerrada.
- Excepción aprobada (05/10): las herramientas de investigación de `htr/`, que no son código del backend, pueden tener su propia suite `pytest`, ejecutada en el contenedor `servidor-htr` (`docker compose exec servidor-htr pytest`), antes de que se cierre el paso 1. Integrar sus resultados al pipeline de ingesta sí espera al paso 2.
- Las funciones nuevas esperan a que el paso 2 esté cerrado; las correcciones de errores, no.
- Un módulo se da por hecho cuando todas sus pruebas pasan.

## Tipos de prueba

- **Unitarias**: la lógica del backend (servicios, validaciones, armado de filtros y prompts), con SQL Server, Qdrant, Ollama y Redis simulados.
- **Integración**: la API contra SQL Server, Qdrant y Tika reales del entorno aislado (Redis simulado): rutas y roles, datos guardados, fragmentos en Qdrant y registro en la bitácora.
- **Extremo a extremo**: los flujos de la interfaz en el navegador con los dos roles, incluida una pantalla más pequeña (RNF-04), desde la spec de la red de seguridad. Existe desde la spec 005a: `npm run e2e` (Playwright, instancia aislada `servia_pruebas_e2e`).

## Cómo se escriben

- Cada prueba indica el requisito que cubre (`RF-19.1`). La meta es que cada requisito tenga al menos una prueba que pase, no el 100 % de cobertura de líneas: la cobertura (skill `pytest-coverage`) es un indicador para encontrar huecos, no un objetivo.
- Primero la prueba, y se comprueba que falla; después el código.
- **Spec retroactiva**: las pruebas se escriben contra lo que dice el ERS, no contra lo que hace el código. Si el código no lo cumple (un «Estado actual»), la prueba se marca como fallo esperado (`xfail`) con la referencia al requisito, y la marca se quita cuando se corrige.
- **Errores**: toda corrección empieza por una prueba de regresión que falla con el error y pasa con la corrección.
- **LLM**: sus respuestas no son deterministas. Se prueba la estructura (cita la fuente, se limita al tema o notebook correcto, responde en español), no el texto exacto. En las unitarias, Ollama se simula.
- Las pruebas nunca tocan datos reales: solo el entorno aislado, y cada una limpia lo que crea.
- Las pruebas existentes no se borran ni se desactivan para que algo pase.

## Verificación manual (además de las pruebas)

1. Aplica el cambio: `docker compose restart backend celery-worker` (o `build` si cambiaron dependencias). El frontend con `npm run dev` recarga solo.
2. Backend sano: `docker compose ps` sin reinicios y `docker compose logs --tail 100 backend celery-worker` sin errores nuevos.
3. Recorre el flujo en el navegador (Claude in Chrome o Chrome DevTools MCP) con cada rol que corresponda —y comprueba que el otro rol NO puede entrar—, en escritorio y en una pantalla más pequeña (RNF-04), con la consola sin errores.
4. Confirma el efecto en los datos, no solo en la pantalla: la fila en SQL Server (sin borrados físicos, RN-01), los fragmentos en Qdrant con su clave (`metadata.numero_expediente`) y la acción en la bitácora (RF-21).
5. Casos de error: datos inválidos, sesión vencida, recurso de otro usuario (404) y un servicio detenido (Ollama o Qdrant), con mensaje en español y sin pantalla rota.
6. Si cambió el frontend: `npm run build` sin errores.

## Datos de prueba

- Solo datos inventados y no sensibles: nada de documentos institucionales reales ni datos personales.
- Nómbralos con el prefijo `PRUEBA` (notebook «PRUEBA hooks», archivo `prueba_contrato.pdf`) para encontrarlos y limpiarlos.
- Al terminar la verificación manual, límpialos: documento, fragmentos en Qdrant, archivo en `uploads/` y filas de prueba. Prefiere quitarlos desde la interfaz; por terminal, el hook `validate-bash.sh` pide confirmación.
- El borrado físico de los datos de prueba que la propia suite crea, solo en el entorno aislado, es la excepción aprobada a RN-01 y RNF-10 (constitución, principio 5; «Datos» de `CLAUDE.md`): nunca se aplica a datos reales.
- Las contraseñas de prueba las genera la suite en cada corrida y no se escriben ni se muestran; las de la verificación manual no se escriben en ningún archivo del proyecto: las da Andrés.

## Evidencia

Reporta la salida de las pruebas (cuántas pasan, cuántas fallan y cuántas son fallos esperados) y la del extremo a extremo cuando la tarea toca el frontend o la API, y lo que observaste en la verificación manual. Sin evidencia, la tarea no está hecha.
