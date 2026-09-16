"""
Amplía el corpus de texto generando oraciones por combinación de
plantillas y vocabulario del dominio administrativo y judicial.

POR QUÉ ASÍ Y NO EXTRAYENDO DOCUMENTOS REALES
---------------------------------------------
Para enseñarle español al modelo hacen falta *oraciones con el vocabulario
correcto*, no documentos auténticos. Generarlas evita tres problemas de
golpe:

  * **Ley 8968 (datos personales).** La jurisprudencia real contiene
    nombres de partes, cédulas y domicilios; en materia penal y de familia,
    información especialmente sensible. Acá no hay dato de ninguna persona:
    los sujetos son roles ("el juez", "la parte actora"), nunca nombres.
  * **Derechos de autor.** No se pudo verificar en la Ley 6683 que los
    textos legales de Costa Rica estén excluidos de protección. El texto
    generado acá es de elaboración propia.
  * **Términos de uso.** SCIJ bloquea el acceso automatizado (HTTP 403).
    Acá no se consulta ninguna fuente externa.

El resultado es funcionalmente equivalente para el objetivo —enseñar
ortografía, acentuación, `ñ` y registro administrativo— sin ninguno de
esos riesgos.

REGLAS DE CONTENIDO (no romper)
-------------------------------
  * Cero nombres de personas, reales o inventados.
  * Cero cédulas y cero números de expediente con formato real.
  * Solo roles procesales y órganos genéricos.

Uso:
    .venv/Scripts/python.exe ampliar_corpus.py --cantidad 2000
"""

from __future__ import annotations

import argparse
import random
import re
from pathlib import Path

RAIZ = Path(__file__).parent
SALIDA = RAIZ / "corpus" / "oraciones_es_generadas.txt"

# --- Vocabulario, agrupado para que la concordancia funcione -----------------

ORGANO = ["el Juzgado", "el Tribunal", "el despacho", "la Sala",
          "el órgano director", "la autoridad administrativa",
          "el juzgador", "la institución"]

ROL_M = ["el apoderado", "el representante legal", "el perito",
         "el funcionario", "el interesado", "el recurrente",
         "el solicitante", "el testigo", "el servidor"]

ROL_F = ["la parte actora", "la parte demandada", "la contraparte",
         "la apoderada", "la recurrente", "la solicitante",
         "la perita", "la testigo"]

DOCUMENTO = ["el escrito", "el recurso", "el informe", "el oficio",
             "el expediente", "el dictamen", "el memorial",
             "el documento", "el certificado"]

DOCUMENTO_F = ["la demanda", "la resolución", "la solicitud",
               # "el acta" lleva articulo masculino por la "a"
               # tonica, pero adjetivo femenino: "el acta fue
               # archivada". Por eso va en esta lista.
               "el acta",
               "la certificación", "la notificación", "la gestión",
               "la diligencia", "la prueba", "la comparecencia",
               "la declaración"]

ACCION_M = ["admitido", "rechazado", "aportado", "presentado", "remitido",
            "archivado", "notificado", "aprobado", "trasladado", "recibido"]

ACCION_F = ["admitida", "rechazada", "aportada", "presentada", "remitida",
            "archivada", "notificada", "aprobada", "trasladada", "recibida"]

VERBO_ORGANO = ["ordena", "dispone", "resuelve", "confirma", "deniega",
                "acoge", "autoriza", "requiere", "señala"]

# Verbos que rigen "que + subjuntivo". Se separan porque no todos los de
# VERBO_ORGANO lo admiten: "confirma que se practique" es incorrecto.
VERBO_MANDATO = ["ordena", "dispone", "resuelve", "autoriza", "solicita"]

PLAZO_NUM = ["tres", "cinco", "ocho", "diez", "quince", "veinte",
             "treinta", "sesenta"]

PLAZO_TIPO = ["días hábiles", "días naturales", "meses", "días"]

MATERIA = ["civil", "laboral", "administrativa", "contenciosa",
           "de familia", "agraria", "notarial"]

CUALIDAD = ["improcedente", "extemporánea", "insuficiente", "procedente",
            "admisible", "inadmisible"]

MOTIVO = ["falta de interés actual", "falta de legitimación",
          "caducidad del plazo", "defectos de forma",
          "falta de fundamentación", "prescripción de la acción",
          "incompetencia territorial", "cosa juzgada"]

TRAMITE = ["la inscripción", "la certificación", "el traslado",
           "la devolución", "el archivo", "la acumulación",
           "la suspensión", "el desglose", "la foliatura"]

LUGAR = ["la oficina correspondiente", "el medio señalado",
         "el domicilio contractual", "la sede del despacho",
         "el sistema de gestión documental", "la plataforma institucional"]

ADVERBIO = ["oportunamente", "debidamente", "válidamente",
            "parcialmente", "expresamente", "formalmente"]

# --- Plantillas: cada hueco se llena con una lista compatible ---------------

PLANTILLAS = [
    "{ORGANO} {VERBO_ORGANO} {TRAMITE} solicitada por {ROL_F}.",
    "{ORGANO} {VERBO_MANDATO} que se practique {DOCUMENTO_F} en {LUGAR}.",
    "{DOCUMENTO} fue {ACCION_M} {ADVERBIO} por {ROL_M}.",
    "{DOCUMENTO_F} fue {ACCION_F} {ADVERBIO} dentro del término conferido.",
    "Se declara {CUALIDAD} {DOCUMENTO_F} por {MOTIVO}.",
    "Se rechaza {DOCUMENTO_F} presentada por {ROL_F} por {MOTIVO}.",
    "Se confiere audiencia por el plazo de {PLAZO_NUM} {PLAZO_TIPO} a {ROL_F}.",
    "Se previene a {ROL_F} aportar {DOCUMENTO} en {PLAZO_NUM} {PLAZO_TIPO}.",
    "{ROL_M} acreditó su representación mediante {DOCUMENTO} habilitante.",
    "{ROL_F} manifestó su conformidad con lo resuelto por {ORGANO}.",
    "{ORGANO} {VERBO_MANDATO} remitir {DOCUMENTO} al superior en grado.",
    "El plazo para interponer {DOCUMENTO} venció hace {PLAZO_NUM} {PLAZO_TIPO}.",
    "Se tiene por {ACCION_F} {DOCUMENTO_F} en materia {MATERIA}.",
    "{DOCUMENTO_F} quedó firme al no haberse interpuesto recurso alguno.",
    "Se ordena {TRAMITE} previa razón consignada en el expediente.",
    "{ORGANO} valoró {DOCUMENTO_F} conforme a las reglas de la sana crítica.",
    "{ROL_M} compareció {ADVERBIO} a la hora y fecha señaladas.",
    "Se dispone {TRAMITE} por resultar {CUALIDAD} la gestión anterior.",
    "{DOCUMENTO} consta agregado al expediente en materia {MATERIA}.",
    "La resolución fue {ACCION_F} a ambas partes en {LUGAR}.",
    "{ORGANO} {VERBO_MANDATO} el cumplimiento en {PLAZO_NUM} {PLAZO_TIPO}.",
    "Se acoge {DOCUMENTO_F} por existir peligro en la demora.",
    "{ROL_F} desistió {ADVERBIO} de la acción interpuesta.",
    "Se declara sin lugar {DOCUMENTO} por {MOTIVO}.",
    "{DOCUMENTO_F} se practicó en presencia de {ROL_M}.",
    "Se autoriza la consulta del expediente a {ROL_F} acreditada.",
    "{ORGANO} requiere la actualización de los datos del trámite.",
    "Se ordena {TRAMITE} conforme al reglamento vigente.",
    "{DOCUMENTO} fue {ACCION_M} en la plataforma de gestión documental.",
    "{ROL_M} rindió {DOCUMENTO} dentro del plazo de {PLAZO_NUM} {PLAZO_TIPO}.",
    "Se tiene por cumplida la prevención efectuada a {ROL_F}.",
    "{ORGANO} {VERBO_MANDATO} la comparecencia para dentro de {PLAZO_NUM} {PLAZO_TIPO}.",
    "¿Cuál es el fundamento de {DOCUMENTO_F} presentada por {ROL_F}?",
    "¿Se cumplió el requisito de agotamiento de la vía administrativa?",
    "Los daños alegados se liquidarán en ejecución de sentencia.",
    "El diseño del trámite debe garantizar la confidencialidad de los datos.",
    "La enseñanza del procedimiento exige el estudio de la jurisprudencia.",
    "{ROL_M} señaló que el año anterior no se recibió la notificación.",
    "Se acompaña copia fiel de {DOCUMENTO} para su cotejo.",
    "{DOCUMENTO_F} en materia {MATERIA} fue {ACCION_F} sin observaciones.",
]

LISTAS = {
    "ORGANO": ORGANO, "ROL_M": ROL_M, "ROL_F": ROL_F,
    "DOCUMENTO": DOCUMENTO, "DOCUMENTO_F": DOCUMENTO_F,
    "ACCION_M": ACCION_M, "ACCION_F": ACCION_F,
    "VERBO_ORGANO": VERBO_ORGANO, "VERBO_MANDATO": VERBO_MANDATO, "PLAZO_NUM": PLAZO_NUM,
    "PLAZO_TIPO": PLAZO_TIPO, "MATERIA": MATERIA, "CUALIDAD": CUALIDAD,
    "MOTIVO": MOTIVO, "TRAMITE": TRAMITE, "LUGAR": LUGAR,
    "ADVERBIO": ADVERBIO,
}

HUECO = re.compile(r"\{([A-Z_]+)\}")


def generar_una(rng: random.Random) -> str:
    plantilla = rng.choice(PLANTILLAS)
    oracion = HUECO.sub(lambda m: rng.choice(LISTAS[m.group(1)]), plantilla)
    # Mayúscula inicial, respetando el signo de apertura de pregunta.
    if oracion[0] == "¿":
        return oracion[0] + oracion[1].upper() + oracion[2:]
    return oracion[0].upper() + oracion[1:]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cantidad", type=int, default=2000)
    ap.add_argument("--semilla", type=int, default=11)
    ap.add_argument("--min-largo", type=int, default=38,
                    help="descartar oraciones más cortas (una línea manuscrita "
                         "ronda los 40-80 caracteres)")
    ap.add_argument("--max-largo", type=int, default=95)
    args = ap.parse_args()

    rng = random.Random(args.semilla)
    vistas: set[str] = set()
    intentos = 0
    limite = args.cantidad * 80

    while len(vistas) < args.cantidad and intentos < limite:
        intentos += 1
        o = generar_una(rng)
        if args.min_largo <= len(o) <= args.max_largo:
            vistas.add(o)

    oraciones = sorted(vistas)

    encabezado = [
        "# Corpus generado por combinación de plantillas y vocabulario.",
        "#",
        "# Contenido INVENTADO. Sin nombres de personas, sin cédulas y sin",
        "# números de expediente: los sujetos son roles procesales y órganos",
        "# genéricos. No se extrajo de ninguna fuente externa, precisamente",
        "# para no incurrir en problemas de datos personales (Ley 8968),",
        "# derechos de autor ni términos de uso de sitios institucionales.",
        "#",
        f"# Generado por ampliar_corpus.py --cantidad {args.cantidad} "
        f"--semilla {args.semilla}",
        "",
    ]
    SALIDA.write_text("\n".join(encabezado + oraciones) + "\n", encoding="utf-8")

    largos = [len(o) for o in oraciones]
    print(f"Oraciones únicas generadas : {len(oraciones)}")
    print(f"Intentos                   : {intentos}")
    print(f"Largo (caracteres)         : min {min(largos)}, "
          f"promedio {sum(largos)//len(largos)}, max {max(largos)}")
    print(f"Salida                     : {SALIDA}")
    print("\nMuestra:")
    for o in rng.sample(oraciones, min(6, len(oraciones))):
        print(f"  {o}")


if __name__ == "__main__":
    main()
