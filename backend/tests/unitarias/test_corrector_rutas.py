"""Corrector de rutas de la respuesta del chat (RF-12.1, RF-18.20).

El modelo a veces «corrige» la ortografía al copiar la ruta de un archivo (`deposito` → `depósito`, `Filosofa` → `Filosofía`) y el
enlace de descarga deja de coincidir con el archivo registrado. `app.services.RAG.corrector_rutas` cambia una ruta escrita por la
ruta registrada (y visible para el usuario) de la MISMA carpeta que mejor coincide, solo si la coincidencia es clara. La descarga
sigue exigiendo la ruta exacta (RNF-07.20): este módulo no la afloja, evita que el modelo la rompa. Los nombres son inventados.
"""
import pytest

from app.services.RAG.corrector_rutas import CorrectorDeRutas, ruta_mas_parecida

CARPETA = "PRUEBA-TEMA"
EXACTA = f"uploads/{CARPETA}/Formulario de deposito legal Biblioteca de la Facultad de Filosofa y Letras 1.pdf"
OTRA = f"uploads/{CARPETA}/Reglamento general de la Biblioteca 2.pdf"
CONOCIDAS = [EXACTA, OTRA]


# --- ruta_mas_parecida ----------------------------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-12.1")
def test_una_ruta_exacta_no_se_cambia():
    assert ruta_mas_parecida(EXACTA, CONOCIDAS) is None


@pytest.mark.requisito("RF-12.1")
@pytest.mark.parametrize("escrita", [
    f"uploads/{CARPETA}/Formulario de depósito legal Biblioteca de la Facultad de Filosofa y Letras 1.pdf",        # una tilde de más
    f"uploads/{CARPETA}/Formulario de depósito legal Biblioteca de la Facultad de Filosofía y Letras 1.pdf",       # tilde y letra de más
    f"uploads/{CARPETA}/FORMULARIO DE DEPOSITO LEGAL BIBLIOTECA DE LA FACULTAD DE FILOSOFA Y LETRAS 1.PDF",        # mayúsculas
    f"uploads/{CARPETA}/Formulario  de deposito legal Biblioteca de la Facultad de Filosofa y Letras 1.pdf",       # espacio doble
])
def test_el_modelo_que_corrige_la_ortografia_se_devuelve_a_la_ruta_registrada(escrita):
    assert ruta_mas_parecida(escrita, CONOCIDAS) == EXACTA


@pytest.mark.requisito("RF-12.1")
def test_si_dos_rutas_se_parecen_igual_no_se_adivina():
    a = f"uploads/{CARPETA}/Circular DE 12-2024.pdf"
    b = f"uploads/{CARPETA}/Circular DE 13-2024.pdf"
    assert ruta_mas_parecida(f"uploads/{CARPETA}/Circular DE 1-2024.pdf", [a, b]) is None


@pytest.mark.requisito("RF-12.1")
def test_una_ruta_que_no_se_parece_a_ninguna_no_se_toca():
    assert ruta_mas_parecida(f"uploads/{CARPETA}/Receta del gallo pinto.pdf", CONOCIDAS) is None
    assert ruta_mas_parecida(EXACTA, []) is None


# --- CorrectorDeRutas: el flujo de la respuesta ---------------------------------------------------------------------------------

def _corrector(conocidas=None, llamadas=None):
    def conocidas_de(carpeta):
        if llamadas is not None:
            llamadas.append(carpeta)
        return list(CONOCIDAS if conocidas is None else conocidas) if carpeta == CARPETA else []
    return CorrectorDeRutas(conocidas_de)


def _pasar(corrector, trozos):
    salida = "".join(corrector.procesar(t) for t in trozos)
    return salida + corrector.vaciar()


MALA = f"uploads/{CARPETA}/Formulario de depósito legal Biblioteca de la Facultad de Filosofía y Letras 1.pdf"


@pytest.mark.requisito("RF-12.1")
def test_corrige_la_ruta_entre_parentesis_de_la_seccion_de_fuentes():
    texto = f"Según el formulario.\n\n**FUENTES:**\n- Formulario: ({MALA})\n"
    esperado = f"Según el formulario.\n\n**FUENTES:**\n- Formulario: ({EXACTA})\n"
    assert _pasar(_corrector(), [texto]) == esperado


@pytest.mark.requisito("RF-12.1")
def test_corrige_una_ruta_que_llega_partida_en_varios_trozos():
    texto = f"Fuentes: ({MALA}) fin."
    trozos = [texto[i:i + 7] for i in range(0, len(texto), 7)]  # trozos de 7 caracteres: parten «uploads/» y la ruta
    assert _pasar(_corrector(), trozos) == f"Fuentes: ({EXACTA}) fin."


@pytest.mark.requisito("RF-12.1")
def test_un_texto_sin_rutas_pasa_igual_aunque_termine_en_parte_del_marcador():
    texto = "El resumen no cita rutas y termina con «upl"
    assert _pasar(_corrector(), [texto[:10], texto[10:]]) == texto


@pytest.mark.requisito("RF-12.1")
def test_una_ruta_exacta_pasa_igual():
    texto = f"- Formulario: ({EXACTA})"
    assert _pasar(_corrector(), [texto]) == texto


@pytest.mark.requisito("RF-12.1")
def test_una_ruta_de_otra_carpeta_sin_rutas_conocidas_pasa_igual():
    texto = "- Otro: (uploads/OTRO-TEMA/Algun documento.pdf)"
    assert _pasar(_corrector(), [texto]) == texto


@pytest.mark.requisito("RF-12.1")
def test_si_no_se_pueden_consultar_las_rutas_conocidas_el_texto_pasa_igual():
    def falla(carpeta):
        raise RuntimeError("base no disponible")
    texto = f"- Formulario: ({MALA})"
    assert _pasar(CorrectorDeRutas(falla), [texto]) == texto


@pytest.mark.requisito("RF-12.1")
def test_una_ruta_sin_cierre_no_retiene_la_respuesta_para_siempre():
    texto = "uploads/" + "x" * 2000
    salida = _pasar(_corrector(), [texto])
    assert salida == texto, "el texto retenido debe salir completo al terminar o al pasar el límite"


@pytest.mark.requisito("RF-12.1")
def test_consulta_las_rutas_conocidas_de_la_carpeta_de_cada_ruta():
    llamadas = []
    _pasar(_corrector(llamadas=llamadas), [f"({MALA}) y ({EXACTA})"])
    assert llamadas == [CARPETA, CARPETA]
