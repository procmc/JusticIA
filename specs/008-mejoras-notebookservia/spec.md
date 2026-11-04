# Spec 008 — Mejoras de NotebookServIA
Estado: validada (04/11/2026): implementada (04/11/2026); validación del reviewer APROBADA

## Contexto y objetivo
- Dos arreglos del notebook que el ERS ya define, más la verificación pendiente de la 007:
  1. **Confirmar antes de quitar un documento** (RF-19): hoy la «x» lo quita sin preguntar; la e2e RF-19.40 (005b) lo prueba como fallo esperado.
  2. **Textos sin voseo** en la pantalla del notebook (decisión 9 de Andrés; precedente RF-16.61 de la 007): seis textos visibles en voseo.
  3. **Paso 8 de la verificación de la 007 (R-5)**: una imagen `PRUEBA` en un notebook; quedó como hueco declarado por falta de memoria.
- «Reintentar» del chat del notebook (RF-15) sale a una futura 008b (ver «Fuera de alcance»), por el plazo de 10 días.
- Son correcciones del módulo (testing.md, paso 3): primero la prueba que falla y después el código; los requisitos existentes del módulo siguen pasando.
- Presupuesto: **~4,5 h** (A ~1,5 h; C ~1 h; CF-1 ~0,75 h; verificación manual y propuesta de documentación ~1,25 h).

## Trazabilidad
- ERS V1.9: RF-05 (carga de imagen en el notebook), RF-09 (texto en imagen), RF-19, RF-21, RNF-04, RN-01, RT-07.
- HU-19 · CU-08, CU-09 (FA-05), CU-11 (paso 2), CU-13 (pasos 1-3, 9, FA-01).
- «Estado actual» que cierra: RF-19 (sin confirmación; pasa a Implementado). Completa el de RF-05. El de RF-15 sigue abierto (008b).
- Bloque de numeración: **.70+** (007: .60+). RF-19.40 conserva su número (005b).
- `[NUEVO]` marca un requisito que pide texto nuevo o cambiado en la documentación; sin la marca, solo detalla texto vigente.

## Usuarios
- Usuario Gubernamental: dueño del notebook; quita documentos y lee los textos.
- Administrador: no entra a NotebookServIA (RN-03); lo cubren las pruebas de acceso existentes, que siguen pasando.

## Historias de usuario
HU-19 (sin historias nuevas).

## Requisitos funcionales

### A. Confirmar antes de quitar un documento (RF-19, HU-19, CU-13)
- **RF-19.40** (005b; CU-13 pasos 2-3, FA-01): CUANDO el Usuario Gubernamental pulsa la «x» de un documento del notebook, EL SISTEMA muestra una confirmación con el nombre del documento y la advertencia de que no se puede deshacer, sin quitar nada todavía.
  - SI el usuario pulsa «Cancelar» o cierra la confirmación, ENTONCES el documento sigue en la lista y en el sistema, sin ninguna petición de quitar.
  - *Prueba*: la e2e existente de la 005b, a 1366 y 616 px; se quita su marca de fallo esperado tras verla en XPASS.
- **RF-19.70** (RF-19; CU-13 p. 2; decisión 5) `[NUEVO]`: EL SISTEMA muestra la confirmación con:
  - título «Quitar documento»;
  - cuerpo con el texto exacto, comillas incluidas: «¿Quitar "<nombre>" del notebook? Esta acción no se puede deshacer.»;
  - botones «Quitar» y «Cancelar».
  - CUANDO el usuario pulsa «Quitar», EL SISTEMA sigue el flujo vigente de RF-19 (deshabilitado mientras se quita, luego fuera de la lista y del chat).
  - SI el usuario pulsa «Quitar» dos veces seguidas (doble clic), ENTONCES EL SISTEMA envía una sola petición de quitar.
  - MIENTRAS un documento se está quitando, EL SISTEMA lo mantiene deshabilitado hasta que termine, aunque el usuario confirme quitar otro (cada documento conserva su propio estado).
  - SI el quitar falla tras confirmar, ENTONCES aplica RF-19.42 vigente (aviso y reintento); la confirmación ya está cerrada.
  - SI el documento desaparece con la confirmación abierta (quitado en otra pestaña), ENTONCES confirmar sigue el comportamiento vigente de RNF-07.40 (sesión y pantalla siguen).
  - Probado con documentos Procesado; la confirmación se muestra igual para Pendiente y Error (ver riesgo en «Fuera de alcance»).
  - A 616 px la confirmación cabe sin desborde horizontal con un nombre corto (el de las pruebas); el nombre largo queda fuera (D1).
  - Pulsar el documento fuera de la «x» sigue abriendo la vista previa (RF-18), sin confirmación.
  - Sin requisito propio de teclado (Escape, foco): se acepta el comportamiento del cuadro de confirmación del sistema.
  - *Prueba* (fundida en la e2e de RF-19.40, a 1366 y 616 px, decisión C3):
    - título, texto exacto del cuerpo, botones, «Cancelar» sin petición;
    - doble clic en «Quitar»: una sola petición de quitar, el documento sale de la lista y del chat;
    - con el quitar retenido por el control existente de la instancia: confirmar un segundo documento no habilita el primero.
  - Las e2e de RF-19.41, RF-19.42 y RNF-07.40 no cambian: su ayuda de quitar ya acepta la confirmación cuando aparece.
  - Las e2e localizan la «x» por la etiqueta accesible «close chip» del componente; si cambia, cambian las pruebas.
  - Desaparecer con la confirmación abierta: sin e2e propia (exención por presupuesto); verificación manual.
- **RF-21.70** (RF-21; CU-13 p. 9): EL SISTEMA registra en la bitácora solo el quitar confirmado, con el tipo existente de quitar documento del notebook; mostrar o cancelar la confirmación no registra nada.
  - *Prueba*: la e2e de RF-19.40 (cancelar: sin petición ni registro; quitar confirmado con doble clic: exactamente un registro).

### C. Textos sin voseo en la pantalla del notebook (RT-07; decisión 9; CU-11, CU-09 FA-05)
- **RT-07.70** (RT-07; CU-11 p. 2, CU-09 FA-05; decisión 9, precedente RF-16.61) `[NUEVO]`: EL SISTEMA muestra en la pantalla de NotebookServIA estos textos, en español neutro (usted):

  | Dónde | Hoy | Nuevo |
  |---|---|---|
  | Lista vacía | Todavía no tenés notebooks. Creá uno arriba. | Todavía no tiene notebooks. Cree uno arriba. |
  | Sin notebook abierto | Elegí o creá un notebook para empezar | Elija o cree un notebook para empezar |
  | Archivos en revisión | … — revisá antes de subir: | … — revise antes de subir: |
  | Arrastre sobre el chat | Soltá la imagen para subirla a "<nombre>" | Suelte la imagen para subirla a "<nombre>" |
  | Campo del chat | Preguntale algo a "<nombre>"... (podés pegar una imagen con Ctrl+V) | Pregúntele algo a "<nombre>"... (puede pegar una imagen con Ctrl+V) |
  | Error al subir | No se pudo subir el archivo. Intentá de nuevo. | No se pudo subir el archivo. Intente de nuevo. |

  - Formas con voseo buscadas: tenés, creá/Creá, elegí/Elegí, revisá, soltá/Soltá, preguntale/Preguntale, podés, intentá/Intentá.
  - CU-11 (p. 2) y CU-09 (FA-05) citan los textos viejos: quedan en desacuerdo con el sistema hasta aplicar la propuesta de documentación.
  - *Prueba* (decisión C3, sin e2e nuevas):
    - las aserciones e2e que hoy buscan el texto con voseo pasan a buscar el nuevo (vistas primero en rojo);
    - en las e2e que ya abren el notebook, a 1366 y 616 px: la pantalla no contiene ninguna forma buscada en tres estados: lista vacía, notebook abierto y archivos elegidos en revisión («revise»);
    - aviso de arrastre: un arrastre sintético de una imagen sobre el chat en una de esas e2e muestra el texto nuevo; si el plan comprueba que el evento sintético no lo reproduce, exención justificada y verificación manual;
    - error al subir: si una e2e existente ya provoca ese error, la aserción va ahí; si no, exención en el plan y verificación manual.
  - Hoy ninguna e2e arrastra ni pega una imagen sobre el chat del notebook (la carga se prueba eligiendo archivos).

### D. Requisitos existentes del módulo (testing.md, paso 3)
- Las e2e de notebooks, del chat del notebook (005b, 007), del chat general y de acceso por rol siguen pasando; solo cambian el texto que buscan (RT-07.70), las aserciones fundidas (RF-19.70, RT-07.70) y, si hiciera falta, el recorte de contingencia de RNF-04.70.

## Requisitos no funcionales
- **RNF-04.70** (RNF-04): la confirmación (A) y los textos (C) se prueban a 1366 y 616 px.
- **Presupuesto e2e** (RA-02.47; C3): la «suite» de `npm run e2e` queda **≤ 569 s** (límite 600 s; última medida 550,3 s).
  - Estimación: aserciones fundidas ~2-3 s a dos anchos → **~553 s**, con ~16 s de margen. No se espera recorte.
  - Contingencia (solo si dos corridas seguidas superan 569 s), en este orden, hasta quedar ≤ 569 s: pasar a solo 1366 px, con el mismo mecanismo «solo escritorio» que ya usa el chat del notebook,
    1. «RNF-07.40 · documento quitado en otra pestaña» (no depende del ancho);
    2. «RF-17.40 · otro usuario no lo ve» (no depende del ancho);
    3. «RF-18.40 · Pendiente y Error no se abren» (no depende del ancho).
  - Si tras el recorte 3 sigue por encima, parar y preguntar.
- **RN-01.70** (RN-01, RNF-10): lo único que se borra es el documento que el usuario confirma quitar (excepción vigente) y los datos `PRUEBA` de la verificación. Sin esquema nuevo, migración, dependencia, prompt ni modelo.

## Casos límite
- Dos «x» seguidas en documentos distintos: cada una pide su propia confirmación (RF-19.70).
- Un documento que cambia de estado con la confirmación abierta: confirmar lo quita igual.
- Un documento quitado en otra pestaña con la confirmación abierta: RNF-07.40 (RF-19.70).

## Fuera de alcance
- **Futura spec 008b (sin fecha, solo si hay tiempo)**: «Reintentar» del chat del notebook (RF-15, HU-15, CU-10 FA-01, CU-09 FE-01). Hereda lo ya decidido:
  - RF-15.70 (D1 = A): reintentar agrega al final la misma pregunta y la nueva respuesta, sin tocar lo anterior; RF-15.71: no lee ni cambia el campo de texto.
  - RF-15.72 (D2 = B, D3 = A, A1): reintentar con una respuesta en curso la cancela de verdad en el servidor (como la conexión cerrada de RF-16.62: deja de generar, libera el motor, sin historial RF-11.68 ni bitácora RF-21.60); la burbuja cancelada muestra «Consulta cancelada por el usuario» (con el texto parcial y un separador, o solo el aviso).
  - A1 incluye el arreglo de la cancelación compartido con el chat general (RF-15.74: el chat general no empeora).
  - RF-15.73: reintentar durante «Reintentando obtener respuesta...» o tras un error.
  - B1: RF-17.70 (abrir otro notebook cancela la consulta en curso sin alterar el que se abre) y RF-17.71 (Enter no envía durante una respuesta).
  - RF-21.71: cada reintento que termina se registra como consulta del notebook; las canceladas no.
  - Pruebas: e2e R1 (reintentar simple) y R2 (cancelaciones, cambio de notebook, Enter) solo a 1366 px, con secuencia de respuestas del motor simulado y un punto de sincronización con el motor retenido (señal de que el servidor abandonó cada consulta cancelada; quizá un control nuevo de la instancia ⚠️); integración: la desconexión de la 007 extendida al notebook.
  - E1: al cerrarla, RF-15 pasa de «Parcial» a Implementado y RF-15.72 entra al ERS.
  - Dudas que hereda: la prueba de RF-15.73 (aserción dentro de R1 si el control lo permite, o exención) y qué muestra el notebook anterior al volver tras RF-17.70 (recomendación: el aviso de cancelación).
- Borrar o archivar notebooks. Residuos pendientes: el notebook vacío 90003 (`PRUEBA 007 verificacion`) y el notebook `PRUEBA 006` (80003); sin spec reservada (decisión 2).
- «expediente» en el panel del Administrador y en las tarjetas de inicio, y «Poder Judicial» en el pie: van por `/feature` aparte (decisión 3).
- Arrastrar documentos (C4); el desborde del aviso y de la confirmación con un nombre muy largo (U2, C5, D1): por presupuesto (decisión 10).
- E2e de pegar o arrastrar una imagen real sobre el chat (RF-05): funciona, sin prueba automatizada; se anota en el «Estado actual» de RF-05.
- Riesgo vigente: quitar un documento Pendiente mientras el worker lo procesa puede dejar fragmentos tras quitarlo; no se prueba ni se corrige aquí.
- Textos en tuteo fuera de la tabla de RT-07.70: el estado vacío del chat (también con «JusticBot» y «jurídico») y un mensaje de error de conexión compartido por los chats.
- La calidad de la respuesta sobre una imagen (exenta, §14 de la 007) y cualquier cambio de prompts (decisión 6).

## Criterios de finalización
- Cada requisito con su prueba vista en rojo y luego en verde (o su exención en el plan); la marca de fallo esperado de RF-19.40 retirada tras verla en XPASS.
- `pytest` (normal e inverso): 0 fallos, 0 XPASS, sin fallos esperados nuevos. `npm run e2e`: «CORRECTO» (0 fallos, 0 XPASS, residuos 0, contraseñas 0), con un fallo esperado menos, dentro del presupuesto e2e.
- **CF-1. Paso 8 de la 007 (R-5)** (RF-05, RF-09, CU-08; decisiones 6-8): verificación manual, sin código. En desarrollo, en un notebook `PRUEBA`, una imagen PNG `PRUEBA` con texto tipeado (no manuscrito) que incluye una cadena distintiva inventada (p. ej. «PRUEBA-R5-K7Q2»).
  - ⚠️ El PNG es un archivo nuevo: se crea dentro del proyecto (el navegador del MCP solo sube desde ahí), en una carpeta que el plan elige y comprueba como ignorada por git; se borra al terminar y nunca se sube al repositorio.
  - Orden (decisión 8): sin suites en marcha y ≥ 1,5 GB libres → arrancar con `docker compose start` (nunca `up -d backend`, que levantaría el reconocimiento de imagen sin control) Tika, el worker y el reconocimiento de texto en imagen → subir la imagen por «Subir documentos» y esperar Procesado → comprobar en la base vectorial que algún fragmento bajo la clave del notebook contiene la cadena → detener el reconocimiento de imagen y el worker (libera memoria para el modelo) → consultar → quitar la imagen → detener Tika.
  - Si la cadena no está en la base vectorial, es un hallazgo del reconocimiento de imagen (no de R-5): se anota y decide Andrés.
  - Aprobación: «¿Qué dice la imagen?», a 1366 y 616 px, recibe una respuesta que incluye la cadena o su contenido (el texto llega al contexto y a la respuesta); la bitácora registra la carga y la consulta.
  - Exención: la calidad y la redacción de la respuesta. Si no responde con el texto: hallazgo y decide Andrés, sin cambiar prompts.
  - Limpieza: la imagen se quita desde la interfaz (con la confirmación de RF-19.70), 0 fragmentos del notebook en la base vectorial y el PNG borrado.
- Verificación manual (Andrés inicia sesión en la ventana del navegador; el agente no recibe contraseñas), 1366 y 616 px, consola sin errores:
  - quitar: cancelar no cambia nada; «Quitar» lo quita y deja un registro; un documento quitado en otra pestaña con la confirmación abierta;
  - los seis textos de RT-07.70, incluidos el arrastre y el error al subir;
  - el Administrador no entra a NotebookServIA.
- Propuesta de documentación a Andrés en la última tarea (decisión 11, opción A ajustada):
  - RF-19: quitar su «Estado actual» (→ Implementado);
  - RF-05: completar su «Estado actual» con la e2e pendiente de pegar o arrastrar una imagen y el resultado del paso 8;
  - CU-11 (p. 2) y CU-09 (FA-05): corregir las citas con voseo por los textos nuevos;
  - en el ERS, si Andrés lo aprueba: RF-19.70 y RT-07.70;
  - RF-15: su «Estado actual» sigue abierto (pasa a la 008b).

## Decisiones (Andrés, 04/11/2026)
- 1 alcance A+C+CF-1 (B a la 008b) · 2 sin borrado de notebooks · 3 textos heredados aparte · 4 suite ≤ 569 s · 5 texto y título de la confirmación («Quitar documento») · 6 R-5 fallido = hallazgo · 7 PNG tipeado temporal (archivo nuevo, se aprueba en su tarea) · 8 memoria y orden del paso 8 (detener HTR y worker antes de la consulta) · 9 voseo aquí · 10 C4 y C5 fuera · 11 documentación por propuesta (opción A ajustada).
- Revisión: C3 e2e fundidas con recorte solo de contingencia · D1 nombres largos fuera. A1, B1 y E1 pasan a la 008b.

## Dudas abiertas
- Ninguna. Resueltas: orden de CF-1 (detener HTR y worker antes de consultar) y título de la confirmación («Quitar documento»). Las de RF-15.73 y RF-17.70 pasan a la 008b.
