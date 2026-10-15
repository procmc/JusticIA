# Spec 004a — Correcciones urgentes de seguridad en los archivos de documentos
Estado: implementada (14/10/2026; aprobada el 12/10/2026)

> No se publica hasta que las correcciones estén hechas y validadas (repo público); lo abierto se describe solo en términos generales, el detalle queda en las pruebas. La carpeta `respaldo/` tampoco se publica: se borra al cerrar (T7).
> Cumplido el 14/10/2026 (validación APROBADO, `respaldo/` borrada): publicable.

Historial:
- 12/10/2026 — creada a partir de tres fallos confirmados por el reviewer en la 004. Andrés: correcciones de error aparte, cada una con regresión que falla primero, antes de la 004; incluye el defecto de la ruta relativa al guardar (hallazgo T6 de la 002).
- 12/10/2026 — condensada para ahorrar tokens; versión completa en `respaldo/`.
- 12/10/2026 — revisión del reviewer y decisiones de Andrés: dudas 1-6, 8 y 9 → A; duda 7 → B (solo el motivo); nuevo RNF-07.24 (datos personales, Ley 8968); no Procesado → 404 uniforme; notebook sin distinguir mayúsculas y contra la base; límite de 255 bytes; reserva `profiles`; la interfaz que no muestra el rechazo se documenta y se arregla en la 004.

## Objetivo
Cerrar tres fallos en la entrega y el guardado de originales, **sin romper** la descarga de la fuente citada (RF-12), los temas similares (RF-20), la previsualización y el borrado en NotebookServIA (RF-18, RF-19), la carga ni los avatares (RF-04):
1. **Descarga sin confinar (crítico)**: una descarga por ruta no comprueba que esté dentro de la carpeta de documentos ni la pertenencia del notebook.
2. **Guardado sin confinar (crítico, a confirmar con su prueba)**: tema y nombre forman la ruta de escritura sin confinar; además, la ruta relativa falla si la carpeta de documentos no está en su ubicación habitual (la suite) y deja un archivo sin registro.
3. **Carpeta de documentos pública (alto)**: se publica como estática sin token (para servir avatares).

## Trazabilidad
- ERS V1.5: RNF-07, RF-04, RF-05, RF-06, RF-12, RF-17, RF-18, RF-19, RF-20, RF-21, RN-01, RNF-10, RT-07, RA-02. Ley 8968 (protección de datos personales): RNF-07.24 `[NUEVO]` en el ERS.
- HU: 01, 02, 04, 05, 06, 12, 17..21, 24. CU: 06, 07, 09, 11..15.
- «Estado actual» que cierra: ninguno. Al cerrar se agrega al de RNF-07 que los avatares siguen sin sesión (D1).
- Numeración: bloque **.20+** para no chocar con la 004 (D8).

## Usuarios
Usuario Gubernamental (carga, descarga, temas similares, notebook); Administrador (no usa estas funciones, RN-03; ve los rechazos en la bitácora, CU-15); sin sesión (no obtiene ningún documento).

## Definiciones
- **Carpeta de documentos**: carpeta configurada con una subcarpeta por tema (notebook: su clave interna); en la suite, temporal (RA-02.5). **Carpeta de avatares**: en producción, la subcarpeta `profiles` de la carpeta de documentos; en la suite, otra carpeta temporal.
- **Ruta de documento**: `uploads/<tema>/<nombre>`, como se guarda hoy en la base y en Qdrant.
- **Tema de notebook**: tema con la forma de clave interna (`NB-` y un número) **sin distinguir mayúsculas** (`nb-5` también lo es, porque el disco y la base no distinguen); su dueño se consulta en la base por el número.
- **Documento descargable**: registrado, asociado al tema y con el nombre de su ruta, Procesado, con archivo dentro de la carpeta del tema y, si el tema es de notebook, de un notebook existente del usuario que lo pide.
- **Confinado**: su ubicación real (resueltos `..`, separadores y enlaces simbólicos) queda dentro de la carpeta de su tema.
- **Nombre seguro** (tema o archivo): usable como un solo nombre: no vacío ni solo espacios o puntos; sin `/`, `\`, `..` como componente, caracteres de control, NUL ni `:`; sin espacio ni punto final; no reservado de Windows (CON, PRN, AUX, NUL, COM1-9, LPT1-9, con o sin extensión, sin distinguir mayúsculas); tema ≤ 60 caracteres; archivo ≤ **255 bytes** en UTF-8 (tildes y ñ ocupan 2), **incluido** el sufijo de nombre repetido; el tema no puede ser `profiles` (sin distinguir mayúsculas). Tildes, ñ, espacios intermedios, paréntesis y guiones valen.
- **Respuesta de no encontrado uniforme**: 404 «Archivo no encontrado», sin contenido, rutas del servidor ni texto de excepción; igual si no existe, está fuera, no es documento, no está Procesado o es de otro notebook.

## Requisitos funcionales

### A. Descargar y abrir (fallo 1)
- **RNF-07.20** (RNF-07, RF-12): CUANDO un usuario pide descargar, por ruta o por tema y nombre, EL SISTEMA entrega el archivo **solo si es un documento descargable**; SI no (absoluta, con `..`, `\`, codificada, enlace que sale, carpeta, no documento, no Procesado, avatares o fuera), ENTONCES respuesta de no encontrado uniforme. Se comprueba la ruta **final**, tras toda decodificación.
  - *Comprobación*: integración: testigo `PRUEBA_testigo` fuera de la carpeta de documentos pero dentro de la temporal, pedido con A1-A9 y A11: todas 404 sin su contenido. Unitaria con la tabla completa de casos límite. Nunca archivos reales del servidor.
- **RNF-07.21** (RNF-07, RF-18, RF-19): EL SISTEMA aplica el mismo confinamiento a **toda** operación que abre o borra un archivo por tema y nombre (descarga por tema y nombre, previsualización y borrado en NotebookServIA). SI no está confinado, ENTONCES no lo entrega ni lo borra y responde 404 uniforme.
  - *Comprobación*: unitaria de la función común (la usan las tres vías: basta una): con tema o nombre no seguros, o carpeta de tema enlazada fuera, no devuelve ubicación ni toca el disco. Camino feliz: pruebas de RF-18 y RF-19 de la 004.
- **RF-18.20** (RF-17, RF-18): SI la ruta es de un documento de un notebook **ajeno** o inexistente, con cualquier combinación de mayúsculas en la clave, ENTONCES 404 uniforme, sin revelar que existe, por **cualquier** vía de descarga.
  - *Comprobación*: unitaria (con base simulada): el usuario ajeno recibe «documento ajeno» con `NB-<id>` y `nb-<id>`; el dueño recibe la ubicación. Integración: dos usuarios `PRUEBA`; el segundo pide el documento Procesado del notebook del primero (ambas grafías) → 404 sin contenido y bitácora con «documento ajeno»; el primero lo recibe completo (control: el 404 no se debe a la ubicación).
- **RF-12.20** (RF-12, RF-20): CUANDO descarga la fuente citada en el chat o un documento de un tema similar, EL SISTEMA lo entrega íntegro con su nombre, incluidos espacios, tildes, ñ, paréntesis y el sufijo de nombre repetido.
  - *Comprobación*: documento Procesado inventado en la carpeta temporal, descargado con la ruta como la cita el chat y como la da temas similares, byte a byte; repetido con tildes, ñ, espacios y paréntesis.

### B. Guardar archivos (fallo 2 y ruta relativa)
- **RF-06.20** (RF-06, RF-05): CUANDO carga archivos, EL SISTEMA comprueba que el tema sea nombre seguro **antes de escribir nada**; SI no, ENTONCES rechaza la carga completa con **400 «El tema indicado no es válido»**, sin escribir ni encolar.
  - *Comprobación*: carga por la API con cada tema B1-B7: 400 con el mensaje, carpeta temporal **exactamente igual**, sin tareas encoladas (si otra vía ya lo impide, caracterización).
- **RF-05.20** (RF-05): CUANDO un archivo de la carga tiene un nombre no seguro, EL SISTEMA rechaza **ese archivo** con el aviso genérico «Nombre de archivo no válido», identificado por su posición en la carga y **sin repetir su nombre**, no lo escribe y sigue con los demás.
  - *Comprobación*: dos archivos, uno con nombre B1-B6 y otro válido: el inválido figura rechazado con el aviso y sin su nombre; el válido se guarda en su tema y se encola; nada fuera de la carpeta del tema.
- **RF-05.21** (RF-05, RF-06; hallazgo T6 de la 002): CUANDO guarda un archivo aceptado, EL SISTEMA lo escribe confinado en su tema y devuelve `uploads/<tema>/<nombre>` **sea cual sea la ubicación** de la carpeta de documentos. SI la escritura falla, ENTONCES ese archivo figura rechazado con «No se pudo guardar el archivo», sin archivo a medias ni sin registro, y sin rutas.
  - *Comprobación*: (a) integración: carga válida en la carpeta temporal → id de tarea, archivo en `<temporal>/uploads/<tema>/`, ruta `uploads/<tema>/<nombre>`; (b) unitaria: escritura simulada que falla a mitad → ningún archivo en la carpeta del tema y resultado «rechazado».

### C. Carpeta pública (fallo 3)
- **RNF-07.22** (RNF-07): EL SISTEMA **no publica** la carpeta de documentos sin sesión; los documentos solo salen por descarga y previsualización con token y rol. Única excepción: la carpeta de avatares (D1).
  - *Comprobación*: (a) unitaria: ninguna publicación estática cuya carpeta sea o contenga la de documentos; (b) integración: sin token, la dirección pública de un documento inventado da 404 o 401 sin contenido.
- **RF-04.20** (RF-04): EL SISTEMA sigue entregando el avatar en la **misma dirección** de hoy (la interfaz no cambia), con `GET` y `HEAD`. Solo entrega archivos de la carpeta de avatares con la forma de nombre que les da el sistema; lo demás, 404.
  - *Comprobación*: avatar inventado de un usuario `PRUEBA` en su dirección, contenido idéntico, con `GET`, `HEAD` y `?v=…`; nombre fuera de forma, con `..` o separadores → 404. Aspecto visual: manual (E1).

### D. Bitácora, mensajes y datos personales
- **RF-21.20** (RF-21): CUANDO rechaza una descarga (RNF-07.20, RNF-07.21, RF-18.20) o un archivo o tema (RF-05.20, RF-06.20), EL SISTEMA registra un intento fallido del usuario **solo con el motivo clasificado** («ruta no permitida», «documento ajeno», «documento no disponible», «nombre de archivo no válido», «tema no válido») como error de acceso o de validación, no como error interno (D7-B). SI el registro falla, ENTONCES la respuesta es la misma.
  - *Comprobación*: tras cada tipo de rechazo hay su fila con su motivo y su clasificación; con la bitácora simulada para fallar, respuesta idéntica.
- **RNF-07.23** (RNF-07, convención de errores): EN descarga y carga, EL SISTEMA no devuelve rutas del servidor ni texto de excepciones; un error inesperado responde **500 «Error interno del servidor»** y el detalle va solo al registro del servidor. (La previsualización ya no devuelve texto de excepción; su confinamiento lo cubre RNF-07.21.)
  - *Comprobación*: error simulado en cada función, con una ruta inventada en el mensaje → 500 con ese mensaje exacto, sin la ruta.
- **RNF-07.24** (RNF-07, RF-21; Ley 8968) `[NUEVO]`: SI rechaza una descarga, un archivo o un tema, ENTONCES ni la respuesta, ni la bitácora, ni el registro del servidor contienen el nombre del archivo, el tema ni la ruta o texto pedido (pueden contener nombres de personas): la persona ve el aviso genérico y la bitácora guarda solo el motivo. Todo texto que sí se registra (descarga o carga exitosa) se guarda sin caracteres de control ni NUL.
  - *Comprobación*: nombre y ruta con un nombre de persona inventado (`PRUEBA Juana Inventada Solís`) y un carácter no válido, en carga y en descarga: no aparece en la respuesta, en ninguna fila de la bitácora ni en el registro capturado; una ruta con `%00` da 404 uniforme y nada registrado contiene NUL ni caracteres de control.

## Requisitos no funcionales
- RNF-07.20 a RNF-07.24 (arriba).
- Sin dependencias, servicios, cambios al `docker-compose.yml`, migraciones ni cambios en datos guardados (principio 1; RN-01).
- Solo carpeta temporal y datos `PRUEBA`; nunca archivos reales ni la carpeta de desarrollo (RA-02.5, RA-02.7).

## Casos límite
Cada uno es una fila de la tabla unitaria (y de integración si se indica); datos inventados, sin formas concretas de aprovecharlos.

**A. Descarga** (RNF-07.20, RNF-07.21, RF-18.20, RNF-07.24)
- A1. `..` al inicio, en medio o al final, también tras el prefijo.
- A2. Absoluta (Linux, Windows, recurso de red) o que empieza por separador.
- A3. Codificada una o dos veces, mayúsculas/minúsculas, o mezclada.
- A4. `\` en lugar de `/`, solo o mezclado.
- A5. Enlace simbólico en un tema que apunta fuera.
- A6. Ruta a una carpeta (la de documentos o de un tema).
- A7. Archivo no registrado, o documento registrado en otro tema.
- A8. Archivo de la carpeta de avatares.
- A9. Vacía, solo espacios, caracteres de control o NUL (también `%00`).
- A10. Documento de notebook ajeno o que ya no existe, con la clave en cualquier grafía (`NB-5`, `nb-5`, `Nb-5`).
- A11. Registrado pero no Procesado: 404 uniforme, motivo «documento no disponible».
- A12. Nombres legítimos (espacios, tildes, ñ, paréntesis, sufijo `_1`): **se entregan** (RF-12.20).
- A13. Ruta con un nombre de persona inventado: rechazo sin eco (RNF-07.24).

**B. Carga** (RF-05.20, RF-06.20, RF-05.21, RNF-07.24)
- B1. Vacío, solo espacios, `.` o `..`.
- B2. Con `/`, `\` o `..` como componente.
- B3. Absoluto o con `:`.
- B4. Caracteres de control o NUL.
- B5. Reservado de Windows (con o sin extensión), o termina en espacio o punto.
- B6. Más largo de lo permitido: tema > 60 caracteres; nombre > 255 bytes (p. ej. 200 caracteres con tildes o ñ), o que llegaría a > 255 bytes con el sufijo de nombre repetido.
- B7. Tema `profiles` en cualquier grafía: no válido.
- B8. Nombre ya existente: sufijo de siempre, confinado.
- B9. Carpeta de documentos fuera de la ubicación habitual: la carga funciona (RF-05.21).
- B10. Escritura que falla a mitad: rechazado, sin archivo a medias (RF-05.21).
- B11. Nombre con un nombre de persona inventado y un carácter no válido: rechazo sin eco (RNF-07.24).

**C. Dirección pública** (RNF-07.22, RF-04.20)
- C1. Documento por la dirección pública, sin y con token: no se entrega.
- C2. Avatar con `GET`, `HEAD` y `?v=`: se entrega.
- C3. Nombre de avatar con `..`, separadores, otra extensión o fuera de forma: 404.

## Fuera de alcance
- **004**: inventario y 401 en todas las rutas, flujos completos, qué rutas son públicas. La 004 clasificará la dirección de avatares, quitará de su RF-05.1 el «Estado actual» del guardado y **arreglará la interfaz para que un archivo rechazado muestre su aviso** (hoy la interfaz trata cada elemento de la respuesta como una tarea que sondear y no muestra «Nombre de archivo no válido»); en la 004a esa limitación solo se documenta y se verifica a mano (por `/sdd-change` sobre la 004).
- **Autenticación**: avatares con sesión (abierto a propósito, D1), rutas sin token, demás registros.
- **Notebooks o ingesta**: carga en el notebook de otro usuario (D6), contenido de las tareas del Worker, que el listado de archivos de un tema no devuelva rutas del servidor, tema libre de RF-06.
- Cambiar el formato de la ruta de documento, migrar o corregir datos, renombrar «expediente», prompts o la forma de citar.
- La interfaz no cambia; el extremo a extremo es de la 005.

## Criterios de finalización
- Cada requisito con prueba que pasa; regresiones vistas en rojo antes, con la causa del rojo anotada (plan §9), o anotadas como caracterización; exenciones justificadas en el plan.
- Suite completa y `--orden-inverso` pasan, sin residuos, sin tocar pruebas existentes.
- Manual con ambos roles, escritorio y pantalla pequeña: fuente citada se descarga; tema similar se abre; documento de notebook se previsualiza y se quita; avatar en menú y chat; carga llega a Procesado; qué ve el usuario con un archivo rechazado (anotado para la 004); documento no accesible sin sesión; bitácora con rechazos y sin nombres; consola sin errores.
- Inventario de solo lectura (plan §5) reportado; ningún dato modificado.
- Documentación (plan §13) y `MEMORY.md` en términos generales; `respaldo/` borrada.

## Dudas abiertas
Ninguna. Decisiones: D1-A, D2-A (con no Procesado → 404 uniforme, ajuste del reviewer), D3-A, D4-A, D5-A, D6-A, D7-B, D8-A, D9-A (plan §14).
