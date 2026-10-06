---
description: SDD · Valida la spec requisito por requisito (pruebas automatizadas + verificación de punta a punta)
argument-hint: <carpeta-de-la-spec>
disallowed-tools: Edit, Write, NotebookEdit
agent: reviewer
---
Recorre `specs/$1/spec.md` requisito por requisito, con el RF/RNF del ERS de cada uno.

Primero ejecuta la suite completa de pruebas y muestra el resultado (cuántas pasan, fallan y son fallos esperados): ninguna prueba existente puede romperse.

Para cada requisito indica cómo se comprobó y el resultado:
- Sus pruebas automatizadas y su resultado. Un requisito sin prueba automatizada que pase no se aprueba, salvo la exención justificada en el plan. Revisa también que las pruebas comprueben de verdad el requisito y no usen datos reales.
- Además, compruébalo de punta a punta según la línea "Hecho cuando:" de `tasks.md` y la sección «Verificación» de `CLAUDE.md`: la API y los logs, la ingesta y los fragmentos en Qdrant, y la interfaz con el navegador (Claude in Chrome o Chrome DevTools MCP) con los roles que correspondan, revisando la consola y una pantalla más pequeña que la de escritorio sin funciones rotas (RNF-04).
- Si el requisito registra acciones del usuario, confirma que quedan en la bitácora (RF-21).
- En una spec retroactiva, cada fallo esperado (`xfail`) debe corresponder a un «Estado actual» real del ERS.

Usa solo archivos de prueba no sensibles y limpia los datos de prueba al terminar.

Si algún requisito no está cubierto o falla, dilo claramente. NO arregles nada todavía.

Después comprueba los criterios de finalización y dame un veredicto: ¿la spec está cumplida? Si lo está, indica qué «Estado actual» del ERS se puede cerrar y qué documentos habría que actualizar.
