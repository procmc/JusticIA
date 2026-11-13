"""Lógica pura del Estudio del notebook (spec 010: RF-11.122, RF-11.125, RF-11.126, RF-12.120, RF-14.120, RF-14.122).

`app.services.estudio_logica` no llama al motor, a Qdrant ni a la base de datos: parte el contenido de las fuentes en partes que
caben en la ventana del modelo, valida la estructura del mapa mental, comprueba que un texto cite alguna fuente de la selección y
arma el título por omisión. Los textos son inventados (prefijo PRUEBA).
"""
import math
from datetime import datetime

import pytest

from app.config.contexto_config import CONFIGURACION as CFG
from app.services import estudio_logica as el


def _tokens(texto: str) -> int:
    return math.ceil(len(texto) / CFG.caracteres_por_token)


def _trozo(fuente: str, largo: int, marca: str = "x") -> el.Trozo:
    return el.Trozo(fuente=fuente, texto=marca * largo)


# --- partir en partes (RF-11.126) -------------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-11.126")
def test_si_todo_cabe_es_una_sola_parte_con_sus_fuentes():
    trozos = [_trozo("PRUEBA_a.pdf", 300, "a"), _trozo("PRUEBA_a.pdf", 300, "b"), _trozo("PRUEBA_b.pdf", 300, "c")]
    partes = el.partir(trozos, maximo_tokens=2000)
    assert len(partes) == 1
    assert partes[0].fuentes == ["PRUEBA_a.pdf", "PRUEBA_b.pdf"]
    assert "### Fuente: \"PRUEBA_a.pdf\"" in partes[0].texto and "### Fuente: \"PRUEBA_b.pdf\"" in partes[0].texto


@pytest.mark.requisito("RF-11.126")
def test_cada_parte_cabe_y_no_se_pierde_ningun_trozo():
    trozos = [_trozo(f"PRUEBA_{i % 3}.pdf", 1400, chr(ord("a") + i % 20)) for i in range(40)]
    maximo = 1500
    partes = el.partir(trozos, maximo_tokens=maximo)
    assert len(partes) > 1
    for parte in partes:
        assert _tokens(parte.texto) <= maximo
    texto_total = "".join(p.texto for p in partes)
    for trozo in trozos:
        assert trozo.texto in texto_total, "un trozo quedó fuera de todas las partes"


@pytest.mark.requisito("RF-11.126")
def test_al_cortar_una_fuente_su_nombre_se_repite_en_la_parte_siguiente():
    trozos = [_trozo("PRUEBA_larga.pdf", 1400, "a") for _ in range(12)]
    partes = el.partir(trozos, maximo_tokens=1200)
    assert len(partes) > 1
    assert all("### Fuente: \"PRUEBA_larga.pdf\"" in p.texto for p in partes)
    assert all(p.fuentes == ["PRUEBA_larga.pdf"] for p in partes)


@pytest.mark.requisito("RF-11.126")
def test_un_trozo_mas_grande_que_el_presupuesto_se_recorta_para_caber():
    partes = el.partir([_trozo("PRUEBA_a.pdf", 50000)], maximo_tokens=500)
    assert len(partes) == 1 and _tokens(partes[0].texto) <= 500


@pytest.mark.requisito("RF-11.126")
def test_sin_contenido_no_hay_partes():
    assert el.partir([], maximo_tokens=500) == []
    assert el.partir([el.Trozo(fuente="PRUEBA_a.pdf", texto="   ")], maximo_tokens=500) == []


@pytest.mark.requisito("RF-11.126")
def test_agrupar_notas_junta_las_que_caben_y_nunca_deja_una_fuera():
    notas = ["n" * 1000, "m" * 1000, "o" * 1000, "p" * 1000, "q" * 1000]
    grupos = el.agrupar(notas, maximo_tokens=700)  # 700 tokens ≈ 2030 caracteres: caben dos notas por grupo
    assert [len(g) for g in grupos] == [2, 2, 1]
    assert [n for g in grupos for n in g] == notas
    for grupo in grupos:
        assert _tokens("\n\n".join(grupo)) <= 700


@pytest.mark.requisito("RF-11.126")
def test_agrupar_una_nota_que_no_cabe_la_deja_sola():
    grupos = el.agrupar(["a" * 100, "b" * 9000, "c" * 100], maximo_tokens=500)
    assert grupos == [["a" * 100], ["b" * 9000], ["c" * 100]]


# --- citas (RF-12.120) ------------------------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-12.120")
@pytest.mark.parametrize("texto, esperado", [
    ("Según [PRUEBA_informe.pdf] el plazo es de diez días.", True),
    ("Según PRUEBA_INFORME.PDF el plazo es de diez días.", True),          # sin distinguir mayúsculas
    ("Según el documento PRUEBA_informe, el plazo es de diez días.", True),  # nombre sin la extensión
    ("El plazo es de diez días, sin decir de dónde sale.", False),
    ("Según [otro_documento.pdf] el plazo es de diez días.", False),       # una fuente fuera de la selección
    ("", False),
])
def test_citas_validas_exige_una_fuente_de_la_seleccion(texto, esperado):
    assert el.citas_validas(texto, ["PRUEBA_informe.pdf", "PRUEBA_anexo.docx"]) is esperado


@pytest.mark.requisito("RF-12.120")
def test_asegurar_fuentes_no_toca_un_texto_que_ya_cita():
    texto = "Según [PRUEBA_informe.pdf] el plazo es de diez días."
    assert el.asegurar_fuentes(texto, ["PRUEBA_informe.pdf", "PRUEBA_anexo.docx"]) == texto


@pytest.mark.requisito("RF-12.120")
def test_asegurar_fuentes_agrega_las_fuentes_de_la_seleccion_si_el_texto_no_cita_ninguna():
    texto = "El plazo es de diez días, sin decir de dónde sale."
    resultado = el.asegurar_fuentes(texto, ["PRUEBA_informe.pdf", "PRUEBA_anexo.docx"])
    assert resultado.startswith(texto)
    assert resultado.endswith("**Fuentes consultadas:** [PRUEBA_informe.pdf], [PRUEBA_anexo.docx]")
    assert el.citas_validas(resultado, ["PRUEBA_informe.pdf", "PRUEBA_anexo.docx"]) is True


# --- mapa mental (RF-11.122, RF-11.125) -------------------------------------------------------------------------------------

BUENO = '{"titulo": "Teletrabajo", "ramas": [{"titulo": "Plazos", "ramas": [{"titulo": "Diez días", "ramas": []}]}, {"titulo": "Equipo", "ramas": []}]}'


@pytest.mark.requisito("RF-11.122")
def test_un_mapa_valido_se_normaliza():
    mapa = el.analizar_mapa(BUENO)
    assert mapa["titulo"] == "Teletrabajo"
    assert [r["titulo"] for r in mapa["ramas"]] == ["Plazos", "Equipo"]
    assert mapa["ramas"][0]["ramas"] == [{"titulo": "Diez días", "ramas": []}]


@pytest.mark.requisito("RF-11.125")
def test_el_mapa_se_extrae_aunque_venga_con_cercas_o_texto_alrededor():
    assert el.analizar_mapa(f"```json\n{BUENO}\n```")["titulo"] == "Teletrabajo"
    assert el.analizar_mapa(f"Aquí está el mapa:\n{BUENO}\nEspero que sirva.")["titulo"] == "Teletrabajo"


@pytest.mark.requisito("RF-11.125")
@pytest.mark.parametrize("salida", [
    "", "   ", "no es un json", "{no cerrado", "[1, 2, 3]",
    '{"ramas": [{"titulo": "A", "ramas": []}]}',                 # sin tema central
    '{"titulo": "  ", "ramas": [{"titulo": "A", "ramas": []}]}',  # tema central vacío
    '{"titulo": "Tema", "ramas": []}',                            # sin ramas
    '{"titulo": "Tema", "ramas": "texto"}',                       # ramas que no es una lista
    '{"titulo": "Tema", "ramas": [{"sin_titulo": 1}]}',          # ninguna rama válida
])
def test_un_mapa_sin_la_estructura_exigida_es_invalido(salida):
    assert el.analizar_mapa(salida) is None


@pytest.mark.requisito("RF-11.122")
def test_el_mapa_se_poda_a_tres_niveles_bajo_el_tema_central():
    profundo = ('{"titulo": "T", "ramas": [{"titulo": "N1", "ramas": [{"titulo": "N2", "ramas": '
                '[{"titulo": "N3", "ramas": [{"titulo": "N4", "ramas": []}]}]}]}]}')
    mapa = el.analizar_mapa(profundo)
    n1 = mapa["ramas"][0]
    n2 = n1["ramas"][0]
    n3 = n2["ramas"][0]
    assert (n1["titulo"], n2["titulo"], n3["titulo"]) == ("N1", "N2", "N3")
    assert n3["ramas"] == [], "el nivel cuatro no debe quedar"


@pytest.mark.requisito("RF-11.122")
def test_el_mapa_limita_las_ramas_por_nodo_y_el_total_de_nodos():
    muchas = ",".join(f'{{"titulo": "R{i}", "ramas": [' + ",".join(f'{{"titulo": "S{i}_{j}", "ramas": []}}' for j in range(8)) + "]}" for i in range(30))
    mapa = el.analizar_mapa('{"titulo": "T", "ramas": [' + muchas + "]}")

    def contar(nodo):
        return 1 + sum(contar(r) for r in nodo["ramas"])

    assert len(mapa["ramas"]) <= el.MAX_RAMAS_POR_NODO
    assert contar(mapa) <= el.MAX_NODOS_MAPA


@pytest.mark.requisito("RF-14.122")
def test_el_mapa_se_copia_como_lista_anidada():
    texto = el.texto_de_mapa(el.analizar_mapa(BUENO))
    assert texto.splitlines() == ["Teletrabajo", "- Plazos", "  - Diez días", "- Equipo"]


# --- título por omisión (RF-14.120) -----------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-14.120")
@pytest.mark.parametrize("tipo, etiqueta", [("resumen", "Resumen"), ("informe", "Informe"),
                                            ("mapa_mental", "Mapa mental"), ("nota", "Nota")])
def test_el_titulo_por_omision_lleva_el_tipo_y_la_hora_de_costa_rica(tipo, etiqueta):
    # 19:40 UTC es 13:40 en Costa Rica (UTC-6, sin horario de verano)
    assert el.titulo_por_omision(tipo, datetime(2026, 11, 9, 19, 40)) == f"{etiqueta} · 09/11/2026 13:40"


@pytest.mark.requisito("RF-14.120")
def test_la_hora_de_costa_rica_puede_ser_del_dia_anterior():
    assert el.titulo_por_omision("resumen", datetime(2026, 11, 10, 3, 5)) == "Resumen · 09/11/2026 21:05"
