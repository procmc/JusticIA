"""
Instrucciones del chat de un Notebook (NotebookServIA; spec 007, RF-12.61; plan §6.3) y adaptación de las
referencias a imágenes de la pregunta.

Lenguaje genérico: un notebook puede contener cualquier tipo de documento gubernamental. El texto es plano
(sin plantilla de LangChain); `presupuesto_contexto` agrega la lista de archivos y los fragmentos.

Ver también:
    * app.services.RAG.expediente_prompt: instrucciones equivalentes para un tema
    * app.services.RAG.rag_chain_service: usa reformular_referencia_imagen

Authors:
    ServIA Team

Version:
    1.0.0
"""

import re

# Detecta si la pregunta del usuario menciona un archivo de imagen (por
# extensión o por la palabra "imagen"/"foto"). Cuando pasa, el modelo tiende
# a interpretar la pregunta como un pedido de "ver" la imagen directamente
# -- ignorando el contexto -- y responde negando acceso, aunque el texto ya
# reconocido esté servido completo más abajo en el prompt. Verificado: el
# disparador está en la redacción de la PREGUNTA, no en cómo se presenta el
# contexto (se probó reformular la anotación de origen y ocultar la
# extensión en el header, sin efecto).
_PATRON_REFERENCIA_IMAGEN = re.compile(
    r'\b[\w\-]+\.(jpg|jpeg|png|tif|tiff|bmp)\b|\bimagen(es)?\b|\bfoto(s|graf[ií]a)?\b',
    re.IGNORECASE,
)


def _menciona_archivo_de_imagen(pregunta: str) -> bool:
    return bool(pregunta) and bool(_PATRON_REFERENCIA_IMAGEN.search(pregunta))


# Patrones para reformular la pregunta ANTES de que el modelo la vea (última
# vía probada, distinta a reforzar instrucciones): si el disparador está en
# la redacción de la pregunta del usuario, la única forma de evitarlo del
# todo es que el modelo nunca lea la palabra "imagen"/"foto" ni un nombre de
# archivo con extensión de imagen. El historial de la conversación guarda
# esta versión reformulada, no la original -- limitación conocida y
# aceptada de esta técnica.
# Frase completa PRIMERO: "la imagen (agregada) (llamada) archivo.png" es
# una sola referencia, no dos -- si se reemplazan "la imagen" y
# "archivo.png" por separado (como se hacía antes), queda duplicada
# ("el documento escaneado agregada llamada el documento escaneado"),
# confirmado en pruebas reales y suficiente para confundir al modelo.
_PATRON_FRASE_COMPLETA = re.compile(
    r'\b(?:la|una)?\s*imagen(?:es)?\s*(?:agregada|subida|cargada|adjunta)?\s*'
    r'(?:llamada|nombrada|de nombre)?\s*[\w\-]+\.(?:jpg|jpeg|png|tif|tiff|bmp)\b',
    re.IGNORECASE,
)
_PATRON_ARCHIVO_IMAGEN_CON_ARTICULO = re.compile(
    r'\b(?:(?:la|el|lo|una|un)\s+)?[\w\-]+\.(?:jpg|jpeg|png|tif|tiff|bmp)\b',
    re.IGNORECASE,
)
_PATRON_LA_IMAGEN = re.compile(r'\b(la|una)\s+imagen(es)?\b', re.IGNORECASE)
_PATRON_IMAGEN_SOLA = re.compile(r'\bimagen(es)?\b', re.IGNORECASE)
_PATRON_FOTO = re.compile(r'\bfoto(s|graf[ií]a)?\b', re.IGNORECASE)


def reformular_referencia_imagen(pregunta: str) -> str:
    """Reemplaza menciones a archivos de imagen por una referencia genérica.

    Devuelve la pregunta sin cambios si no menciona ninguna imagen.

    La referencia usada, "el documento escaneado", no es arbitraria: es
    literalmente la misma frase que document_formatter.py ya escribe en
    la anotación "**Origen:** documento escaneado, ya transcrito
    automáticamente a texto" para los chunks que vienen de una imagen —
    y SOLO para esos, nunca para un PDF. Un genérico como "el archivo
    subido" (probado antes) es ambiguo en cuanto hay más de un
    documento en el notebook: el modelo llegó a responder sobre el PDF
    cuando se le preguntaba por la imagen. Repetir la misma frase que ya
    aparece en el contexto le da al modelo un ancla textual única para
    encontrar el chunk correcto.
    """
    if not _menciona_archivo_de_imagen(pregunta):
        return pregunta

    resultado = _PATRON_FRASE_COMPLETA.sub("el documento escaneado", pregunta)
    resultado = _PATRON_ARCHIVO_IMAGEN_CON_ARTICULO.sub("el documento escaneado", resultado)
    resultado = _PATRON_LA_IMAGEN.sub("el documento escaneado", resultado)
    resultado = _PATRON_IMAGEN_SOLA.sub("documento escaneado", resultado)
    resultado = _PATRON_FOTO.sub("documento escaneado", resultado)
    return resultado


_INSTRUCCIONES_NOTEBOOK = """Eres el asistente de ServIA y analizas los documentos del notebook «{notebook}», una colección de documentos que cargó el usuario.

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

- Notebook "{notebook}": (<nombre del archivo>)"""


def instrucciones_notebook(notebook: str) -> str:
    """Instrucciones nuevas de NotebookServIA (spec 007, RF-12.61; plan §6.3).

    Reemplazo de texto, no plantilla de LangChain. La lista de archivos y los fragmentos los agrega el armado
    de `presupuesto_contexto` (títulos `TITULO_LISTA` y `TITULO_FRAGMENTOS`).
    """
    return _INSTRUCCIONES_NOTEBOOK.replace("{notebook}", notebook)
