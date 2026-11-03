"""CF-1 (spec 007; RF-11.60, RF-20.60): el conteo de tokens de entrada del motor real contra el estimado del sistema.

Por llamada compara `prompt_eval_count` (lo que cuenta Ollama, plantilla incluida) con la estimación de
`presupuesto_contexto.tokens`. Falla si hay recorte (real > 7.168, o 4.098 con un estimado mayor) o si el real
supera al estimado; en ese último caso hay que PARAR y preguntar a Andrés (Q-B). Datos inventados `PRUEBA`.
"""
import pytest

from app.config.contexto_config import CONFIGURACION
from app.services.RAG import presupuesto_contexto as pc
from app.services.RAG.prompts import INSTRUCCION_REFORMULACION, INSTRUCCIONES_GENERAL
from app.services.RAG.prompts.expediente_prompt import instrucciones_tema
from app.services.RAG.prompts.notebook_prompt import instrucciones_notebook

PRESUPUESTO = CONFIGURACION.presupuesto
CASOS_CHAT = ["general", "tema", "notebook"]


def _narrativo(n: int, largo: int) -> str:
    base = ("PRUEBA: la Dirección resolvió remitir el oficio a la unidad competente para que, en el plazo establecido, "
            "analice la solicitud presentada por la institución y comunique su criterio por los medios oficiales. ")
    texto = f"Párrafo {n}. " + base * (largo // len(base) + 1)
    return texto[:largo]


def _denso(n: int, largo: int) -> str:
    """Texto administrativo con códigos y montos, a ~2,95 caracteres/token medidos en Ollama (el fragmento real más
    denso de Nexus dio 2,91; Q-B = A, 03/11/2026). No bajar de 2,9 ni hacerlo más denso que el texto real."""
    filas = []
    i = 0
    while sum(len(f) + 1 for f in filas) < largo:
        i += 1
        filas.append(f"Mediante oficio MICITT-DGD-OF-{n:03d}-{2020 + i % 7} la Dirección remitió el trámite "
                     f"SICOP-{n}{i:04d} a la unidad competente de la CCSS, para que analice la solicitud de la "
                     f"institución, con un monto de ₡{1234567 + n * i * 37:,}.")
    return "\n".join(filas)[:largo]


GENERADORES = {"narrativo": _narrativo, "denso": _denso}


def _fragmentos(estilo: str, cantidad: int, largo: int):
    gen = GENERADORES[estilo]
    return [pc.Fragmento(texto=gen(i, largo), archivo=f"PRUEBA_documento_{i}.pdf", tema="PRUEBA tema largo",
                         ruta=f"/api/descargar/PRUEBA_documento_{i}.pdf", pagina_inicio=i, pagina_fin=i + 1)
            for i in range(1, cantidad + 1)]


def _historial(estilo: str, mensajes: int, largo: int):
    gen = GENERADORES[estilo]
    return [gen(i, largo) for i in range(mensajes)]


def _con_roles(historial):
    """Alterna usuario y asistente de modo que el último mensaje sea del asistente."""
    n = len(historial)
    return [{"role": "assistant" if (n - 1 - i) % 2 == 0 else "user", "content": t} for i, t in enumerate(historial)]


def _instrucciones(chat: str) -> str:
    return {"general": INSTRUCCIONES_GENERAL, "tema": instrucciones_tema("PRUEBA tema largo"),
            "notebook": instrucciones_notebook("PRUEBA notebook")}[chat]


def _entrada_respuesta(chat: str, estilo: str):
    """La entrada más grande de la respuesta: 20 mensajes de historial y 15 fragmentos para elegir (k ≤ 8)."""
    pregunta = GENERADORES[estilo](0, 1200)
    armada = pc.armar_respuesta(chat, _instrucciones(chat), pregunta, _historial(estilo, 20, 700), _fragmentos(estilo, 15, 1500))
    mensajes = [{"role": "system", "content": armada.sistema}, *_con_roles(armada.historial),
                {"role": "user", "content": armada.pregunta}]
    return mensajes, armada.tokens_total


def _entrada_reformulacion(estilo: str):
    """Los 2 últimos mensajes (del tamaño de una respuesta completa) más una pregunta larga."""
    pregunta = GENERADORES[estilo](0, 1500)
    previos = pc.mensajes_para_reformular(INSTRUCCION_REFORMULACION, pregunta, _historial(estilo, 2, 3500))
    mensajes = [{"role": "system", "content": INSTRUCCION_REFORMULACION}, *_con_roles(previos),
                {"role": "user", "content": pregunta}]
    estimado = pc.tokens(INSTRUCCION_REFORMULACION) + pc.tokens(pregunta) + sum(pc.tokens(m) for m in previos)
    return mensajes, estimado


def _entrada_resumen(estilo: str):
    """Tema largo: 20 chunks de 7.000 caracteres; el contexto se arma con el mismo código del resumen."""
    from langchain_core.documents import Document
    from app.services.busqueda_similares.similarity_prompt_builder import (
        create_similarity_summary_context, create_similarity_summary_prompt)
    gen = GENERADORES[estilo]
    docs = [Document(page_content=gen(i, 7000), metadata={"id_documento": i, "nombre_archivo": f"PRUEBA_{i}.pdf", "indice_chunk": 0})
            for i in range(1, 21)]
    instrucciones = pc.tokens(create_similarity_summary_prompt("", "PRUEBA-001"))
    contexto = create_similarity_summary_context(docs, max_docs=20, max_tokens=PRESUPUESTO - instrucciones)
    prompt = create_similarity_summary_prompt(contexto, "PRUEBA-001")
    return [{"role": "user", "content": prompt}], pc.tokens(prompt)


def _comprobar(nombre: str, real: int, estimado: int):
    margen = estimado - real
    print(f"\nCF-1 | {nombre:<34} | real {real:>5} | estimado {estimado:>5} | margen {margen:>+5} | presupuesto {PRESUPUESTO}")
    assert real <= PRESUPUESTO, f"{nombre}: el motor cuenta {real} tokens, por encima del presupuesto {PRESUPUESTO}"
    assert not (real == 4098 and estimado > 4098), f"{nombre}: 4.098 con estimado mayor: la entrada se recortó"
    assert real <= estimado, (f"{nombre}: el conteo real ({real}) supera al estimado ({estimado}) por {-margen} tokens: "
                              "PARAR y preguntar a Andrés (Q-B)")


def test_conteo_sin_cache_es_estable(motor):
    """RF-11.60: la misma entrada, dos veces con `keep_alive: 0`, da el mismo conteo (el motor no descuenta caché)."""
    mensajes, estimado = _entrada_respuesta("general", "narrativo")
    primero = motor.contar(mensajes)["real"]
    segundo = motor.contar(mensajes)["real"]
    print(f"\nCF-1 | estabilidad (Ollama {motor.version}) | 1.ª {primero} | 2.ª {segundo} | estimado {estimado}")
    assert primero == segundo, f"el conteo cambia entre llamadas ({primero} y {segundo}): hay caché de prefijos; PARAR y preguntar"


@pytest.mark.parametrize("estilo", ["narrativo", "denso"])
@pytest.mark.parametrize("caso", [f"{c}-{e}" for c in CASOS_CHAT for e in ("reformulacion", "respuesta")] + ["resumen"])
def test_entrada_maxima(motor, caso, estilo):
    """RF-11.60, RF-20.60: con las entradas más grandes, el conteo real no supera el presupuesto ni el estimado."""
    if caso == "resumen":
        mensajes, estimado = _entrada_resumen(estilo)
    elif caso.endswith("reformulacion"):
        mensajes, estimado = _entrada_reformulacion(estilo)
    else:
        mensajes, estimado = _entrada_respuesta(caso.split("-")[0], estilo)
    real = motor.contar(mensajes)["real"]
    _comprobar(f"{caso} / {estilo}", real, estimado)
