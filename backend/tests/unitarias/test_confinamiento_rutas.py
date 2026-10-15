"""Pruebas de la spec 004a: confinamiento de los archivos de documentos por tema y nombre.

T1 (RNF-07.21): la función común que abren y borran por tema y nombre (descarga, previsualización y borrado
en NotebookServIA) solo devuelve una ubicación si tema y nombre son nombres seguros y el archivo, ya resuelto
(`..`, separadores y enlaces simbólicos), queda dentro de la carpeta de su tema.

T2 (RNF-07.20, RF-18.20): la descarga por ruta solo entrega un documento registrado, Procesado, confinado y, si es de
un notebook, del usuario que lo pide; todo lo demás es el mismo «no encontrado». La base y el dueño del notebook se
simulan (sin SQL Server).

T4 (RF-06.20, RF-05.20, RF-05.21): `guardar_archivo` valida tema y nombre antes de escribir, devuelve `uploads/<tema>/<nombre>`
sea cual sea la ubicación de la carpeta y no deja archivos a medias ni borra los ajenos.

Todo ocurre en una carpeta temporal (`carpeta_archivos`): nunca se toca el `uploads/` real ni se leen
archivos del servidor. Los nombres son inventados (`PRUEBA…`). Los módulos del sistema se importan dentro de
cada prueba.
"""
import asyncio
import os
from pathlib import Path
from urllib.parse import unquote

import pytest

CONTENIDO = b"PRUEBA contenido inventado"
TESTIGO = "PRUEBA_testigo.txt"


@pytest.fixture
def servicio(carpeta_archivos):
    """El servicio de archivos apuntando a la carpeta temporal (la fixture desvía y restaura `BASE_UPLOAD_DIR`)."""
    from app.services.documentos.file_management_service import file_management_service

    return file_management_service


@pytest.fixture
def testigo(carpeta_archivos) -> Path:
    """Un archivo fuera de la carpeta de documentos pero dentro de la temporal: nunca debe salir."""
    ruta = carpeta_archivos / TESTIGO
    ruta.write_bytes(CONTENIDO)
    return ruta


def _crear(servicio, tema: str, nombre: str, contenido: bytes = CONTENIDO) -> Path:
    carpeta = servicio.BASE_UPLOAD_DIR / tema
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre
    ruta.write_bytes(contenido)
    return ruta


def _instantanea(raiz: Path) -> list[str]:
    """Todo lo que hay bajo `raiz` (sin seguir enlaces), para comprobar que no se creó ni borró nada."""
    return sorted(str(p.relative_to(raiz)) for p in raiz.rglob("*"))


# --- es_nombre_seguro (RNF-07.21, casos límite B1-B7 y A12) ------------------------------------------------

# Inválidos tanto para tema como para archivo.
NO_SEGUROS = [
    pytest.param("", id="B1-vacio"),
    pytest.param("   ", id="B1-espacios"),
    pytest.param(".", id="B1-punto"),
    pytest.param("..", id="B1-dos-puntos"),
    pytest.param("...", id="B1-solo-puntos"),
    pytest.param("a/b", id="B2-separador"),
    pytest.param("a\\b", id="B2-contrabarra"),
    pytest.param("../PRUEBA", id="B2-padre-al-inicio"),
    pytest.param("PRUEBA/..", id="B2-padre-al-final"),
    pytest.param("..\\PRUEBA", id="B2-padre-contrabarra"),
    pytest.param("/PRUEBA", id="B3-absoluto-linux"),
    pytest.param("C:\\PRUEBA", id="B3-absoluto-windows"),
    pytest.param("\\\\servidor\\PRUEBA", id="B3-recurso-de-red"),
    pytest.param("PRUEBA:flujo", id="B3-dos-puntos"),
    pytest.param("PRUEBA\x00x", id="B4-nul"),
    pytest.param("PRUEBA\nx", id="B4-salto-de-linea"),
    pytest.param("PRUEBA\tx", id="B4-tabulacion"),
    pytest.param("PRUEBA\x1bx", id="B4-escape"),
    pytest.param("PRUEBA\x7fx", id="B4-supr"),
    pytest.param("PRUEBA ", id="B5-espacio-final"),
    pytest.param("PRUEBA.", id="B5-punto-final"),
    pytest.param("CON", id="B5-reservado-con"),
    pytest.param("con", id="B5-reservado-minusculas"),
    pytest.param("Prn.txt", id="B5-reservado-con-extension"),
    pytest.param("AUX", id="B5-reservado-aux"),
    pytest.param("NUL.tar.gz", id="B5-reservado-varias-extensiones"),
    pytest.param("COM1", id="B5-reservado-com1"),
    pytest.param("com9.pdf", id="B5-reservado-com9"),
    pytest.param("LPT1", id="B5-reservado-lpt1"),
    pytest.param("lpt9.txt", id="B5-reservado-lpt9"),
]

# Válidos tanto para tema como para archivo (A12: tildes, ñ, espacios intermedios, paréntesis, guiones, sufijo).
SEGUROS = [
    pytest.param("PRUEBA", id="simple"),
    pytest.param("PRUEBA-TEMA_1", id="guiones"),
    pytest.param("NB-5", id="clave-de-notebook"),
    pytest.param("PRUEBA tema con espacios", id="espacios-intermedios"),
    pytest.param("Resolución Nº 5 – ñandú (copia)", id="tildes-ñ-y-parentesis"),
    pytest.param("informe final (copia) año 2026_1.pdf", id="A12-nombre-legitimo"),
    pytest.param("PRUEBA_contrato.pdf", id="con-extension"),
    pytest.param("informe..final", id="dos-puntos-no-son-componente"),
    pytest.param(".oculto", id="empieza-por-punto"),
    pytest.param("CONSOLA", id="empieza-como-reservado"),
    pytest.param("COM10", id="com10-no-esta-reservado"),
    pytest.param("COM0.txt", id="com0-no-esta-reservado"),
]


@pytest.mark.parametrize("texto", NO_SEGUROS)
@pytest.mark.parametrize("es_tema", [True, False], ids=["tema", "archivo"])
def test_es_nombre_seguro_rechaza_los_nombres_no_seguros(texto, es_tema):
    """RNF-07.21, B1-B5: lo que no sirve como un solo nombre se rechaza, sea tema o archivo."""
    from app.services.documentos.file_management_service import es_nombre_seguro

    assert es_nombre_seguro(texto, es_tema) is False


@pytest.mark.parametrize("texto", SEGUROS)
@pytest.mark.parametrize("es_tema", [True, False], ids=["tema", "archivo"])
def test_es_nombre_seguro_acepta_los_nombres_legitimos(texto, es_tema):
    """RNF-07.21, A12: tildes, ñ, espacios intermedios, paréntesis y guiones valen."""
    from app.services.documentos.file_management_service import es_nombre_seguro

    assert es_nombre_seguro(texto, es_tema) is True


def test_es_nombre_seguro_limite_del_tema_en_caracteres():
    """RNF-07.21, B6: el tema admite hasta 60 caracteres (no bytes); 61 se rechaza."""
    from app.services.documentos.file_management_service import es_nombre_seguro

    assert es_nombre_seguro("a" * 60, True) is True
    assert es_nombre_seguro("ñ" * 60, True) is True
    assert es_nombre_seguro("a" * 61, True) is False
    assert es_nombre_seguro("ñ" * 61, True) is False


def test_es_nombre_seguro_limite_del_archivo_en_bytes():
    """RNF-07.21, B6: el archivo admite hasta 255 bytes en UTF-8; las tildes y la ñ ocupan 2."""
    from app.services.documentos.file_management_service import es_nombre_seguro

    assert es_nombre_seguro("a" * 255, False) is True
    assert es_nombre_seguro("a" * 256, False) is False
    justo = "á" * 127 + "a"                      # 254 + 1 = 255 bytes, 128 caracteres
    assert len(justo.encode("utf-8")) == 255 and es_nombre_seguro(justo, False) is True
    pasado = "á" * 128                           # 256 bytes, solo 128 caracteres
    assert len(pasado.encode("utf-8")) == 256 and es_nombre_seguro(pasado, False) is False
    # 200 caracteres con ñ (400 bytes) pasarían un límite en caracteres y no el de bytes.
    assert es_nombre_seguro("ñ" * 200, False) is False
    # El límite en bytes no se aplica al tema (60 caracteres) ni al revés.
    assert es_nombre_seguro("a" * 100, True) is False


@pytest.mark.parametrize("tema", ["profiles", "PROFILES", "Profiles", "pRoFiLeS"])
def test_es_nombre_seguro_reserva_la_carpeta_de_avatares_como_tema(tema):
    """RNF-07.21, B7: `profiles` en cualquier grafía no es un tema válido (D4-A), pero sí un nombre de archivo."""
    from app.services.documentos.file_management_service import es_nombre_seguro

    assert es_nombre_seguro(tema, True) is False
    assert es_nombre_seguro(tema, False) is True


def test_es_nombre_seguro_no_reserva_nombres_parecidos_a_la_carpeta_de_avatares():
    """B7: solo el nombre exacto está reservado; `profiles_2` o `mis profiles` siguen siendo temas."""
    from app.services.documentos.file_management_service import es_nombre_seguro

    assert es_nombre_seguro("profiles_2", True) is True
    assert es_nombre_seguro("mis profiles", True) is True


def test_la_carpeta_reservada_sale_de_la_constante_de_produccion():
    """Decisión 6 del plan: se reserva el nombre de la carpeta de avatares de producción, no el de la suite."""
    from app.constants.avatar_constants import AVATAR_UPLOAD_DIR
    from app.services.documentos import file_management_service as fms

    assert fms.CARPETA_AVATARES == Path(AVATAR_UPLOAD_DIR).name == "profiles"


# --- obtener_ruta_archivo confinada (RNF-07.21, A5, A9, A12) ------------------------------------------------

def test_obtener_ruta_archivo_confinada_entrega_un_documento_legitimo(servicio):
    """RNF-07.21, A12 (camino feliz): nombres con espacios, tildes, ñ, paréntesis y sufijo se entregan completos."""
    nombres = ["PRUEBA_contrato.pdf", "informe final (copia) año 2026_1.pdf", "Resolución ñandú.docx"]
    for nombre in nombres:
        creada = _crear(servicio, "PRUEBA tema (año)", nombre)
        assert servicio.obtener_ruta_archivo("PRUEBA tema (año)", nombre) == creada.resolve()


def test_obtener_ruta_archivo_confinada_no_existente_devuelve_none(servicio):
    """RNF-07.21: lo que no existe, o es una carpeta, no es un documento."""
    _crear(servicio, "PRUEBA", "PRUEBA_a.txt")
    (servicio.BASE_UPLOAD_DIR / "PRUEBA" / "subcarpeta").mkdir()
    assert servicio.obtener_ruta_archivo("PRUEBA", "no_existe.txt") is None
    assert servicio.obtener_ruta_archivo("TEMA_INEXISTENTE", "PRUEBA_a.txt") is None
    assert servicio.obtener_ruta_archivo("PRUEBA", "subcarpeta") is None
    assert servicio.obtener_ruta_archivo("PRUEBA", "PRUEBA_a.txt") is not None


@pytest.mark.parametrize("tema, nombre", [
    pytest.param("PRUEBA", f"../../{TESTIGO}", id="A1-nombre-con-padre"),
    pytest.param("PRUEBA", f"..{os.sep}..{os.sep}{TESTIGO}", id="A1-nombre-con-padre-y-separador"),
    pytest.param("..", TESTIGO, id="A1-tema-padre"),
    pytest.param("../", TESTIGO, id="A1-tema-padre-con-separador"),
    pytest.param("PRUEBA", "..\\..\\PRUEBA_testigo.txt", id="A4-contrabarra"),
    pytest.param("PRUEBA\\..", TESTIGO, id="A4-tema-con-contrabarra"),
    pytest.param("PRUEBA", "", id="A9-nombre-vacio"),
    pytest.param("", TESTIGO, id="A9-tema-vacio"),
    pytest.param("PRUEBA", "   ", id="A9-nombre-espacios"),
    pytest.param("PRUEBA", "PRUEBA_testigo\x00.txt", id="A9-nul-en-el-nombre"),
    pytest.param("PRUEBA\x00", TESTIGO, id="A9-nul-en-el-tema"),
    pytest.param("PRUEBA", "PRUEBA\ntestigo.txt", id="A9-control"),
    pytest.param("PRUEBA", unquote("PRUEBA_testigo%00.txt"), id="A9-percent00-ya-decodificado"),
    pytest.param("PRUEBA", unquote(unquote("PRUEBA_testigo%2500.txt")), id="A9-percent00-doble-decodificado"),
    pytest.param("PRUEBA", unquote("%2e%2e%2f%2e%2e%2f" + TESTIGO), id="A3-codificado-ya-decodificado"),
    pytest.param("profiles", "PRUEBA_avatar.png", id="A8-carpeta-de-avatares"),
    pytest.param("PROFILES", "PRUEBA_avatar.png", id="A8-carpeta-de-avatares-mayusculas"),
    pytest.param("CON", TESTIGO, id="B5-tema-reservado"),
    pytest.param("PRUEBA", "NUL.txt", id="B5-nombre-reservado"),
])
def test_obtener_ruta_archivo_confinada_no_devuelve_ubicaciones_no_seguras(servicio, testigo, carpeta_archivos, tema, nombre):
    """RNF-07.21: con tema o nombre no seguros no devuelve ubicación (aunque haya un archivo que sí existe) ni toca el disco."""
    _crear(servicio, "PRUEBA", "PRUEBA_a.txt")
    avatares = carpeta_archivos / "uploads" / "profiles"
    avatares.mkdir(exist_ok=True)
    (avatares / "PRUEBA_avatar.png").write_bytes(CONTENIDO)
    antes = _instantanea(carpeta_archivos)

    assert servicio.obtener_ruta_archivo(tema, nombre) is None
    assert _instantanea(carpeta_archivos) == antes
    assert testigo.read_bytes() == CONTENIDO


# Ubicaciones que el sistema de archivos SÍ puede crear con un nombre no seguro: ahí hay un archivo real, así que
# `None` se debe a la protección y no a que no exista nada. Sin `es_nombre_seguro` estas se entregarían (comprobado
# en la prueba siguiente). Quedan fuera, por no poder crearse en el sistema de archivos, y se cubren con la prueba
# directa de `es_nombre_seguro` (B1-B5): los NUL (A9-nul-*, A9-percent00-*; sin la protección, `resolve()` lanza
# ValueError y el resultado sigue siendo None), los nombres de Windows en Linux si el sistema los rechaza.
SENUELOS = [
    pytest.param("PRUEBA", "   ", id="A9-nombre-espacios"),
    pytest.param("PRUEBA", "PRUEBA\ntestigo.txt", id="A9-control"),
    pytest.param("CON", TESTIGO, id="B5-tema-reservado"),
    pytest.param("PRUEBA", "NUL.txt", id="B5-nombre-reservado"),
    pytest.param("PROFILES", "PRUEBA_avatar.png", id="A8-carpeta-de-avatares-mayusculas"),
]


def _sembrar_senuelo(servicio, tema: str, nombre: str) -> Path:
    """Crea el archivo real en la ubicación no segura; si el sistema de archivos no la admite, omite la prueba."""
    try:
        return _crear(servicio, tema, nombre)
    except (OSError, ValueError) as error:
        pytest.skip(f"El sistema de archivos no admite crear esa ubicación: {type(error).__name__}")


@pytest.mark.parametrize("tema, nombre", SENUELOS)
def test_obtener_ruta_archivo_confinada_rechaza_un_archivo_real_en_ubicacion_no_segura(servicio, tema, nombre):
    """RNF-07.21, A8, A9, B5: con un archivo real en la ubicación no segura, el `None` es por la protección."""
    _sembrar_senuelo(servicio, tema, nombre)

    assert servicio.obtener_ruta_archivo(tema, nombre) is None


@pytest.mark.parametrize("tema, nombre", SENUELOS)
def test_el_senuelo_se_entrega_sin_la_proteccion_de_nombres(servicio, monkeypatch, tema, nombre):
    """Verifica la prueba anterior: sin `es_nombre_seguro` (desactivada solo aquí) el archivo real SÍ se entrega,
    así que esa prueba falla cuando la protección falta."""
    from app.services.documentos import file_management_service as fms

    creada = _sembrar_senuelo(servicio, tema, nombre)
    monkeypatch.setattr(fms, "es_nombre_seguro", lambda texto, es_tema: True)

    assert servicio.obtener_ruta_archivo(tema, nombre) == creada.resolve()


def test_obtener_ruta_archivo_confinada_con_enlace_dentro_del_tema_que_sale(servicio, testigo):
    """RNF-07.21, A5: un enlace simbólico dentro de la carpeta del tema que apunta fuera no se entrega."""
    carpeta = servicio.BASE_UPLOAD_DIR / "PRUEBA"
    carpeta.mkdir()
    try:
        (carpeta / "PRUEBA_enlace.txt").symlink_to(testigo)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"No se pueden crear enlaces simbólicos aquí: {type(error).__name__}")

    assert (carpeta / "PRUEBA_enlace.txt").read_bytes() == CONTENIDO       # el enlace funciona: sin confinar saldría
    assert servicio.obtener_ruta_archivo("PRUEBA", "PRUEBA_enlace.txt") is None


def test_obtener_ruta_archivo_confinada_con_carpeta_de_tema_enlazada_fuera(servicio, carpeta_archivos, testigo):
    """RNF-07.21, A5: si la carpeta del tema es un enlace a algo fuera de la carpeta de documentos, tampoco se entrega."""
    fuera = carpeta_archivos / "PRUEBA_fuera"
    fuera.mkdir()
    (fuera / "PRUEBA_secreto.txt").write_bytes(CONTENIDO)
    try:
        (servicio.BASE_UPLOAD_DIR / "PRUEBA").symlink_to(fuera, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"No se pueden crear enlaces simbólicos aquí: {type(error).__name__}")

    assert (servicio.BASE_UPLOAD_DIR / "PRUEBA" / "PRUEBA_secreto.txt").read_bytes() == CONTENIDO
    assert servicio.obtener_ruta_archivo("PRUEBA", "PRUEBA_secreto.txt") is None


def test_obtener_ruta_archivo_confinada_con_enlace_dentro_del_tema_que_no_sale(servicio):
    """RNF-07.21: un enlace que apunta a otro archivo del mismo tema sigue dentro de la carpeta y se entrega."""
    original = _crear(servicio, "PRUEBA", "PRUEBA_original.txt")
    try:
        (original.parent / "PRUEBA_alias.txt").symlink_to(original)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"No se pueden crear enlaces simbólicos aquí: {type(error).__name__}")

    assert servicio.obtener_ruta_archivo("PRUEBA", "PRUEBA_alias.txt") == original.resolve()


# --- obtener_documento_por_ruta (RNF-07.20, RF-18.20, casos A1-A12) ----------------------------------------------

USUARIO = "PRUEBA000001"
OTRO_USUARIO = "PRUEBA000002"


@pytest.fixture
def base_simulada(monkeypatch):
    """Sustituye la consulta «¿está Procesado?» y la pertenencia del notebook por una base inventada.

    `procesados` guarda (tema en minúsculas, nombre): SQL Server compara sin distinguir mayúsculas, y el simulado
    debe hacer lo mismo, porque `nb-5` y `NB-5` son el mismo tema para la base. `notebooks` va de id a dueño.
    """
    from app.repositories.documento_repository import DocumentoRepository
    from app.services.notebook_service import NotebookService

    base = {"procesados": set(), "notebooks": {}}

    def _procesado(self, db, expediente_numero, nombre_archivo):
        return (expediente_numero.casefold(), nombre_archivo) in base["procesados"]

    async def _dueno(self, db, notebook_id, usuario_id):
        return object() if base["notebooks"].get(notebook_id) == usuario_id else None

    monkeypatch.setattr(DocumentoRepository, "verificar_esta_procesado", _procesado)
    monkeypatch.setattr(NotebookService, "obtener_notebook_de_usuario", _dueno)
    return base


def _registrar(servicio, base, tema, nombre, procesado=True):
    """Crea el archivo en la carpeta temporal y, si `procesado`, lo da de alta en la base simulada."""
    ruta = _crear(servicio, tema, nombre)
    if procesado:
        base["procesados"].add((tema.casefold(), nombre))
    return ruta


def _pedir(servicio, ruta, usuario=USUARIO):
    return asyncio.run(servicio.obtener_documento_por_ruta(None, ruta, usuario))


@pytest.fixture
def escenario(servicio, base_simulada, testigo, carpeta_archivos):
    """Un tema `PRUEBA` con un documento Procesado, otro sin registrar y otro registrado pero no Procesado; un
    avatar y los documentos de dos notebooks: el 5 es de otro usuario y el 7 es del que pide."""
    base_simulada["notebooks"] = {5: OTRO_USUARIO, 7: USUARIO}
    _registrar(servicio, base_simulada, "PRUEBA", "PRUEBA_a.txt")
    _registrar(servicio, base_simulada, "PRUEBA", "PRUEBA_noregistrado.txt", procesado=False)
    _registrar(servicio, base_simulada, "PRUEBA", "PRUEBA_pendiente.txt", procesado=False)
    _registrar(servicio, base_simulada, "PRUEBA_otro_tema", "PRUEBA_a.txt", procesado=False)
    (servicio.BASE_UPLOAD_DIR / "PRUEBA" / "subcarpeta").mkdir()
    _registrar(servicio, base_simulada, "profiles", "PRUEBA_avatar.png")
    _registrar(servicio, base_simulada, "NB-5", "PRUEBA_imagen.png")
    _registrar(servicio, base_simulada, "NB-7", "PRUEBA_imagen.png")
    return base_simulada


RUTA_NO_PERMITIDA = "ruta no permitida"
AJENO = "documento ajeno"
NO_DISPONIBLE = "documento no disponible"

# La ruta llega ya decodificada (la ruta del API decodifica una vez más, D9); `unquote` reproduce esa segunda vuelta.
RECHAZADAS = [
    pytest.param(f"uploads/../{TESTIGO}", RUTA_NO_PERMITIDA, id="A1-padre-tras-el-prefijo"),
    pytest.param(f"uploads/PRUEBA/../../{TESTIGO}", RUTA_NO_PERMITIDA, id="A1-padre-en-medio"),
    pytest.param("uploads/PRUEBA/..", RUTA_NO_PERMITIDA, id="A1-padre-al-final"),
    pytest.param("../uploads/PRUEBA/PRUEBA_a.txt", RUTA_NO_PERMITIDA, id="A1-padre-al-inicio"),
    pytest.param("/etc/passwd", RUTA_NO_PERMITIDA, id="A2-absoluta-linux"),
    pytest.param("C:\\Windows\\win.ini", RUTA_NO_PERMITIDA, id="A2-absoluta-windows"),
    pytest.param("\\\\servidor\\recurso\\PRUEBA_a.txt", RUTA_NO_PERMITIDA, id="A2-recurso-de-red"),
    pytest.param("/uploads/PRUEBA/PRUEBA_a.txt", RUTA_NO_PERMITIDA, id="A2-empieza-por-separador"),
    pytest.param(unquote("uploads/%2e%2e/" + TESTIGO), RUTA_NO_PERMITIDA, id="A3-codificada-una-vez"),
    pytest.param(unquote(unquote("uploads/%252e%252e/" + TESTIGO)), RUTA_NO_PERMITIDA, id="A3-codificada-dos-veces"),
    pytest.param(unquote("uploads/%2E%2E%5CPRUEBA/PRUEBA_a.txt"), RUTA_NO_PERMITIDA, id="A3-mayusculas-y-contrabarra"),
    pytest.param("uploads\\PRUEBA\\PRUEBA_a.txt", RUTA_NO_PERMITIDA, id="A4-solo-contrabarras"),
    pytest.param("uploads/PRUEBA\\..\\PRUEBA_a.txt", RUTA_NO_PERMITIDA, id="A4-mezcladas"),
    pytest.param("uploads", RUTA_NO_PERMITIDA, id="A6-carpeta-de-documentos"),
    pytest.param("uploads/", RUTA_NO_PERMITIDA, id="A6-carpeta-de-documentos-con-separador"),
    pytest.param("uploads/PRUEBA", RUTA_NO_PERMITIDA, id="A6-carpeta-de-un-tema"),
    pytest.param("uploads/PRUEBA/", RUTA_NO_PERMITIDA, id="A6-carpeta-de-un-tema-con-separador"),
    pytest.param("uploads/PRUEBA/subcarpeta", NO_DISPONIBLE, id="A6-subcarpeta-no-registrada"),
    pytest.param("uploads/PRUEBA/PRUEBA_noregistrado.txt", NO_DISPONIBLE, id="A7-archivo-no-registrado"),
    pytest.param("uploads/PRUEBA_otro_tema/PRUEBA_a.txt", NO_DISPONIBLE, id="A7-registrado-en-otro-tema"),
    pytest.param("uploads/PRUEBA/PRUEBA_inexistente.txt", NO_DISPONIBLE, id="A7-ni-registrado-ni-en-disco"),
    pytest.param("uploads/profiles/PRUEBA_avatar.png", RUTA_NO_PERMITIDA, id="A8-avatar"),
    pytest.param("uploads/PROFILES/PRUEBA_avatar.png", RUTA_NO_PERMITIDA, id="A8-avatar-mayusculas"),
    pytest.param("", RUTA_NO_PERMITIDA, id="A9-vacia"),
    pytest.param("   ", RUTA_NO_PERMITIDA, id="A9-espacios"),
    pytest.param("uploads/PRUEBA/\x00", RUTA_NO_PERMITIDA, id="A9-nul-solo"),
    pytest.param("uploads/PRUEBA/PRUEBA_a\x00.txt", RUTA_NO_PERMITIDA, id="A9-nul-en-el-nombre"),
    pytest.param(unquote("uploads/PRUEBA/PRUEBA_a%00.txt"), RUTA_NO_PERMITIDA, id="A9-percent00"),
    pytest.param("uploads/PRUEBA/PRUEBA\na.txt", RUTA_NO_PERMITIDA, id="A9-control"),
    pytest.param("uploads/PRUEBA/PRUEBA_a.txt/otro", RUTA_NO_PERMITIDA, id="partes-de-mas"),
    pytest.param("PRUEBA/PRUEBA_a.txt", RUTA_NO_PERMITIDA, id="sin-el-prefijo-uploads"),
    pytest.param("Uploads/PRUEBA/PRUEBA_a.txt", RUTA_NO_PERMITIDA, id="prefijo-en-mayusculas"),
    pytest.param("uploads/NB-5/PRUEBA_imagen.png", AJENO, id="A10-notebook-ajeno-NB"),
    pytest.param("uploads/nb-5/PRUEBA_imagen.png", AJENO, id="A10-notebook-ajeno-nb"),
    pytest.param("uploads/Nb-5/PRUEBA_imagen.png", AJENO, id="A10-notebook-ajeno-Nb"),
    pytest.param("uploads/nB-5/PRUEBA_imagen.png", AJENO, id="A10-notebook-ajeno-nB"),
    pytest.param("uploads/NB-999/PRUEBA_imagen.png", AJENO, id="A10-notebook-inexistente"),
    pytest.param("uploads/nb-999/PRUEBA_imagen.png", AJENO, id="A10-notebook-inexistente-minusculas"),
    # Decisión 13 (14/10/2026): un id mayor que 2^63-1 no es una clave canónica, así que es «ruta no permitida» (antes «documento ajeno»).
    pytest.param("uploads/NB-99999999999999999999/PRUEBA_imagen.png", RUTA_NO_PERMITIDA, id="A10-notebook-con-id-fuera-de-rango"),
    pytest.param("uploads/PRUEBA/PRUEBA_pendiente.txt", NO_DISPONIBLE, id="A11-registrado-no-procesado"),
]


@pytest.mark.parametrize("ruta, motivo", RECHAZADAS)
def test_obtener_documento_por_ruta_rechaza(servicio, escenario, testigo, carpeta_archivos, ruta, motivo):
    """RNF-07.20, RF-18.20 (A1-A11): lo que no es un documento descargable del usuario da el mismo 404 «Archivo no
    encontrado», con el motivo clasificado (sin ruta ni nombre) y sin tocar el disco."""
    from app.services.documentos.file_management_service import AccesoArchivoDenegado
    from fastapi import HTTPException

    antes = _instantanea(carpeta_archivos)

    with pytest.raises(AccesoArchivoDenegado) as error:
        _pedir(servicio, ruta)

    assert isinstance(error.value, HTTPException)
    assert (error.value.status_code, error.value.detail) == (404, "Archivo no encontrado")
    assert error.value.motivo == motivo
    assert _instantanea(carpeta_archivos) == antes
    assert testigo.read_bytes() == CONTENIDO


def test_obtener_documento_por_ruta_rechaza_un_enlace_que_sale_de_la_carpeta(servicio, escenario, testigo):
    """RNF-07.20, A5: un documento registrado y Procesado cuyo archivo es un enlace hacia fuera no se entrega."""
    from app.services.documentos.file_management_service import AccesoArchivoDenegado

    carpeta = servicio.BASE_UPLOAD_DIR / "PRUEBA"
    try:
        (carpeta / "PRUEBA_enlace.txt").symlink_to(testigo)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"No se pueden crear enlaces simbólicos aquí: {type(error).__name__}")
    escenario["procesados"].add(("prueba", "PRUEBA_enlace.txt"))

    with pytest.raises(AccesoArchivoDenegado) as error:
        _pedir(servicio, "uploads/PRUEBA/PRUEBA_enlace.txt")

    assert error.value.motivo == RUTA_NO_PERMITIDA


def test_enlace_de_un_tema_a_la_carpeta_de_otro_tema_no_se_entrega(servicio, escenario):
    """RNF-07.21, RNF-07.20: si la carpeta de un tema es un enlace a OTRA carpeta dentro de `uploads/` (un notebook
    ajeno, `NB-5`, o `profiles`), no se entrega: la carpeta real debe llamarse igual que el tema pedido, y así la
    pertenencia (que se evalúa por el texto del tema) no se salta con un enlace."""
    from app.services.documentos.file_management_service import AccesoArchivoDenegado

    base = servicio.BASE_UPLOAD_DIR
    enlaces = [base / "PRUEBA_enlace_nb", base / "PRUEBA_enlace_avatar"]
    try:
        try:
            enlaces[0].symlink_to(base / "NB-5", target_is_directory=True)
            enlaces[1].symlink_to(base / "profiles", target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"No se pueden crear enlaces simbólicos aquí: {type(error).__name__}")
        escenario["procesados"].add(("prueba_enlace_nb", "PRUEBA_imagen.png"))
        escenario["procesados"].add(("prueba_enlace_avatar", "PRUEBA_avatar.png"))

        # Control: pedido directamente, el notebook ajeno sí se rechaza.
        with pytest.raises(AccesoArchivoDenegado):
            _pedir(servicio, "uploads/NB-5/PRUEBA_imagen.png")

        # Por el enlace, ni el archivo ajeno ni el avatar se entregan (ruta del API y función común).
        for ruta in ("uploads/PRUEBA_enlace_nb/PRUEBA_imagen.png", "uploads/PRUEBA_enlace_avatar/PRUEBA_avatar.png"):
            with pytest.raises(AccesoArchivoDenegado):
                _pedir(servicio, ruta)
        assert servicio.obtener_ruta_archivo("PRUEBA_enlace_nb", "PRUEBA_imagen.png") is None
        assert servicio.obtener_ruta_archivo("PRUEBA_enlace_avatar", "PRUEBA_avatar.png") is None
    finally:
        for enlace in enlaces:
            if enlace.is_symlink():
                enlace.unlink()


def test_obtener_documento_por_ruta_rechaza_un_registrado_que_ya_no_esta_en_disco(servicio, escenario):
    """RNF-07.20: registrado y Procesado, pero sin archivo en su carpeta, es el mismo «ruta no permitida» (no revela nada)."""
    from app.services.documentos.file_management_service import AccesoArchivoDenegado

    escenario["procesados"].add(("prueba", "PRUEBA_borrado.txt"))

    with pytest.raises(AccesoArchivoDenegado) as error:
        _pedir(servicio, "uploads/PRUEBA/PRUEBA_borrado.txt")

    assert error.value.motivo == RUTA_NO_PERMITIDA


@pytest.mark.parametrize("tema, nombre", [
    pytest.param("PRUEBA", "PRUEBA_a.txt", id="documento-simple"),
    pytest.param("NB-7", "PRUEBA_imagen.png", id="notebook-propio"),
])
def test_obtener_documento_por_ruta_entrega_el_documento_legitimo(servicio, escenario, tema, nombre):
    """RF-12.20, RF-18.20 (control): el documento registrado, Procesado y propio sí se entrega, ya resuelto."""
    assert _pedir(servicio, f"uploads/{tema}/{nombre}") == (servicio.BASE_UPLOAD_DIR / tema / nombre).resolve()


def test_obtener_documento_por_ruta_entrega_los_nombres_legitimos_de_los_documentos(servicio, base_simulada):
    """RF-12.20, A12: espacios, tildes, ñ, paréntesis y el sufijo `_1` de un nombre repetido llegan completos."""
    tema = "PRUEBA Resolución Nº 5 (año 2026)"
    nombres = ["PRUEBA informe final (copia) año 2026.pdf", "PRUEBA Resolución ñandú.docx", "PRUEBA_contrato_1.pdf"]
    for nombre in nombres:
        creada = _registrar(servicio, base_simulada, tema, nombre)
        assert _pedir(servicio, f"uploads/{tema}/{nombre}") == creada.resolve()


# --- Claves `NB-` canónicas (T3, plan §8 decisión 13) ----------------------------------------------------------------

@pytest.mark.parametrize("tema", [
    pytest.param("NB-0005", id="ceros-a-la-izquierda"),
    pytest.param("nb-0005", id="ceros-a-la-izquierda-minusculas"),
    pytest.param("NB-٥", id="digito-arabe"),
    pytest.param("NB-５", id="digito-de-ancho-completo"),
    pytest.param("NB-5x", id="sufijo"),
    pytest.param("NB-5 ", id="espacio-final"),
    pytest.param("NB-", id="sin-digitos"),
    pytest.param("NB-0", id="cero"),
    pytest.param("NB--5", id="signo"),
    pytest.param("NB-9223372036854775808", id="2-a-la-63"),
])
def test_clave_nb_no_canonica_se_rechaza(servicio, base_simulada, monkeypatch, tema):
    """RF-18.20, decisión 13: todo tema que empieza por `nb-` y no es `NB-` + dígitos ASCII sin cero inicial y ≤ 2^63-1
    da «ruta no permitida» y NO consulta la base (ni la pertenencia ni el estado): no hay alias de `NB-5`."""
    from app.repositories.documento_repository import DocumentoRepository
    from app.services.documentos.file_management_service import AccesoArchivoDenegado
    from app.services.notebook_service import NotebookService

    consultas = []

    async def _dueno(self, db, notebook_id, usuario_id):
        consultas.append(("notebook", notebook_id))

    def _procesado(self, db, tema_pedido, nombre):
        consultas.append(("procesado", tema_pedido))
        return True

    monkeypatch.setattr(NotebookService, "obtener_notebook_de_usuario", _dueno)
    monkeypatch.setattr(DocumentoRepository, "verificar_esta_procesado", _procesado)

    with pytest.raises(AccesoArchivoDenegado) as error:
        _pedir(servicio, f"uploads/{tema}/PRUEBA_imagen.png")

    assert error.value.motivo == RUTA_NO_PERMITIDA
    assert consultas == []


@pytest.mark.parametrize("tema", ["NB-9223372036854775807", "nb-9223372036854775807", "NB-5", "nb-5", "Nb-5"])
def test_clave_nb_limite_y_minusculas(servicio, escenario, tema):
    """RF-18.20, decisión 13: el mayor id posible (2^63-1) y `nb-5` se tratan como cualquier notebook: ajeno o
    inexistente da «documento ajeno» (`nb-5` es el mismo notebook que `NB-5`, que es de otro usuario)."""
    from app.services.documentos.file_management_service import AccesoArchivoDenegado

    with pytest.raises(AccesoArchivoDenegado) as error:
        _pedir(servicio, f"uploads/{tema}/PRUEBA_imagen.png")

    assert error.value.motivo == AJENO


def test_clave_nb_propia_en_mayusculas_se_entrega(servicio, escenario):
    """RF-18.20 (control de la decisión 13): `NB-7` (del usuario que pide) se entrega; la clave canónica no se rechaza."""
    assert _pedir(servicio, "uploads/NB-7/PRUEBA_imagen.png") == (servicio.BASE_UPLOAD_DIR / "NB-7" / "PRUEBA_imagen.png").resolve()


def test_sin_control_quita_nul_y_caracteres_de_control():
    """RNF-07.24: lo que se registra de una descarga o carga exitosa no lleva NUL ni caracteres de control; el resto
    del texto (tildes, ñ, espacios) queda igual."""
    from app.services.documentos.file_management_service import _sin_control

    assert _sin_control("PRUEBA Resolución ñandú (1).pdf") == "PRUEBA Resolución ñandú (1).pdf"
    assert _sin_control("PRUEBA\x00_a\n.txt\r\x1b\x7f\x85") == "PRUEBA_a.txt"
    assert _sin_control("") == ""


# --- T4: guardar_archivo (RF-06.20, RF-05.20, RF-05.21) ---------------------------------------------------------

def _subir(servicio, nombre: str, tema: str, contenido: bytes = CONTENIDO):
    import io

    from fastapi import UploadFile

    archivo = UploadFile(file=io.BytesIO(contenido), filename=nombre)
    return asyncio.run(servicio.guardar_archivo(archivo, tema))


@pytest.mark.parametrize("tema, nombre, mensaje", [
    ("../PRUEBA", "PRUEBA_a.txt", "El tema indicado no es válido"),
    ("profiles", "PRUEBA_a.txt", "El tema indicado no es válido"),
    ("PRUEBA tema", "../PRUEBA_a.txt", "Nombre de archivo no válido"),
    ("PRUEBA tema", "", "Nombre de archivo no válido"),
    ("PRUEBA tema", "ñ" * 128 + ".txt", "Nombre de archivo no válido"),
])
def test_guardar_archivo_rechaza_tema_o_nombre_no_validos_sin_escribir(servicio, carpeta_archivos, tema, nombre, mensaje):
    """RF-06.20 y RF-05.20: con un tema o un nombre no válidos, el servicio responde 400 con el aviso genérico (sin repetir lo
    pedido) y no crea ni carpeta ni archivo."""
    from fastapi import HTTPException

    antes = _instantanea(carpeta_archivos)
    with pytest.raises(HTTPException) as error:
        _subir(servicio, nombre, tema)
    assert (error.value.status_code, error.value.detail) == (400, mensaje)
    assert _instantanea(carpeta_archivos) == antes


def test_guardar_archivo_devuelve_la_ruta_del_documento_sea_cual_sea_la_ubicacion(servicio):
    """RF-05.21 (B9): la carpeta de documentos está fuera de `/app` y aun así la ruta es `uploads/<tema>/<nombre>`."""
    resultado = _subir(servicio, "PRUEBA año (1).txt", "PRUEBA tema")
    assert resultado["relative_path"] == "uploads/PRUEBA tema/PRUEBA año (1).txt"
    assert Path(resultado["filepath"]).read_bytes() == CONTENIDO


def test_escritura_fallida_no_deja_archivo(servicio, monkeypatch):
    """RF-05.21 (b, B10): una escritura que falla a mitad no deja el archivo a medias y el error no lleva rutas ni el
    texto de la excepción: 500 «No se pudo guardar el archivo»."""
    from fastapi import HTTPException

    from app.services.documentos import file_management_service as modulo

    abrir = open

    class _Archivo:
        def __init__(self, real):
            self._real = real

        def write(self, datos):
            self._real.write(datos[: len(datos) // 2])
            self._real.flush()
            raise OSError("disco lleno en /srv/PRUEBA_interna/secreto.txt")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self._real.close()
            return False

    monkeypatch.setattr(modulo, "open", lambda *a, **k: _Archivo(abrir(*a, **k)), raising=False)
    with pytest.raises(HTTPException) as error:
        _subir(servicio, "PRUEBA_a.txt", "PRUEBA tema")

    assert (error.value.status_code, error.value.detail) == (500, "No se pudo guardar el archivo")
    assert list((servicio.BASE_UPLOAD_DIR / "PRUEBA tema").iterdir()) == []


def test_choque_de_nombre_no_sobrescribe_ni_borra_el_archivo_ajeno(servicio, monkeypatch):
    """RF-05.21 (D5): si el nombre único aparece ocupado entre el cálculo y la escritura, la escritura no sobrescribe
    (modo exclusivo), se trata como fallo y el archivo ajeno queda intacto."""
    from fastapi import HTTPException

    existente = _crear(servicio, "PRUEBA tema", "PRUEBA_a.txt", b"PRUEBA ajeno")
    monkeypatch.setattr(servicio, "_get_unique_filename", lambda carpeta, nombre: nombre)

    with pytest.raises(HTTPException) as error:
        _subir(servicio, "PRUEBA_a.txt", "PRUEBA tema")

    assert (error.value.status_code, error.value.detail) == (500, "No se pudo guardar el archivo")
    assert existente.read_bytes() == b"PRUEBA ajeno"


# --- T5 (RNF-07.22): ninguna ruta publica la carpeta de documentos ------------------------------------------------

def test_ningun_montaje_publica_la_carpeta_de_documentos():
    """RNF-07.22 (a): la aplicación no monta `StaticFiles` ni expone otra ruta bajo `/uploads` salvo la de avatares.

    Hoy `main.py` monta `uploads/` entero en `/uploads`, sin sesión: cualquier documento cargado sería público.
    """
    import contextlib

    from starlette.staticfiles import StaticFiles

    with contextlib.chdir(Path(__file__).resolve().parents[2]):
        import main

    montajes_estaticos = [
        ruta.path for ruta in main.app.routes if isinstance(getattr(ruta, "app", None), StaticFiles)
    ]
    assert montajes_estaticos == [], f"Montajes estáticos que publican archivos sin sesión: {montajes_estaticos}"

    bajo_uploads = [
        ruta.path for ruta in main.app.routes
        if getattr(ruta, "path", "").startswith("/uploads") and not ruta.path.startswith("/uploads/profiles/")
    ]
    assert bajo_uploads == [], f"Rutas públicas bajo /uploads distintas de la de avatares: {bajo_uploads}"
