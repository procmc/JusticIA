"""Instrucciones fijas del Estudio del notebook (spec 010: RF-11.122, RF-11.123, RF-11.124, RF-12.120).

El usuario no escribe indicaciones (RF-11.123): estos textos son las únicas instrucciones. Todo va en español (RF-11.124) y pide
citar cada idea con el nombre exacto de la fuente entre corchetes, que es lo que luego se comprueba (RF-12.120). Cada texto
cuenta como instrucciones del presupuesto del motor y nunca se recorta.

Ver también: `app.services.estudio_service` (quien los envía al motor).
"""

REGLAS = (
    "Responda siempre en español. Use únicamente la información de los textos recibidos: no invente datos, cifras, fechas, "
    "nombres ni fuentes. Cada fuente aparece en el texto como: ### Fuente: \"nombre\"."
)

# Paso por partes: notas fieles de un tramo, con su fuente.
NOTAS = (
    REGLAS + "\n\nSu tarea es tomar notas fieles del tramo recibido: liste en viñetas cortas las ideas, datos y conclusiones "
    "importantes. Al final de cada viñeta indique su fuente con el nombre exacto entre corchetes, por ejemplo [nombre.pdf]. "
    "No agregue introducción ni comentarios."
)

# Paso de unión: junta notas de varios tramos sin perder ideas ni fuentes.
UNION = (
    REGLAS + "\n\nRecibirá notas tomadas de varios tramos. Únalas en una sola lista de viñetas más corta: elimine repeticiones, "
    "conserve todas las ideas importantes y mantenga al final de cada viñeta su fuente entre corchetes con el nombre exacto, "
    "por ejemplo [nombre.pdf]. No agregue introducción ni comentarios."
)

RESUMEN = (
    REGLAS + "\n\nRedacte un RESUMEN breve, de entre 120 y 250 palabras, con las ideas principales de las fuentes, en uno o dos "
    "párrafos y, si ayuda, algunas viñetas. Cite la fuente de cada idea con el nombre exacto entre corchetes, por ejemplo "
    "[nombre.pdf]. Si un texto está deformado o es poco legible, igual nombre su fuente entre corchetes y diga qué se pudo "
    "entender de él."
)

INFORME = (
    REGLAS + "\n\nRedacte un INFORME en formato Markdown con esta estructura: un título (#), una breve introducción, secciones "
    "con encabezados (##) que agrupen las ideas por tema y una sección final ## Conclusiones. Cite la fuente de cada idea con "
    "el nombre exacto entre corchetes, por ejemplo [nombre.pdf]. Si un texto está deformado o es poco legible, igual nombre su "
    "fuente entre corchetes y diga qué se pudo entender de él."
)

MAPA = (
    REGLAS + "\n\nConstruya un MAPA MENTAL de las fuentes como JSON válido, sin texto adicional ni bloques de código, con esta "
    "forma exacta: {\"titulo\": \"tema central\", \"ramas\": [{\"titulo\": \"rama\", \"ramas\": [{\"titulo\": \"subrama\", "
    "\"ramas\": []}]}]}. Use como máximo 3 niveles bajo el tema central y entre 3 y 8 ramas principales; cada título es una "
    "frase corta de hasta 8 palabras."
)

FINAL_POR_TIPO = {"resumen": RESUMEN, "informe": INFORME, "mapa_mental": MAPA}
