# Spec 008b — «Reintentar» en NotebookServIA
Estado: validada (04/11/2026): implementada; validación del reviewer APROBADA

## Contexto y objetivo
- En el chat de NotebookServIA, «Reintentar consulta» aparece sobre la última pregunta, pero no hace nada (RF-15, «Estado actual»).
- Esta spec lo hace funcionar como en el Asistente Virtual y cierra tres huecos vecinos que el reintento deja a la vista:
  - una respuesta en curso que se reintenta debe cancelarse de verdad en el servidor;
  - abrir otro notebook con una respuesta en curso no debe mezclar conversaciones;
  - Enter no debe enviar con una respuesta en curso.
- Hereda lo decidido en la 008 («Fuera de alcance»): D1 = A, D2 = B, D3 = A, A1, B1 y E1.
- Son correcciones del módulo (testing.md, paso 3): primero la prueba que falla y después el código; los requisitos existentes del módulo siguen pasando.
- Presupuesto: **~6,5 h** (rango 5-8 h): spec, plan y tareas ~1 h; interfaz y cancelación compartida ~1,5 h; integración ~0,25 h; e2e ~2 h (escritura, depuración y dos corridas); verificación manual ~0,75 h; documentación, memoria y grafo ~0,75 h.

## Trazabilidad
- ERS V1.10: RF-15, RF-16 (RF-16.62), RF-11 (RF-11.68), RF-17, RF-21 (RF-21.31, RF-21.60), RNF-04, RN-01, RA-02.
- HU-15 · CU-10 (FA-01) · CU-09 (FA-05, FE-01, FE-02).
- «Estado actual» que cierra: RF-15 (pasa de Parcial a Implementado, E1).
- Bloque de numeración: **.70+**, siguiendo el bloque de la 008. Las decisiones de la 008 se citan con su letra.
- `[NUEVO]` marca un requisito que pide texto nuevo en la documentación; sin la marca, solo detalla texto vigente.

## Usuarios
- Usuario Gubernamental: dueño del notebook; pregunta, reintenta y cambia de notebook.
- Administrador: no entra a NotebookServIA (RN-03); lo cubren las pruebas de acceso existentes.

## Historias de usuario
HU-15 (sin historias nuevas).

## Requisitos funcionales

### A. Reintentar en el chat del notebook (RF-15, CU-10 FA-01)
- **RF-15.70** (D1 = A; RF-15, CU-10 FA-01): CUANDO el Usuario Gubernamental pulsa «Reintentar consulta» sobre su última pregunta en el chat de un notebook, EL SISTEMA vuelve a enviar esa pregunta con el alcance de ese notebook y agrega al final la misma pregunta y la nueva respuesta, sin cambiar ni borrar los mensajes anteriores.
  - La nueva respuesta sigue las reglas de RF-11 y RF-12 (etapas, cita, tope de 180 s, avisos de error) y se guarda en la conversación al terminar (RF-11.68).
- **RF-15.71** (RF-15, CU-10 FA-01): CUANDO el Usuario Gubernamental reintenta, EL SISTEMA usa el texto de la pregunta original, sin leer ni cambiar lo que haya escrito en el campo de texto.
- **RF-15.72** (D2 = B, D3 = A, A1; RF-15, RF-16.62) `[NUEVO]`: SI el Usuario Gubernamental reintenta mientras una respuesta está en curso, ENTONCES EL SISTEMA:
  - la cancela en el servidor: el motor deja de generar y queda libre, igual que con la conexión cerrada de RF-16.62;
  - no guarda ese turno en la conversación (RF-11.68) ni lo registra en la bitácora (RF-21.60);
  - deja en esa burbuja el texto parcial, un separador y el aviso «Consulta cancelada por el usuario», o solo el aviso si no había texto;
  - y luego inicia el reintento según RF-15.70.
  - A confirmar en el plan: qué alternativas descartaron D2 y D3; en la 008 solo constan sus letras, asignadas juntas a este requisito.
- **RF-15.73** (RF-15; CU-09 FE-01): CUANDO el Usuario Gubernamental reintenta durante «Reintentando obtener respuesta...» o después de una respuesta con aviso de error, EL SISTEMA aplica RF-15.72 si hay una respuesta en curso y RF-15.70 en todos los casos.
  - La pausa de «Reintentando obtener respuesta...» cuenta como respuesta en curso (P-4 = A): el reintento automático pendiente se anula y esa burbuja queda con «Consulta cancelada por el usuario».
  - Hoy la pausa es inalcanzable: desde la 007, el servidor sustituye la respuesta vacía por su aviso de «sin respuesta», así que «Reintentando…» no aparece. Esa mitad se implementa sin prueba (exención en el plan; decisión del 04/11/2026).
- **RF-15.74** (A1; RF-15, RF-11): EL SISTEMA cancela una consulta del chat de la misma forma en el Asistente Virtual y en el notebook, y una cancelación no impide cancelar la consulta que la sigue.
  - El arreglo es compartido por ambos chats (P3 = A); el Asistente Virtual no empeora: sus pruebas existentes siguen pasando.
  - A confirmar en el plan: en qué consiste el arreglo de A1, que la 008 no describe.
    - Hipótesis: la consulta abortada, al terminar, borra la referencia de cancelación de la consulta nueva y la deja sin poder cancelarse (cliente de consultas del chat, cierre de la consulta, hacia sus líneas 270-273).

### B. Consulta en curso y cambio de notebook (RF-17, B1)
- **RF-17.70** (B1, P1 = A; RF-17) `[NUEVO]`: CUANDO el Usuario Gubernamental abre otro notebook con una respuesta en curso, EL SISTEMA:
  - cancela la consulta en curso como en RF-15.72;
  - no escribe nada en la conversación del notebook que se abre;
  - al volver al notebook anterior, muestra la burbuja con el texto parcial y «Consulta cancelada por el usuario».
- **RF-17.71** (B1; RF-17, CU-09 FA-05): MIENTRAS una respuesta está en curso en el chat del notebook, EL SISTEMA no envía la pregunta al pulsar Enter, igual que el botón de enviar ya deshabilitado; el texto escrito se conserva.

### C. Bitácora (RF-21)
- **RF-21.71** (RF-21, RF-21.31, RF-21.60): EL SISTEMA registra cada reintento que termina como una consulta del notebook, con la clave del notebook como tema. No registra la consulta cancelada por reintentar ni por abrir otro notebook.
  - No hay tipo de acción nuevo ni migración.

### D. Requisitos existentes del módulo (testing.md, paso 3)
- Siguen pasando las e2e de notebooks, del chat del notebook (005b, 007, 008), del chat general y de acceso por rol, junto con las pruebas de integración de RF-16.62 y RF-21.31.

## Requisitos no funcionales
- **RNF-04.71** (RNF-04; P4 = A): una sola prueba e2e a 1366 px recorre reintentar, cancelar, cambiar de notebook y Enter, con una aserción por requisito (RF-15.70 a RF-15.73, RF-17.70, RF-17.71 y RF-21.71).
  - El ancho de 616 px queda en la verificación manual (exención por presupuesto).
- **RF-15.73, prueba** (P2 = A, ajustada el 04/11/2026): dentro de esa e2e se prueba solo la segunda mitad, reintentar tras una respuesta con aviso de error (fallo de conexión del motor simulado), en ≤ 5 s. La primera mitad (durante «Reintentando…») queda exenta en el plan por inalcanzable.
- **Integración**: la prueba de desconexión de RF-16.62 de la 007 cubre también el chat del notebook; si ya lo cubre, se cita.
- **Presupuesto e2e** (RA-02.47): la «suite» de `npm run e2e` queda **≤ 569 s** (límite 600 s; última medida 499,4 s; margen 69,6 s).
  - Estimación de la e2e nueva: ~15-25 s, sin medir.
  - Ante un tiempo alto, se repite la corrida antes de recortar. El recorte solo procede si dos corridas seguidas superan 569 s, y lo decide Andrés.
- **RN-01.71** (RN-01, RNF-10): nada se borra; solo los datos `PRUEBA` de la verificación. Sin esquema, migración, dependencia, prompt ni modelo nuevos.

## Casos límite
- Reformulación sesgada:
  - el reintento es una pregunta de seguimiento, y la reformulación usa los 2 últimos mensajes (CU-09 p. 8);
  - por eso puede reformularse con la pregunta y la respuesta anteriores y dar una respuesta distinta a la de una pregunta nueva;
  - se acepta: la calidad de la respuesta está exenta y no se cambian prompts.
- Reintentar varias veces seguidas: cada pulsación cancela la anterior en curso (RF-15.72); solo la última que termina se guarda y se registra.
- Reintentar justo cuando la respuesta termina: si ya terminó, no hay cancelación; vale RF-15.70.
- La conversación tiene un único «Reintentar»: el de la última pregunta, que tras reintentar es la copia agregada al final.
- Sesión vencida o notebook quitado durante el reintento: se aplica el manejo existente (RF-11 y RNF-07), sin requisito nuevo.

## Fuera de alcance
- La e2e de pegar o arrastrar una imagen sobre el chat (RF-05; sigue en su «Estado actual»).
- Borrar o archivar notebooks (residuos 90003, 80003 y 90004).
- «expediente» en el panel del Administrador y en las tarjetas de inicio, y «Poder Judicial» en el pie.
- Una e2e nueva de reintentar en el Asistente Virtual (P3 = A).
- Un botón «Detener» en el chat del notebook; los textos en tuteo del estado vacío del chat («JusticBot»).
- La calidad de la respuesta reintentada y cualquier cambio de prompts.

## Criterios de finalización
- Cada requisito tiene su prueba vista en rojo y luego en verde, o su exención en el plan.
- `pytest` (normal e inverso): 0 fallos, 0 XPASS y ningún fallo esperado nuevo.
- `npm run e2e`: «CORRECTO» (0 fallos, 0 XPASS, residuos 0, contraseñas 0), dentro del presupuesto e2e.
- Verificación manual con el motor real, a 1366 y 616 px y con la consola sin errores. Andrés inicia sesión; el agente no recibe contraseñas.
  - Reintentar con la respuesta terminada.
  - Reintentar con una respuesta en curso: el aviso y el motor libre.
  - Abrir otro notebook en curso y volver.
  - Enter con una respuesta en curso.
  - En la bitácora: un registro por reintento terminado y ninguno por cancelación.
  - El Asistente Virtual sigue cancelando y reintentando.
  - El Administrador no entra.
- Documentación (E1), como propuesta a Andrés en la última tarea:
  - RF-15 sin «Estado actual» y en estado Implementado;
  - RF-15.72 y RF-17.70 al ERS;
  - CU-10 FA-01: la cancelación de la respuesta en curso.

## Decisiones (Andrés)
- De la 008: D1 = A · D2 = B · D3 = A · A1 · B1 · E1. Se consignan con su letra y su significado en la 008; las alternativas de D2 y D3 quedan a confirmar en el plan.
- 04/11/2026: alcance completo · P1 = A (aviso de cancelación al volver) · P2 = A (RF-15.73 en la e2e si suma ≤ 5 s) · P3 = A (arreglo compartido, sin e2e del chat general) · P4 = A (una sola e2e a 1366 px).

## Dudas abiertas
- [A CONFIRMAR EN EL PLAN] En qué consiste A1 (hipótesis en RF-15.74).
- [A CONFIRMAR EN EL PLAN] Las alternativas descartadas por D2 y D3.
- [A CONFIRMAR EN EL PLAN] La señal de que el servidor abandonó la consulta cancelada. Puede bastar el estado del motor simulado; si hace falta un control nuevo de la instancia e2e ⚠️, se pregunta.
