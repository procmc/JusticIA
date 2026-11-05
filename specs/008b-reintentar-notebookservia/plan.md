# Plan — Spec 008b: «Reintentar» en NotebookServIA
Estado: aprobado (04/11/2026). Decisiones P-1 a P-4 en §12.

> Parte de la spec aprobada el 04/11/2026; no la repite, remite a sus requisitos. Código ubicado con `Grep` y `Read` por rangos en `fase4` (04/11/2026); no se consultó el grafo: los símbolos están en pocos archivos conocidos.

## 1. Enfoque
- Frontend, pruebas e2e y una prueba de integración; sin cambios en el código de `backend/app/`, esquema, migración, dependencia, prompt, modelo ni `docker-compose.yml` (RN-01.71).
- El servidor ya cancela al cerrarse la conexión (RF-16.62, `general_chains.py:161`, `:228`) y ya registra el chat del notebook como «notebook» (`rag.py:159-161`, RF-21.31).
- Corrección del módulo (testing.md, paso 3): primero la prueba que falla y después el código.
- Ningún archivo nuevo. ⚠️ T2 toca el control de la instancia e2e (código de pruebas; aprobado, P-2 = A).

## 2. Archivos

| Archivo | Cambio | Requisitos |
|---|---|---|
| `frontend/services/consultaService.js` | `finally` (`:270-273`): anular la referencia solo si es el controlador propio (§3). | RF-15.74 |
| `frontend/pages/notebooks/index.js` | `enviarPregunta`, `reintentar`, `cancelarEnCurso`; `onRetry` (`:529`); `seleccionarNotebook` (`:115`); Enter (`:536`) (§4). | RF-15.70 a .73, RF-17.70, RF-17.71 |
| `frontend/e2e/flujos/notebooks.spec.js` | E2e única nueva (§6). | todos, RNF-04.71 |
| `frontend/e2e/soporte/control.js` | Lectura de `abandonados` si `chatEstado` no lo trae ya (se comprueba en T2). | RF-15.72 |
| `backend/tests/instancia_e2e/simulados_e2e.py` ⚠️ | Contador `abandonados` en el envoltorio del turno (`:1005-1020`) y en `estado` (`:1056-1061`); se pone a 0 al restablecer. | RF-15.72, RF-17.70 |
| `backend/tests/unitarias/test_instancia_e2e.py` | Prueba del contador. | RA-02.49 |
| `backend/tests/integracion/test_chat_contexto.py` | `test_desconexion_antes_y_despues_cancela` (`:286`) parametrizada con `TRES_CHATS` (hoy solo general: `_cuerpo(..., {})`). | RF-16.62, RF-11.68, RF-21.60, RF-21.71 |

`Chat.jsx` y `messageUtils.js` no cambian (el arreglo de FE-01 es hallazgo, P-3).

## 3. A1: la cancelación compartida (RF-15.74)
- Confirmado leyendo el código:
  - la consulta nueva (`:128-134`) aborta el controlador anterior y guarda el suyo de forma síncrona;
  - el `AbortError` de la anterior se procesa después (microtarea) y su `finally` pone `this.abortController = null`, borrando el de la nueva.
- Efecto: la segunda cancelación seguida no cierra nada; la consulta sigue en el servidor y, al terminar, se guarda y se registra. Afecta también al Asistente Virtual.

```
consultaGeneralStreaming(...):
  si this.abortController → abort()
  const propio = new AbortController(); this.abortController = propio
  ... (sin cambios)
  finally: si this.abortController === propio → this.abortController = null
```

- Regresión: no hay pruebas unitarias del frontend (`package.json` solo tiene `e2e`). La cubre el paso 2 de la e2e (dos reintentos seguidos: 2 conexiones abortadas y 2 abandonos).

## 4. Notebook (`pages/notebooks/index.js`)

```
enviarPregunta(query):                    (el cuerpo actual de handleEnviarMensaje, :294-329, sin setTexto)
handleEnviarMensaje():  query = texto.trim(); si vacío o hayEnCurso() → nada; setTexto(''); enviarPregunta(query)
reintentar(textoPregunta):                (RF-15.70, .71: no lee ni toca `texto`)
  cancelarEnCurso(); enviarPregunta(textoPregunta)
hayEnCurso(): currentRequestRef.current?.active || streamingMessageIndex !== null || hayReintentoAutomaticoPendiente
cancelarEnCurso():                        (RF-15.72, .73, RF-17.70)
  si no hayEnCurso() → nada
  consultaService.cancelConsulta()
  currentRequestRef.current = { active: false, id: 'cancelada' }   (no null: el temporizador de FE-01, messageUtils.js:353, se dispara con null)
  marcar con markMessageAsCanceled la burbuja en curso (o la de «Reintentando…», P-4)
  setStreamingMessageIndex(null); setIsTyping(false)
  devolver los mensajes marcados
seleccionarNotebook(nb):                  (RF-17.70)
  si hayEnCurso(): marcados = cancelarEnCurso(); saveNotebookChatToSessionStorage(anterior.id, sessionId, marcados)
  ... (sin cambios: restaurar o sesión nueva)
Input.onKeyDown: Enter → handleEnviarMensaje (que ya comprueba hayEnCurso)   (RF-17.71)
MessageList onRetry={reintentar}
```

- Burbuja de «Reintentando…» (P-4): se reconoce por `isRetrying: true` (`messageUtils.js:347`). Durante la pausa de 1,5 s, `currentRequestRef` vale `null`. Al poner la marca `'cancelada'`, el temporizador ya no relanza (`:353`).
- Guardado explícito del notebook anterior: el efecto de `:141-145` se ejecuta ya con el notebook nuevo.
- Índice de la burbuja nueva: `messages.length + 1` sigue siendo correcto, porque marcar como cancelada no cambia la longitud.

## 5. Contador `abandonados` (T2 ⚠️, P-2 = A)
- En `envolver_turno`, una bandera `terminado` se activa al emitir una línea `done` o `error`. En el `finally`, si no terminó, `abandonados += 1` bajo candado.
- `estado()` lo devuelve; `configurar`/`restablecer` lo ponen a 0 (la limpieza tras cada prueba lo deja en 0).
- Por qué no basta lo existente: el motor retiene en un hilo (`Compuerta.esperar`, `:574-584`). Cancelar en el servidor no suelta ese hilo, así que `esperando` sigue en 1. `consultas` cuenta llamadas, no abandonos.
- Con `abandonados` alcanzado, liberar el motor ya no puede registrar la consulta cancelada.

## 6. E2e única (RNF-04.71: solo 1366 px)
- Título: «RF-15.70 · reintentar, cancelar, cambiar de notebook y Enter». `test.skip` en el proyecto `pequena`, como `chat.spec.js:78`.
- Preparación por API: usuario, `notebookConDocumento`, segundo notebook, `abrirNotebookConDocumentos`. CDP `Network.loadingFailed` con `canceled` sobre `consulta-con-historial-stream`, como `chat.spec.js:133-138`.

| Paso | Acciones y aserciones | Requisito | Coste |
|---|---|---|---|
| 1 | Motor «PRUEBA A»; enviar → A. Escribir «borrador PRUEBA»; motor «PRUEBA B»; «Reintentar» → 4 burbujas, B al final, A intacta; el campo sigue con «borrador PRUEBA». | RF-15.70, .71 | ~2 s |
| 2 | Motor `retener_tras: 2`; reintentar → texto parcial; reintentar ×2 → abortadas = 2 y `abandonados` = 2 (poll); 2 burbujas con texto parcial, separador y «Consulta cancelada por el usuario»; motor sin retener → respuesta final. | RF-15.72, .74 | ~4 s |
| 3 | Motor `modo: 'conexion'`; reintentar → burbuja con el aviso de error; motor «PRUEBA tras error»; «Reintentar» → la pregunta y «PRUEBA tras error» se agregan al final (RF-15.70) y la burbuja del error queda intacta. Solo la segunda mitad (§7a). | RF-15.73 | ~1,5-2 s (umbral 5 s) |
| 4 | Retener; enviar en A → texto parcial; abrir B → abortadas +1, `abandonados` +1; B sin burbujas nuevas y con el envío libre; volver a A → texto parcial y aviso. | RF-17.70 | ~3 s |
| 5 | Retener; enviar; escribir y pulsar Enter → ninguna petición nueva; el texto se conserva; liberar. | RF-17.71 | ~1 s |
| 6 | Administrador por API; `GET /bitacora/registros?usuario=<cédula>` (como `notebooks.spec.js:291`): consultas «notebook» = 6 turnos terminados (corregido en T6; antes decía 7 y la suma daba 6) (1: A y B; 2: la final; 3: el error, con su motivo por RF-21.60, y su reintento; 4: ninguno; 5: el liberado); ninguna de las 3 canceladas. | RF-21.71 | ~1,5 s |

- Total ~17-21 s → suite ~520 s, por debajo del tope de 569 s.
- El paso 3 se mide aparte en T4. Si pasa de 5 s, se retira de la e2e: exención en §7a y verificación manual (P2 de la spec).

## 7. Pruebas por requisito

| Requisito | Prueba | Rojo esperado |
|---|---|---|
| RF-15.70, .71 | e2e paso 1 | Sí (T3): una sola corrida con el código actual falla aquí; «Reintentar» no hace nada. |
| RF-15.72, .74 | e2e paso 2; integración (desconexión, `notebook`) | e2e (T4): con todo T4 salvo el `finally` de A1, el paso 2 falla con 1 conexión abortada en vez de 2; con A1, verde. Integración verde desde el inicio (cubre lo existente). |
| RF-15.73 (tras error) | e2e paso 3 | Sí. |
| RF-15.73 (durante «Reintentando…»), P-4 | Exención (§7a) | — |
| RF-17.70 | e2e paso 4 | Sí: hoy escribe en la conversación de B. |
| RF-17.71 | e2e paso 5 | Sí: Enter envía. |
| RF-21.71 | e2e paso 6; integración `:331-343` (tipo «notebook», existente) | e2e sí. |
| Contador | `test_instancia_e2e.py` | Sí: la clave no existe. |
| D (existentes) | `chat.spec.js`, `notebooks.spec.js`, suites completas | Deben seguir verdes. |

### 7a. Exenciones
- RF-15.73, primera mitad, y P-4 (reintentar durante «Reintentando obtener respuesta...»): camino inalcanzable hoy.
  - La burbuja solo aparece si la respuesta llega vacía a la interfaz (`messageUtils.js:338-347`).
  - Desde la 007, `stream_chain_response` (`general_chains.py:211-258`, `:274`) descarta el `answer` vacío y, con `if not completo:`, emite `MSG_SIN_RESPUESTA`, que `consultaService.js:215` entrega como fragmento.
  - `secuencia: ['']`, `None` y `sin_datos` no producen la burbuja vacía.
  - P-4 se implementa igual en T4 (§4), sin prueba ni verificación manual posible. Descartada: forzar la respuesta vacía con un control nuevo (cambiaría el servidor solo para probar un camino muerto).

## 8. Reglas operativas (cada corrida de suite)
- Memoria libre antes: pytest ≥ 1,5 GB, e2e ≥ 2,3 GB. Nunca dos suites a la vez; `npm run dev` cerrado durante el e2e.
- Servicios con `docker compose start <servicio>`, nunca `up -d`; `tika`, `celery-worker` y `servidor-htr` detenidos.
- Evidencia: pytest (pasan, `xfail`, fallos, XPASS) y e2e (recolectadas, pasan, fallan, esperados, omitidas, XPASS, residuos, contraseñas, suite contra 569 s).
- Durante T3 y T4, solo `npm run e2e -- e2e/flujos/notebooks.spec.js` (y `chat.spec.js` en T4).
- Suite > 569 s: repetir una vez; recortar solo si dos corridas seguidas pasan, y lo decide Andrés.

## 9. Verificación manual (T5; Andrés inicia sesión en el MCP; 1229 ≈ 1366 px y 554 ≈ 616 px)
- Usuario Gubernamental, notebook `PRUEBA 008b` con un `.txt` `PRUEBA`, Ollama real:
  - reintentar con la respuesta terminada;
  - reintentar en curso: aviso, y el motor libre (`docker compose exec ollama ollama ps`, sin generación colgada);
  - abrir otro notebook en curso y volver;
  - Enter en curso.
- Asistente Virtual: enviar dos veces seguidas con una respuesta en curso; solo la última se completa.
- Administrador: bitácora con un registro por turno terminado y ninguno por cancelación; `/notebooks` lo redirige.
- Consola sin errores. Limpieza: quitar el `.txt`; el notebook queda vacío como residuo (RN-01).

## 10. Documentación (T6, propuesta a Andrés; el planner no la edita)
- ERS RF-15: sin «Estado actual»; Estado Implementado. Frase de RF-15.72 en «Reglas y validaciones»: «Si se reintenta mientras una respuesta está en curso, esa consulta se cancela en el servidor, no se guarda ni se registra, y su respuesta conserva el texto recibido seguido de "Consulta cancelada por el usuario".»
- ERS RF-17: «Abrir otro notebook mientras una respuesta está en curso la cancela de la misma forma; al volver, esa respuesta muestra el aviso de cancelación.»
- CU-10 FA-01: la cancelación de la respuesta en curso.
- Hallazgo FE-01 (P-3): «Estado actual» de RF-16 o CU-09 FE-01 (el que corresponda): el reintento automático es un camino inalcanzable hoy (el servidor sustituye la respuesta vacía desde la 007); si se alcanzara, no mostraría su respuesta y dejaría el envío bloqueado.
- `graphify-out/` (grafo y mapas), `MEMORY.md` (hallazgo FE-01 incluido) y el estado de la spec.

## 11. Decisiones
- D-1: arreglo de A1 por identidad del controlador. Descartada: un controlador por llamada sin estado compartido (cambia la API de `cancelConsulta`, usada por `Chat.jsx`).
- D-2: marca inactiva `'cancelada'` en lugar de `null`. Descartada: tocar el temporizador de `messageUtils.js` (compartido; es el terreno del hallazgo FE-01).
- D-3: una sola e2e con pasos (P4 de la spec). Descartada: R1 y R2 (preparación duplicada, ~8-10 s).
- D-4: T0 reutiliza las cifras del cierre de la 008. Descartada: correr de nuevo (+25 min sin cambio de código).
- D-5: pytest completo solo en T0 (reutilizado) y T5; en T1 y T2, solo los archivos tocados.

## 12. Decisiones de Andrés (04/11/2026)
- P-1 = A: D2 = B, cancelar de verdad en el servidor y no solo dejar de mostrar la respuesta; D3 = A, conservar el texto parcial con el aviso en vez de borrar la burbuja. **Confirmada por Andrés (04/11/2026).**
- P-2 = A: contador `abandonados` en el estado de `/control/chat` (T2 ⚠️, aprobada con esta respuesta; solo código de pruebas, sin archivos nuevos).
- P-3 = A: el reintento automático de FE-01 está roto en los tres chats (`messageUtils.js:361-362`: el id pasa a `requestId + 0.1` y los callbacks comparan con `requestId`). Queda como hallazgo en `MEMORY.md` y en la propuesta de T6, documentado como «camino inalcanzable hoy (el servidor sustituye la respuesta vacía desde la 007)»; no se arregla aquí.
- P-4 = A: reintentar durante «Reintentando obtener respuesta...» anula el automático pendiente; la burbuja queda con «Consulta cancelada por el usuario» (RF-15.73 de la spec).
- Hallazgo de T3 (opción A, 04/11/2026): RF-15.73 se prueba en la e2e solo en su segunda mitad (tras un error, `modo: 'conexion'`, < 5 s). La primera mitad y P-4 quedan exentas por inalcanzables (§7a); P-4 se implementa igual en T4.
