# Spec 006 — Ingesta de los documentos de Nexus
Estado: implementada (28/10/2026); aprobada (27/10/2026); dudas resueltas (D1-D5, R1-R5, S1-S4, T1-T2, Andrés, 27/10/2026); corrección T10 (CC1-CC2, DD1, Andrés, 28/10/2026); asistencia operativa en Nexus, la Asamblea Legislativa, el repositorio de CONARE, Kimuk y SINALEVI (KK1-EEE1, Andrés, 28/10/2026)

## Contexto y objetivo
- El tutor autorizó por correo cargar documentos de interés general de Nexus. Andrés los descarga a mano o con la asistencia operativa de un agente (KK1, ver «Datos de la verificación manual y carga del piloto»): PDF con texto seleccionable, públicos y sin datos personales salvo la firma del funcionario en su cargo (PP1), lote piloto de 10-30. Él los revisa y los carga con la Ingesta de siempre, como temas (salvo EEE1: la revisión y la carga las hace un agente).
- ServIA no se entrena: carga (ingesta → fragmentos → Qdrant) y cita (RAG). El chat general ya busca en todo lo procesado (spec 005b); lo usa solo el Usuario Gubernamental (RN-03).
- Antes del piloto hay que corregir los hallazgos de la 005b en la ingesta: (a) dos temas en un mismo Guardar dejan todo en el último; (b) un PDF que falla en la extracción no queda en Error, no deja fila y deja el archivo huérfano; (c) el aviso de rechazo con nombre largo se desborda a 616 px.
- Además (D1, D3): Ingesta acepta temas de nombre libre con un campo «Tema», admite imágenes y muestra la advertencia de manuscrito.
- Según `testing.md` (paso 3), la spec prueba los requisitos del módulo que toca; lo que el código no cumpla y quede fuera, como fallo esperado con su referencia.

## Trazabilidad
- ERS V1.8: RF-05, RF-06, RF-07, RF-10, RF-19 (quitar un documento en Error), RF-21 (fila de error), RNF-04, RNF-09, RN-01 / RNF-10. Sin cambios, como regresión: RF-08, RF-09, RF-17.4, RF-22.
- HU-05, HU-06, HU-07, HU-10 · CU-07 (pasos 2-9, FA-01, FE-01, FE-03), CU-08 (advertencia).
- «Estado actual» que cierra: en RF-07, la extracción fallida y el texto técnico del progreso; en RF-05, imágenes en Ingesta, advertencia y desborde por nombre largo; en RF-06, el formato heredado en Ingesta; en RNF-04, el desborde.
- Quedan abiertos: RF-05 (validación en el servidor, D4), RF-06 (chat acotado a un tema libre, D1) y RF-07 (cancelación, R4); los tres siguen «Parcial».
- Requisitos nuevos en el bloque **.50+** (004: .1+, 004a: .20+, 004b: .30+, 005: .40+). Se conserva RF-07.2 de la 004, que esta spec cumple.

## Usuarios
- Usuario Gubernamental: carga en Ingesta y en sus notebooks, y consulta en el chat general (RN-03).
- Administrador: no carga ni consulta (RN-03); ve las filas de la bitácora.

## Historias de usuario
HU-05, HU-06, HU-07, HU-10 (sin historias nuevas).

## Definiciones
- **Fallo del procesamiento**: cualquier error después de encolado el archivo en la extracción, el reconocimiento de imagen o audio, o la vectorización.
  - No incluye la validación en segundo plano de extensión o formato (R2): sigue sin fila y la cubre el fallo esperado de RF-05.51.
  - No incluye la cancelación del usuario (RF-07.53).
- **Desborde**: en el contenedor del texto del aviso de rechazo, `scrollWidth > clientWidth`.
- **Archivo pendiente**: agregado a la lista de Ingesta y aún no enviado con Guardar.
- **Texto del campo**: el valor del campo «Tema» sin los espacios del inicio y del final.
- **Tema confirmado**: el texto del campo al pulsar Enter o al perder el foco; solo se usa para los pendientes sin tema (S2).

## Requisitos funcionales

### A. Tema de cada archivo (hallazgo a; D1, D2, R1, S1, S2)
- **RF-06.50** (RF-06, HU-06, CU-07 paso 3): CUANDO el Usuario Gubernamental agrega archivos, EL SISTEMA fija a cada uno el texto del campo en ese momento, esté confirmado o no, y lo muestra en su fila.
  - Cambiar el campo no altera el tema de los pendientes ya agregados; para un segundo grupo: cambiar el campo y después agregar.
  - Un pendiente agregado con el campo vacío toma el primer tema confirmado después.
  - Cambio: se retira el campo editable por fila; la fila solo muestra el tema (R1).
  - MIENTRAS algún pendiente siga sin tema, Guardar está deshabilitado y se muestra «Indique el tema antes de guardar los archivos.» (sin alerta nativa del navegador).
  - *Prueba*: e2e (escritorio), una sola prueba: dos temas válidos, un archivo agregado sin tema que toma el confirmado, un grupo con tema no válido (más de 60 caracteres) y la confirmación agrupada; la API lista cada documento en su tema y nada en el otro.
- **RF-06.51** (RF-06, CU-07 paso 5): CUANDO pulsa Guardar, EL SISTEMA muestra en la confirmación los archivos agrupados por tema y la advertencia de asociación permanente.
  - *Prueba*: e2e, en la prueba de RF-06.50.
- **RF-06.52** (RF-06, «Estado actual»): EL SISTEMA acepta en Ingesta de Datos un tema de nombre libre y aplica las reglas de RF-06 solo en el servidor (constitución, principio 3).
  - La pantalla solo comprueba que el tema no esté vacío; no valida caracteres ni longitud, ni limita lo que se puede escribir (S1). El servidor admite hasta 60 caracteres.
  - SI el servidor rechaza el tema de un grupo al confirmar la carga, ENTONCES los archivos de ese grupo aparecen como rechazados con «El tema indicado no es válido» y los de los demás grupos siguen su curso.
  - Cambio: hoy ese rechazo deja los archivos del grupo como fallidos con un mensaje genérico de subida.
  - Un tema con forma de clave de notebook (o que coincide con el tema de un notebook) recibe el 404 de RF-17.4; la pantalla lo muestra igual que un tema no válido: rechazados con «El tema indicado no es válido», sin revelar si el notebook existe (T1).
  - Sus documentos se consultan desde el chat general; el chat acotado a ese tema (RF-06.2) sigue en fallo esperado.
  - *Prueba*: unitaria del servicio con un tema no válido; e2e: el grupo no válido rechazado y el válido Procesado (en la prueba de RF-06.50); la integración existente (tema libre se crea) y las de RF-17.4 siguen pasando.
- **RF-06.53** (RF-06, RF-08) `[NUEVO]`: EL SISTEMA normaliza el tema antes de validarlo y asociarlo, para que un mismo tema no genere dos carpetas ni dos grupos de fragmentos.
  - Quita los espacios al inicio y al final antes de la validación de RF-06 (hoy un tema que termina en espacio se rechaza).
  - SI ya existe un tema igual salvo mayúsculas y minúsculas, ENTONCES usa el nombre ya registrado en la base, en la carpeta y en los metadatos de los fragmentos.
  - Las tildes distinguen temas («Políticas» ≠ «Politicas») (R5).
  - SI un mismo Guardar lleva un tema nuevo en dos grafías («PRUEBA» y «prueba»), ENTONCES EL SISTEMA registra un solo tema y usa su nombre en la base, la carpeta, las rutas, los fragmentos y la bitácora de todos sus documentos (CC1).
  - El tema se resuelve o se crea al cargar, antes de guardar y encolar los archivos (CC2).
  - SI todos los archivos de esa carga se rechazan, ENTONCES el tema queda creado y vacío (residuo aceptado, CC2).
  - *Prueba*: integración parametrizada: «Normativa», «normativa» y « Normativa » → un solo tema, una carpeta y un único valor del tema en los fragmentos; «Normatíva» → otro tema.
  - *Prueba* (T10, regresión): integración con un tema nuevo en dos grafías cargado sin procesar entre medio → una fila, una carpeta, un valor en los fragmentos, rutas y bitácora con el registrado; unitaria del alta en carrera.
- **RF-06.54** (RF-06, RT-06, constitución principio 7): EL SISTEMA no muestra «expediente» ni el formato del identificador heredado en ninguna parte de la pantalla de Ingesta de Datos, incluida la confirmación.
  - El campo se rotula «Tema», sin ejemplo, sin mínimo ni máximo de caracteres, y «Limpiar» se describe como «Limpiar lista de archivos y tema».
  - La confirmación dice «tema» (advertencia, encabezado de cada grupo y el caso sin tema).
  - Se retiran la validación de formato heredado, su indicación «Formato no válido» y sus alertas nativas.
  - *Prueba*: e2e (escritorio y 616 px, aserción añadida a una prueba existente de Ingesta): rótulo «Tema», sin «expediente» visible en la pantalla ni en la confirmación, y un tema de 3 caracteres habilita Guardar.

### B. Fallo del procesamiento (hallazgo b)
- **RF-07.2** (RF-07, HU-07, CU-07 FE-03; de la 004, se quita el `xfail`): SI hay un fallo del procesamiento, ENTONCES el documento queda registrado en Error, asociado a su tema y sin fragmentos, y el archivo guardado queda ligado a esa fila.
  - El archivo no se borra (RN-01) y deja de ser huérfano; los demás archivos de la carga siguen su curso (prueba existente).
  - *Prueba*: integración `documento_queda_en_error` (hoy `xfail`), parametrizada: PDF dañado, PDF sin texto extraíble, imagen sin texto reconocible (reconocimiento simulado sin texto) y fallo del reconocimiento (simulado con fallo); Qdrant sin fragmentos de ese documento.
- **RF-07.52** (RF-07, RF-22; de la 004, se quita el `xfail`): EL SISTEMA informa el fallo en el progreso con «No se pudo procesar el archivo. Por favor, intente nuevamente.» y la causa del conjunto cerrado de RF-22, sin texto técnico ni rutas.
  - *Prueba*: integración `progreso_con_texto_fijo_y_causa` (hoy `xfail` con la referencia RF-07.2; pasa a RF-07.52).
- **RF-07.50** (RF-07, RNF-03, CU-07 paso 9): CUANDO un archivo termina en fallo, la pantalla de Ingesta lo muestra en Error con ese mensaje y su causa, y los contadores lo cuentan como error.
  - *Prueba*: e2e (escritorio) con un PDF inventado dañado junto a una imagen válida (RF-05.50): uno en Error, otro Procesado.
- **RF-07.51** (RF-07, RN-01, HU-07; R3) `[NUEVO]`: SI un reintento interno vuelve a ejecutar la misma tarea de procesamiento, ENTONCES EL SISTEMA la reconoce por su identificador de tarea y no crea otra fila ni duplica fragmentos.
  - CUANDO el usuario vuelve a cargar un archivo que quedó en Error, EL SISTEMA crea una fila nueva y conserva la anterior en Error.
  - *Prueba*: integración: la misma tarea ejecutada dos veces → una fila; una carga nueva tras un Error → dos filas, la primera en Error.
- **RF-07.53** (RF-07, CU-07 FA-03, «Estado actual»; R4): CUANDO el usuario cancela el procesamiento de un archivo en curso, EL SISTEMA lo marca como cancelado por el usuario.
  - Hoy queda como «Error»: no se corrige en esta spec.
  - *Prueba*: integración, fallo esperado `RF-07.53 · ingesta`.
- **RF-07.54** (RF-07, RF-19, CU-07 FA-01 y FE-03) `[NUEVO]`: CUANDO falla el procesamiento de un archivo cargado en un notebook, EL SISTEMA lo muestra en Error en la lista de documentos del notebook, con su archivo ligado, y el Usuario Gubernamental lo quita con la «x» como cualquier otro documento (RF-19).
  - El procesamiento es el mismo que en Ingesta, así que RF-07.2 aplica también a los notebooks.
  - *Prueba*: integración: carga con fallo en un notebook → fila en Error; quitarlo borra la fila y el archivo, sin fragmentos; las pruebas e2e de NotebookServIA siguen pasando.
- **RF-21.50** (RF-21, RF-22): CUANDO hay un fallo del procesamiento, EL SISTEMA sigue registrando la fila de error con su tema y su causa, a nombre del usuario; si el registro falla, el documento queda igual en Error.
  - *Prueba*: integración existente (`fila_de_error_con_la_causa`) y una con la bitácora simulada para fallar.

### C. Aviso de rechazo con nombre largo (hallazgo c)
- **RNF-04.50** (RNF-04, RF-05): MIENTRAS la pantalla mide 616 px o más, el contenedor del texto del aviso de un archivo rechazado con un nombre de 255 bytes sin espacios no se desborda, y el nombre completo sigue legible (se parte en varias líneas).
  - *Prueba*: e2e a 616 px y en escritorio, aserción añadida a `RNF-04.40` (sin prueba nueva).

### D. Imágenes y manuscrito (D3)
- **RF-10.50** (RF-10, RF-05, HU-10, CU-08): EL SISTEMA muestra en Ingesta de Datos y en la carga de un notebook la advertencia «Las imágenes deben contener texto impreso o tipeado: la escritura a mano no se reconoce de forma confiable.»
  - *Prueba*: e2e, aserción añadida a una prueba existente de cada pantalla (en ambos anchos, sin prueba nueva).
- **RF-05.50** (RF-05, RF-09, «Estado actual»): EL SISTEMA admite en Ingesta de Datos las imágenes JPG, JPEG, PNG, TIF, TIFF y BMP, como en NotebookServIA, y las procesa con el reconocimiento de texto en imagen.
  - La lista de formatos visible y el selector de archivos incluyen las seis extensiones; la pantalla filtra por extensión, como hoy con los demás formatos.
  - Cada imagen agregada se identifica como imagen (no como documento ni audio) en la lista y en su progreso.
  - Una imagen no se rechaza por posible manuscrito (RF-10); si el reconocimiento falla, sigue RF-07.2.
  - *Prueba*: e2e (escritorio), en la prueba de RF-07.50: una PNG inventada con el reconocimiento simulado → Procesado e identificada como imagen; la lista de formatos incluye las seis.

### E. Requisitos existentes del módulo (testing.md, paso 3)
- **RF-05.51** (RF-05, «Estado actual»; D4, R2): SI llega al servidor un archivo con extensión, tipo MIME real o tamaño no permitidos, ENTONCES lo rechaza al cargar con su motivo, sin guardarlo ni encolarlo.
  - *Prueba*: integración, fallo esperado `RF-05.51 · ingesta` (uno por motivo: extensión, MIME, tamaño); no se corrige en esta spec.
- **RF-06.2** sigue en fallo esperado; RF-08, RF-09, RF-17.4 y RF-22: sus pruebas siguen pasando sin cambios.

## Requisitos no funcionales
- **RNF-09.50** (RNF-09, constitución principio 6; S4): MIENTRAS se cargan y consultan documentos, EL SISTEMA no envía documentos, fragmentos, preguntas ni respuestas a servicios externos, incluido el rastreo de LangChain.
  - Al arrancar, el backend y el proceso de ingesta fuerzan `LANGSMITH_TRACING` y `LANGCHAIN_TRACING_V2` a `false`, aunque vengan activos o falten.
  - SI alguna venía activa, ENTONCES escribe un aviso en el log (sin valores de claves).
  - *Prueba*: unitaria: con ambas variables forzadas a «true», tras el arranque quedan apagadas y se registra el aviso; ausentes, quedan apagadas sin aviso.
  - *Verificación manual aparte*: Andrés revisa el `.env` real del `backend` y del `celery-worker` de desarrollo antes del piloto.
- **RN-01.50** (RN-01, RNF-10): ningún cambio de esta spec borra físicamente documentos, archivos ni temas; las únicas excepciones son quitar un documento de un notebook (RF-19) y los datos de prueba en los entornos aislados.
- **Presupuesto del extremo a extremo** (RA-02.47):
  - Antes de escribir pruebas, una tarea 0 mide la línea base con dos corridas completas de `npm run e2e` (sin cambios).
  - Lo nuevo o ampliado suma como máximo **30 s** a la «suite» respecto de la media de la línea base, incluidas las aserciones añadidas en ambos anchos (RF-06.54, RNF-04.50, RF-10.50); la corrida completa queda en **≤ 560 s** (límite 600 s).
  - Solo dos pruebas nuevas, en escritorio: temas (RF-06.50-52) y fallo más imagen (RF-07.50, RF-05.50).
  - SI se supera cualquiera de las dos cifras, ENTONCES se para y se pregunta a Andrés; el límite de 600 s no se sube por cuenta propia.
- Sin esquema nuevo, migración, dependencia ni cambio de prompts o modelos.

## Orden de trabajo pedido al plan
- Por valor, con pocas corridas completas (agrupar las e2e al cierre de cada bloque).
- Bloque 1 (imprescindible para el piloto): RF-06.50-54, RF-07.2, RF-07.50-52, RF-07.54, RF-21.50, RNF-09.50.
- Bloque 2: RNF-04.50, RF-10.50, RF-05.50, RF-05.51 y RF-07.53.
- Corte: si el bloque 2 no cabe, se cierra la spec con el bloque 1 y lo restante pasa a otra spec, con su «Estado actual» en el ERS.

## Casos límite
- Varios archivos y varios temas en un Guardar; uno agregado con el campo vacío; uno agregado con el texto escrito sin confirmar (toma ese texto, S2) (RF-06.50).
- Pendiente sin tema: Guardar deshabilitado con su texto (RF-06.50).
- Un grupo con tema no válido (más de 60 caracteres) y otro válido en el mismo Guardar: resultado parcial (RF-06.52).
- Tema con forma de clave de notebook en Ingesta: 404 de RF-17.4, mostrado como tema no válido (RF-06.52).
- «Normativa», «normativa», « Normativa » y «Normatíva» (RF-06.53).
- Tema nuevo en dos grafías en un mismo Guardar (peticiones simultáneas): un solo nombre, el que se registra primero (RF-06.53, CC1).
- Carga con todos los archivos rechazados a un tema nuevo: el tema queda creado y vacío (RF-06.53, CC2).
- PDF dañado, PDF sin texto extraíble, imagen sin texto reconocible y fallo del reconocimiento: en Error con su causa (RF-07.2).
- Validación en segundo plano de extensión o formato: sin fila (R2, RF-05.51, fallo esperado).
  - Diferencia con CU-07 FE-03, que incluye «formato o tamaño no permitido» entre las causas de Error: con R2 ese caso no deja documento en Error; se anota en el texto propuesto.
- Imagen manuscrita: se acepta y se procesa; el texto puede tener errores (RF-10).
- Cancelación: queda «Error» en lugar de «cancelado» (RF-07.53, fallo esperado).
- La causa visible en el progreso dura lo que dura su seguimiento; después queda en la bitácora. Guardarla en el documento exigiría cambiar el esquema: fuera de alcance.
- El mismo archivo vuelto a cargar por el usuario tras un Error: fila nueva, la anterior en Error (RF-07.51); dos cargas correctas del mismo archivo al mismo tema: comportamiento actual, se anota si el piloto lo muestra.
- Archivo en Error dentro de un notebook: visible y quitable con la «x» (RF-07.54).
- Nombre de 255 bytes sin espacios (RNF-04.50).
- Tema con bitácora: no se puede borrar (clave foránea, RN-01; documentación 005b, sección 7).

## Datos de la verificación manual y carga del piloto (D5, S3)
- Verificación manual en desarrollo con los temas `PRUEBA` y `PRUEBA 2` (dos temas en un Guardar), con archivos inventados (PDF válido, PDF dañado, PNG de texto impreso, nombre largo).
  - `PRUEBA 3` (con `prueba 3` en el mismo Guardar) verifica la corrección T10 (DD1); el notebook `PRUEBA 006` verifica RF-07.54 y RF-10.50.
  - Al terminar se quitan sus documentos, fragmentos y archivos (también los del notebook `PRUEBA 006`), solo con la aprobación explícita de Andrés en ese momento.
  - Los temas `PRUEBA`, `PRUEBA 2` y `PRUEBA 3` quedan vacíos como residuo aceptado, anotado como en la 005b (sección 7), porque la bitácora los referencia.
- Los PDF de Nexus son documentos institucionales reales y **nunca** son datos de prueba: no entran en las pruebas automatizadas ni en el repositorio; solo en `~\Documents\ServIA-fuentes\Nexus` (descargas, fuera del repositorio; LL1), `uploads/` (ignorado por git) y Qdrant de desarrollo.
- Los carga Andrés (salvo EEE1: un agente) en desarrollo como paso operativo tras la validación, con RNF-09.50 comprobado. Sin anonimización (públicos y sin datos personales salvo la firma del funcionario en su cargo, PP1).
- **Asistencia operativa en Nexus (KK1)**: un agente usa el navegador de Andrés (su ventana y su sesión) para explorar Nexus, explicarle la interfaz y descargar documentos candidatos.
  - No es una función del producto: ServIA sigue sin conexión, API ni rastreo de Nexus; nada de código, scripts ni descargas masivas automatizadas.
  - El agente nunca recibe contraseñas; si Nexus pide sesión, la inicia Andrés.
  - Regla precisada (BBB1, todas las fuentes): `evaluate_script` solo lee el DOM de la página ya cargada; nunca hace peticiones de red (`fetch` u otras).
  - Solo documentos públicos de interés general (autorización del tutor por correo), PDF con texto seleccionable: circulares y avisos de política general; se acepta el nombre del funcionario que firma en su cargo y se descarta todo documento sobre personas concretas (ascensos, nombramientos, reconocimientos, vacaciones, actas, sentencias, resoluciones disciplinarias) (PP1).
  - Las descargas van solo a `~\Documents\ServIA-fuentes\Nexus` (LL1); nunca a `uploads/` ni a ninguna ruta del repositorio. Las fuentes futuras de otras páginas irán a `ServIA-fuentes\<página>`.
  - Andrés revisa uno por uno los descargados y solo él decide qué entra; la carga la hace él por la pantalla de Ingesta (que guarda su copia en `uploads/`); salvo EEE1: revisión y carga las hace un agente (bloque «Carga del corpus (DDD1, EEE1)»).
  - El piloto sigue siendo de 10-30 PDF; se amplía después del piloto.
  - Aviso legal de Nexus: el Art. 37 del Reglamento de Datos Personales del Poder Judicial (Corte Plena, sesión 33-2024, Art. XV) prohíbe respaldos particulares y bases paralelas con herramientas robotizadas o de IA.
  - El uso de Nexus en esta spec cuenta con la aprobación del tutor, expuesta en reunión y confirmada por correo (NN1).
- **Segunda fuente: Asamblea Legislativa (TT1)**: la misma asistencia operativa de KK1, con todos sus límites, sobre https://www.asamblea.go.cr/.
  - Descargas solo a `~\Documents\ServIA-fuentes\Asamblea` (LL1).
  - Criterio PP1: se acepta el nombre del funcionario o diputado que firma en su cargo; se descarta todo documento sobre personas concretas.
  - Se descartan, por ejemplo: nombramientos, pensiones de gracia, naturalizaciones, ciudadanías honoríficas, actas con intervenciones de ciudadanos y expedientes de personas. Solo texto extraíble; nada casi vacío.
  - Excepción (WW1): se aceptan los listados oficiales de leyes publicadas en La Gaceta aunque nombren al beneficiario de una ley (pensión de gracia, naturalización, benemérito, donación de terreno); sin cédulas, correos ni celulares.
  - Compilados (VV1): los 8 PDF (2006-2017, sin duplicados) de la biblioteca «Resumen de leyes aprobadas» (https://asamblea.go.cr/glcp/Resumen_proyecto/Forms/AllItems.aspx), al tema `ASAMBLEA-Leyes-y-Proyectos`.
  - Volumen: el 10-30 era el piloto de Nexus; para la Asamblea, Andrés fijó «30 o más que sean documentos de interés general para el país».
  - Condiciones de uso: el pie del sitio declara licencia Creative Commons Reconocimiento 4.0 Internacional; no hay restricción como el Art. 37 de Nexus.
  - Los Términos de uso (https://www.asamblea.go.cr/SitePages/Terminos_Uso.aspx) autorizan «ver, copiar, imprimir y distribuir (sin modificar)» con fines informativos y conservando la atribución.
  - Ambigüedad menor: «sin modificar» frente a fragmentar o resumir con IA; CC BY lo permite y ServIA cita la fuente, lo que cumple la atribución.
  - Temas sugeridos: `ASAMBLEA-Investigaciones-CEDIL`, `ASAMBLEA-Reglamento-y-Normativa`, `ASAMBLEA-Informes-y-Presupuesto`, `ASAMBLEA-Leyes-y-Proyectos`, `ASAMBLEA-Estadisticas-Legislativas`.
  - La autorización del tutor para esta fuente aún no está por escrito; Andrés se la comunicará por correo (SS1, no bloqueante).
- **Tercera fuente: repositorio de CONARE (XX1)**: la asistencia operativa de KK1, con todos sus límites, sobre https://repositorio.conare.ac.cr/home (DSpace 7; comunidades CENAT, OPES y PEN); unos 30 PDF con el criterio PP1.
  - Descargas solo a `~\Documents\ServIA-fuentes\CONARE` (LL1).
  - Solo ítems con licencia CC BY-NC-SA 4.0 verificada en los metadatos de cada ítem (`dc.rights.uri`).
  - Se descartan: los que solo dicen «acceso abierto» sin licencia CC, los que tengan ND (sin obras derivadas) y los PDF que solo contienen un enlace al editor.
  - Lectura de la licencia: NC encaja (uso institucional público y sin lucro); BY se cumple al citar la fuente; SA aplica a lo que se derive del contenido.
  - Política del repositorio: no se pudo leer (https://repositorio.conare.ac.cr/info/politicas devuelve 404); no se vio una restricción como el Art. 37 de Nexus, pero no se puede afirmar que no exista.
  - Se prefieren resúmenes y capítulos a los informes completos muy grandes.
  - Temas (YY1; 30 PDF descargados, todos con CC BY-NC-SA 4.0 verificada): `CONARE-Estado-de-la-Nacion` (13), `CONARE-Estado-de-la-Region` (1), `CONARE-Estado-de-la-Justicia` (4), `CONARE-Estado-de-la-Educacion` (6), `CONARE-OPES-Estadisticas` (1), `CONARE-OPES-Planes-e-Informes` (5).
  - Autorización del tutor para esta fuente: pendiente por correo, no bloqueante (como SS1).
- **Cuarta fuente: Kimuk (AAA1)**: la asistencia operativa de KK1, con todos sus límites, sobre https://kimuk.conare.ac.cr/ (buscador nacional de CONARE que cosecha los repositorios de UCR, UNA, TEC, UNED, UTN, CATIE, LEAD y TSE); unos 30 PDF con el criterio PP1.
  - Kimuk no aloja los PDF: se bajan del repositorio de origen (p. ej. Kérwá de la UCR). Descargas solo a `~\Documents\ServIA-fuentes\Kimuk` (LL1).
  - Solo ítems con licencia Creative Commons explícita en el repositorio de origen (`dc.rights.uri`), sin ND; se descartan los que solo dicen «acceso abierto».
  - Se descartan también las tesis y trabajos finales de graduación y los estudios clínicos o con participantes identificables.
  - Condiciones: Kimuk no tiene propias y delega los derechos en cada repositorio (https://kimuk.conare.ac.cr/Content/about); no hay restricción como el Art. 37 de Nexus.
  - Kérwá (https://kerwa.ucr.ac.cr/info/politicas) permite descargar, copiar y reproducir «de forma personal y con propósitos educativos o de investigación», sin uso comercial, con atribución, enlace al original e integridad de la obra.
  - Riesgo aceptado (AAA1): la ambigüedad de «de forma personal» frente a un sistema institucional sin fines de lucro; consulta opcional al repositorio.
  - Temas (BBB1; 19 artículos de los portales de revistas de UCR y UNA, todos con CC explícita sin ND): `KIMUK-UCR-Ciencias-Juridicas` (10, CC BY-SA 4.0), `KIMUK-UCR-Administracion-Publica` (7, CC BY-NC-SA 4.0), `KIMUK-UCR-Educacion` (1), `KIMUK-UNA-Ciencias-Ambientales` (1).
  - Incidencia (lección): `evaluate_script` con `fetch` leyó listas y licencias, hasta unas 12 páginas por llamada, más allá de la lectura puntual de KK1, y Kimuk dejó de responder; de ahí la regla precisada de KK1.
  - Autorización del tutor: pendiente por correo, no bloqueante (como SS1).
- **Quinta fuente: SINALEVI (CCC1)**: la asistencia operativa de KK1, con todos sus límites, sobre https://sinalevi.go.cr/ (Sistema Nacional de Legislación Vigente, Procuraduría General de la República), con el criterio PP1.
  - Unas 30 leyes vigentes de interés general, con su número y vigencia comprobados en SINALEVI, siempre la última versión, una a una con «Exportar a PDF».
  - Descargas solo a `~\Documents\ServIA-fuentes\SINALEVI` (LL1).
  - Se excluyen las leyes sobre personas concretas (WW1 no aplica: no son listados) y, por ahora, los códigos muy extensos (Civil, Penal, Procesales, de Trabajo); la Constitución Política se sube aparte.
  - Condiciones: sin términos, aviso legal ni política; solo el pie «© 2026 Procuraduría de la Republica. Todos los derechos reservados.», que no prohíbe ni permite respaldos, bases paralelas ni IA.
  - Lectura: protegería el sitio y su compilación, no el texto de las leyes (norma pública), sin poder afirmarlo; riesgo aceptado (CCC1), consulta opcional a la PGR por su formulario de contacto.
  - Temas sugeridos (se ajustan a lo descargado): `SINALEVI-Constitucion-y-Derechos`, `SINALEVI-Administracion-Publica`, `SINALEVI-Hacienda-y-Contratacion`, `SINALEVI-Ambiente-y-Salud`, `SINALEVI-Trabajo-y-Social`.
  - Temas definitivos (DDD1; 31 PDF): `SINALEVI-Constitucion-y-Derechos` (8), `SINALEVI-Administracion-Publica` (7), `SINALEVI-Hacienda-y-Contratacion` (5), `SINALEVI-Ambiente-y-Salud` (6), `SINALEVI-Trabajo-y-Social` (5).
  - Ley 8764 descartada: su texto está dañado en el propio sitio desde el artículo 35; queda en `ServIA-fuentes\SINALEVI\_descartados\` (no se carga), sustituida por la Ley 7472.
  - Autorización del tutor: pendiente por correo, no bloqueante (como SS1).
- **Carga del corpus (DDD1, EEE1)**: descargas cerradas; 158 PDF en 24 temas: Nexus 30 (3), Asamblea 48 (5), CONARE 30 (6), Kimuk 19 (4), SINALEVI 31 (5).
  - La carga la hace un agente con el MCP `chrome-devtools`, con la sesión del Usuario Gubernamental que inicia el desarrollador (el agente nunca recibe contraseñas), por la pantalla de Ingesta, desde `ServIA-fuentes\<fuente>`.
  - Orden: una prueba con un archivo; tandas de un mismo tema; los tres archivos largos al final, uno a uno.
  - El agente revisa cada PDF antes de cargarlo (metadatos, primera página y texto extraído con `pdftotext`), comprueba el estado de cada tanda y reporta los Error con su causa.
  - SI el MCP no admite archivos fuera del proyecto, ENTONCES el agente para y avisa; nunca copia un PDF dentro del repositorio.
- **Fuente descartada: Atlas.co (ZZ1)**: https://atlas.co/data-portals/datos-abiertos-costa-rica/ es un directorio privado de portales de datos abiertos (tablas, no documentos); no se usa.
- Riesgo conocido (RF-06.2, fallo esperado): seleccionar un tema de Nexus en el chat consulta todos los documentos; el piloto se verifica desde el chat general.

## Fuera de alcance
- Conexión, API, rastreo o MCP de ServIA hacia Nexus, la Asamblea Legislativa, el repositorio de CONARE, Kimuk o sus repositorios de origen, o SINALEVI (la asistencia operativa de KK1, TT1, XX1, AAA1 y CCC1 no es función del producto); corpus o esquema nuevos; OCR de escaneados; anonimización.
- Chat acotado a un tema de nombre libre (RF-06.2), detección de temas libres en el chat y en temas similares (RT-06).
- Validación en el servidor de extensión, MIME y tamaño (RF-05.51), validación en el cliente del tipo MIME y del límite de 1 GB, y la corrección de la cancelación (RF-07.53): solo fallo esperado o sin cambio.
- Imágenes: pegar o arrastrar sobre el chat del notebook, calidad del reconocimiento (RF-09) y su integración más allá de admitirlas en Ingesta.
- Rechazados en las estadísticas, la causa persistida en el documento, duplicados por el usuario, edición del tema por fila.
- Ajustes gráficos de la 005b: «expediente» en el panel del Administrador, «Poder Judicial» en el pie.
- Mejoras del notebook (RF-19.40), renombrar «expediente» en el código o la base.

## ⚠️ Pregunta antes (CLAUDE.md) que tocará el plan
- Crear archivos nuevos: los archivos inventados de prueba (PDF dañado, PDF sin texto, PNG) y, si hiciera falta, un archivo de prueba nuevo.
- Borrar datos de SQL Server, Qdrant o `uploads/` de desarrollo: limpieza de los temas `PRUEBA`, `PRUEBA 2` y `PRUEBA 3` y del notebook `PRUEBA 006`, solo con la aprobación explícita de Andrés en ese momento.
- Commit y push: al cierre, con @committer.
- No se toca: esquema, migraciones, prompts, modelos, `docker-compose.yml` (S4: el rastreo se apaga en el código) ni el nombre «expediente» en el código o la base.

## Criterios de finalización
- Cada requisito con su prueba vista en rojo antes del código y luego en verde.
- Fallos esperados al cerrar (pytest): ≈ 45 − 2 (RF-07.2, RF-07.52) + 3 (RF-05.51) + 1 (RF-07.53) = **47**; el plan lo recalcula sobre la línea base real. E2e: sin fallos esperados nuevos.
- `pytest` y `--orden-inverso`: 0 fallos, 0 XPASS, sin residuos. `npm run e2e`: «CORRECTO» dentro del presupuesto.
- Verificación manual en desarrollo, en escritorio y a 616 px, con los temas `PRUEBA` y `PRUEBA 2` (y `PRUEBA 3` para T10): dos temas en un Guardar, un tema nuevo en dos grafías con un solo nombre, un PDF dañado en Error con su causa, una PNG Procesada, el aviso largo sin desborde, la advertencia en Ingesta y en el notebook; fila en SQL Server, Qdrant y bitácora; el Administrador no entra en Ingesta.
- Limpieza hecha con la aprobación de Andrés y los temas `PRUEBA`, `PRUEBA 2` y `PRUEBA 3` vacíos anotados como residuo aceptado.
- Paso operativo de Andrés tras la validación: piloto de Nexus cargado, cada PDF Procesado o en Error con su causa, y el chat general cita al menos uno.
- Texto propuesto para el ERS y el CU (sección siguiente) entregado a Andrés; `MEMORY.md` actualizado.

## Texto propuesto para el ERS y el CU (lo aplica Andrés en la entrega de la semana 4)
- **RF-05** (Estado actual): quitar «la pantalla de Ingesta de Datos todavía no admite imágenes… y la advertencia sobre la escritura a mano aún no se muestra» y «El aviso con un nombre de archivo muy largo se desborda a 616 px…».
  - Queda: «El servidor todavía no valida el formato, el tipo MIME ni el tamaño de los archivos; hoy solo lo hace la interfaz (fallo esperado, spec 006).» Estado: Parcial.
- **RF-06**: añadir «Antes de asociarlo, el sistema quita los espacios al inicio y al final del tema y, si ya existe uno igual salvo mayúsculas y minúsculas, usa el ya registrado; las tildes distinguen temas.» `[NUEVO]` (RF-06.53).
  - Añadir: «El tema se resuelve o se crea al cargar, antes de almacenar y encolar los archivos; un tema nuevo escrito en dos grafías en una misma carga queda con un solo nombre. Si se rechazan todos los archivos, el tema queda creado y vacío.» `[NUEVO]` (RF-06.53, CC1-CC2).
  - Cambiar el límite del tema de «255 bytes» a «60 caracteres», como ya aplica el sistema (T2; sin cambio de código).
  - Estado actual: «La pantalla de Ingesta de Datos acepta temas de nombre libre (spec 006); el chat acotado a uno de ellos todavía consulta todos los documentos (ver RT-06).» Estado: Parcial.
- **RF-07**: añadir «Si un archivo que quedó en Error se vuelve a cargar, se crea un documento nuevo y el anterior se conserva en Error» `[NUEVO]` (RF-07.51) y «Un archivo cargado en un notebook que falla queda en Error en la lista del notebook y puede quitarse» `[NUEVO]` (RF-07.54).
  - Estado actual: reemplazar por «Al cancelar el procesamiento, el archivo queda en Error en lugar de cancelado por el usuario (fallo esperado, spec 006).» Estado: Parcial.
- **RF-10**: anotar que la advertencia se muestra en Ingesta de Datos y en NotebookServIA (spec 006).
- **RNF-04** (Estado actual): quitar el desborde por nombre largo.
- **RNF-09**: anotar que el sistema apaga al arrancar el rastreo de LangChain (spec 006).
- **CU-07 paso 3**: «El usuario escribe el tema y agrega uno o varios archivos; cada archivo queda con el tema escrito al agregarlo, que la lista muestra en su fila. Para otro tema, cambia el campo y agrega los siguientes.» (D2, R1).
- **CU-07 paso 5**: «… con el resumen de archivos agrupados por tema y la advertencia de que quedarán asociados permanentemente a su tema.»
- **CU-07 paso 7**: «El sistema asocia cada archivo al tema indicado, creándolo si todavía no existe (con el nombre ya registrado si coincide salvo mayúsculas) antes de almacenarlo y encolarlo; si no se acepta ningún archivo, el tema queda creado y vacío.» (CC2).
- **CU-07 FE-03**: quitar «formato o tamaño no permitido» de las causas de Error, o anotar que hoy ese rechazo en segundo plano no deja documento (R2, RF-05.51).
- **CU-07 FA-01**: anotar que un archivo del notebook que falla queda en Error y se quita con la «x» (RF-07.54).

## Notas para el plan (código verificado el 27/10/2026; no son requisitos)
- RF-06.52 / S1: tope de 25 caracteres en `ExpedienteInput.jsx:34-39` (`EXPEDIENTE_INPUT_MAX_LENGTH`, `expedienteValidator.js:44`); el servidor limita a 60 (`LONGITUD_MAXIMA_TEMA`, `file_management_service.py:24`).
- RF-06.52: el 400/404 de un grupo cae en el `catch` de `useFileUploadProcess.js:421-439` y deja el grupo `fallido`.
- RF-06.53: `es_nombre_seguro` (`file_management_service.py:46`) rechaza el final en espacio; el recorte va antes de `validar_tema` (`:62`).
- RF-06.54, piezas con «expediente» o formato heredado: `ExpedienteInput.jsx:30, 32, 44-58, 92`; `UploadConfirmModal.jsx:37, 49, 86`; `FilesList.jsx:100-110` (campo por fila, se retira; placeholder «Núm. expediente» en `:103`); `IngestaDatos.jsx:54, 63` (alertas) y `:92` (mínimo de 17).
- e2e: el localizador `campoDelTema` (`frontend/e2e/soporte/pantallas.js:93`) usa el placeholder `02-000744-0164-CI`; el plan debe cambiarlo al rótulo «Tema».
- RF-07.53: `test_red_ingesta.py:436` (`test_falla_la_vectorizacion_el_documento_queda_en_error[cancelacion]`) fija hoy lo contrario (cancelación → Error); cambiará cuando se corrija la cancelación, no en esta spec.

## Decisiones (27/10/2026, Andrés: D1-D5, R1-R5, S1-S4, T1-T2)
- **D1 = A**: Ingesta acepta un tema de nombre libre (reglas de RF-06); se consulta desde el chat general; RF-06.2 sigue en fallo esperado.
- **D2 = A**: cada archivo conserva su tema; la confirmación agrupa por tema (precisado por R1).
- **D3 = B**: advertencia de manuscrito en Ingesta y en el notebook, e imágenes admitidas en Ingesta (reconocimiento simulado en las pruebas), con alcance acotado.
- **D4 = A**: la validación en el servidor (RF-05.51) entra como fallo esperado, sin corregir.
- **D5 = A** (ampliada por S3): temas `PRUEBA` y `PRUEBA 2` en desarrollo, vacíos al final como residuo aceptado; el piloto de Nexus es un paso operativo de Andrés; los PDF de Nexus nunca son datos de prueba.
- **R1 = A**: el tema se fija al agregar y se ve en cada fila; un pendiente sin tema toma el primer tema confirmado (Enter o foco perdido); sin edición por fila; Guardar deshabilitado con texto mientras falte un tema.
- **R2 = A**: la validación en segundo plano queda fuera de «fallo del procesamiento»; la cubre el fallo esperado de RF-05.51.
- **R3 = A**: el reintento interno se deduplica por identificador de tarea; una recarga del usuario tras un Error crea una fila nueva y conserva la anterior (RN-01, HU-07).
- **R4 = A**: la cancelación se cubre con un fallo esperado (RF-07.53), sin corregirla; RF-07 queda «Parcial».
- **R5 = A**: las tildes distinguen temas. El plan lo confirma contra la intercalación de SQL Server; si la base no las distingue, se PARA y se pregunta a Andrés (no se igualan por cuenta propia).
- **S1 = A**: se retira el tope de 25 caracteres de la pantalla; la longitud solo la valida el servidor (60); un tema demasiado largo sale rechazado con su mensaje.
- **S2 = A**: al agregar se toma el texto actual del campo (recortado), confirmado o no; «tema confirmado» solo aplica a los pendientes sin tema.
- **S3 = A**: verificación manual con `PRUEBA` y `PRUEBA 2`, ambos residuo aceptado y anotado.
- **S4 = A**: el backend fuerza el rastreo de LangChain a apagado al arrancar, con aviso en el log si venía activo; la revisión del `.env` real sigue aparte.
- **T1 = A**: un tema con forma de clave de notebook en Ingesta (404 de RF-17.4) deja el grupo rechazado con «El tema indicado no es válido», igual que un tema no válido, sin revelar si el notebook existe (RF-06.52).
- **T2 = A**: el ERS baja el límite del tema de RF-06 de 255 bytes a 60 caracteres, como hace hoy el sistema; no cambia el código (texto propuesto para el ERS).

## Decisiones de la corrección T10 (28/10/2026, Andrés: CC1, CC2, DD1)
- **CC1 = A**: se corrige la carrera de RF-06.53 hallada en la verificación manual de T9: un tema nuevo en dos grafías en un mismo Guardar deja un solo nombre (corrección T10).
- **CC2 = A**: el tema se resuelve o se crea al cargar, antes de guardar y encolar; si todos los archivos se rechazan, queda creado y vacío (residuo aceptado).
- **DD1 = A**: la corrección se verifica a mano con `PRUEBA 3` y `prueba 3` en un mismo Guardar; `PRUEBA 3` queda como residuo aceptado.

## Decisiones de la asistencia operativa en Nexus, la Asamblea Legislativa, CONARE, Kimuk y SINALEVI (28/10/2026, Andrés: KK1-EEE1)
- **KK1 = C**: un agente puede usar el MCP `chrome-devtools`, en la ventana y con la sesión de Andrés, para explorar Nexus, enseñarle la interfaz y descargar candidatos; con los límites de «Datos de la verificación manual y carga del piloto».
- **LL1 = A**: las descargas van a `~\Documents\ServIA-fuentes\Nexus`, fuera del repositorio; otras páginas, a `ServIA-fuentes\<página>`.
- **MM1 = A** (28/10/2026): solo se descargan candidatos sin datos personales; uno con nombres u otros datos de personas se descarta (línea de KK1 en «Datos de la verificación manual y carga del piloto») (precisada por PP1 y WW1).
- **NN1 = A** (28/10/2026): se sigue con Nexus pese al aviso del Art. 37, con la aprobación del tutor por correo; recomendación no bloqueante: reenviarle el texto del Art. 37 para que la aprobación lo mencione expresamente.
- **PP1 = A** (28/10/2026; precisa MM1): se acepta el nombre del funcionario que firma en su cargo; se descartan los documentos sobre personas concretas; quedan circulares y avisos de política general.
- **SS1** (28/10/2026): la autorización del tutor para la Asamblea Legislativa aún no está por escrito; Andrés se la comunicará por correo; no bloqueante.
- **TT1 = A** (28/10/2026): segunda fuente, la Asamblea Legislativa; un agente explora y descarga con el MCP con los límites de KK1, el criterio PP1 y «30 o más» documentos (bloque «Segunda fuente: Asamblea Legislativa (TT1)»).
- **VV1 = A** (28/10/2026): de la Asamblea se bajan también los 8 compilados de «Resumen de leyes aprobadas» (2006-2017, sin los 2 duplicados), al tema `ASAMBLEA-Leyes-y-Proyectos`.
- **WW1 = A** (28/10/2026; precisa PP1): se aceptan los listados oficiales de leyes publicadas en La Gaceta aunque nombren al beneficiario de una ley concreta; ningún compilado trae cédulas, correos ni celulares.
- **XX1 = A** (28/10/2026): tercera fuente, el repositorio de CONARE; un agente descarga con el MCP unos 30 PDF con los límites de KK1, el criterio PP1 y solo licencia CC BY-NC-SA 4.0 verificada (bloque «Tercera fuente: repositorio de CONARE (XX1)»).
- **YY1 = A** (28/10/2026): los 30 PDF de CONARE van a seis temas, dos nuevos (`CONARE-Estado-de-la-Educacion`, `CONARE-OPES-Planes-e-Informes`); todos con CC BY-NC-SA 4.0 verificada.
- **ZZ1 = B** (28/10/2026): Atlas.co queda fuera: directorio privado de portales de datos abiertos (tablas, no documentos).
- **AAA1 = B** (28/10/2026): cuarta fuente, Kimuk; un agente descarga del repositorio de origen unos 30 PDF con los límites de KK1, el criterio PP1, licencia CC explícita sin ND y sin tesis ni estudios con participantes identificables; se acepta el riesgo de «de forma personal» de Kérwá (bloque «Cuarta fuente: Kimuk (AAA1)»).
- **BBB1 = A** (28/10/2026): los 19 artículos de Kimuk van a cuatro temas según su revista de origen y sustituyen a los sugeridos en AAA1; tras la incidencia, `evaluate_script` solo lee el DOM, sin peticiones de red (todas las fuentes, KK1).
- **CCC1 = A** (28/10/2026): quinta fuente, SINALEVI; unas 30 leyes vigentes de interés general, última versión, con los límites de KK1 y el criterio PP1, sin códigos extensos salvo la Constitución aparte; se acepta el riesgo del pie de derechos reservados (bloque «Quinta fuente: SINALEVI (CCC1)»).
- **DDD1 = A** (28/10/2026): se cierran las descargas: 158 PDF en 24 temas; en SINALEVI, la Ley 8764 (texto dañado en el sitio) se descarta y la sustituye la Ley 7472.
- **EEE1 = A** (28/10/2026; modifica KK1): la revisión y la carga las hace un agente por la pantalla de Ingesta, con la sesión que inicia el desarrollador; sustituye la revisión uno por uno de KK1 (bloque «Carga del corpus (DDD1, EEE1)»).

## Decisiones de implementación (Andrés, 27-28/10/2026; detalle en `tasks.md` y `MEMORY.md`)
- **W1 = A**: si un reintento interno vuelve a ejecutar la misma tarea y el documento Pendiente ya tiene fragmentos parciales, se da por Procesado (RF-07.51); riesgo aceptado, para una spec posterior.
- **X1 = A**: se hace el bloque 2 (T6-T8); no hay corte.
- **Y1 = A**: la corrida de 568,7 s de T6 fue ruido de la máquina (repetida sin cambios en 511,6 s); el presupuesto se mantiene.
- **Z1 = A**: la prueba de RF-07.50 acepta cualquiera de las 4 causas del conjunto cerrado de RF-22, no una fija.

## Dudas abiertas
Ninguna.
