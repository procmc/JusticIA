---
name: sdd
description: Úsala siempre que trabajes con Spec-Driven Development en ServIA (docs/constitution.md o cualquier archivo dentro de specs/) - redactar, revisar o cambiar specs, planes y tareas, o implementar y validar tareas de una spec.
---

# Spec-Driven Development (SDD) en ServIA

## Flujo

Constitución (`/sdd-constitution`) → Spec (`/sdd-spec`) → Clarificación (`/sdd-clarify`) → Plan (`/sdd-plan`) → Tareas (`/sdd-tasks`) → Implementación (`/sdd-implement`) → Validación (`/sdd-validate`) → Cambio (`/sdd-change`). En cualquier momento: `/sdd-status`.

- Nunca pases a la siguiente fase sin la aprobación explícita del usuario.
- La documentación de planificación (`Documentacion/Documentacion_ServIA_2026/`) define el producto; la spec detalla y vuelve verificable la parte que se construye ahora. Si la spec contradice al ERS, para y pregunta.
- La spec manda sobre el código: si algo no está en la spec, no se implementa. Si falta una decisión, para y pregunta.
- Un cambio de requisitos se hace primero en la spec, luego en el plan y las tareas, y por último en el código. Si cambia lo que el producto debe hacer, se actualiza también el ERS.
- Cada spec vive en su carpeta: `specs/NNN-nombre/` (desde `001`), con `spec.md`, `plan.md` y `tasks.md`.
- Al terminar cada fase, actualiza `MEMORY.md`.

## Plantilla de spec (spec.md)

```
# Spec NNN — <Nombre>
Estado: borrador | aprobada | en implementación | implementada

## Contexto y objetivo

## Trazabilidad
- ERS: RF-xx, RNF-xx · Historias de usuario: HU-xx · Casos de uso: CU-xx
- «Estado actual» del ERS que cierra: <requisito, o "ninguno">

## Usuarios
<Usuario Gubernamental, Administrador o ambos>

## Historias de usuario
- HU-xx (de la documentación). Si hace falta una nueva: HU-NUEVA. Como <rol>, quiero <acción> para <beneficio>.

## Definiciones (solo si hay términos que puedan interpretarse de varias formas)

## Requisitos funcionales

## Requisitos no funcionales

## Casos límite

## Fuera de alcance

## Criterios de finalización
- Cada requisito tiene al menos una prueba automatizada que pasa (o su exención justificada en el plan) y su verificación manual.

## Dudas abiertas
- [NECESITA ACLARACIÓN] <duda>
```

La spec describe el QUÉ y el POR QUÉ. Nada de stack, arquitectura ni nombres de archivos. En español y con el vocabulario del proyecto («tema», Usuario Gubernamental, Administrador).

## Requisitos en EARS (en español)

Cada requisito se numera a partir del RF/RNF del ERS que detalla: `RF-19.1`, `RF-19.2`, `RNF-08.1`… Si no corresponde a ningún requisito del ERS, se marca `[NUEVO]` y se propone agregarlo a la documentación.

- RF-xx.n: CUANDO <evento>, EL SISTEMA <respuesta>.
- RF-xx.n: SI <condición no deseada>, ENTONCES EL SISTEMA <respuesta>.
- RF-xx.n: MIENTRAS <estado>, EL SISTEMA <respuesta>.
- RF-xx.n: EL SISTEMA <comportamiento permanente>.

Ejemplo: RF-19.1: CUANDO el Usuario Gubernamental confirma que quiere quitar un documento de su notebook, EL SISTEMA elimina los fragmentos, el archivo y el registro de ese documento.

Cada requisito debe ser verificable y, salvo una exención justificada, comprobable con una prueba automatizada: nada de "rápido", "intuitivo" o "bonito" sin un criterio medible.

## Specs retroactivas (código existente)

El código heredado se cubre con specs retroactivas (orden en `.claude/rules/testing.md`). Una spec retroactiva documenta lo que el ERS define para un módulo que ya existe, con la misma plantilla:

- Sus requisitos salen del ERS, no del código. Donde el código no los cumple, el requisito se mantiene y se señala su «Estado actual».
- Su implementación consiste en escribir las pruebas: las que el código no cumple se marcan como fallo esperado (`xfail`) con su referencia, y se corrigen en tareas aparte, cada una con su prueba de regresión.
- Fuera de alcance: reescribir código que ya funciona.
- Al cerrarla, la spec queda en `specs/` como referencia viva del módulo (constitución, principio 2).

## Plan (plan.md)

Archivos y responsabilidades · Lógica por capa (router → servicio → repositorio) y dependencias externas (SQL Server, Qdrant, Ollama, Redis, HTR) · Algoritmo o flujo en pseudocódigo · Datos (migración de Alembic, metadatos de Qdrant, Redis; cómo se conservan los datos existentes) · Interfaz (roles, mensajes en español, `ROUTE_PERMISSIONS`) · Bitácora (RF-21) · Decisiones justificadas con su alternativa descartada · Pruebas (las unitarias, de integración y de extremo a extremo que cubren cada requisito, y la exención justificada de lo que no se pueda automatizar) · Verificación manual de punta a punta · Documentación que habrá que actualizar. Indica qué requisito cubre cada parte.

## Tareas (tasks.md)

```
- [ ] **Tn. <Descripción>.** RF-xx.n, RF-xx.m  ⚠️ <si toca algo de «Pregunta antes» de CLAUDE.md>
  - Pruebas: <las pruebas que se escriben primero>.
  - Hecho cuando: <esas pruebas y la suite completa pasan, y la comprobación de punta a punta se cumple>.
```

Máximo 20-30 min por tarea, en orden de dependencia (por ejemplo: migración → backend → Worker → frontend → verificación); cada tarea empieza por sus pruebas. La última tarea actualiza la documentación de planificación afectada. Si salen más de 10, propón dividir la spec.

## Implementación

Una sola tarea cada vez: primero las pruebas, comprobando que fallan, y los pasos de verificación manual con su resultado esperado; después el código; luego las pruebas de la tarea y la suite completa pasando, y la verificación manual cumplida; por último, marcar la tarea, actualizar `MEMORY.md` si corresponde y parar. Si la infraestructura de pruebas todavía no existe, solo se implementan tareas de esa spec. Ante algo de «Pregunta antes» que el plan no haya aprobado, detente y pregunta.

## Validación

Requisito por requisito: su prueba automatizada (debe pasar) y su comprobación de punta a punta (API, Qdrant, interfaz con los roles que correspondan y bitácora). Un requisito sin prueba automatizada que pase no se aprueba, salvo la exención justificada en el plan. La suite completa debe pasar. Sin arreglar nada durante la validación. Al final, veredicto y qué «Estado actual» del ERS se puede cerrar.
