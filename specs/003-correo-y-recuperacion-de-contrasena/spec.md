# Spec 003 (paraguas) — Correo y recuperación de contraseña
Estado: implementada (003a y 003b)

> Este documento describe las debilidades pendientes solo en términos generales; el detalle de lo corregido está en el código y en las pruebas.

Historial: 07/10/2026 — borrador creado a partir de las decisiones de Andrés (D1 a D7) sobre el informe de preguntas del planner. 07/10/2026 — clarificación del revisor: Andrés respondió sus 8 preguntas (D8 a D15); la spec se **divide en dos** (003a «correo» y 003b «recuperación pública segura») y este archivo queda como **paraguas corto**. El estado sigue siendo borrador hasta su aprobación. 08/10/2026 — decisión de Andrés (validación de la 003a, decisión 2): RNF-08.2 se acota a los flujos de cuentas y a la bitácora; los demás registros de errores de la autenticación y de la auditoría pasan a la spec de autenticación (ver «Fuera de alcance» y «Documentos a actualizar»). 08/10/2026 — Andrés respondió las 4 preguntas del revisor sobre la 003b (ver su Historial): se precisa el hallazgo del almacén temporal de la recuperación y se actualiza D6. 12/10/2026 — Redacción para publicación: lo abierto en términos generales. 12/10/2026 — Cierre: la 003b quedó implementada y validada (08/10/2026) y sus documentos editados y exportados (12/10/2026); el paraguas pasa a «implementada».

## Contexto y objetivo

El correo electrónico lleva tres funciones de seguridad del sistema: la contraseña temporal de una cuenta nueva (RF-02), el restablecimiento de contraseña por el Administrador (RF-03, vía a) y la recuperación por código que hace el propio usuario (RF-03, vía b). Hoy el ERS las marca como parciales: el envío falla en silencio, el sistema responde «se envió» aunque no haya salido y el Administrador no se entera. Al revisar el código aparecieron además problemas de seguridad en el mismo módulo (la recuperación por código no protege el código ni limita los intentos, y hay funciones sensibles de correo y de restablecimiento sin sesión de Administrador: RNF-07).

El trabajo se divide en dos specs, para cuidar el tamaño (máximo 10 tareas cada una) y el orden:

| Spec | Qué hace | Tareas estimadas | Depende de |
|---|---|---|---|
| **003a — `specs/003a-correo-de-cuentas/`** (se hace primero) — **implementada (08/10/2026)** | Correo de las cuentas: restablecimiento por el Administrador (vía a), crear cuenta, tiempo máximo del envío (15 s), rutas de correo protegidas, retiro de `POST /auth/restablecer-contrasenna`, bitácora del resultado del envío, UTF-8, configuración del correo, contraseñas fuera de los registros, reloj controlable y correo simulado ampliado. | 8 (10 al planificar) | Spec 002 |
| **003b — `specs/003b-recuperacion-publica-segura/`** (enseguida) — **implementada (08/10/2026)** | Recuperación pública segura (vía b): código solo por correo, respuestas uniformes, límites, falla cerrada, clave de firma fuerte, bitácora de cada paso, interfaz. | 10 | 003a |
| 004 | Red de seguridad del backend con pytest | — | 003a y 003b (excepción E1) |
| 005 | Red de seguridad de extremo a extremo con Playwright | — | 004 |

Cada una tiene su propia lista de requisitos, pruebas, casos límite, criterios de finalización y tareas estimadas. Lo común vive **solo aquí**: el contexto, las decisiones D1 a D15, las excepciones E1 y E2, las referencias de mercado, el «Fuera de alcance» común, la lista consolidada de documentos a actualizar y la trazabilidad completa.

Las correcciones de errores no esperan a la red de seguridad (`.claude/rules/testing.md`); las funciones nuevas (los límites, el tiempo máximo del envío, la clave de firma y demás `[NUEVO]`) se adelantan con la excepción E1.

## Trazabilidad
- ERS: **RF-02**, **RF-03**, **RF-21**, **RF-22** (detalle del Historial), **RNF-07**, **RNF-08** (solo lo que cubre RNF-08.1 y RNF-08.2: contraseñas, códigos y correos fuera de los registros de los flujos de cuentas y de la bitácora (acotado el 08/10/2026); el mínimo de 8 caracteres en el servidor queda fuera), FS-03 (2.2.1), la sección 2.3.2, RNF-06, RNF-09 y RT-02 (el correo no es un servicio de IA; el entorno de desarrollo usa un servicio de pruebas externo solo con datos inventados), RT-07, RA-02 (2.4.3) y la dependencia organizacional de la cuenta de correo (2.5).
- Historias de usuario: HU-02, HU-03, HU-25, HU-01 y HU-04 (por RNF-08), HU-21, HU-22 y HU-24 (por RF-21, RF-22, RNF-07), y la nueva **HU-26** (propuesta, ver 003b). Casos de uso: CU-03, CU-04 (incluida FE-05), CU-05 (incluidas FA-02 y FE-02), CU-15, CU-01.
- «Estado actual» del ERS que cierran las dos specs: **RF-02** (aviso al Administrador cuando no sale el correo de una cuenta nueva) y **RF-03** (el envío falla en silencio y no hay alerta). Lo que **no** cierran:
  - La cuenta de correo institucional definitiva (dependencia organizacional, ERS 2.5).
  - **RF-03 sigue «Parcial»**: el último paso de la recuperación todavía acepta contraseñas desde 6 caracteres; el mínimo de 8 es RNF-08, de la spec de autenticación.
  - **RNF-07 no pasa a «Implementado»**: el ERS lo marca así hoy, pero no se cumple del todo: algunas funciones de la cuenta del propio usuario todavía no exigen token (pendiente de la revisión del módulo de autenticación). Al cerrar se propone pasarlo a «Parcial» con un «Estado actual» redactado en esos términos generales, más la regla `[NUEVO]` de la clave de firma. Corrige un error del ERS vigente (el PDF V1.4 dice «Implementado»; no pude comprobarlo contra el Word).
- Origen de cada requisito («detalla» = ya está en el ERS; `[NUEVO]` = el ERS no lo pide y se propone agregarlo al cerrar):

| Requisito | Spec | Origen | ERS | Historias | Casos de uso |
|---|---|---|---|---|---|
| RF-03.13, RF-03.14, RF-03.15 | 003a | detalla (vía a) | RF-03, RF-02, FS-03 | HU-25 | CU-05 (FA-02) |
| RF-02.1, RF-02.2 | 003a | detalla | RF-02 | HU-25, HU-02 | CU-05 (FE-02) |
| RF-03.16 (15 s) | 003a | `[NUEVO]` | RF-03, FS-03 | HU-03, HU-25 | CU-04, CU-05 |
| RF-03.17 (envío fallido) | 003a | detalla | RF-03, FS-03 | HU-03, HU-25 | CU-04, CU-05 |
| RF-03.18 (UTF-8) | 003a | `[NUEVO]` | RF-02, RF-03, RT-07 | HU-25, HU-03 | CU-04, CU-05 |
| RF-03.19 (configuración del correo) | 003a | `[NUEVO]` | RNF-06, ERS 2.5 | — | — |
| RNF-07.1 (ruta heredada), RNF-07.2 (rutas de correo) | 003a | detalla | RNF-07, RF-02 | HU-01, HU-02, HU-24 | CU-01, CU-02, CU-03 |
| RF-21.4 (resultado del envío) | 003a | detalla | RF-21, RF-02, RF-03 | HU-21, HU-24, HU-25 | CU-05 |
| RF-21.6 (detalle en el Historial) | 003a | detalla | RF-21, RF-22 | HU-22 | CU-15 |
| RNF-08.1, RNF-08.2 | 003a (y 003b) | `[NUEVO]` | RNF-08 | HU-01, HU-03, HU-04, HU-25 | CU-01, CU-04, CU-05, CU-06 |
| RA-02.9, RA-02.10 | 003a | `[NUEVO]` (infraestructura) | RA-02 | — | — |
| RF-03.1 (código solo por correo) | 003b | `[NUEVO]` | RF-03, RNF-07 | HU-03 | CU-04 |
| RF-03.2 (respuesta uniforme), RF-03.7 (caducidades y mensajes) | 003b | detalla | RF-03 | HU-03 | CU-04 (pasos 4 y 5, FE-01 a FE-04) |
| RF-03.3 (tiempo uniforme) | 003b | `[NUEVO]` | RF-03 | HU-03 | CU-04 |
| RF-03.4 (6 dígitos, solo cuenta Activa, 15 min) | 003b | detalla; generación criptográfica y código único vigente `[NUEVO]` | RF-03 | HU-03 | CU-04 |
| RF-03.5, RF-03.6, RF-03.8 | 003b | `[NUEVO]` | RF-03, RF-02 | HU-03 | CU-04 |
| RF-03.9 a RF-03.12 (límites), RF-03.20 (Redis caído), RF-03.25 (pérdida de claves) | 003b | `[NUEVO]` | RF-03, RF-21 | HU-03 | CU-04 |
| RF-03.21, RF-03.22, RF-03.23, RF-03.24 | 003b | `[NUEVO]` | RF-03, RNF-07 | HU-03 | CU-04 |
| RNF-07.3, RNF-07.4 (clave de firma) | 003b | `[NUEVO]` | RNF-07, RNF-06 | HU-01, HU-02, HU-24 | CU-01, CU-02, CU-03 |
| RF-21.1, RF-21.5 | 003b | detalla | RF-21 | HU-21, HU-24, HU-25 | CU-04, CU-15 |
| RF-21.2 (cada paso en la bitácora) | 003b | `[NUEVO]` | RF-21 | HU-21 | CU-04 |
| RF-21.3 (filtro y detalle) | 003b | detalla | RF-21, RF-22 | HU-22 | CU-15 |
| RA-02.11 | 003b | `[NUEVO]` (infraestructura) | RA-02 | — | — |

## Usuarios
- **Usuario Gubernamental** y **Administrador**, como personas que recuperan su contraseña (003b), y **Administrador**, que crea cuentas, restablece contraseñas y consulta la bitácora (003a). Actor secundario: el servicio de correo electrónico. Detalle en cada spec.

## Historias de usuario
- HU-03, HU-25, HU-02 y HU-22 (de la documentación) y la HU-NUEVA propuesta (**HU-26**, en la 003b). Detalle en cada spec.

## Decisiones de Andrés (07/10/2026)
Se conservan los identificadores porque las specs los citan. D1 a D7 son de la primera ronda; D8 a D15 son de la clarificación del revisor (la tabla de abajo muestra la correspondencia con sus 8 preguntas).
- **D1 — Clave de firma (opción personal).** La clave de firma de desarrollo se rotó el 07/10/2026 (fuera del repositorio); es una acción de Andrés, hecha. Se incluye el requisito RNF-07.3: la recuperación queda inhabilitada si la clave falta, es un valor de respaldo conocido o es débil (regla: D10). El archivo de ejemplo la define con un marcador. El manejo de la clave de firma fuera de la recuperación se endurecerá en el módulo de autenticación.
- **D2 — Mensaje.** Se conserva el del ERS tal cual («Si el correo existe en nuestro sistema, recibirás un email con las instrucciones»); no se cambian RF-03, HU-03 ni CU-04 por este texto.
- **D3 — Orden.** La 003 (ahora 003a y 003b) va antes de la red de seguridad (004 y 005): excepción E1.
- **D4 — Extremo a extremo.** Exención temporal al principio 4 solo para la parte visual, con seguimiento en la 005: excepción E2.
- **D5 — Redis caído.** Falla cerrado, con un error de «servicio no disponible» igual para todas las cuentas (RF-03.20 de la 003b); la bitácora tiene seis resultados (RF-21.1). La pérdida de claves se trata aparte (D12).
- **D6 — Tolerancia de tiempo.** 500 ms, medidos con la mediana de varias solicitudes (RF-03.3 de la 003b). Desde el 08/10/2026 esa medición es la **verificación manual** (`curl -w`); la prueba automatizada es determinista (envío simulado «colgado» y respuesta observada antes de liberarlo) y no mide tiempo real.
- **D7 — Inventario de rutas sin sesión.** No entra en la 003: va a la spec 004.
- **D8 — El fallo del envío en la recuperación pública se informa solo a la bitácora**, no al usuario (revelaría qué correos existen). Cambia el ERS: HU-03 (cuarto criterio de aceptación), RF-03 («manejo de errores» y «en caso de error»), CU-04 FE-05, FS-03 y ERS 2.3.2 (ver «Documentos a actualizar»). *(Pregunta 3 del revisor.)*
- **D9 — Dividir la spec** en la 003a «correo» (primero) y la 003b «recuperación pública segura» (enseguida); esta spec queda como paraguas. *(Pregunta 1.)*
- **D10 — Regla de la clave de firma fuerte** (RNF-07.3): al menos 32 caracteres y 12 caracteres distintos; se aceptan hexadecimal y base64; se rechaza además una lista de valores de respaldo y de ejemplo conocidos (incluido el marcador del archivo de ejemplo). Sustituye la regla de «3 clases de caracteres». La guía `openssl rand -hex 32` del archivo de ejemplo sigue siendo válida. *(Pregunta 2.)*
- **D11 — Límites** (RF-03.9 a RF-03.12): las solicitudes bloqueadas por un límite no cuentan para las 5 por hora ni reinician los 60 s; un código nuevo invalida el anterior (un solo código vigente por correo); la ventana de la hora es fija; cada contador sale del correo normalizado (minúsculas simples, espacios recortados, máximo 100 caracteres). Los límites son por correo; no hay límite por origen de red en esta versión (riesgo aceptado). Si un usuario queda sin poder pedir un código, el Administrador le restablece la contraseña (vía a). *(Pregunta 4.)*
- **D12 — Pérdida de claves de Redis: falla cerrado.** El código y su contador de intentos viven en la misma entrada: si falta, el código no se acepta y hay que pedir uno nuevo. «Redis no responde» es no contestar dentro de un tiempo de espera fijo (el valor lo decide el plan). El almacén temporal de la recuperación (Redis) requiere endurecer su configuración y su acceso; se atiende en una spec de infraestructura aparte (decisión de Andrés, 08/10/2026; no se cambia el `docker-compose.yml` aquí). *(Pregunta 5.)*
- **D13 — Retirar `POST /auth/restablecer-contrasenna`** (nadie en el frontend la usa); el restablecimiento queda solo en `POST /usuarios/{id}/resetear-contrasenna`. Hay una sola lógica de restablecimiento, con prueba de regresión (la ruta heredada responde 404). RNF-07.1 pasa a ser ese retiro. *(Pregunta 6.)*
- **D14 — El reloj se inyecta en el código** (sin dependencias nuevas ni librería de tiempo): una misma inyección sirve para el tiempo máximo del envío (15 s) y para las caducidades de 15 y 10 minutos, la ventana de la hora y los 60 s (RA-02.9). *(Pregunta 7.)*
- **D15 — Versionado.** Las specs se mantuvieron fuera del repositorio hasta corregir lo que describían; se publicaron con lo abierto en términos generales. *(Pregunta 8.)*

## Excepciones aprobadas
Aprobadas por Andrés el 07/10/2026; los planes las registran y el revisor las comprueba.

- **E1 — Orden de las specs (D3).** `.claude/rules/testing.md` pone las funciones nuevas después de la red de seguridad (specs 004 y 005). La 003a y la 003b se implementan **antes**, la 003a primero. Razón: los límites de la recuperación, el tiempo máximo del envío y la validación de la clave de firma son funciones nuevas, pero protegen el mismo flujo que se corrige: sin ellos, el código de 6 dígitos podría probarse por fuerza bruta; y las correcciones de errores (RNF-07.1, RNF-07.2, RF-02.1, RF-03.5, RF-03.14) no esperan a la red de seguridad.
- **E2 — Principio 4 de la constitución, solo la parte visual (D4).** Exención **temporal** para cuatro pantallas, que no tendrán prueba automatizada de la interfaz: (1) el mensaje del cuadro de reseteo (003a, RF-03.15); (2) la advertencia al crear la cuenta (003a, RF-02.2); (3) el detalle del registro en el Historial de Actividades (003a, RF-21.6; 003b, RF-21.3); (4) **las pantallas de la recuperación de contraseña** (003b, RF-03.23). El backend se cubre con pytest (incluido el texto exacto que devuelve la API) y la interfaz con la verificación manual de punta a punta en el navegador. **Seguimiento**: la spec 005 (Playwright) debe incluir una tarea que automatice esas cuatro pantallas; al retirar la exención se actualizan las specs. Se aprueba con el mismo criterio de la exención de RA-02.8 de la spec 002: limitada, justificada y con fecha de retiro conocida (la 005). **Retirada (21/10/2026, spec 005a)**: la exención E2 se retira: las cuatro pantallas tienen prueba de extremo a extremo en `specs/005-red-de-seguridad-extremo-a-extremo/` (cuadro de reseteo: RF-03.40; advertencia al crear la cuenta: RF-02.42; detalle del Historial: RF-21.40; recuperación de contraseña: RF-03.41), pendiente de la validación de la 005a.

## Fuera de alcance (común a la 003a y la 003b)
Pendiente de la **futura spec de autenticación** (retroactiva), a la que se pasan estos puntos:
- Endurecimiento del inicio de sesión y de las sesiones: spec de autenticación.
- Algunas funciones de la cuenta del propio usuario todavía no exigen token (pendiente de la revisión del módulo de autenticación).
- RNF-08: el mínimo de 8 caracteres exigido en el servidor (hoy acepta 6).
- El pie de los correos con vocabulario heredado («Gestión de Documentos Jurídicos») y los proveedores de correo del archivo de ejemplo que el sistema no soporta.
- El manejo de la clave de firma fuera de la recuperación se endurecerá en el módulo de autenticación (RNF-07.3 solo obliga a la recuperación).
- Otros registros de errores de la autenticación y de la auditoría pueden incluir datos de la excepción; se revisarán con el módulo de autenticación. Aceptado por Andrés el 08/10/2026 (validación de la 003a, decisión 2); RNF-08.2 queda acotado a los flujos de cuentas y a la bitácora.

Para la **spec 004** (red de seguridad del backend con pytest, matriz rol × endpoint del flujo F1): la prueba que recorre todas las rutas del servidor y comprueba que cada una exige sesión, salvo una lista explícita de excepciones (inicio de sesión y recuperación pública), con las excepciones conocidas marcadas como fallo esperado. No entra en la 003 (D7). Las rutas que la 003a sí corrige (RNF-07.1 y RNF-07.2) tienen su propia prueba de regresión.

Y además:
- Un límite por origen de red en la recuperación: los límites son por correo; no hay límite por origen de red en esta versión (riesgo aceptado).
- Un botón «Reenviar» el correo de una cuenta nueva (no está en el ERS).
- Una cuenta de correo institucional definitiva y el envío real a usuarios reales.
- Tablas o migraciones nuevas, cambios al `docker-compose.yml`, a los prompts o a los modelos de IA, y librerías o dependencias nuevas.
- Pruebas de extremo a extremo de la interfaz (Playwright): llegan con la spec 005a, que retira E2 (21/10/2026; retirada el 22/10/2026, cubierta por la 005a).

## Hallazgos para una revisión posterior (no se corrigen en la 003; ⚠️ `docker-compose.yml` es de «Pregunta antes»)
Decisión de Andrés (08/10/2026): la 003b **no toca** la configuración de Redis ni el `docker-compose.yml`.
- **Almacén temporal de la recuperación**: el almacén temporal de la recuperación (Redis) requiere endurecer su configuración y su acceso; se atiende en una spec de infraestructura aparte. La recuperación falla cerrada si el almacén no responde o pierde datos y no guarda el código en claro.

## Documentos a actualizar al cerrar
Con `/sdd-change` (aprobación de Andrés), sobre el Word vigente y con su PDF; el planner no los edita. «(003a)» y «(003b)» indican en qué cierre se actualiza cada punto.

- **ERS**:
  - RF-02 (003a): quitar el «Estado actual» del aviso; el mensaje de la cuenta con correo fallido.
  - RF-03: vía a (003a: el aviso al Administrador, la contraseña no cambia si el correo falla); vía b (003b: el fallo del envío se registra solo en la bitácora, el código no viaja en lo que recibe el navegador, los límites `[NUEVO]` RF-03.9 a RF-03.12, el último paso comprueba el estado, cada paso con su resultado en la bitácora); **«manejo de errores» y «en caso de error»** (D8); quitar el «Estado actual» del envío, **pero RF-03 sigue «Parcial»** (el mínimo de 8 caracteres es RNF-08; spec de autenticación). El mensaje de RF-03 **no cambia** (D2).
  - **FS-03** (2.2.1) (003a y 003b): «todo fallo de envío se informa» pasa a «se informa al Administrador; en la recuperación pública, solo a la bitácora».
  - **ERS 2.3.2** (003b): el fallo del envío en la recuperación pública se informa solo a la bitácora (D8).
  - **RNF-07** (003a y 003b): hoy figura «Implementado» y no lo está del todo; pasar a «Parcial» con un «Estado actual» general (ver «Trazabilidad») y agregar la regla `[NUEVO]` RNF-07.3 de la clave de firma, sin describir la falla anterior.
  - **RNF-08** (003a): la regla de no mostrar contraseñas, códigos ni correos completos en los registros de los flujos de cuentas y de la bitácora (RNF-08.1, RNF-08.2). No se propone al ERS «los correos se enmascaran en los registros del servidor» en general: el resto de los registros (autenticación y otros servicios de auditoría) queda para la spec de autenticación.
  - **RF-21** (003a y 003b): «Contenido del registro»: el resultado del envío de cada correo, los seis resultados de la solicitud y los de cada paso; **RF-22** (003a y 003b): el detalle muestra el resultado.
  - **RA-02** (2.4.3) (003a y 003b): la infraestructura de pruebas del backend ya está; agregar un párrafo del reloj controlable y de los simulados ampliados (RA-02.9 a RA-02.11).
  - **4.1 Matriz de trazabilidad** (003b): agregar la HU-26 a la fila de RF-03 y revisar las filas de RF-21, RF-22 y RNF-07/RNF-08. **2.5** «Dependencias organizacionales»: sin cambios de fondo.
- **Historias de usuario**: HU-03 (003b: cuarto criterio —el fallo del envío no se informa al usuario— y el límite de intentos), HU-25 (003a: la advertencia de notificación no entregada), HU-22 (003a y 003b: el detalle muestra el resultado) y la **HU-26 nueva** (003b), con su identificador en el documento.
- **Casos de uso**: **CU-04** FE-05 (003b: el sistema ya no muestra «Error enviando email de recuperación»: responde igual y deja el resultado en la bitácora; agregar los flujos de límites y de «servicio no disponible»; el mensaje de la respuesta uniforme no cambia, D2); **CU-05** FA-02 y FE-02 (003a: hoy dicen que «se restablece igualmente»: pasan a «la contraseña no se modifica y se informa al Administrador»; la creación de cuenta sigue creándose con la advertencia); CU-15 (003a y 003b: el detalle).
- **Procesos** (Word y PDF; código en `Diagramas/Procesos/`): **P6** «Recuperación, Cambio de Contraseña y Perfil» (003b) y **P7** «Administración de Cuentas de Usuario» (003a).
- **Diagramas** (PlantUML): los de CU-04 y CU-05 si reflejan el aviso; la arquitectura (C4), si se precisa, para señalar que la recuperación usa Redis (003b).
- **Archivo de ejemplo de configuración del backend**: se actualiza dentro de la implementación (003a: variables del correo y tiempo máximo; 003b: clave de firma con marcador), sin valores reales.
- **`.claude/agents/planner.md` y `coordinator.md`, `.claude/rules/testing.md`, `CLAUDE.md` («Verificación») y `MEMORY.md`**: Andrés decide (el planner no los edita). Todos hablan de **una sola** spec de red de seguridad; hoy son dos, la 004 (backend con pytest) y la 005 (extremo a extremo con Playwright), y la 003 son dos (003a y 003b) que se implementan antes de ellas con la excepción E1. En `MEMORY.md` anotar además la rotación de la clave de desarrollo del 07/10 (sin su valor), los hallazgos de Redis y, al cerrar, que el hallazgo de las rutas de correo sin sesión quedó corregido.
- **Spec 005 (cuando se cree)**: incluir la tarea de seguimiento de E2 (automatizar con Playwright las cuatro pantallas). **Spec 004**: incluir la prueba de inventario de rutas sin sesión (D7).

## Criterios de finalización del paraguas
- La 003a y la 003b están implementadas y validadas, cada una con sus criterios.
- La documentación de la lista de arriba está actualizada.
- Lo que siga abierto quedó redactado en términos generales antes de publicar las specs (D15).
- Ya no queda un «Estado actual» del ERS que solo esta spec describa.

## Dudas abiertas
Ninguna. Las dudas D1 a D7 y las 8 preguntas del revisor (D8 a D15) las resolvió Andrés el 07/10/2026. La 003a quedó implementada (08/10/2026) y la 003b también: Andrés la aprobó el 08/10/2026, el revisor la validó ese mismo día (27 requisitos cumplen; dos visuales bajo la exención E2) y su documentación oficial se editó y exportó el 12/10/2026. Las observaciones menores del revisor sobre la 003b se anotan en términos generales en las tareas de esa spec y no cambian el QUÉ.

## Referencias de mercado
Consulta del 07/10/2026. Los valores salen de resúmenes de búsqueda y de context7, **no de la lectura directa de cada página**: son una referencia para la decisión, no una fuente normativa.

| Tema | Referencia | Valor de ServIA |
|---|---|---|
| Tiempo máximo del envío SMTP | aiosmtplib: 60 s por omisión (github.com/cole/aiosmtplib, docs/timeouts.rst). Django `EMAIL_TIMEOUT`: ninguno (None). Flask-Mail `MAIL_TIMEOUT`: None. Nodemailer: conexión 120 s, saludo 30 s, socket 600 s (nodemailer.com/smtp). Spring Mail: infinito por omisión; su guía usa 5 s. Symfony y Laravel (PHP): unos 60 s. RFC 5321 §4.5.3.2: 2 a 10 min (mínimos entre servidores de correo, no una guía para peticiones web). | **15 s** (juicio del equipo: menos que los 30 s del navegador) |
| Recuperación de contraseña | OWASP ASVS (OTP fuera de banda): exige limitar la tasa, sin dar una cifra. Auth0: 10 intentos de OTP (foro de la comunidad: fuente secundaria). NIST SP 800-63B §5.2.2: techo de 100 fallos consecutivos. Laravel `throttle`: 60 s entre solicitudes y vigencia del enlace de 60 min (laravel.com/docs/passwords). ASVS: vigencia de 10 min. OWASP Forgot Password Cheat Sheet: mensaje y tiempo de respuesta uniformes; vigencia «rara vez más de una hora». | **5 intentos** (juicio del equipo); **60 s** entre solicitudes (estándar de hecho); **5 por hora por correo** (juicio del equipo, sin estándar encontrado); sin límite por IP en la 003 |
| Inicio de sesión (spec futura) | Endurecimiento del inicio de sesión y de las sesiones: spec de autenticación. | Fuera de la 003 |

**No confirmado**: los valores exactos de Cognito y de Firebase; los valores por omisión de `django-ratelimit` y de `ThrottleRequests` de Laravel; un máximo por hora estándar; el texto literal de NIST §5.1.1.2; el valor de OWASP para un código de 6 dígitos; la versión instalada de la librería de envío (no está fijada, `>=3.0.0`).
