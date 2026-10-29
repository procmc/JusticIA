# Plan — Spec 007: Contexto y señales del chat (corrección)
Estado: aprobado (29/10/2026), con P-1 a P-5 resueltas. Incluye los textos de instrucciones nuevos (§6), que se aprueban con este plan («cambiar prompts»).

> Parte de la spec aprobada el 29/10/2026. No repite la spec: remite a sus requisitos. Archivos y líneas verificados el 29/10/2026 en `fase4` leyendo el código: el MCP de graphify no respondió (`uv_spawn`), así que se ubicó con `graphify-out/mapa_codigo.md`, `mapa_pruebas.md` y `Grep`.
> Tamaño: ~2,5 veces la referencia de la 004a. Justificación: R1 = A (una sola spec) y este plan recibe el «Anexo», las «Decisiones» y las «Pistas» de la spec (P-β).

Historial:
- 29/10/2026 — creado (fase 3, planner). Anexo, Decisiones y Pistas trasladados desde la spec (Anexos A-C de este plan). Cuatro dudas abiertas (§21).
- 29/10/2026 — P-1 = C, P-2 = A, P-3 = A, P-4 = A incorporadas (RF-11.69 nuevo, T5b), y la corrección de `.env.example` (RNF-09.60) en T13. §21 cerrada salvo P-5 (umbral), redactada con su recomendación.
- 29/10/2026 — aprobado por Andrés, con los textos de §6 y `tasks.md`; P-5 = A; §21 cerrada.

## 1. Enfoque
- Corrección de errores (testing.md): primero las regresiones (RF-11.60, RF-08.60, RF-11.64, RF-20.60), vistas en rojo con su causa anotada.
- Se sustituye el armado de LangChain (`create_history_aware_retriever`, `create_stuff_documents_chain`, `RunnableWithMessageHistory`) por un armado explícito y medido. Motivo en §2 y §12 (D-1).
- Un solo módulo de presupuesto para los tres chats, la reformulación y el resumen (§5).
- Sin esquema, migración, dependencia, modelo ni `docker-compose.yml` (R2, RNF-09.60). La ventana se envía en cada llamada desde el backend; `docker-compose.yml` no define `LLM_*`.
- Motores simulados en unitarias, integración y e2e; el motor real solo en CF-1 (§15) y en la verificación manual (§17).

## 2. Causa de los ~85.000 tokens (determinada leyendo el código)
- **Causa principal: el bloque de fragmentos se inserta varias veces en la misma entrada.**
  - `ANSWER_SYSTEM_PROMPT` (`prompts/answer_prompt.py:73-351`) contiene `{context}` **5 veces** (:89, :288, :293, :311, :312). `ChatPromptTemplate` reemplaza todas: el chat general envía 5 copias de los 15 fragmentos.
  - `get_expediente_system_prompt` (`prompts/expediente_prompt.py:82-280`) es un f-string con `{{context}}` **7 veces** (:115, :197, :202, :208, :212, :216, :221): el chat por tema envía 7 copias de sus 10 fragmentos.
  - El notebook lo tiene una sola vez (`notebook_prompt.py:209`).
- Cuenta: 15 fragmentos con encabezado ≈ 60.000 caracteres × 5 ≈ 300.000; más 13.448 de instrucciones y el historial ≈ 85.000 tokens a 3,67 caracteres por token. Coincide con `prompt=85158` del motor.
- Contribuyentes secundarios (sin tope, pero menores):
  - historial de hasta 20 mensajes (`rag_config.py:216`), con respuestas de hasta `LLM_NUM_PREDICT` tokens (`.env.example:51` dice 4.096);
  - reformulación del general: 7.900 caracteres de instrucciones (`contextualize_prompt.py:72-216`) más los 20 mensajes;
  - encabezados de grupo por tema (`formatted_retriever.py:104-121`, `document_formatter.py:119-124`).
- Descartados: el texto de imágenes es un fragmento más; la lista del notebook (`rag_chain_service.py:496-501`) usa otra búsqueda pero no llama al motor (sí nombra archivos no enviados: RF-12.62).
- Consecuencia para la regresión de RF-11.60: además del presupuesto, comprueba que cada fragmento aparece **una sola vez** en la entrada capturada (hoy: 5 en el general, 7 en el tema). No hace falta una tarea de medición previa.
- Hallazgo del código, no del diagnóstico: solo el chat general reformula. Los chats por tema y notebook no usan la pregunta para buscar (`retriever.py:165-198`: los primeros N fragmentos del tema por número de fragmento). Resuelto con P-1 = C: RF-11.69 y RF-11.66 en los tres chats (§5.1).

## 3. Archivos
Nuevos (⚠️ crear archivos):

| Archivo | Responsabilidad | Requisitos |
|---|---|---|
| ⚠️ `backend/app/config/contexto_config.py` | Valores del contexto leídos del entorno, validados una vez al arrancar; aviso y valores por omisión si son incoherentes. | RF-08.62, RF-11.63, RF-11.65 |
| ⚠️ `backend/app/services/RAG/presupuesto_contexto.py` | Conteo, espacio mínimo, rechazo de pregunta larga, reparto (historial y fragmentos), encabezado, lista del notebook, entrada de reformulación y del resumen. Funciones puras. | RF-11.60-62, RF-11.66, RF-12.60, RF-12.62, RF-20.60-62 |
| ⚠️ `backend/app/services/ingesta/refragmentado.py` | Procedimiento interno con `python -m` (sin ruta de la API). | RF-08.63, RN-01.60 |
| ⚠️ `backend/tests/unitarias/test_contexto_config.py` | Coherencia y valores únicos. | RF-08.62, RF-11.63 |
| ⚠️ `backend/tests/unitarias/test_fragmentacion.py` | Tamaño, solapamiento y páginas. | RF-08.60, RF-08.61 |
| ⚠️ `backend/tests/unitarias/test_presupuesto_contexto.py` | Armado por chat y del resumen. | RF-11.60-62, 65, 66, RF-12.60, 62, RF-20.60-62 |
| ⚠️ `backend/tests/unitarias/test_instrucciones_chat.py` | Estructura de los cuatro textos. | RF-12.61, RF-11.66 |
| ⚠️ `backend/tests/unitarias/test_flujo_consulta.py` | Etapas, señal de vida, tope (reloj simulado). | RF-11.64, RF-16.60, RF-16.62 |
| ⚠️ `backend/tests/integracion/test_chat_contexto.py` | Rechazo, tope, desconexión, historial y bitácora por chat; recuperación por relevancia en tema y notebook; resumen 500. | RF-11.62, 64, 68, 69, RF-16.60, 62, RF-21.60, RF-20.62 |
| ⚠️ `backend/tests/integracion/test_refragmentado.py` | Procedimiento en el entorno aislado. | RF-08.60, RF-08.63 |
| ⚠️ `backend/tests/motor_real/conftest.py` y `test_conteo_motor_real.py` | CF-1 (§15). | CF-1 |
| ⚠️ `frontend/e2e/flujos/chat.spec.js` | Matriz e2e (§16). | RF-11.62, 64, 67, RF-16.40, 60-62 |

Modificados (backend):

| Archivo (símbolo, línea) | Cambio | Requisitos |
|---|---|---|
| `app/config/config.py:74-75` | Por omisión 8.192/1.024; nuevas variables (§4) leídas aquí, validadas en `contexto_config`. | RF-11.63 |
| `backend/.env.example:50-51` | 8.192/1.024 y las variables nuevas con su valor por omisión (T1). | RF-11.63 |
| ⚠️ `backend/.env.example:38-44` | Motor local: `OLLAMA_BASE_URL=http://ollama:11434`, `OLLAMA_MODEL=llama3.1:8b`, `OLLAMA_API_KEY=` vacía; se quitan el bloque de la nube y el `llama2:7b` comentado (T13). | RNF-09.60 |
| `app/config/rag_config.py` (:33, :148-191, docstrings) | Quitar 32.768 y los `TOP_K_*` fijos: se leen de `contexto_config`. `CHAT_HISTORY_LIMIT = 20` queda como candidatos. | RF-11.63, RF-11.65 |
| `app/llm/llm_service.py` (`get_llm`, :100-101) | `num_ctx`/`num_predict` desde `contexto_config` (los mismos que el presupuesto). | RF-11.63 |
| `app/vectorstore/storage.py:144-218` | Tamaño y solapamiento configurables; páginas por posición real (`add_start_index`); identificadores propios de los puntos; parámetro opcional para conservar fechas originales. | RF-08.60, 61, 63 |
| `app/vectorstore/qdrant_backend.py` (:353, :395) | Leer puntos de un documento (ids y metadatos) y borrar por lista de ids. | RF-08.63 |
| `prompts/answer_prompt.py`, `expediente_prompt.py`, `notebook_prompt.py`, `contextualize_prompt.py` | ⚠️ Textos de §6 como constantes de texto (sin `ChatPromptTemplate`). Se conserva `reformular_referencia_imagen` (:69). | RF-12.61, RF-11.66 |
| `services/RAG/general_chains.py` (:92-231) | Orquestador del turno (§7) en lugar de las cadenas y de `stream_chain_response`. | RF-11.64, 68, RF-16.60, 62 |
| `services/RAG/expediente_chains.py`, `notebook_chains.py` | Solo aportan instrucciones y recuperador de su chat. | RF-12.61 |
| `services/RAG/formatted_retriever.py`, `document_formatter.py` | Encabezado por fragmento de §5 (sin encabezado de grupo). | RF-12.60 |
| `services/RAG/rag_chain_service.py` (:275-551) | Los tres flujos llaman al orquestador; quitar `MAX_TOP_K = 15` (:289), el `top_k=15` del respaldo (:369) y la búsqueda aparte del notebook (:496-501). | RF-11.65, RF-12.62 |
| `services/RAG/retriever.py` (:142-198) y `search_strategies.py` (:128) | Cantidad desde `contexto_config`; respaldo ≤ esa cantidad. Con `expediente_filter` en el chat: búsqueda semántica con filtro `metadata.numero_expediente`, sin umbral (§5.1); `_get_expediente_documents` queda solo para el resumen (`documentos_visibles`). | RF-11.65, RF-11.69 |
| `services/RAG/session_store.py` (:113-151) | Se lee el historial completo para el reparto; el guardado lo hace el orquestador al terminar. | RF-11.61, RF-11.68 |
| `routes/rag.py` (:89-95, :154, :163-202) | `top_k` opcional (≤ 0 → servidor; tope = configurado); la bitácora pasa al final del turno mediante un registrador que arma el router. | RF-11.65, RF-21.60 |
| `services/bitacora/rag_audit_service.py` (`registrar_consulta_rag`, :100) | Parámetro `motivo` opcional en `info_adicional`. | RF-21.60 |
| `services/busqueda_similares/summary_generator.py` (:169-265), `similarity_prompt_builder.py` (:163-183), `chunk_context_builder.py` (:83-109) | Contexto del resumen seleccionado por el presupuesto, sin cortar fragmentos. El texto de :113-158 no cambia. | RF-20.60-62 |

Modificados (pruebas y frontend):

| Archivo | Cambio | Requisitos |
|---|---|---|
| `backend/pytest.ini:9` y `tests/soporte/marcadores.py:11-15` | Marcador `motor_real` por carpeta, excluido por omisión. | CF-1 |
| `tests/soporte/simulados.py` (`LLMSimulado`, :454-488) | `_astream` que registra cada llamada y su cancelación; retener hasta liberar; fallar tras N trozos. | RF-11.60, RF-16.62 |
| `tests/instancia_e2e/simulados_e2e.py` (:641-745) y `control.py` | Programar señal de vida y tope por prueba; modo «mudo» (no sale ningún dato); pausa entre etapas; evento desconocido inyectado. Solo en la instancia. | RF-16.40, 60, 62, RF-11.64, 67 |
| `frontend/e2e/soporte/control.js` | Métodos de esas capacidades. | ídem |
| `frontend/services/consultaService.js:199-217` | Eventos `etapa` y `vida`; todo dato llama a `onDato`; `error` lleva el texto del servidor. | RF-11.64, RF-16.60, RF-11.67 |
| `frontend/utils/chat/messageUtils.js` (:171-181, :219-285) | Plazo reiniciado con cualquier dato; aviso «Intente de nuevo.»; error conserva el texto y libera el control. | RF-16.40, 60, 61, RF-11.67 |
| `frontend/components/consulta-datos/chat/TypingIndicator.jsx:4-13` (y quien lo muestra: `MessageBubble.jsx`) | Muestra la etapa recibida; sin animación de fases. | RF-11.64 |

## 4. Configuración (RF-08.62, RF-11.63, RF-11.65)

| Variable de entorno | Por omisión | Uso |
|---|---|---|
| `LLM_NUM_CTX` (existe) | 8192 | Ventana enviada en cada llamada y base del presupuesto |
| `LLM_NUM_PREDICT` (existe) | 1024 | Reserva de respuesta |
| `CHAT_CARACTERES_POR_TOKEN` | 3.5 | Conteo (Q-B) |
| `CHAT_FRAGMENTOS_POR_CONSULTA` | 8 | Recuperación y tope por solicitud |
| `FRAGMENTO_TAMANO_MAXIMO` / `FRAGMENTO_SOLAPAMIENTO` | 1500 / 200 | Fragmentación |
| `CHAT_SENAL_DE_VIDA_SEGUNDOS` | 10 | Intervalo de la señal de vida |
| `CHAT_TIEMPO_MAXIMO_SEGUNDOS` | 180 | Tope de la consulta |

- `contexto_config` expone un objeto `ConfiguracionContexto` (presupuesto = ventana − reserva) calculado una vez. `get_llm`, el presupuesto, `storage.py` y la recuperación lo leen de ahí: un solo origen (RF-11.63).
- Coherencia: los casos de RF-08.62, más intervalo ≤ 0, tope ≤ 0 o intervalo ≥ tope (D-9). Ante cualquiera: `logger.warning` con el motivo y **todos** los valores por omisión.
- Un valor no numérico cuenta como incoherente (no tumba el arranque).
- Señal de vida y tope se leen en cada consulta, para que la instancia e2e los programe por prueba.
- ⚠️ El `.env` de desarrollo lo ajusta Andrés (los agentes no lo leen ni lo editan): `LLM_NUM_CTX=8192`, `LLM_NUM_PREDICT=1024` o quitar ambas líneas. Sin eso, un 4.096 heredado del `.env` dejaría vigente el valor viejo.

## 5. Presupuesto y armado (RF-11.60-62, RF-11.65-66, RF-12.60, RF-12.62)
- `tokens(texto) = ceil(len(texto) / caracteres_por_token)`, por pieza; la suma de piezas redondeadas es prudente (≥ el total).
- `espacio_minimo(chat) = tokens(" " * (tamaño + 500 [+ 300 en el notebook]))` = 572 / 658 por omisión.
- Encabezado de cada fragmento enviado (RF-12.60), en lugar de los encabezados de grupo:
  ```
  [Fragmento n] Archivo: <nombre> | Tema: <tema o nombre del notebook> | Págs.: a-b
  Origen: documento escaneado, ya transcrito automáticamente a texto   ← solo imágenes
  Ruta: <ruta de descarga>
  <texto>
  ```
- Entrada de respuesta: `[Sistema(instrucciones + lista? + "FRAGMENTOS RECUPERADOS:\n" + bloques), *historial, Humano(pregunta)]`. Los títulos fijos cuentan con las instrucciones.

```
cabe_la_pregunta(chat, pregunta):                       # RF-11.62, antes de todo
    return tokens(instr+títulos) + tokens(pregunta) + espacio_minimo(chat) <= P

armar_respuesta(chat, pregunta, historial, fragmentos):
    base  = tokens(instr+títulos) + tokens(pregunta)
    tope_h = min(0.2*P, P - base - espacio_minimo(chat))
    hist = []                                            # RF-11.61: recientes y completos
    for m in reversed(historial):
        if usado + tokens(m) > tope_h: break             # se omite con los anteriores
        hist.insert(0, m)
    libre = P - base - tokens(hist)
    for f in fragmentos[:k]:                             # orden de la recuperación, k ≤ 8
        costo = tokens(encabezado(f) + f.texto)
        if notebook and f.archivo nuevo: costo += tokens(linea_lista(f.archivo))   # RF-12.62
        if costo <= libre: enviar(f); libre -= costo     # el que no cabe se salta entero
    entrada = armar(instr, lista(enviados), enviados, hist, pregunta)
    assert tokens(entrada) <= P                          # defensa; si falla, registro de error
```

- Reformulación (RF-11.66): `[Sistema(instr_reformulación), *últimos 2 mensajes, Humano(pregunta)]`. Si no cabe, quita el más antiguo; con 0 mensajes no hay llamada y se busca con la pregunta original.
- La reformulada solo busca; la respuesta recibe la pregunta del usuario (en el notebook, la adaptada por `reformular_referencia_imagen`).
- La lista del notebook (RF-12.62) sale de los fragmentos enviados; se elimina la búsqueda aparte.
- Cantidad (RF-11.65): `k = configurado si solicitud ≤ 0 o ausente; si no, min(solicitud, configurado)`. Se aplica en la ruta, en los tres flujos y en el respaldo (`search_strategies.py:128`).

### 5.1 Recuperación y reformulación en los tres chats (RF-11.66, RF-11.69; P-1 = C)
```
consulta_busqueda(chat, pregunta, historial):
    p = reformular_referencia_imagen(pregunta) if notebook else pregunta     # la que recibe la respuesta
    if historial: p_busqueda = reformular(p, últimos 2 mensajes)          # mismo texto §6.4; omite mensajes si no cabe
    else:         p_busqueda = p
recuperar(chat, p_busqueda, k):
    general     -> búsqueda de hoy (umbral + respaldo)
    tema/notebook -> similarity_search(p_busqueda, k, filtro metadata.numero_expediente = tema o NB-<id>), sin umbral
```
- El nombre visible del notebook (`nombre_visible`) se sigue aplicando a los metadatos recuperados, como hoy (`retriever.py:188-189`).
- El resumen (RF-20) no cambia de lectura: `_get_expediente_documents` con `documentos_visibles`.

## 6. Textos de instrucciones nuevos (⚠️ prompts; RF-12.61, RF-11.66)
- Sustituyen a los de §2. Se insertan con reemplazo de texto (no `ChatPromptTemplate`): un nombre con llaves ya no rompe el armado.
- Tamaños estimados (la prueba de T4 los mide de verdad); máximo de RF-12.61: ~5.000 caracteres (1.433 tokens):
  - general ≈ 2.300 caracteres (~660 tokens);
  - tema ≈ 2.950 + 2 × 60 del tema ≈ 3.070 (~880 tokens);
  - notebook ≈ 3.100 + 3 × 255 del nombre ≈ 3.870 (~1.110 tokens), más el título de la lista;
  - reformulación ≈ 750 (~215 tokens), menor que cualquiera de las tres.
- Cambios de fondo respecto de hoy (D-5): «JusticBot» pasa a «asistente de ServIA»; se quita la restricción a temas jurídicos; ante otro idioma responde en español en vez de negarse; el notebook pierde el recordatorio dinámico de imágenes (sus reglas quedan fijas en IMÁGENES).
- El texto del resumen (`similarity_prompt_builder.py:113-158`) no cambia.

### 6.1 Chat general
```
Eres el asistente de ServIA y respondes preguntas sobre documentos del Sector Público de Costa Rica.

REGLAS
1. Usa solo la información de los FRAGMENTOS RECUPERADOS que aparecen al final de estas instrucciones. No uses conocimiento general ni completes con suposiciones.
2. Si los fragmentos no contienen la respuesta, o no hay fragmentos, dilo con claridad: «Los documentos recuperados no contienen información suficiente para responder esa pregunta.» Puedes sugerir que se reformule con otros términos.
3. Cita el archivo de origen de cada afirmación relevante, con el nombre que aparece en «Archivo:». No inventes nombres de archivo ni atribuyas a un documento lo que dice otro.
4. Si la pregunta se refiere a un documento de forma ambigua (por ejemplo, «el archivo que subí» cuando hay varios), pide una aclaración en lugar de suponer cuál es.
5. Responde siempre en español, con lenguaje claro y profesional, aunque la pregunta esté escrita en otro idioma.
6. Ante un saludo o una pregunta sobre quién eres, preséntate en una oración como el asistente de ServIA y ofrece ayuda con los documentos.
7. Si la pregunta remite a la conversación anterior («el primero», «ese documento»), usa los mensajes previos para identificarlo; si no puedes identificarlo con certeza, pregunta.

FORMATO
- Usa Markdown: negritas para los datos clave, listas con guiones y una línea en blanco entre párrafos. No uses HTML.
- Usa tablas solo para datos breves y estructurados; nunca pongas fuentes ni rutas dentro de una tabla.
- Para citar texto literal, ponlo entre comillas e indica el archivo y, si se conoce, la página.

FUENTES (obligatorio)
Termina toda respuesta que use los fragmentos con esta sección, una línea por archivo, sin repetir archivos:

**FUENTES:**

- <nombre del archivo>: (<ruta>)

Copia la ruta exacta de la línea «Ruta:» del fragmento, entre paréntesis. Lista solo archivos de los fragmentos recuperados. Sin esta forma exacta, los enlaces de descarga no funcionan.
```

### 6.2 Chat por tema (`{tema}` se reemplaza por el tema, ≤ 60 caracteres)
```
Eres el asistente de ServIA y analizas los documentos del tema «{tema}».

REGLAS
1. Usa solo la información de los FRAGMENTOS RECUPERADOS del tema, que aparecen al final de estas instrucciones. No uses conocimiento general, información de otros temas ni suposiciones.
2. Si los fragmentos no contienen la respuesta, o no hay fragmentos, dilo con claridad: «Los documentos recuperados del tema no contienen información suficiente para responder esa pregunta.»
3. Cita el archivo de origen de cada afirmación relevante, con el nombre que aparece en «Archivo:». No inventes nombres de archivo ni atribuyas a un documento lo que dice otro.
4. Si la pregunta se refiere a un documento de forma ambigua, pide una aclaración en lugar de suponer cuál es.
5. Responde siempre en español, con lenguaje claro y profesional.
6. Ante un saludo, preséntate en una oración como el asistente de ServIA para este tema.
7. Los documentos no los envía el usuario: el sistema los recuperó del tema. No digas «los documentos que me proporcionaste». Los fragmentos de imágenes ya vienen transcritos a texto (línea «Origen:»); trátalos como cualquier otro documento.
8. Si en los mensajes previos aparece información de otro tema, ignórala.

REDACCIÓN DE DOCUMENTOS
Si el usuario incluye una plantilla o un documento de ejemplo y pide redactar uno similar:
- Toma de la plantilla solo la estructura (secciones, numeración y estilo) y conserva su numeración exacta.
- Llena el contenido solo con datos de los fragmentos del tema y cita sus archivos.
- Marca lo que falte como **[PENDIENTE: especificar]**; no lo inventes.
- Separa las secciones con líneas en blanco, sin líneas horizontales (---, ___, ===).

FORMATO
- Usa Markdown: negritas para los datos clave, listas con guiones y una línea en blanco entre párrafos. No uses HTML.
- Usa tablas solo para datos breves y estructurados; nunca pongas fuentes ni rutas dentro de una tabla.

FUENTES (obligatorio)
Termina toda respuesta que use los fragmentos con esta sección, una línea por archivo, sin repetir archivos:

**FUENTES:**

- <nombre del archivo>: (<ruta>)

Copia la ruta exacta de la línea «Ruta:» del fragmento, entre paréntesis. Sin esta forma exacta, los enlaces de descarga no funcionan.
```

### 6.3 NotebookServIA (`{notebook}` se reemplaza por su nombre)
```
Eres el asistente de ServIA y analizas los documentos del notebook «{notebook}», una colección de documentos que cargó el usuario.

REGLAS
1. Usa solo la información de los FRAGMENTOS RECUPERADOS del notebook, que aparecen al final de estas instrucciones. No uses conocimiento general ni suposiciones.
2. Si los fragmentos no contienen la respuesta, o no hay fragmentos, dilo con claridad: «Los documentos recuperados del notebook no contienen información suficiente para responder esa pregunta.»
3. Cita el archivo de origen de cada afirmación relevante. Los únicos nombres válidos son los de la lista ARCHIVOS DE ESTA CONSULTA; no inventes otros ni completes la lista con documentos que parezcan propios del asunto.
4. Si la pregunta se refiere a un documento de forma ambigua (por ejemplo, «el archivo que subí» cuando la lista tiene varios), pide una aclaración; si la lista tiene un solo archivo, la referencia es a ese.
5. Responde siempre en español, con lenguaje claro y profesional.
6. Ante un saludo, preséntate en una oración como el asistente de ServIA para el notebook «{notebook}».
7. El usuario no adjunta archivos en el chat: sus documentos están en el notebook y el sistema ya recuperó los fragmentos. Nunca respondas que no hay archivos adjuntos si hay fragmentos.
8. Si se pregunta qué archivos hay, responde con los de la lista y aclara que son los recuperados para esta consulta.

IMÁGENES
- El sistema convierte las imágenes y los manuscritos a texto antes de enviártelos. Sus fragmentos llevan la línea «Origen: documento escaneado, ya transcrito automáticamente a texto».
- Cuando la pregunta mencione «el documento escaneado», responde con el texto de esos fragmentos, no con el de otro archivo.
- Nunca digas que no puedes leer imágenes. Si no hay fragmentos de imágenes, di que no se recuperó ningún documento escaneado para esta consulta.

FORMATO
- Usa Markdown: negritas para los datos clave, listas con guiones y una línea en blanco entre párrafos. No uses HTML.

FUENTES (obligatorio)
Termina toda respuesta que use los fragmentos con esta sección, una línea por archivo, sin repetir archivos:

**FUENTES:**

- Notebook "{notebook}": (<nombre del archivo>)
```
- Título fijo de la lista (cuenta con las instrucciones): `ARCHIVOS DE ESTA CONSULTA:`; cada línea: `- "<nombre>"` (RF-12.62).
- El formato de FUENTES del notebook es el de hoy (`notebook_prompt.py:241`): no cambia cómo se muestran sus citas.

### 6.4 Reformulación (único, para los tres chats; P-1 = C; el texto no cambia)
```
Reescribe la última pregunta del usuario como una consulta de búsqueda autónoma, en español, para recuperar fragmentos de documentos.
- Usa los mensajes previos solo para resolver referencias como «el primero», «ese documento» o «lo anterior»; reemplázalas por el nombre del archivo, el tema o el asunto concreto.
- Si la pregunta no depende de los mensajes previos o cambia de asunto, devuélvela casi igual.
- Conserva exactos los identificadores, números, siglas y nombres de archivo. Puedes añadir la forma completa de una sigla o uno o dos sinónimos clave.
- Si el mensaje incluye un documento largo (una plantilla) seguido de una solicitud, reescribe solo la solicitud.
- No respondas la pregunta ni añadas explicaciones: devuelve solo la consulta, en una línea.
```

## 7. Flujo del turno (RF-11.62, 64, 67, 68, RF-16.60, 62, RF-21.60)
Eventos del stream (SSE, `data: {json}`): `etapa` (texto en `content`), `vida`, `chunk`, `done`, `error` (texto en `content`).

```
turno(chat, pregunta, ...):                          # orquestador en general_chains.py
    if not cabe_la_pregunta(chat, pregunta):         # sin etapas ni llamadas
        registrar("pregunta demasiado larga"); emitir error(MSG_LARGA); return
    cola = Queue(); limite = reloj.monotonico() + tope
    productor = tarea(lambda:
        put etapa("Procesando consulta"); consulta = consulta_busqueda(...)  # §5.1, los tres chats
        put etapa("Analizando documentos"); frags = recuperar(consulta, k)
        put etapa("Generando respuesta")
        async for trozo in llm.astream(armar_respuesta(...)): put chunk(trozo)
        put FIN)
    try:
        loop:
            restante = limite - reloj.monotonico()
            if restante <= 0: cancelar(productor); registrar("tiempo máximo agotado"); emitir error(MSG_TOPE); return
            ev = await reloj.con_limite(cola.get(), min(intervalo, restante))
                 on TimeoutError: if desconectado(): cancelar(productor); return    # sin historial ni bitácora
                                  emitir vida; continue
            FIN   -> si no hubo texto: chunk(relleno de hoy)                         # fuera de alcance
                     guardar(pregunta, texto); título; registrar(None); emitir done; return
            ERROR -> registrar("error del motor"); emitir error(texto de hoy, FE-03); return
            chunk -> si desconectado(): cancelar(productor); return
            emitir ev
    finally: cancelar(productor) si sigue vivo       # cierre del cliente (GeneratorExit/CancelledError)
```
- `MSG_LARGA` = «La pregunta es demasiado larga. Acórtela e intente de nuevo.»; `MSG_TOPE` = «La consulta tardó demasiado. Intente de nuevo.».
- Cancelar el productor cierra la petición `astream` a Ollama, que deja de generar (libera el motor). La espera en la cola de Ollama (`OLLAMA_NUM_PARALLEL=1`) ocurre dentro del productor: recibe señales de vida y cuenta contra el tope.
- Historial (RF-11.68): se lee completo de `session_store` para el reparto y se guarda pregunta y respuesta solo en FIN. Se retira `RunnableWithMessageHistory`.
- Bitácora (RF-21.60): el router arma `registrar(motivo)` con lo que hoy calcula en `rag.py:167-180` y abre su propia sesión de base (la del `Depends` ya cerró al enviar el stream). Un registro por turno; ninguno si el usuario se desconecta.
- El intento sobre una clave de notebook ajena (`rag.py:193-199`) se sigue registrando al recibir la petición: es otro evento.
- El reloj es `obtener_reloj()` (`app/utils/reloj.py`): las unitarias usan el reloj controlable de `tests/soporte/reloj.py`.
- Tope por consulta (P-2 = A): `limite` se calcula al empezar cada turno; el reintento de la interfaz por respuesta vacía (`messageUtils.js`) llega como petición nueva con su propio límite. Sin cambios en el reintento.

## 8. Resumen (RF-20.60-62)
- `crear_contexto_resumen` toma los 20 primeros fragmentos, los ordena como el formateador actual (por documento y número de fragmento) y recorre ese orden con el presupuesto: el que no cabe entero (con el encabezado de su documento, si es el primero) se omite y se prueba el siguiente.
- Instrucciones = `create_similarity_summary_prompt("", tema)` (texto intacto). Si solas superan el presupuesto: excepción sin llamar al motor; la ruta responde el 500 de hoy (`similarity.py:299`) y la bitácora queda como hoy.
- El formateador se llama sin corte de caracteres. Cada intento (`MAX_INTENTOS = 3`) usa la misma entrada, comprobada ≤ presupuesto.

## 9. Re-fragmentado (RF-08.63, RN-01.60)
Comando (desarrollador, en el contenedor):
`docker compose exec backend python -m app.services.ingesta.refragmentado --tema "NEXUS-Avisos-Corte" --tema "NEXUS-Circulares-DE" --tema "NEXUS-Circulares-SC" [--simular]`

```
refragmentar(temas, simular):                       # exige ≥ 1 --tema; no existe «todos»
    docs = documentos Procesado unidos a esos temas por T_Expediente_Documento
    informe(temas, len(docs), fragmentos_actuales)  # simulación: solo esto, sin cambios
    for d in docs:
        viejos = puntos de Qdrant con metadata.id_documento = d.id (ids y metadatos)
        try:
            texto = extract_text_from_file(archivo guardado de d)            # por el núcleo de archivos
            nuevos = store_in_vectorstore(texto, metadatos de viejos, ids propios, fechas originales)
        except: borrar(nuevos insertados); informar(d, causa); continue     # quedan los anteriores
        borrar(puntos de d cuyo id ∉ nuevos)        # también limpia duplicados de una corrida fallida
    informe(final: documentos, fragmentos nuevos, fallidos)
```
- Conserva fila, tema, archivo, estado y, en cada fragmento, `id_documento`, `id_expediente`, `numero_expediente`, `nombre_archivo`, `fecha_carga`, `fecha_expediente_creacion` y `meta.ruta_archivo`.
- Idempotente: la segunda corrida deja el mismo número de fragmentos.
- Sin bitácora (no es una acción de usuario; D-8); el informe va a la salida y al registro del servidor.
- Secuencia (§17): simulación = 27 en desarrollo → Andrés aplica la primera parte del Anexo (Anexo C.1) → aprueba la lista → corrida real (T12).

## 10. Interfaz y roles
- Sin páginas nuevas ni `ROUTE_PERMISSIONS`. El Administrador sigue sin acceso al chat (RN-03).
- Antes de la primera etapa, el indicador muestra solo los puntos; luego, el texto de la etapa recibida. Desaparece con el primer texto o con un error.
- Error: conserva el texto recibido, añade el texto del servidor en la conversación y libera el control (RF-11.67). Un tipo desconocido se ignora (como hoy) pero reinicia el plazo.
- Aviso de RF-16.40: «Se perdió la conexión con el servidor. Intente de nuevo.».

## 11. Datos
- SQL Server: sin cambios de esquema ni migración. `T_Bitacora` usa el tipo `CONSULTA_RAG` existente con `motivo` en la información adicional.
- Qdrant: mismos metadatos; los fragmentos nuevos llevan páginas por posición real. Los antiguos fuera de Nexus quedan como están (Casos límite de la spec).
- Redis: mismo historial; solo se agregan turnos terminados.

## 12. Decisiones (cada una con su alternativa descartada)
- **D-1** Armado explícito de mensajes (descartada: conservar las cadenas de LangChain e interceptarlas; no permiten medir ni repartir la entrada y repiten `{context}`).
- **D-2** Un módulo de presupuesto de funciones puras (descartada: un cálculo por chat; tres copias divergentes).
- **D-3** Configuración validada en `contexto_config` y leída por todos (descartada: constantes en `rag_config.py`; no se ajustan sin tocar código).
- **D-4** Páginas con `add_start_index` del separador (descartada: `text.find` propio; duplica lo que ya ofrece la biblioteca).
- **D-5** Textos nuevos más cortos y genéricos (§6) (descartada: recortar los actuales; arrastran voseo, «JusticBot» y vocabulario judicial).
- **D-6** Señal de vida y tope con una cola y `reloj.con_limite` (descartada: un temporizador por tarea aparte; complica la cancelación).
- **D-7** Bitácora con un registrador que arma el router y se llama al final (descartada: que el servicio arme el registro; duplicaría la lógica de `rag.py:167-180`).
- **D-8** Re-fragmentado como módulo `python -m`, sin bitácora (descartada: tarea de Celery o ruta oculta; la spec exige que no haya ruta).
- **D-9** Señal de vida y tope entran en la coherencia de RF-08.62 (≤ 0 o intervalo ≥ tope) (descartada: dejarlos sin validar). Confirmada (P-3 = A) y ya en la spec.
- **D-11** Tema y notebook por búsqueda semántica filtrada, con reformulación en los tres chats (P-1 = C) (descartadas: los primeros N por número, A; relevancia sin reformular, B).
- **D-12** Cada consulta, incluido el reintento por respuesta vacía, con su propio presupuesto y tope (P-2 = A) (descartada: descontar el tiempo ya usado; toca el reintento, fuera de alcance).
- **D-13** Sin umbral de similitud en tema y notebook (P-5 = A, Andrés) (descartada: el umbral del general; una pregunta general sobre el tema quedaría sin fragmentos).
- **D-14** Los 128 PDF se cargan dentro de la 007, en T13 (P-4 = A) (descartada: paso operativo aparte).
- **D-10** CF-1 con la API nativa de Ollama y una variable propia `SERVIA_MOTOR_REAL_URL` (descartada: relajar la protección de la suite, que hoy rechaza `OLLAMA_BASE_URL` real).

## 13. Pruebas por requisito (las de regresión, primero y en rojo)

| Requisito | Unitaria | Integración | E2e |
|---|---|---|---|
| RF-11.60 | `test_entrada_dentro_del_presupuesto[general/tema/notebook]` (15 × 7.000, 20 mensajes largos; cada llamada capturada), `test_fragmento_una_sola_vez` | — | — |
| RF-11.61 | `test_historial_largo`, `test_fragmentos_de_sobra`, `test_ambos`, `test_historial_corto_cede`, `test_mensaje_mayor_que_20`, `test_fragmento_grande_saltado` | — | — |
| RF-11.62 | `test_justo_bajo_el_limite_llama`, `test_justo_sobre_el_limite_no_llama[3 chats]` | `test_pregunta_larga_solo_error` | sí (§16) |
| RF-11.63 | `test_llamada_y_presupuesto_misma_configuracion`, `test_valores_por_omision` | — | — |
| RF-11.64 | `test_etapas_en_orden` (regresión), `test_error_del_motor_tras_dos_etapas` | etapas por chat | sí |
| RF-11.65 | `test_cantidad_recuperada[>8, 3, 0, -1]`, `test_respaldo_no_supera`, por chat | — | — |
| RF-11.66 | `test_reformula_con_dos_mensajes[3 chats]`, `test_mensajes_enormes_1_o_0`, `test_sin_historial_no_reformula[3 chats]`, `test_notebook_reformula_la_adaptada` | — | — |
| RF-11.69 | `test_tema_y_notebook_sin_umbral` | `test_recupera_por_relevancia[tema, notebook]` (regresión), `test_no_mezcla_otro_tema`, `test_pregunta_sin_relacion_trae_8` | — |
| RF-11.67 | — | — | sí |
| RF-11.68 | — | `test_historial_solo_turnos_terminados[rechazo, tope, error, desconexión antes/después, terminado]` | — |
| RF-12.60 | `test_encabezado_y_sin_rastros_de_omitidos` | — | RF-11.40 sigue pasando |
| RF-12.61 | `test_instrucciones_estructura[4 textos]` (tamaño, reglas, sin «Intentá», «vos», «decí», «usá», «buscá», «leé», «respondé», «tenés», «podés») | — | — |
| RF-12.62 | `test_lista_solo_enviados`, `test_lista_dentro_del_presupuesto`, `test_notebook_bajo_el_limite_cabe_uno` | — | — |
| RF-16.40, 16.61 | — | — | sí |
| RF-16.60 | `test_senal_de_vida_cada_intervalo` (reloj) | `test_senal_de_vida_con_motor_retenido` | sí |
| RF-16.62 | `test_tope_cancela` (reloj) | `test_tope_libera_el_motor`, `test_desconexion_antes_y_despues_cancela` | sí |
| RF-21.60 | — | `test_bitacora_por_turno[3 chats × terminado, rechazo, tope, error; desconexión: ninguno]` | — |
| RF-08.60 | `test_tamano_y_solapamiento_configurados` (regresión) | `test_documento_prueba_fragmentos_de_1500` | — |
| RF-08.61 | `test_paginas_por_posicion_real` (7.000 caracteres) | — | — |
| RF-08.62 | `test_incoherente[cada caso]`, `test_coherente_sin_aviso` | — | — |
| RF-08.63 | `test_cli_exige_temas` | `test_refragmentado[tema indicado, otro intacto, archivo faltante, inserción fallida, dos corridas, simulación]` | — |
| RF-20.60-61 | `test_resumen_dentro_del_presupuesto` (regresión), `test_resumen_fragmentos_enteros_en_orden`, `test_tema_corto_completo` | — | — |
| RF-20.62 | `test_instrucciones_solas_no_llama` | `test_resumen_500_literal` | — |
| D (004, 005) | las existentes | `test_red_chat.py`, `test_aislamiento_notebooks.py`, `test_red_notebooks.py` | `RF-11.40` |

- Pruebas que fijan el comportamiento viejo (se ajustan solo si lo fijaban, sin borrarlas): cualquiera que espere `type: chunk` como primer evento o el texto «Intentá». Se anotan en la tarea.

## 14. Exenciones de automatización
- **Calidad del texto del LLM** (que cite bien, no invente, pida aclaración): no es determinista (testing.md). Se automatiza la estructura de los textos y la entrada; la calidad se comprueba a mano con el motor real (§17).
- **Aspecto visual** del indicador de etapa (animación, colores): se automatiza que aparezca el texto en orden; el aspecto, a mano en ambos anchos.
- **Recorte real del motor y tokens de plantilla**: no se ven con el motor simulado; los cubre CF-1, corrida a mano (Q1 = B).

## 15. CF-1: conteo con el motor real
- Carpeta ⚠️ `backend/tests/motor_real/`, marcador `motor_real` (en `marcadores.py` y `pytest.ini`), excluido por omisión: `addopts = ... -m "not infraestructura and not motor_real"`.
- Comando: `docker compose exec -e SERVIA_MOTOR_REAL_URL=http://ollama:11434 backend pytest -m motor_real -s`.
- El `conftest.py` de la carpeta aborta si falta la variable o si su host no es local (RNF-09). No toca SQL Server ni Qdrant: arma las entradas con `presupuesto_contexto` y textos `PRUEBA` generados en memoria.
- Llamada: `POST /api/chat` nativo con `stream: false`, las mismas opciones que `get_llm` (8.192/1.024) y `keep_alive: 0`.
- **Sin caché de prefijos**: con `keep_alive: 0` el modelo se descarga tras cada llamada, así la siguiente evalúa la entrada entera y `prompt_eval_count` cuenta todo, plantilla incluida.
- Comprobación en la versión instalada (primera prueba): `GET /api/version` se imprime; la misma entrada dos veces con `keep_alive: 0` da el mismo conteo. Si no, PARAR y preguntar.
- Casos: reformulación y respuesta de los tres chats (P-1 = C) y el resumen; cada uno con texto narrativo y **denso** (números, siglas, tablas), con las entradas máximas (15 × 7.000, 20 mensajes, tema largo).
- Falla si `prompt_eval_count > 7.168`, si es 4.098 con estimado mayor, o si el real supera al estimado. Esto último: PARAR y preguntar (Q-B).
- Duración estimada: ~15 min (carga del modelo en cada llamada). GPU libre: sin HTR en uso.

## 16. Matriz e2e y presupuesto (RNF-04.60, RA-02.47)
- Archivo ⚠️ `frontend/e2e/flujos/chat.spec.js`; 12 ejecuciones según la tabla de la spec.
- Línea base **M**: media de 2 corridas de `npm run e2e` en T0, antes de cualquier código. Lo nuevo suma ≤ 40 s; un exceso se confirma con otra corrida antes de parar.
- Técnica por prueba (sin esperas reales de 30 s):
  - etapas: pausa programada entre etapas en la instancia; el evento desconocido se inyecta en el general;
  - servidor mudo: la instancia no deja salir ningún dato; `page.clock` avanza 29 s (control bloqueado) y luego 2 s (aviso y control libre);
  - motor lento con señal: motor retenido, señal de vida a 1 s; `page.clock` avanza 20 s tras cada señal recibida, más de 30 s en total; al liberar, llega la respuesta sin aviso;
  - tope: tope programado a 5 s con el motor retenido;
  - pregunta larga: ~30.000 caracteres pegados.
- Cada prueba empieza con su requisito (`RF-11.64 · chat general: …`); limpia lo que crea.

## 17. Verificación manual de punta a punta
1. Andrés reinicia `backend` y `celery-worker` (los agentes no reinician).
2. `docker compose exec ollama ollama ps` tras una consulta: contexto 8192 (si es menor, PARAR: riesgo R-1).
3. Simulación del re-fragmentado: 27 documentos, 48 fragmentos actuales (19 + 24 + 5). Tras la corrida real: mismas filas, fragmentos ≤ 1.500, puntos fuera de Nexus iguales (`curl http://localhost:6333/collections/<colección>` antes y después).
4. Modelo frío: pregunta sobre Nexus en cada chat, a 1366 y 616 px (Andrés inicia la sesión): etapas visibles, sin aviso de conexión, < 180 s, cita descargable.
5. `docker compose logs ollama` sin `truncating input prompt`; conteo ≤ 7.168 también con 20 mensajes.
6. Resumen de un resultado de Temas Similares sobre Nexus: se genera, sin recorte.
7. Cerrar la pestaña a mitad de respuesta: `ollama ps` muestra el motor libre en ≤ 10 s; sin mensaje nuevo en el historial ni en la bitácora.
8. Notebook con una imagen `PRUEBA`: la pregunta por «la imagen» responde con su texto (calidad, §14).
9. Administrador: no entra al chat. Consola sin errores. `npm run build` sin errores.
10. Recarga: SC 182, 183 y 177 por Ingesta (fila nueva; las anteriores quedan en Error, RF-07.51); luego los 128 PDF en tandas ≤ 10 (P-4 = A).
11. Chat por tema y notebook (RF-11.69): una pregunta sobre un dato del final de una circular larga de Nexus lo cita; una de seguimiento («¿y la segunda?») se responde sobre lo anterior.
12. `.env.example` (RNF-09.60): sin `ollama.com` ni modelos `-cloud`; motor local y `llama3.1:8b`.
13. Limpieza de los datos `PRUEBA` creados.

## 18. Riesgos
- **R-1** El motor recortó a 4.098 aunque el `.env` decía 8.192: puede que el `.env` no tenga 8.192 o que Ollama reduzca la ventana por memoria de GPU. T0 lo comprueba con `ollama ps`; CF-1 y el paso 5 de §17 lo confirman.
- **R-2** Con P-1 = C, una pregunta global («resume el tema») recibe los 8 fragmentos más parecidos, no el inicio de cada documento; la calidad se mira en el paso 11 de §17.
- **R-3** La desconexión en la integración depende de que el cliente de pruebas propague `http.disconnect`; si no, PARAR y preguntar antes de bajar la prueba a unitaria.
- **R-4** Nombres de archivo o rutas muy largos superan los 500 caracteres de encabezado estimados (P-α): la garantía de RF-11.62 podría fallar por pocos tokens. Nexus tiene nombres cortos.
- **R-5** Quitar el recordatorio dinámico de imágenes puede empeorar el notebook con imágenes: paso 8 de §17.
- **R-6** El tiempo e2e (M ≈ 475-513 s) más 40 s queda cerca de 560 s; control en cada tarea con e2e.
- **R-7** Horas: ~58 h de 64 compartidas con la spec del notebook (P-1 = C y P-4 = A): quedan ~6 h para ella.
- `.env.example:38-40` apunta a un Ollama en la nube (`https://ollama.com`, `gpt-oss:20b-cloud`), contra RNF-09: se corrige en T13 (RNF-09.60).

## 19. Documentación a actualizar (T13)
- Entregar a Andrés la segunda parte del Anexo (Anexo C.2), con la viñeta de CF-1 para `CLAUDE.md` (redactada abajo).
- Spec 005: RF-16.40 con «Intente de nuevo.» y «tras el último dato». Spec 006: L231 «(salvo EEE1)» y los resultados del piloto (Nexus re-fragmentado, recarga).
- Spec 007 «implementada»; `MEMORY.md` (con los Error nuevos de la carga de los 128 PDF); `graphify-out/` (`python.exe` de uv) y mapas.

## 20. Cobertura
- §4-§5: RF-08.62, RF-11.60-63, 65, 66, RF-12.60, 62. §5.1: RF-11.66, RF-11.69. §6: RF-12.61, RF-11.66. §3 y T13: RNF-09.60 (`.env.example`). §7: RF-11.62, 64, 67, 68, RF-16.60-62, RF-21.60. §8: RF-20.60-62.
- §9: RF-08.63, RN-01.60. Fragmentación (`storage.py`): RF-08.60-61. §10: RF-16.40, 61, RF-11.67. §16: RNF-04.60. RNF-09.60: §1 y §15.

## 21. Dudas del plan
- Resueltas por Andrés (29/10/2026): **P-1 = C**, **P-2 = A**, **P-3 = A**, **P-4 = A** (Anexo A; D-9, D-11, D-12, D-14). La spec ya las recoge (RF-11.66, RF-11.69, RF-08.62, RF-16.62).
- **P-5 = A** (Andrés, 29/10/2026; D-13): sin umbral en tema y notebook, siempre los k más cercanos del tema. Descartada B (el umbral del general): «resume el tema» o un saludo podría quedar sin fragmentos.
- Sin dudas abiertas.

---

## Anexo A. Decisiones de la spec (trasladadas el 29/10/2026; Andrés, 28-29/10/2026)
- **P1 = A** (RF-11.63): la ventana que ya usaba el `.env` de desarrollo. **P2 = B** (RF-08.60-62): de 7.000 caracteres caben muy pocos.
- **P3 = A** (RF-12.61): 13.448 caracteres de instrucciones se comían la ventana. **P4 = A** (RF-11.61): 20 mensajes sin tope desplazaban los fragmentos.
- **P5 = A** (RF-11.64, RF-16.60, RF-16.62): la espera real (51-80 s) supera los 30 s. **P-D = A**: sin esperas reales en el e2e.
- **P6 = C** (RF-08.63): el piloto vive en Nexus; tocar solo eso limita el riesgo. **P7 = A**: la causa de Tika no es de esta corrección.
- **P8 = A**: el defecto está en los tres chats. **P9 = A** (RF-16.40) y **D1 = A** (RF-16.62): español neutro.
- **P-A = C** (RF-11.61): la prueba mide el presupuesto, no la cantidad. **P-G = B** (RF-11.65): 15 fragmentos ya no caben.
- **P-B = A** (RF-11.66): conserva CU-09 p. 8 con costo acotado. **P-H = A** (RF-11.63): el 4.098 es el recorte del motor.
- **P-C = B** (RF-12.61-62): la lista del notebook venía de otra búsqueda y nombraba archivos no enviados.
- **P-E = C** y **R3 = A** (RF-08.63, RN-01.60): re-fragmentar borra fragmentos, que el principio 5 y RN-01 prohíben.
- **P-F = A** y **Q3 = A** (RF-11.68, RF-21.60): un turno incompleto o una pestaña cerrada no es conversación ni error del sistema.
- **Q1 = B** (CF-1): el recorte solo se ve con el motor real. **Q2 = A** (RF-20.60-62): el resumen envía hasta 20 fragmentos de 7.000.
- **Q4 = A** (RF-20.61): conserva el comportamiento actual sin texto nuevo. **R1 = A**: una sola spec, más compacta.
- **R2 = A** (RF-21.60): sin tipo nuevo ni migración. **R4 = A** (RF-08.61): el texto extraído no trae páginas reales.
- **R5 = B** (RF-11.62): una respuesta sin espacio para ningún fragmento no podría citar la fuente.
- **D-2 = A** (RF-21.60): el error del motor se registra con el motivo «error del motor»; es un fallo del sistema y no una decisión del usuario, y el Administrador debe verlo (descartado: no registrarlo, como la desconexión).
- **P-α = A** (Definiciones, RF-11.61-62, RF-08.62): encabezado estimado en 500 caracteres fijos; espacio mínimo de fragmento 2.000 caracteres (~572 tokens).
- **P-β = A**: los textos para la documentación van al plan (última tarea); mientras no exista, se guardan en el Anexo.
- **Q-A = A** (Casos límite, RF-11.62): sin fragmento que quepa, la respuesta dice que el contexto no alcanza; caso residual, porque Nexus se re-fragmenta (RF-08.63).
- **Q-B = A** (Conteo, CF-1): caracteres por token configurables (3,5 por omisión); si CF-1 lo contradice, se para y se pregunta en vez de ajustar a ciegas.
- Tras el plan (29/10/2026): **P-1 = C** (RF-11.66, RF-11.69): CU-09 p. 5 y p. 8 y el «orden de relevancia» de RF-11.61 en los tres chats. **P-2 = A** (RF-16.62): el reintento no se toca. **P-3 = A** (RF-08.62, D-9). **P-4 = A**: los 128 PDF en T13. Coordinador: `.env.example` con el motor local en T13 (RNF-09.60).
- Revisión QA 3 (redacción del planner, sin cambio de diseño): M1 línea de la lista en 300 caracteres fijos (alternativa descartada: suponer que la cubren los 500 del encabezado); B1 todos los valores por omisión (descartado: solo el incoherente, que admite mezclas incoherentes) y cantidad ≤ 0 → la del servidor (descartado: rechazar la solicitud con un mensaje nuevo); B3 matriz e2e en RNF-04.60; B4 «Mensaje» por separado, como ya cuenta el historial.

## Anexo B. Pistas del diagnóstico y de las revisiones QA (trasladadas; no son requisitos)
- Fragmentación y páginas: `vectorstore/storage.py:144-149, :168`. Qdrant: Circulares-DE 19 fragmentos/18 documentos (872/3.252/6.991 car. mín/media/máx), SC 24/4 (504/6.021/6.999), Avisos-Corte 5/5; colección 2.261 puntos.
- Recorte medido: `truncating input prompt limit=4098 prompt=85158 keep=4 new=4098`.
- General: `general_chains.py:103-107` (reformulada solo para buscar; la respuesta recibe la pregunta original y todo el historial), `contextualize_prompt.py:~190-223`; igual en `expediente_chains.py` y `notebook_chains.py`. *(Nota del plan, §2: estos dos no reformulan.)*
- Prompts: `expediente_prompt.py:197-221`; `notebook_prompt.py:119-141` (voseo `:123,134`). Notebook: adaptación de imágenes `rag_chain_service.py:477-485`, lista con búsqueda aparte `:496-501`.
- `top_k`: `rag.py:93,154` (15, tope 30), `rag_chain_service.py:289,382,465`, respaldo `search_strategies.py:10`.
- Ventana: `config.py:74` (2048), `.env.example:50-51`, `rag_config.py` (32768); `get_llm()` en `llm/llm_service.py:100-101`.
- Stream: `general_chains.py:148-228` (desconexión solo entre fragmentos, `:156-162`); interfaz `messageUtils.js:171-177, 190-208, 219, 270-272`, `consultaService.js:204-217`, `TypingIndicator.jsx:6-11`; enlaces `markdownUtils.js:47-56`, `MarkdownRenderer.jsx:97-108`.
- Bitácora: `rag.py:163-165` (registra al crear la respuesta); el historial se guarda al terminar la cadena.
- Resumen: `summary_generator.py:169-196` (`max_docs=20`, `max_chars_per_doc=7000`), `generar_respuesta_llm` `:202-265`; formateador `chunk_context_builder.py:83-109`; lo llama `similarity_service.py:378-381`.
- Simulados e2e: «no emitir ningún dato» y «retener la respuesta» (`simulados_e2e.py:645,705`); faltan el servidor mudo frente a la señal de vida y el modo lento con señal. El marcador `infraestructura` muestra cómo excluir uno del comando por omisión.

## Anexo C. Textos para la documentación (trasladados de la spec; dos partes, B5)
La **primera** se aprobó con la spec y Andrés la aplica antes de la corrida real de RF-08.63 (T12); la **segunda** la entrega T13.

### C.1 Primera parte (antes de T12)

#### Constitución, principio 5
> 5. **Datos institucionales protegidos**: nada se borra físicamente, salvo los documentos de un notebook, los datos de prueba que la propia suite crea en el entorno de desarrollo y borra al terminar sus pruebas, y los fragmentos que reemplaza el procedimiento de re-fragmentado de la spec 007, solo en una lista explícita de temas aprobada por Andrés (inserta los nuevos antes de borrar los anteriores, conserva el documento, su fila y su archivo y, si algo falla, deja los anteriores); toda función sensible exige token y rol; las contraseñas se guardan con hash; y el repositorio público nunca recibe credenciales, `.env`, documentos cargados ni datos personales. Se viola con un borrado físico fuera de los notebooks, de los datos de prueba y de ese procedimiento sobre temas aprobados por Andrés, un endpoint sensible sin `require_*`, o un secreto o un documento real en un commit. *(RN-01, RNF-07, RNF-08, RNF-10)*

#### `CLAUDE.md`, «Datos» (sustituye la viñeta de RN-01)
> - Ningún registro se elimina físicamente (RN-01, RNF-10); las únicas excepciones son quitar un documento de un notebook (borra sus fragmentos en Qdrant, el archivo y la fila), el procedimiento de re-fragmentado de la spec 007, solo en una lista explícita de temas aprobada por Andrés (reemplaza los fragmentos en Qdrant: inserta los nuevos antes de borrar los anteriores y conserva el documento, su fila y su archivo), y los datos de prueba que la propia suite crea y borra al terminar sus pruebas.

#### ERS, RN-01 (`ERS.txt:307-310`)
- Sustituir «La única excepción son los documentos que un usuario carga en sus propios notebooks, que puede quitar de forma definitiva (RF-19).» por:
> Las excepciones son los documentos que un usuario carga en sus propios notebooks, que puede quitar de forma definitiva (RF-19), y el reemplazo de los fragmentos de un documento por el procedimiento de re-fragmentado (RF-08), que inserta los nuevos antes de borrar los anteriores y conserva el documento, su registro y su archivo.
- Sin contradicción con `ERS.txt:402-403` (el borrado de datos de prueba «no contradice RN-01, que rige los datos del sistema»): los datos de prueba no son una excepción, sino ajenos a RN-01. `ERS.txt:1042` («la única eliminación definitiva que el sistema permite a un usuario») sigue siendo cierto: el re-fragmentado no es una acción del usuario.

#### ERS, RNF-10 (`ERS.txt:1339-1341`)
- Sustituir «La única excepción son los documentos que un usuario carga en sus propios notebooks, que puede quitar de forma definitiva (RF-19).» por el mismo texto de RN-01.

### C.2 Segunda parte (T13)

#### `CLAUDE.md`, «Comandos» (viñeta nueva de CF-1)
- Texto original del Anexo: «el plan redacta la viñeta del comando de CF-1 (marcador, requisitos de GPU y modelo, entorno aislado)». Redacción propuesta:
> - Prueba contra el motor real (CF-1 de la spec 007; fuera del comando por omisión): con el servidor en marcha, la GPU libre (sin HTR en uso) y `llama3.1:8b` descargado, `docker compose exec -e SERVIA_MOTOR_REAL_URL=http://ollama:11434 backend pytest -m motor_real -s`. Usa solo el entorno aislado y textos `PRUEBA` generados en memoria; descarga el modelo tras cada llamada (para medir sin la caché de prefijos) y tarda unos 15 minutos. Imprime, por llamada, el conteo real y el estimado.

#### ERS y CU
- **RF-08**: «El tamaño máximo de los fragmentos (por omisión 1.500 caracteres), su solapamiento (200) y la cantidad recuperada por consulta (8, que una solicitud solo puede reducir) son configurables. Cada fragmento guarda su página estimada de inicio y de fin. Un documento puede volver a fragmentarse sin perder su registro ni su archivo. Una configuración incoherente se sustituye entera por los valores por omisión.» `[NUEVO]` (RF-08.60-63, RF-11.65).
- **RF-11**: «La entrada de cada llamada al modelo se ajusta a su ventana (8.192 tokens, 1.024 reservados para la respuesta): las instrucciones (máximo 20 %) y la pregunta nunca se recortan; el historial ocupa como máximo el 20 % con los mensajes más recientes, y los fragmentos el resto, enteros y por relevancia, hasta 8 (pueden caber menos si el historial o los fragmentos son largos). La reformulación usa los 2 últimos mensajes. Una pregunta que no deja espacio para un fragmento se rechaza con un mensaje. Solo se guardan los turnos terminados.» `[NUEVO]` (RF-11.60-68, RF-12.61-62).
  - Precisar que las etapas las emite el servidor en los tres chats (RF-11.64) y que la estimación de caracteres por token es configurable (por omisión 3,5).
- **RF-16**: Reglas: «El período se reinicia con cada dato recibido del servidor (texto, etapa o señal de vida, que el servidor envía al menos cada 10 s). Una consulta que supera 180 s se detiene con el aviso "La consulta tardó demasiado. Intente de nuevo."». Salida: «Se perdió la conexión con el servidor. Intente de nuevo.» (RF-16.60-62).
- **RF-21**: «La consulta se registra al terminar la respuesta. Una pregunta rechazada por demasiado larga, una consulta detenida por el tope de tiempo o una que termina en error del modelo se registran como consulta, con su motivo en la información adicional. Una consulta abandonada por el usuario no se registra.» (RF-21.60).
- **RF-20**: «La entrada del resumen se ajusta a la ventana del modelo (7.168 tokens de entrada); sus instrucciones nunca se recortan y los fragmentos van enteros.» (RF-20.60-62).
- **CU-09**: FE-02 con «Intente de nuevo.» y el tope de 180 s; **FE-04 nuevo** «Pregunta demasiado larga: si la pregunta no deja espacio para el contexto, el sistema no consulta al motor y muestra "La pregunta es demasiado larga. Acórtela e intente de nuevo."»; FE-01: el reintento respeta la ventana y el tope; paso 7: solo turnos terminados.
- **RNF-01**: «Una consulta abandonada por el usuario o que supera el tope de 180 s deja de generar y libera el modelo, que atiende una consulta a la vez.»
- **RF-11** (P-1 = C), además: «En el chat por tema y en NotebookServIA, los fragmentos se recuperan por relevancia dentro del tema o notebook. Los tres chats reformulan la pregunta de seguimiento antes de buscar.» (RF-11.66, RF-11.69).
- **CU-09**: paso 8 (reformulación) vale para los tres chats; FE-01: el reintento es una consulta nueva con su propio tope de 180 s (P-2).
