# Spec 003a — Correo de las cuentas: creación, restablecimiento por el Administrador y rutas de correo protegidas
Estado: implementada (08/10/2026)

> Este documento describe las debilidades pendientes solo en términos generales; el detalle de lo corregido está en el código y en las pruebas.

Historial: 07/10/2026 — creada al dividir la spec 003 (decisión D9 de Andrés, clarificación del revisor). Reúne lo que se hace **primero**: el correo de las cuentas, las rutas protegidas y el tiempo máximo del envío. La recuperación pública va en la 003b, que depende de esta. 08/10/2026 — sincronizada con lo implementado (T10): el plan fijó el código **502** para el reseteo fallido (RF-03.14 dejaba elegir 502 o 503), el nombre de la variable del tiempo máximo es `EMAIL_TIMEOUT` y las tareas fueron 10, no 8; los requisitos no cambiaron. 08/10/2026 — corrección: el caso límite «el correo sale pero el guardado de la contraseña falla» ya decía que el intento queda en la bitácora y el código no lo hacía; ahora lo hace (texto: «Intento de reseteo de contraseña de usuario: <cédula> - notificación por correo: entregada; la contraseña no se guardó»); la spec no cambió. 08/10/2026 — decisión de Andrés (validación, decisión 2): se acepta que otros registros de errores de la autenticación y de la auditoría pueden incluir datos de la excepción (se revisarán con el módulo de autenticación), y se **acota el alcance de RNF-08.2** a los flujos de cuentas y a la bitácora (creación, restablecimiento por el Administrador, su correo en la bitácora y los registros del servidor que esos flujos escriben); el resto pasa a la futura spec de autenticación. Se conserva el enmascarado en un solo punto de la bitácora (opción A). El código y las demás decisiones no cambian. 08/10/2026 — corrección menor de documentos: «Cómo se comprueba» de RNF-08.2 queda en la creación y el reseteo por el Administrador (éxito y fallo) y la bitácora; la recuperación pública de la 003b se acotará en la spec 003b. El requisito no cambia. 08/10/2026 — **cierre formal: implementada.** T1 a T10 hechas; 607 pruebas pasan (469 unitarias y 138 de integración, también con `--orden-inverso`); el revisor aprobó la implementación y la condición B (el intento queda en la bitácora cuando el correo sale pero falla el guardado). Los cuatro documentos de planificación (ERS V1.4, Historias de Usuario V1.1, Casos de Uso V1.1 y Procesos V1.1, con P7) fueron editados y exportados a PDF, y el revisor los verificó contra el plan §13 sin faltantes. Decisiones de Andrés al cerrar: los registros de errores residuales de la autenticación y de la auditoría quedan aceptados y pasan a la spec de autenticación; «No entregada» se mantiene en gris; las specs se mantuvieron fuera del repositorio hasta corregir lo que describían; el ERS se queda en V1.4. Los requisitos no cambian. 12/10/2026 — Redacción para publicación: lo abierto en términos generales.

Contexto compartido, decisiones D1 a D15, excepciones E1 y E2, referencias de mercado y lista consolidada de documentos a actualizar: **spec paraguas `specs/003-correo-y-recuperacion-de-contrasena/spec.md`** (no se repiten aquí).

## Contexto y objetivo

Hoy, cuando el correo de una cuenta falla, el sistema no lo dice: al **crear una cuenta** el usuario queda creado sin que nadie sepa que no recibió su contraseña temporal; al **restablecer la contraseña** (vía a) la contraseña se cambia aunque el correo no salga, y el Administrador ve «éxito». El servicio de correo traga los errores y devuelve «falso» que los llamadores ignoran; no hay un tiempo máximo explícito del envío; y hay rutas de correo y de restablecimiento que no exigen sesión de Administrador (RNF-07).

Esta spec corrige eso, de punta a punta y con sus pruebas:

1. **Todo fallo de envío se informa al Administrador** (FS-03) en la creación de cuentas y en el restablecimiento, y queda en la bitácora con su resultado (RF-21.4).
2. **El restablecimiento no cambia la contraseña si el correo falla** (RF-03.14), y hay **una sola** lógica de restablecimiento (se retira la ruta duplicada del módulo de autenticación).
3. **Las rutas de correo exigen Administrador** (RNF-07.1, RNF-07.2).
4. **Tiempo máximo explícito del envío** (15 s, RF-03.16), codificación UTF-8 (RF-03.18), configuración del correo documentada (RF-03.19) y contraseñas fuera de los registros (RNF-08.1, RNF-08.2).
5. La **infraestructura de pruebas** que esta spec y la 003b necesitan: un reloj que las pruebas controlan y un correo simulado más completo (RA-02.9, RA-02.10).

Tamaño: 8 tareas estimadas al escribir la spec; el plan las llevó a 10 (el máximo; ver `tasks.md`). Orden de las specs: la 003a, luego la 003b, luego la 004 y la 005 (excepción E1 del paraguas).

## Trazabilidad
- ERS: **RF-02** (gestión de cuentas), **RF-03** (vía a), **RF-21** (bitácora), **RF-22** (consulta de la bitácora; solo el detalle), **RNF-07** (autenticación y autorización), **RNF-08** (solo lo que cubre RNF-08.1 y RNF-08.2: contraseñas fuera de los registros; el mínimo de 8 caracteres en el servidor queda fuera), FS-03 (2.2.1), RNF-06, RNF-09 y RT-02 (el correo no es un servicio de IA; el entorno de desarrollo usa un servicio de pruebas externo solo con datos inventados), RT-07, RA-02 (2.4.3) y la dependencia organizacional de la cuenta de correo (2.5).
- Historias de usuario: **HU-25**, HU-02, HU-22 (detalle del Historial), HU-24 y HU-21 (bitácora), HU-01, HU-03 y HU-04 (por RNF-08). Casos de uso: **CU-05** (incluidas FA-02 y FE-02), CU-03, CU-15.
- La tabla completa requisito por requisito (con el origen de cada uno) está en el paraguas.
- «Estado actual» del ERS que cierra: **RF-02** (el aviso al Administrador cuando no sale el correo de una cuenta nueva) y la parte de **RF-03** de la vía a. Lo que no cierra: la cuenta de correo institucional definitiva (dependencia organizacional, ERS 2.5) ni RNF-07 (sigue incompleto: algunas funciones de la cuenta del propio usuario todavía no exigen token (pendiente de la revisión del módulo de autenticación)).
- Los requisitos que el ERS no pide van marcados `[NUEVO]`; los demás «detallan» un requisito existente.

## Usuarios
- **Administrador**: crea cuentas, restablece contraseñas, consulta el Historial de Actividades (CU-05, CU-15).
- **Usuario Gubernamental**: no accede a estas funciones (debe recibir 403); recibe la contraseña temporal por correo.
- Actor secundario: el servicio de correo electrónico.

## Historias de usuario
- **HU-25** (de la documentación): el Administrador crea cuentas y restablece contraseñas. Esta spec agrega el aviso cuando la notificación no se entrega.
- HU-02 (cada rol accede solo a lo suyo; RNF-07.1 y RNF-07.2) y HU-22 (el Administrador consulta la bitácora; RF-21.6).
- No hay historia nueva en esta spec.

## Definiciones
- **Vía (a)**: el Administrador restablece la contraseña de un usuario desde «Usuarios del Sistema». **Vía (b)** o **recuperación pública**: el propio usuario, sin sesión, desde «¿Olvidaste tu contraseña?» (spec 003b).
- **Contraseña temporal**: la contraseña aleatoria de 8 caracteres que el sistema genera al crear una cuenta o restablecerla por la vía (a); obliga a cambiarla al iniciar sesión (último acceso vacío). **Código de verificación**: el número de 6 dígitos de la vía (b). Son cosas distintas.
- **Cuenta Activa**: la que está en estado Activo; «no Activa» es cualquier otro estado. Hoy la tabla de estados solo tiene **Activo** e **Inactivo** (no existe un estado «Bloqueado»); las pruebas de «cuenta no Activa» usan Inactivo.
- **Envío fallido**: el servidor de correo no aceptó el mensaje, por cualquier causa: error del servidor, rechazo del destinatario, autenticación fallida, conexión rechazada, falta de cuenta de correo configurada, puerto inválido o más de 15 segundos (RF-03.16). **Envío exitoso**: el servidor aceptó el mensaje (el sistema no puede saber si llegó al buzón). **Notificación entregada / no entregada**: el envío fue exitoso / fallido.
- **Reloj controlable**: el reloj con el que el sistema consulta la hora y mide plazos; en producción es el reloj real y en las pruebas lo adelanta la prueba a voluntad (RA-02.9). **Margen de RF-03.16**: 1 segundo del reloj controlable (no es tiempo real).
- **Rutas**: «reseteo de gestión de usuarios» es `POST /usuarios/{id}/resetear-contrasenna`; «restablecimiento heredado» es `POST /auth/restablecer-contrasenna` (se retira, RNF-07.1); «creación de cuenta» es `POST /usuarios/`; «rutas de correo» son `POST /email/test-email` y `GET /email/email-config`.
- **Variables del correo**: `EMAIL_PROVIDER` (con el valor `custom` para un servidor propio), `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_USERNAME` y `EMAIL_PASSWORD`.
- **Variable del tiempo máximo del envío**: la variable de configuración que fija el límite de RF-03.16 (el plan fija su nombre); su valor por omisión es 15 segundos.
- **Datos personales en los registros**: el correo electrónico de una persona es un dato personal. «Registros del servidor» son la salida y los archivos de log de los contenedores; la **bitácora** es la tabla de auditoría que solo consulta el Administrador.

## Requisitos funcionales

### A. Restablecimiento por el Administrador (RF-03, vía a; CU-05 FA-02)

- RF-03.13 (detalla RF-03, RF-02): CUANDO el Administrador restablece la contraseña de un usuario, EL SISTEMA genera una contraseña temporal aleatoria de 8 caracteres alfanuméricos con un generador criptográfico, guarda solo su hash, deja vacío el último acceso (para forzar el cambio al siguiente inicio de sesión), la envía por correo al usuario y responde «Contraseña reseteada exitosamente». EL SISTEMA tiene **una sola** lógica de restablecimiento por el Administrador: la del reseteo de gestión de usuarios (el restablecimiento heredado se retira, RNF-07.1).
  - *Cómo se comprueba*: prueba de integración con el correo simulado: la contraseña guardada es un hash (no el texto de la temporal), el último acceso queda vacío, el correo simulado recibe un mensaje al correo del usuario cuyo contenido incluye la temporal, el mensaje de la respuesta es exactamente «Contraseña reseteada exitosamente», un inicio de sesión con la temporal funciona y la respuesta indica que debe cambiar la contraseña; un usuario inexistente responde 404; un Usuario Gubernamental recibe 403 y sin token 401. La «única lógica» la comprueba el revisor en `/sdd-validate` (exención, como RA-02.8): no queda ningún segundo camino que cambie la contraseña de otro usuario.

- RF-03.14 (detalla RF-03, FS-03): SI el envío del correo falla (RF-03.16, RF-03.17), ENTONCES EL SISTEMA **no modifica** la contraseña ni el último acceso del usuario, deja el intento en la bitácora (RF-21.4) y responde con un error que permite al Administrador reintentar, cuyo texto completo es «No se pudo enviar el correo a <correo>. La contraseña no fue modificada. Verifique el servicio de correo e inténtelo de nuevo.» (con el correo del usuario). El código HTTP es de la familia 5xx de servicio externo (**502 o 503**, lo fija el plan; no 500, que es de errores inesperados) y **nunca 401 ni 403**: la interfaz interpreta un 401 como sesión expirada y cerraría la sesión del Administrador. El usuario conserva su contraseña anterior.
  - *Cómo se comprueba*: prueba de regresión (se escribe primero, falla hoy) con el correo simulado configurado para fallar: la contraseña guardada y el último acceso son los mismos de antes, el código está en {502, 503}, el texto de la respuesta es el indicado, y el reintento con el correo funcionando cambia la contraseña. Lo mismo con el simulado que nunca responde (RF-03.16) y con la cuenta de correo sin configurar. Un inicio de sesión con la contraseña anterior sigue funcionando.

- RF-03.15 (detalla RF-03, FS-03): EN la pantalla de gestión de usuarios, EL SISTEMA (a) explica en el cuadro de confirmación que se enviará una **contraseña temporal** al correo del usuario; (b) en éxito, muestra el texto que devuelve la API («Contraseña reseteada exitosamente»); (c) en fallo, mantiene el cuadro abierto para reintentar y muestra, **tal cual lo recibe de la API**, el texto de RF-03.14 (con el correo del usuario), sin cerrar la sesión.
  - *Cómo se comprueba*: el texto completo y el código ya se prueban con pytest (RF-03.13, RF-03.14); lo que queda es solo lo visual: verificación manual de punta a punta con Mailtrap (éxito y fallo provocado) en escritorio y en pantalla pequeña, y con el Usuario Gubernamental sin acceso a la pantalla. Exención temporal aprobada (E2); la prueba de extremo a extremo llega con la spec 005.

### B. Crear cuenta (RF-02, CU-05 FE-02)

- RF-02.1 (detalla RF-02, HU-25): SI el correo con la contraseña temporal de una cuenta nueva falla, ENTONCES EL SISTEMA crea la cuenta igualmente (con su contraseña temporal guardada con hash y el último acceso vacío), la respuesta indica que la notificación **no se entregó** y lleva el texto completo de la advertencia «Usuario creado, pero no se pudo enviar el correo con la contraseña temporal a <correo>. Use "Resetear Contraseña" cuando el servicio de correo esté disponible.», y el resultado queda en la bitácora (RF-21.4). Si el envío sale, la respuesta indica que se entregó y lleva «Usuario creado exitosamente». La respuesta nunca contiene la contraseña temporal. No hay envío automático nuevo ni botón «Reenviar» (no está en el ERS).
  - *Cómo se comprueba*: prueba de regresión (se escribe primero, falla hoy) con el correo simulado en fallo y con la cuenta de correo sin configurar: la cuenta existe, está Activa, su contraseña está guardada con hash, su último acceso está vacío, la respuesta trae el indicador de no entregada y el texto indicado, y el valor de la contraseña temporal no aparece en la respuesta. Con el correo funcionando: indicador de entregada, texto de éxito y un mensaje en el correo simulado que contiene la temporal.

- RF-02.2 (detalla RF-02): EN la pantalla de gestión de usuarios, CUANDO la API indica que la cuenta se creó pero la notificación no se entregó, EL SISTEMA muestra la advertencia con el texto que devuelve la API (distinta del aviso de éxito); CUANDO sí se entregó, muestra el texto de éxito de la API.
  - *Cómo se comprueba*: el texto y el indicador se prueban con pytest (RF-02.1); la advertencia en pantalla, con verificación manual con Mailtrap (éxito y fallo provocado). Exención temporal aprobada (E2); la prueba de extremo a extremo llega con la spec 005.

### C. Envío de correo (transversal)

- RF-03.16 `[NUEVO]` (detalla RF-03, FS-03): EL SISTEMA limita a **15 segundos** la duración **total** del envío de un correo (de principio a fin, no cada paso de la conexión); pasado ese tiempo el envío se da por fallido. El valor se cambia con la variable del tiempo máximo del envío; si su valor no es un número mayor que cero, se usa 15 y se deja una advertencia en el registro del servidor. El sistema siempre indica el límite de forma explícita al enviar: no depende del valor por omisión de la librería de envío.
  - *Cómo se comprueba*: pruebas unitarias con el reloj controlable (RA-02.9) y el correo simulado (RA-02.10): (a) el simulado registra el tiempo máximo con que el sistema lo llama: 15 por omisión, el configurado si la variable cambia, y 15 con advertencia si el valor es inválido; (b) con un simulado que nunca responde, a los 14,9 s del reloj el envío sigue pendiente y termina como fallido a los 15 s y, a más tardar, a los 16 s (margen); (c) con un simulado cuyas cuatro operaciones tardan 5 s cada una (20 s en total) el envío también termina como fallido a los 15 s (el límite es total); (d) ninguna de estas pruebas tarda más de 5 s reales.

- RF-03.17 (detalla RF-03, FS-03): SI el envío de un correo no se completa por cualquier causa (error del servidor, rechazo, autenticación, conexión rechazada, sin cuenta de correo configurada, puerto inválido, tiempo agotado), ENTONCES EL SISTEMA lo trata como **envío fallido** y se lo informa a quien corresponde: al Administrador en la creación de cuentas y en el restablecimiento (RF-02.1, RF-03.14) y, en la recuperación pública, solo a la bitácora (decisión D8, spec 003b). El detalle técnico del servidor de correo no se muestra al usuario ni se guarda en la bitácora; en los registros del servidor consta la causa clasificada (por ejemplo, «tiempo agotado» o «autenticación»), sin credenciales ni el texto crudo del error si puede contenerlas.
  - *Cómo se comprueba*: pruebas unitarias del servicio de correo y de los servicios que lo usan, con el simulado: cada causa produce «envío fallido» y llega a quien llama (hoy se traga); con la cuenta de correo sin configurar y con un puerto inválido, también. Ninguna respuesta al navegador contiene el texto del error del servidor de correo ni credenciales (también las rutas de correo, RNF-07.2).

- RF-03.18 `[NUEVO]` (detalla RF-02, RF-03; RT-07): EL SISTEMA envía los correos con codificación UTF-8, de modo que el asunto, el nombre del destinatario (con tildes y «ñ») y el cuerpo se leen correctamente en el mensaje **tal como viaja** hacia el servidor de correo.
  - *Cómo se comprueba*: prueba unitaria con el simulado, que conserva el mensaje ya serializado (los bytes que se enviarían por la red, RA-02.10): un lector de correos independiente lo decodifica y encuentra un nombre inventado con tilde y «ñ» (por ejemplo «PRUEBA Peña Núñez») en el cuerpo y un asunto con tilde («Contraseña»), sin caracteres dañados ni secuencias de escape sin resolver, para el correo de creación y para el de restablecimiento. Verificación manual en Mailtrap.

- RF-03.19 `[NUEVO]` (RNF-06; ERS 2.5): EL ARCHIVO DE EJEMPLO DE CONFIGURACIÓN del backend documenta cómo apuntar el correo a un servidor propio (las **variables del correo**) y la variable del tiempo máximo del envío, **sin credenciales ni valores reales** (solo marcadores). (La clave de firma de la recuperación va en la 003b, RNF-07.4.)
  - *Cómo se comprueba*: verificación del revisor en `/sdd-validate` (exención, como RA-02.8): el archivo de ejemplo contiene esas variables y ningún valor real; y una prueba unitaria que lo lee desde la ubicación en que está dentro del contenedor y comprueba que define las variables (se omite, con su motivo, si el archivo no está en la imagen).

### D. Funciones que exigen Administrador (RNF-07)

- RNF-07.1 (detalla RNF-07, RF-02; decisión D13): EL restablecimiento heredado del módulo de autenticación **deja de existir**: `POST /auth/restablecer-contrasenna` responde 404 (como una ruta inexistente) con cualquier credencial o sin ella. El restablecimiento por el Administrador queda solo en el reseteo de gestión de usuarios (RF-03.13).
  - *Cómo se comprueba*: prueba de regresión (se escribe primero, falla hoy) que llama a la ruta sin token, con token de Usuario Gubernamental y con token de Administrador y espera 404 en las tres, y comprueba que ninguna contraseña cambió; más la comprobación del revisor de que el frontend no la usa (hoy no la usa).

- RNF-07.2 (detalla RNF-07, RF-02): EL envío de correo de prueba y la consulta de la configuración de correo (las rutas de correo) exigen un token de Administrador: sin token responden 401, con token de Usuario Gubernamental 403 y con token de Administrador funcionan. La configuración nunca devuelve la contraseña de la cuenta de correo, y ninguna ruta de correo devuelve al navegador el texto de una excepción (`detail` genérico en un error inesperado).
  - *Cómo se comprueba*: prueba de regresión (se escribe primero, falla hoy) con las tres credenciales para cada ruta; con Administrador, la respuesta de configuración no contiene el valor de la contraseña de correo (que la suite genera y conoce); con el correo simulado en fallo, la respuesta no contiene el texto del error del servidor.

### E. Bitácora (RF-21)

- RF-21.4 (detalla RF-21, RF-02, RF-03): CUANDO el Administrador crea una cuenta o restablece una contraseña, EL SISTEMA registra en la bitácora quién lo hizo, sobre qué cuenta (su cédula) y el resultado de la notificación (`entregada` o `no entregada`), incluido el intento fallido del restablecimiento (RF-03.14), y nunca guarda la contraseña temporal. SI el registro en la bitácora falla, ENTONCES la acción continúa y responde con su resultado normal (RF-02.1 o RF-03.13/RF-03.14).
  - *Cómo se comprueba*: pruebas de integración con el correo simulado en éxito y en fallo, para la creación y para el reseteo: un registro con el administrador, la cuenta afectada y el resultado; el valor de la contraseña temporal no aparece en el texto ni en la información adicional; y, forzando el fallo del registro, la acción se completa igual.

- RF-21.6 (detalla RF-21, RF-22; HU-22, CU-15): EL Administrador ve en el detalle de cada registro de creación de cuenta y de reseteo de contraseña, en el Historial de Actividades, el resultado de la notificación («Notificación por correo: Entregada» o «No entregada»). Hoy el detalle de esos registros no lo muestra porque el dato no existe.
  - *Cómo se comprueba*: la consulta de la bitácora devuelve el dato en esos registros (prueba de integración, junto con RF-21.4); verificación manual del detalle en la interfaz. Exención temporal aprobada para la parte visual (E2); la prueba de extremo a extremo llega con la spec 005.

## Requisitos no funcionales

- RNF-08.1 `[NUEVO]` (detalla RNF-08, principio 5): LAS contraseñas (temporales o nuevas) y los códigos de verificación **nunca** aparecen en los registros del servidor, en la bitácora, en una respuesta de error ni en la salida de las pruebas; solo viajan en el correo al destinatario (la contraseña temporal solo existe en ese correo y, con hash, en la base de datos).
  - *Cómo se comprueba*: el simulado de correo no basta por sí solo, porque solo oculta lo que él mismo registra. Cada flujo completo (creación, reseteo con éxito y con fallo, y, en la 003b, la recuperación) lee de la prueba el valor real de la contraseña o del código generado (el simulado lo conserva para la prueba sin mostrarlo en los informes, RA-02.10) y lo **busca** en: la salida estándar y de error capturada, los registros del sistema (logging), todas las filas de bitácora creadas por el flujo (texto e información adicional) y los cuerpos de las respuestas HTTP (menos el correo). Encontrarlo falla la prueba. Además, búsqueda del valor en los registros de los contenedores tras la verificación manual.

- RNF-08.2 `[NUEVO]` (detalla RNF-08, principio 5; decisión del planner, ver «Dudas abiertas»; alcance acotado por decisión de Andrés el 08/10/2026): EN los flujos de cuentas (la creación de una cuenta y el restablecimiento por el Administrador) y en la bitácora, EL SISTEMA no escribe el correo electrónico de una persona en claro en los registros del servidor que esos flujos producen, incluido el registro que la bitácora escribe en el servidor (se enmascara en un solo punto): lo enmascara (la primera letra del usuario y el dominio, por ejemplo `a***@dominio.cr`) o lo omite. En la tabla de la bitácora (solo accesible al Administrador) sí consta el correo cuando es necesario para auditar (RF-21.1 de la 003b). **Fuera de este requisito** (pasa a la futura spec de autenticación): otros registros de errores de la autenticación y de la auditoría pueden incluir datos de la excepción; se revisarán con el módulo de autenticación.
  - *Cómo se comprueba*: pruebas de integración de la creación y del reseteo por el Administrador (éxito y fallo) y de la bitácora: con los registros del sistema capturados, ninguno contiene el correo completo de la cuenta de prueba (hoy el servicio de usuarios lo escribe en el registro al enviar el correo). La recuperación pública de la 003b no entra en este requisito: su alcance respecto de RNF-08.2 se acotará en la spec 003b.

### Infraestructura de pruebas que esta spec y la 003b necesitan (no es producto)

- RA-02.9 `[NUEVO]` (detalla RA-02, principio 4; decisión D14): EL SISTEMA obtiene la hora y mide plazos (el tiempo máximo del envío, las caducidades de 15 y 10 minutos, la ventana de la hora y los 60 segundos de la 003b) a través de un **reloj controlable**: en producción es el reloj real y en las pruebas lo adelanta la prueba a voluntad. No se agrega ninguna dependencia ni librería de manejo del tiempo, y ninguna prueba espera tiempo real para comprobar un plazo.
  - *Cómo se comprueba*: (a) prueba unitaria del propio reloj: adelantarlo cambia lo que ven los plazos; el reloj real avanza con el tiempo real; (b) el informe de duraciones de la corrida no muestra ninguna prueba de plazos de la 003a o de la 003b con más de 5 s reales (lo comprueba el revisor en `/sdd-validate`); (c) el revisor comprueba que `requirements.txt` no ganó ninguna entrada (principio 1).

- RA-02.10 `[NUEVO]` (detalla RA-02.6 de la spec 002, `.claude/rules/testing.md`): EL correo simulado de la suite (a) registra el tiempo máximo con que el sistema lo llama; (b) conserva cada mensaje **ya serializado** (los bytes que se enviarían) y permite decodificarlo con un lector de correos independiente; (c) permite a la prueba leer el contenido real del mensaje (por ejemplo, la contraseña generada) sin que aparezca en los informes ni en su representación, y sigue ocultando lo que la prueba le indique; (d) puede simular un servidor que nunca responde y uno lento por operación, medidos con el reloj controlable (RA-02.9).
  - *Cómo se comprueba*: pruebas humo unitarias del simulado (una por capacidad), dentro de las pruebas de RF-03.16, RF-03.18 y RNF-08.1.

## Casos límite
- Usuario inexistente al restablecer: 404, sin envío (RF-03.13).
- Correo sin configurar o puerto inválido: envío fallido; en la creación, la cuenta se crea con la advertencia; en el reseteo, la contraseña no cambia (RF-03.14, RF-03.17).
- El servidor de correo no responde: el envío se da por fallido a los 15 s, antes de que el navegador (30 s) se rinda. Puede ocurrir que el mensaje sí llegue al buzón aunque se haya dado por fallido (por ejemplo, el servidor lo aceptó justo al vencer el tiempo): en el reseteo, el usuario tendría una contraseña temporal que no sirve (no se guardó); el Administrador reintenta y la contraseña de ese reintento es la única válida.
- El correo sale pero el guardado de la contraseña falla (reseteo): el Administrador recibe un error, el usuario conserva su contraseña anterior y el intento queda en la bitácora; el plan debe ordenar los pasos para que sea el caso menos probable. El usuario puede haber recibido un correo con una contraseña que no sirve.
- Dos reseteos seguidos de la misma cuenta: vale la contraseña del último correo entregado.
- Variable del tiempo máximo del envío vacía, no numérica o ≤ 0: se usa 15 y se avisa en el registro del servidor (RF-03.16).
- Un Usuario Gubernamental intenta usar el reseteo, la creación o las rutas de correo: 403; sin token: 401 (RNF-07.2; el reseteo y la creación ya exigen Administrador).
- La bitácora falla: la acción continúa (RF-21.4).
- Dos pestañas del Administrador reseteando la misma cuenta a la vez: cada una recibe su propio resultado; vale el último correo entregado.
- Cuenta Inactiva a la que el Administrador restablece la contraseña: se permite (el reseteo no cambia el estado; la cuenta sigue sin poder iniciar sesión).

## Fuera de alcance
Además de lo común a las dos specs (ver «Fuera de alcance» del paraguas):
- Un botón «Reenviar» el correo de una cuenta nueva (no está en el ERS).
- Registrar en la bitácora el uso del correo de prueba de las rutas de correo (es un diagnóstico del Administrador; se puede abrir más adelante).
- Cambiar el pie de los correos con vocabulario heredado y los proveedores de correo del archivo de ejemplo que el sistema no soporta (spec de autenticación o de limpieza).
- Una cuenta de correo institucional definitiva y el envío real a usuarios reales (dependencia organizacional, ERS 2.5).
- Tablas o migraciones nuevas, cambios al `docker-compose.yml`, a los prompts o a los modelos de IA.
- Pruebas de extremo a extremo de la interfaz: llegan con la spec 005; mientras tanto, E2.

## Criterios de finalización
- Cada requisito tiene al menos una prueba automatizada que pasa (o su exención justificada en el plan) y su verificación manual. Las exenciones son: (1) RF-03.19 y la «única lógica» de RF-03.13 y RA-02.9(b)(c), en lo que revisa el revisor; (2) la parte visual de RF-03.15, RF-02.2 y RF-21.6, solo hasta que exista el extremo a extremo (E2); (3) la entrega real al buzón del usuario, que no se puede automatizar.
- Las pruebas de regresión de **RNF-07.1, RNF-07.2, RF-03.14 y RF-02.1** se escribieron primero y se vio que fallaban con el código anterior.
- La suite completa (`docker compose exec backend pytest`) pasa, también con `--orden-inverso`, y las pruebas dejan cero residuos `PRUEBA`.
- Verificación manual de punta a punta con Mailtrap real, datos inventados (un nombre con tilde y «ñ») y los dos roles: crear una cuenta con éxito y con fallo del envío; restablecer con éxito y con fallo (Andrés edita temporalmente `backend/.env` con un puerto cerrado o un host sin respuesta, y lo restaura; el planner no toca `.env`); el tiempo máximo (host sin respuesta: el error llega en unos 15 s); la bitácora con el resultado de cada caso y su detalle en el Historial; el Usuario Gubernamental sin acceso a estas funciones; contraseñas fuera de los registros. Antes, revisar la cuota mensual de Mailtrap. Al terminar, limpiar lo creado a mano: desactivar desde la interfaz los usuarios de prueba (no hay borrado físico, RN-01) y confirmar que `.env` quedó restaurado.
- `docker compose ps` sin reinicios y `docker compose logs backend celery-worker` sin contraseñas ni correos completos de las cuentas de la verificación (los flujos de cuentas y la bitácora; RNF-08.2 acotado); `npm run build` sin errores.
- La documentación afectada por esta spec está actualizada (ver «Documentos a actualizar al cerrar» del paraguas, filas marcadas 003a).

## Tareas estimadas y ⚠️ de «Pregunta antes»
Estimación para el plan (el detalle va en `tasks.md`, que se genera después; **resultado: 10 tareas**, porque se partieron el reloj y el correo simulado y la verificación y la documentación): **8 tareas** estimadas (máximo 10), de 20 a 30 minutos cada una, en este orden de dependencia:
1. ⚠️ Reloj controlable y correo simulado ampliado (RA-02.9, RA-02.10): toca los archivos de soporte de las pruebas (el simulado de correo y el `conftest`), que son de la spec 002.
2. Retiro de la ruta heredada y protección de las rutas de correo, con su regresión primero (RNF-07.1, RNF-07.2).
3. ⚠️ Servicio de correo: tiempo máximo, causas de fallo, UTF-8 (RF-03.16, RF-03.17, RF-03.18); agrega una variable de configuración nueva.
4. Restablecimiento por el Administrador (RF-03.13, RF-03.14, RF-21.4 del reseteo).
5. Creación de cuenta (RF-02.1, RF-21.4 de la creación).
6. Interfaz de gestión de usuarios e Historial (RF-03.15, RF-02.2, RF-21.6).
7. ⚠️ Archivo de ejemplo de configuración, contraseñas y correos fuera de los registros (RF-03.19, RNF-08.1, RNF-08.2): el archivo de ejemplo está versionado.
8. Verificación manual y actualización de la documentación de planificación afectada.

⚠️ que aplican a toda la spec: **crear archivos nuevos** (la carpeta de esta spec y los archivos de prueba que liste el plan, que quedan aprobados con el plan); **modificar archivos de soporte de las pruebas** (el simulado de correo y el `conftest`); **variable de configuración nueva** (tiempo máximo del envío, también en el archivo de ejemplo); **ninguna librería ni dependencia nueva** (en particular ninguna de manejo del tiempo: RA-02.9); **sin migración** y **sin cambios al `docker-compose.yml`**. Hacer commit o push: lo decide Andrés; las specs se mantuvieron fuera del repositorio hasta corregir lo que describían (D15).

## Dudas abiertas
Ninguna que impida pasar al plan. Decisión del planner a confirmar por Andrés al aprobar la spec (no cambia el QUÉ de nada más): **RNF-08.2** enmascara los correos en los registros del servidor de los flujos de cuentas y de la bitácora, y los conserva en la tabla de la bitácora (Andrés lo confirmó y acotó su alcance el 08/10/2026; ver el Historial).

## Riesgos para el plan (no cambian el QUÉ)
- **Alcance del tiempo máximo**: según la documentación de la librería de envío, su tiempo de espera se aplica a cada operación de la conexión, no al envío completo; el plan debe garantizar los 15 s totales (por ejemplo, un límite global alrededor del envío) y comprobar la versión instalada (no está fijada, `>=3.0.0`).
- **El servicio de correo traga hoy los errores** y devuelve «falso»; los llamadores lo ignoran: el plan decide cómo llega el fallo a quien llama sin cambiar el contrato de los demás usos.
- **Orden del restablecimiento**: cambiar la contraseña y enviar el correo de forma que un fallo del envío no deje la contraseña cambiada (RF-03.14) y un fallo del guardado no deje un correo con una contraseña inútil (por ejemplo, guardar sin confirmar, enviar y confirmar después).
- **El modelo de respuesta de la creación de cuenta cambia** (RF-02.1 agrega el indicador y el texto): el plan comprueba que la lista de usuarios y la edición no se ven afectadas.
- **Reloj controlable**: el plan decide dónde se inyecta sin crear estado global compartido entre pruebas, con el reloj real por omisión.
- **Código muerto**: al retirar el restablecimiento heredado, quitar también lo que solo él usa (esquemas y método del servicio) sin tocar el resto de la autenticación.
- **Mensajes del servidor de correo**: el texto de una falla puede traer el nombre del servidor o el usuario; no se devuelve al navegador ni se guarda en la bitácora (RF-03.17, RNF-08.1). Hoy una de las rutas de correo devuelve el texto de la excepción.
- **Etiqueta de la interfaz**: el texto de RF-02.1 cita «Resetear Contraseña», tal como se llama la opción en el menú de la tabla de usuarios; si cambia la etiqueta, cambia el texto.
- Spec retroactiva: mientras la futura spec de autenticación no exista, las pruebas de esta spec cubren solo el comportamiento de estos requisitos; las que dependan de código heredado con errores se marcan como fallo esperado con su referencia, nunca se debilitan.
