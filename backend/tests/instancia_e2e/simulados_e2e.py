"""Piezas simuladas de la instancia de extremo a extremo (spec 005a, RA-02.49 y RNF-09.40).

Instala los cuatro simulados de la spec 002 (Ollama, HTR, audio y correo) como los fixtures de pytest, pero sin pytest como
ejecutor, y el vigilante que apaga la instancia si nadie la usa. Desde la T3, la limpieza total del entorno aislado y el
conteo de residuos (RA-02.42): como la base nace vacía y es solo de la suite, vale borrar todo lo que no sea un catálogo ni
el administrador sembrado. Desde la T5, la recuperación (código del correo, almacén temporal controlable) y las filas de
bitácora de cada tipo. Desde la T6, el motor programable (cita, secuencia, retención, fallo), la ingesta en el proceso (con
fallos y retenciones por nombre de archivo) y las retenciones de la vista previa y de la eliminación de un documento de un
notebook. No importa `app` al cargarse: lo hace dentro de las funciones.
"""
import asyncio
import itertools
import logging
import re
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import pytest

from tests.instancia_e2e.configuracion import CARPETA_E2E
from tests.soporte import simulados
from tests.soporte.nombres import NOMBRE_PRUEBAS_E2E
from tests.soporte.proteccion import AbortoPruebas, exigir_nombre_pruebas, nombre_activo

logger = logging.getLogger(__name__)

# Sin peticiones al control durante este tiempo, la instancia se apaga sola (plan-005a, §3).
LIMITE_INACTIVIDAD_SEGUNDOS = 15 * 60


class RegistroContrasenas:
    """Las contraseñas que la instancia recibió, solo en memoria (RA-02.43).

    Al apagarse, la instancia cuenta cuántas veces aparecen en su propio registro y devuelve solo ese número: nunca las
    escribe ni las devuelve.
    """

    def __init__(self):
        self._valores = set()
        self._candado = threading.Lock()

    def recordar(self, contrasena: str) -> None:
        if contrasena:
            with self._candado:
                self._valores.add(contrasena)

    def contar_en(self, texto: str) -> int:
        with self._candado:
            valores = list(self._valores)
        return sum(texto.count(valor) for valor in valores)


class Vigilante:
    """Apaga la instancia cuando pasa `limite_segundos` sin que nadie llame al control.

    Cada petición al control llama a `tocar`. El reloj se inyecta para probarlo con tiempo simulado.
    """

    def __init__(self, limite_segundos: float = LIMITE_INACTIVIDAD_SEGUNDOS, reloj: Callable[[], float] = time.monotonic):
        self.limite = limite_segundos
        self._reloj = reloj
        self._ultimo = reloj()
        self._apagado = False
        self._parar = threading.Event()

    def tocar(self) -> None:
        self._ultimo = self._reloj()

    def vencido(self) -> bool:
        return self._reloj() - self._ultimo >= self.limite

    def revisar(self, apagar: Callable[[], None]) -> bool:
        """Si el plazo venció y todavía no se apagó, llama a `apagar` una sola vez y devuelve True."""
        if self._apagado or not self.vencido():
            return False
        self._apagado = True
        apagar()
        return True

    def iniciar(self, apagar: Callable[[], None], intervalo: float = 5.0) -> threading.Thread:
        """Revisa cada `intervalo` segundos en un hilo que no impide cerrar el proceso."""
        def vigilar() -> None:
            while not self._parar.wait(intervalo):
                if self.revisar(apagar):
                    return

        hilo = threading.Thread(target=vigilar, name="vigilante-e2e", daemon=True)
        hilo.start()
        return hilo

    def detener(self) -> None:
        self._parar.set()


def instalar_simulados() -> Dict[str, object]:
    """Reemplaza Ollama, HTR, audio y correo por sus simulados en todo el sistema y comprueba que quedaron activos.

    Igual que las fixtures `ollama_simulado`, `htr_simulado`, `audio_simulado` y `correo_simulado`, con un
    `pytest.MonkeyPatch()` como objeto (no se restaura: viven mientras viva el proceso). Aborta nombrando el servicio si
    alguno no quedó simulado. Requiere la configuración ya aplicada y `app` importable.
    """
    import aiosmtplib

    from app.llm import llm_service
    from app.services.ingesta.audio_transcription.whisper_service import audio_processor
    from app.services.ingesta.htr_service import htr_service

    parches = pytest.MonkeyPatch()
    ollama = clase_motor_programable()(estado=EstadoMotor())  # el LLM simulado de la suite, más el control del motor (T6)
    parches.setattr(llm_service, "_llm", ollama)

    htr = simulados.HTRSimulado()
    parches.setattr(htr_service, "extract_text", htr.extract_text)
    parches.setattr(htr_service, "is_available", htr.is_available)

    audio = simulados.AudioSimulado(audio_processor)
    parches.setattr(audio_processor, "_load_faster_whisper_model", audio.cargar_modelo)
    parches.setattr(audio_processor, "direct_strategy", audio.estrategia_directa)
    parches.setattr(audio_processor, "chunking_strategy", audio.estrategia_por_trozos)

    correo = simulados.CorreoSimulado()
    parches.setattr(aiosmtplib, "send", correo.enviar)

    simulados.comprobar_simulados()
    return {"parches": parches, "ollama": ollama, "htr": htr, "audio": audio, "correo": correo}


def estado_de_simulados() -> Dict[str, bool]:
    """Para cada servicio simulable, si el sistema usa hoy el simulado (no abre ninguna conexión)."""
    activos = {}
    for nombre in ("ollama", "htr", "audio", "correo"):
        try:
            simulados.comprobar_simulados([nombre])
            activos[nombre] = True
        except simulados.AbortoPruebas:
            activos[nombre] = False
    return activos


# --- Limpieza total y residuos (spec 005a, T3, RA-02.42) -------------------------------------------------------------

# Tablas con datos de la aplicación, en el orden de borrado por claves foráneas (lo que apunta a un usuario, un tema o un
# documento se borra antes que ellos). Los catálogos (roles, estados, estados de procesamiento, tipos de acción) no figuran.
TABLAS_DE_DATOS = ("T_Bitacora", "T_Notebook", "T_Expediente_Documento", "T_Documento", "T_Expediente", "T_Usuario")


@dataclass
class DestinoE2E:
    """Dónde limpia y cuenta la instancia. Cada parte es opcional para poder probar la lógica con falsos.

    `borrar(sentencia, parametros)` ejecuta un DELETE y `contar(sentencia, parametros)` un SELECT COUNT en la base de la
    instancia; `qdrant` es un cliente de Qdrant; `carpetas` son las carpetas de archivos y avatares (se vacían, no se
    eliminan) y deben estar dentro de `raiz_carpetas`; `usuarios_sembrados` son las cédulas que ya existían al arrancar (el
    administrador de las migraciones): ni se borran ni se cuentan como residuo.
    """

    base: Optional[str] = None
    coleccion: Optional[str] = None
    carpetas: List[Path] = field(default_factory=list)
    raiz_carpetas: Path = CARPETA_E2E
    borrar: Optional[Callable[[str, dict], int]] = None
    contar: Optional[Callable[[str, dict], int]] = None
    qdrant: object = None
    restablecer_almacen: Optional[Callable[[], None]] = None  # devuelve el almacén temporal a la normalidad (T5)
    restablecer_controles: Optional[Callable[[], None]] = None  # motor, ingesta y notebooks: suelta lo retenido y espera (T6)
    limpiar_redis: Optional[Callable[[], None]] = None
    claves_redis: Optional[Callable[[], int]] = None
    limpiar_conversaciones: Optional[Callable[[], None]] = None
    conversaciones: Optional[Callable[[], int]] = None
    vaciar_buzon: Optional[Callable[[], None]] = None
    mensajes_buzon: Optional[Callable[[], int]] = None
    usuarios_sembrados: Sequence[str] = ()
    # Una petición del navegador puede seguir en vuelo cuando se limpia (interbloqueo con el DELETE, o una fila nueva que
    # apunta a un usuario por borrar). El borrado de las tablas y de las carpetas se repite dentro de este plazo acotado.
    plazo_reintento: float = 5.0
    pausa_reintento: float = 0.2


def exigir_destino_e2e(destino: DestinoE2E) -> List[Path]:
    """Aborta, antes de tocar nada, si el destino no es el de la instancia; devuelve las carpetas resueltas.

    Exige que el nombre activo sea `servia_pruebas_e2e` (con el de pytest, la limpieza total no corre) y que la base, la
    colección y cada carpeta sean exactamente las de la instancia: ni desarrollo ni `servia_pruebas` ni `uploads/`.
    """
    if nombre_activo() != NOMBRE_PRUEBAS_E2E:
        raise AbortoPruebas(
            f"Se aborta la limpieza total: el nombre activo es {nombre_activo()!r} y solo corre en la instancia "
            f"'{NOMBRE_PRUEBAS_E2E}'. No se borró nada."
        )
    if destino.base is not None or destino.borrar is not None or destino.contar is not None:
        exigir_nombre_pruebas(destino.base, "la base de datos de la limpieza total")
    if destino.qdrant is not None or destino.coleccion is not None:
        exigir_nombre_pruebas(destino.coleccion, "la colección de Qdrant de la limpieza total")
    raiz = Path(destino.raiz_carpetas).resolve()
    if raiz.name != CARPETA_E2E.name:
        raise AbortoPruebas(
            f"Se aborta la limpieza total: la raíz de las carpetas es {str(raiz)!r}, no una carpeta '{CARPETA_E2E.name}'."
        )
    carpetas = []
    for carpeta in destino.carpetas:
        resuelta = Path(carpeta).resolve()
        if resuelta == raiz or raiz not in resuelta.parents:
            raise AbortoPruebas(
                f"Se aborta la limpieza total: la carpeta {str(carpeta)!r} no está dentro de {str(raiz)!r}. No se borró nada."
            )
        carpetas.append(resuelta)
    return carpetas


def _filtro_de_usuarios(destino: DestinoE2E) -> tuple:
    """El filtro «no es un usuario sembrado» y sus parámetros (`:s0`, `:s1`...); sin sembrados, no filtra."""
    nombres = [f"s{i}" for i in range(len(destino.usuarios_sembrados))]
    if not nombres:
        return "", {}
    return (" WHERE CN_Id_usuario NOT IN (" + ", ".join(f":{n}" for n in nombres) + ")",
            dict(zip(nombres, destino.usuarios_sembrados)))


def _filtro_de(tabla: str, destino: DestinoE2E) -> tuple:
    return _filtro_de_usuarios(destino) if tabla == "T_Usuario" else ("", {})


def _ids_de_puntos(destino: DestinoE2E) -> list:
    identificadores, desplazamiento = [], None
    while True:
        puntos, desplazamiento = destino.qdrant.scroll(
            collection_name=destino.coleccion, limit=256, offset=desplazamiento, with_payload=False, with_vectors=False
        )
        identificadores.extend(punto.id for punto in puntos)
        if desplazamiento is None:
            return identificadores


def _con_reintento(accion: Callable[[], object], destino: DestinoE2E) -> None:
    """Ejecuta la acción y, si falla, la repite cada `pausa_reintento` hasta cumplirse `plazo_reintento`; el último error sube."""
    limite = time.monotonic() + destino.plazo_reintento
    while True:
        try:
            accion()
            return
        except Exception:
            if time.monotonic() >= limite:
                raise
            time.sleep(destino.pausa_reintento)


def limpiar_todo(destino: DestinoE2E) -> None:
    """Deja el entorno aislado como recién arrancado: borra todas las filas de datos, los puntos, los archivos, Redis, las
    conversaciones en memoria y el buzón. Los catálogos y los usuarios sembrados no se tocan.

    Valida primero TODO el destino y solo después borra. Un paso que falla no impide los demás: al final se lanza un
    `AbortoPruebas` que los nombra. El borrado físico es la excepción aprobada a RN-01 solo en este entorno aislado.
    """
    carpetas = exigir_destino_e2e(destino)
    errores: List[str] = []

    def paso(nombre: str, accion: Callable[[], object]) -> None:
        try:
            accion()
        except Exception as error:
            errores.append(f"{nombre} ({type(error).__name__}: {str(error)[:200]})")

    # Primero se detiene lo que sigue trabajando (una ingesta retenida o en curso, una respuesta retenida): si no, escribiría
    # datos o archivos DESPUÉS del borrado y la prueba siguiente los heredaría.
    if destino.restablecer_controles is not None:
        paso("controles del motor, la ingesta y los notebooks", destino.restablecer_controles)
    def borrar_tablas() -> None:
        # Cada intento recorre todas las tablas en orden: si una fila nueva se coló, se borra en el intento siguiente.
        fallos = []
        for tabla in TABLAS_DE_DATOS:
            filtro, parametros = _filtro_de(tabla, destino)
            try:
                destino.borrar(f"DELETE FROM {tabla}{filtro}", parametros)
            except Exception as error:
                fallos.append(f"{tabla}: {type(error).__name__}: {str(error)[:200]}")
        if fallos:
            raise RuntimeError("; ".join(fallos))

    if destino.borrar is not None:
        paso("tablas de datos", lambda: _con_reintento(borrar_tablas, destino))
    if destino.qdrant is not None:
        def borrar_puntos() -> None:
            identificadores = _ids_de_puntos(destino)
            if identificadores:
                from qdrant_client.models import PointIdsList

                destino.qdrant.delete(
                    collection_name=destino.coleccion, points_selector=PointIdsList(points=identificadores), wait=True
                )

        paso("puntos de la colección de Qdrant", borrar_puntos)

    def vaciar_carpetas() -> None:
        for carpeta in carpetas:
            for hijo in (carpeta.iterdir() if carpeta.is_dir() else []):
                if hijo.is_dir() and not hijo.is_symlink():
                    shutil.rmtree(hijo)
                else:
                    hijo.unlink(missing_ok=True)

    paso("archivos", lambda: _con_reintento(vaciar_carpetas, destino))
    for nombre, accion in (("almacén temporal", destino.restablecer_almacen),
                           ("claves del Redis simulado", destino.limpiar_redis),
                           ("conversaciones en memoria", destino.limpiar_conversaciones),
                           ("buzón del correo simulado", destino.vaciar_buzon)):
        if accion is not None:
            paso(nombre, accion)
    if errores:
        raise AbortoPruebas("No se pudo limpiar por completo el entorno de extremo a extremo: " + "; ".join(errores))


def contar_residuos_e2e(destino: DestinoE2E) -> dict:
    """Lo que hay hoy en el entorno aislado, sin contar catálogos ni usuarios sembrados.

    Devuelve `{filas: {tabla: n}, puntos, archivos, claves_redis, conversaciones, buzon, total, texto}`; `texto` dice en
    español qué quedó (`ninguno` si nada) para nombrar la tabla cuando una prueba deja datos.
    """
    carpetas = exigir_destino_e2e(destino)
    filas: Dict[str, int] = {}
    if destino.contar is not None:
        for tabla in TABLAS_DE_DATOS:
            filtro, parametros = _filtro_de(tabla, destino)
            filas[tabla] = int(destino.contar(f"SELECT COUNT(*) FROM {tabla}{filtro}", parametros))
    puntos = int(destino.qdrant.count(collection_name=destino.coleccion, exact=True).count) if destino.qdrant is not None else 0
    archivos = sum(1 for carpeta in carpetas if carpeta.is_dir() for ruta in carpeta.rglob("*") if ruta.is_file())
    claves_redis = int(destino.claves_redis()) if destino.claves_redis is not None else 0
    conversaciones = int(destino.conversaciones()) if destino.conversaciones is not None else 0
    buzon = int(destino.mensajes_buzon()) if destino.mensajes_buzon is not None else 0
    total = sum(filas.values()) + puntos + archivos + claves_redis + conversaciones + buzon

    partes = [f"{tabla}: {n}" for tabla, n in filas.items() if n]
    for nombre, cantidad in (("puntos de Qdrant", puntos), ("archivos", archivos), ("claves de Redis", claves_redis),
                             ("conversaciones en memoria", conversaciones), ("mensajes en el buzón", buzon)):
        if cantidad:
            partes.append(f"{nombre}: {cantidad}")
    return {"filas": filas, "puntos": puntos, "archivos": archivos, "claves_redis": claves_redis,
            "conversaciones": conversaciones, "buzon": buzon, "total": total, "texto": ", ".join(partes) or "ninguno"}


def leer_usuarios_sembrados() -> tuple:
    """Las cédulas que tiene la base de la instancia recién preparada (el administrador de las migraciones)."""
    from sqlalchemy import text

    from app.db.database import engine

    exigir_nombre_pruebas(engine.url.database, "la base de datos de la instancia")
    with engine.connect() as conexion:
        return tuple(str(fila[0]) for fila in conexion.execute(text("SELECT CN_Id_usuario FROM T_Usuario")))


def _almacen_de_conversaciones():
    import sys

    modulo = sys.modules.get("app.services.RAG.session_store")
    return getattr(modulo, "conversation_store", None) if modulo is not None else None


def vaciar_conversaciones_en_memoria() -> None:
    """Quita TODAS las conversaciones del chat que hay en memoria (en esta instancia no hay datos reales)."""
    almacen = _almacen_de_conversaciones()
    if almacen is None:
        return
    for atributo in ("_store", "_metadata", "_user_sessions", "_efimeras"):
        coleccion = getattr(almacen, atributo, None)
        if isinstance(coleccion, dict):
            coleccion.clear()


def contar_conversaciones_en_memoria() -> int:
    almacen = _almacen_de_conversaciones()
    return len({*almacen._store, *almacen._metadata}) if almacen is not None else 0


def destino_de_la_instancia(carpetas: Sequence[Path], correo, usuarios_sembrados: Sequence[str], almacen=None,
                            controles=None) -> DestinoE2E:
    """El destino real de la instancia: su base, su colección, sus carpetas, el Redis simulado, el almacén controlable, el
    buzón del correo y los controles del motor, la ingesta y los notebooks."""
    import os

    import redis
    from sqlalchemy import text

    from app.db.database import engine
    from tests.soporte import entorno

    def borrar(sentencia: str, parametros: dict) -> int:
        with engine.begin() as conexion:
            return conexion.execute(text(sentencia), parametros).rowcount

    def contar(sentencia: str, parametros: dict) -> int:
        with engine.connect() as conexion:
            return conexion.execute(text(sentencia), parametros).scalar()

    servidor = simulados._estado["servidor_redis"]

    def vaciar_buzon() -> None:
        correo.intentos.clear()
        correo.tiempos_maximos.clear()
        correo._contenidos.clear()
        correo.responder_bien()  # un fallo programado también es un resto de la prueba anterior

    return DestinoE2E(
        base=engine.url.database,
        coleccion=os.environ.get("QDRANT_COLLECTION_NAME"),
        carpetas=list(carpetas),
        borrar=borrar,
        contar=contar,
        qdrant=entorno.cliente_qdrant(),
        restablecer_almacen=almacen.responder_bien if almacen is not None else None,
        restablecer_controles=controles.restablecer if controles is not None else None,
        limpiar_redis=lambda: redis.Redis().flushall(),
        claves_redis=lambda: sum(len(base) for base in servidor.dbs.values()),
        limpiar_conversaciones=vaciar_conversaciones_en_memoria,
        conversaciones=contar_conversaciones_en_memoria,
        vaciar_buzon=vaciar_buzon,
        mensajes_buzon=lambda: len(correo.intentos),
        usuarios_sembrados=tuple(usuarios_sembrados),
    )


# --- Recuperación y bitácora (spec 005a, T5, RA-02.49) -----------------------------------------------------------------

MARCADOR_DEL_CODIGO = "Tu código de verificación es:"
PATRON_DEL_CODIGO = re.compile(re.escape(MARCADOR_DEL_CODIGO) + r"\s*([0-9]{6})")


def codigo_del_correo(correo, destinatario: str) -> str:
    """El código de 6 dígitos del ÚLTIMO correo enviado a `destinatario` que trae uno (RF-03.41).

    Lee el contenido real del correo simulado. Si no hay un correo con código para esa dirección, lanza `LookupError` sin
    repetir el contenido de ningún correo. El código solo viaja en el valor devuelto: quien lo llama no debe imprimirlo.
    """
    buscado = (destinatario or "").strip().lower()
    if buscado:
        for indice in range(len(correo.intentos) - 1, -1, -1):
            contenido = correo.contenido_real(indice)
            if buscado in contenido.a.lower():
                encontrado = PATRON_DEL_CODIGO.search(contenido.texto or "")
                if encontrado:
                    return encontrado.group(1)
    raise LookupError("No hay un correo con código de verificación para ese destinatario.")


def instalar_almacen_controlable(parches: "pytest.MonkeyPatch"):
    """Hace que la recuperación hable con un Redis controlable (RA-02.11): puede dejar de responder y avanzar el tiempo.

    Es el mismo parche de la fixture `redis_controlable` de pytest, aplicado a la instancia: sin fallo programado se
    comporta igual que el Redis simulado. Requiere `app` importable y el Redis simulado ya instalado.
    """
    from app.repositories import recuperacion_estado_repository

    controlable = simulados.RedisControlable()
    parches.setattr(recuperacion_estado_repository, "obtener_cliente", lambda: controlable.cliente)
    return controlable


def almacen_no_disponible(almacen) -> bool:
    """Si el almacén temporal tiene programado un fallo (el controlable no lo expone con un método público)."""
    return getattr(almacen, "_fallo", None) is not None


# Tipos de fila de bitácora que el control sabe crear: los nueve de la carga de documentos (tabla de RF-22.1, spec 004) y los
# tres de notebooks y conversaciones (RF-21.34, spec 004b).
TIPOS_DE_BITACORA = (
    "carga_iniciada", "carga_inicio", "carga_almacenada", "carga_terminada", "carga_error", "carga_rechazada",
    "carga_cancelada", "carga_error_cancelacion", "carga_error_general",
    "crear_notebook", "quitar_documento_notebook", "gestionar_conversacion",
)

_consecutivo_de_fila = itertools.count(1)


def registrar_fila_de_bitacora(tipo: str, cedula: str, tema: Optional[str] = None) -> int:
    """Escribe una fila de bitácora del `tipo` dado, con el mismo servicio de auditoría que usa el sistema, y devuelve su id.

    `cedula` debe ser la de un usuario ya creado. El tema por omisión es un número heredado inventado (`99-NNNNNN-0001-PE`);
    en los tipos de notebook, una clave `NB-<n>`. Lanza `ValueError` si el tipo no existe y `AbortoPruebas` si el servicio
    de auditoría no pudo escribir la fila (devuelve `None` cuando falla, RF-21).
    """
    if tipo not in TIPOS_DE_BITACORA:
        raise ValueError(f"Tipo de bitácora desconocido: {tipo!r}")

    from app.constants.tipos_accion import TiposAccion
    from app.db.database import SessionLocal
    from app.services.bitacora.ingesta_audit_service import ingesta_audit_service as ingesta
    from app.services.bitacora.notebooks_audit_service import MOTIVO_CONVERSACION_NO_DISPONIBLE
    from app.services.bitacora.notebooks_audit_service import notebooks_audit_service as notebooks

    numero = next(_consecutivo_de_fila)
    tema_carga = tema or f"99-{numero:06d}-0001-PE"
    clave = tema or f"NB-{900000 + numero}"
    archivo = f"PRUEBA_documento_{numero}.pdf"
    tarea = f"PRUEBA-tarea-{numero}"
    # Un error de extracción de un servicio caído: la causa clasificada es «servicio de procesamiento no disponible».
    error_crudo = "Error extrayendo texto: connection refused (PRUEBA)"

    escritores = {
        "carga_iniciada": lambda db: ingesta.registrar_ingesta(
            db, cedula, tema_carga, "2 archivo(s)", f"{tarea},{tarea}-b", "iniciado", archivos_aceptados=2, archivos_rechazados=1),
        "carga_inicio": lambda db: ingesta.registrar_ingesta(db, cedula, tema_carga, archivo, tarea, "inicio"),
        "carga_almacenada": lambda db: ingesta.registrar_almacenamiento_vectorial(db, cedula, tema_carga, archivo, 41, 5),
        "carga_terminada": lambda db: ingesta.registrar_ingesta(
            db, cedula, tema_carga, archivo, tarea, "completado", documento_id=tarea),
        "carga_error": lambda db: ingesta.registrar_ingesta(
            db, cedula, tema_carga, archivo, tarea, "error", error_details=error_crudo),
        "carga_rechazada": lambda db: ingesta.registrar_carga_rechazada(db, cedula, "archivo vacío"),
        "carga_cancelada": lambda db: ingesta.registrar_ingesta(db, cedula, "N/A", f"Task {tarea}", tarea, "cancelado"),
        "carga_error_cancelacion": lambda db: ingesta.registrar_ingesta(
            db, cedula, "N/A", f"Task {tarea}", tarea, "error_cancelacion"),
        "carga_error_general": lambda db: ingesta.registrar_ingesta(db, cedula, tema_carga, "Error general", "N/A", "error"),
        "crear_notebook": lambda db: notebooks.registrar_creacion(db, cedula, clave),
        "quitar_documento_notebook": lambda db: notebooks.registrar_quitar(db, cedula, clave, numero, True),
        "gestionar_conversacion": lambda db: notebooks.registrar_intento_fallido(
            db, cedula, TiposAccion.GESTIONAR_CONVERSACION, MOTIVO_CONVERSACION_NO_DISPONIBLE),
    }

    async def escribir() -> int:
        with SessionLocal() as db:
            fila = await escritores[tipo](db)
            if fila is None:
                raise AbortoPruebas(f"El servicio de auditoría no pudo escribir la fila de bitácora «{tipo}».")
            return fila.CN_Id_bitacora

    return asyncio.run(escribir())


# --- Motor, ingesta y notebooks controlables (spec 005a, T6, RA-02.49) -----------------------------------------------------

# Una retención olvidada no deja colgado el servidor: pasado este plazo la espera termina sola.
PLAZO_RETENCION_SEGUNDOS = 120.0
MAXIMO_ELEMENTOS = 20
MAXIMO_TEXTO = 5000
MAXIMO_NOMBRE = 255
# Un texto que solo existe en la excepción simulada: la 005b comprueba que no llegue al usuario (RF-11.42).
TEXTO_DE_FALLO_DE_CONEXION = "PRUEBA-fallo-de-conexion-del-motor-7q3x"


class Retencion:
    """Una compuerta: mientras está cerrada, quien llama a `esperar` queda detenido hasta `liberar` o hasta el plazo.

    Sirve a varios hilos a la vez. `liberar` espera (poco) a que los detenidos salgan, para que el estado que devuelve el control
    ya diga que nadie espera.
    """

    def __init__(self, plazo: float = PLAZO_RETENCION_SEGUNDOS):
        self.plazo = plazo
        self._condicion = threading.Condition()
        self._cerrada = False
        self._esperando = 0

    @property
    def retenida(self) -> bool:
        return self._cerrada

    @property
    def esperando(self) -> int:
        return self._esperando

    def retener(self) -> None:
        with self._condicion:
            self._cerrada = True

    def liberar(self, espera: float = 2.0) -> None:
        with self._condicion:
            self._cerrada = False
            self._condicion.notify_all()
            self._condicion.wait_for(lambda: self._esperando == 0, espera)

    def esperar(self) -> bool:
        """Bloquea el hilo mientras la compuerta esté cerrada; devuelve False si lo soltó el plazo y no `liberar`."""
        with self._condicion:
            if not self._cerrada:
                return True
            self._esperando += 1
            try:
                return self._condicion.wait_for(lambda: not self._cerrada, self.plazo)
            finally:
                self._esperando -= 1
                self._condicion.notify_all()

    async def esperar_async(self) -> bool:
        """Como `esperar`, pero sin bloquear el bucle de eventos de quien la llama."""
        if not self._cerrada:
            return True
        return await asyncio.to_thread(self.esperar)


# Las dos formas en que el contexto que recibe el modelo nombra cada documento: el encabezado de `document_formatter.py` (el que
# usan las cadenas del chat) y el de `chunk_context_builder.py`. La ruta de la interfaz es `uploads/<tema>/<archivo>`.
_ENCABEZADO_FORMATEADO = re.compile(
    r"\*\*Expediente:\*\*[ \t]*(?P<tema>[^|\n]+?)[ \t]*\|[ \t]*\*\*Archivo:\*\*[ \t]*(?P<archivo>[^|\n]+?)[ \t]*(?:\||$)", re.MULTILINE)
_ENCABEZADO_CONSTRUIDO = re.compile(r"^Archivo:[ \t]*(?P<archivo>.+?)[ \t]*\r?\nExpediente:[ \t]*(?P<tema>.+?)[ \t]*$", re.MULTILINE)
_RUTA_DEL_ARCHIVO = re.compile(r"\*\*Ruta:\*\*[ \t]*(?P<ruta>\S[^\n]*)")
_MARCA_DE_REFORMULACION = "experto en reformular preguntas legales"  # el prompt que reescribe la pregunta con el historial
RESPUESTA_SIN_CITAS = "No encontré información en los documentos recuperados (respuesta simulada del motor de pruebas)."


def documentos_del_contexto(contexto: str) -> List[str]:
    """Las rutas `uploads/<tema>/<archivo>` de los documentos que nombra el contexto, sin repetir y en orden de aparición."""
    hallados = []
    for coincidencia in _ENCABEZADO_FORMATEADO.finditer(contexto):
        cercano = contexto[coincidencia.end():coincidencia.end() + 400]
        ruta = _RUTA_DEL_ARCHIVO.search(cercano.split("---")[0])
        hallados.append((coincidencia.start(), coincidencia["tema"], coincidencia["archivo"], ruta["ruta"].strip() if ruta else ""))
    for coincidencia in _ENCABEZADO_CONSTRUIDO.finditer(contexto):
        hallados.append((coincidencia.start(), coincidencia["tema"], coincidencia["archivo"], ""))
    rutas: List[str] = []
    for _, tema, archivo, ruta in sorted(hallados):
        publica = ruta[ruta.index("uploads/"):] if "uploads/" in ruta else f"uploads/{tema}/{archivo}"
        if publica not in rutas:
            rutas.append(publica)
    return rutas


def respuesta_con_citas(contexto: str) -> str:
    """Una respuesta que cita cada documento del contexto en el formato que pide el prompt de respuesta (`(uploads/...)`),
    con el que la interfaz arma el enlace de descarga; sin documentos, dice que no encontró nada."""
    rutas = documentos_del_contexto(contexto)
    if not rutas:
        return RESPUESTA_SIN_CITAS
    lineas = [f"- Fuente: ({ruta})" for ruta in rutas]
    return "Según los documentos recuperados (respuesta simulada del motor de pruebas):\n\n" + "\n".join(lineas) + "\n"


@dataclass
class Decision:
    """Lo que el motor hará con una consulta: el texto, cuántos fragmentos emite antes de detenerse (None: no se detiene)."""

    texto: str
    retener_tras: Optional[int] = None


_DEL_MODO = object()  # «la secuencia se agotó: responde según el modo»


class EstadoMotor:
    """El motor de lenguaje programable (RF-11.40 a RF-11.43, RF-16.40).

    Modos: `cita` (por omisión: cita los documentos del contexto), `texto` (una respuesta fija), `conexion` (falla como un
    Ollama inalcanzable) y `sin_datos` (no emite nada hasta que se libera). Una `secuencia` de respuestas se consume antes que
    el modo: un texto vacío es una respuesta vacía y `None`, un fallo de conexión. `retener_tras=N` detiene la respuesta tras
    N fragmentos hasta `liberar`. La reformulación de la pregunta con el historial ni se cuenta ni consume la secuencia.
    """

    MODOS = ("cita", "texto", "conexion", "sin_datos")

    def __init__(self, plazo: float = PLAZO_RETENCION_SEGUNDOS):
        self.compuerta = Retencion(plazo)
        self._candado = threading.Lock()
        self.restablecer()

    def restablecer(self) -> None:
        with self._candado:
            self.modo, self.texto, self.secuencia, self.retener_tras, self.consultas = "cita", None, [], None, 0
        self.compuerta.liberar()

    def configurar(self, modo: str = "cita", texto: Optional[str] = None, secuencia: Sequence[Optional[str]] = (),
                   retener_tras: Optional[int] = None) -> None:
        """Reemplaza la programación entera. Valida antes de cambiar nada; `ValueError` con el motivo si algo no sirve."""
        if modo not in self.MODOS:
            raise ValueError(f"El modo debe ser uno de: {', '.join(self.MODOS)}")
        if modo == "texto" and texto is None:
            raise ValueError("El modo «texto» necesita el texto de la respuesta")
        if texto is not None and len(texto) > MAXIMO_TEXTO:
            raise ValueError(f"El texto no puede pasar de {MAXIMO_TEXTO} caracteres")
        if len(secuencia) > MAXIMO_ELEMENTOS or any(p is not None and len(p) > MAXIMO_TEXTO for p in secuencia):
            raise ValueError(f"La secuencia admite hasta {MAXIMO_ELEMENTOS} respuestas de {MAXIMO_TEXTO} caracteres")
        if retener_tras is not None and retener_tras < 0:
            raise ValueError("Los fragmentos antes de retener no pueden ser negativos")
        with self._candado:
            self.modo, self.texto, self.secuencia, self.retener_tras = modo, texto, list(secuencia), retener_tras
        if retener_tras is not None or modo == "sin_datos":
            self.compuerta.retener()
        else:
            self.compuerta.liberar()

    def liberar(self) -> None:
        self.compuerta.liberar()

    def estado(self) -> dict:
        with self._candado:
            return {"modo": self.modo, "secuencia_pendiente": len(self.secuencia), "retener_tras": self.retener_tras,
                    "retenida": self.compuerta.retenida, "esperando": self.compuerta.esperando, "consultas": self.consultas}

    def decidir(self, mensajes) -> Decision:
        """El texto y la retención de esta consulta; lanza `ConnectionError` si toca fallar por conexión."""
        completo = "\n".join(str(m.content) for m in mensajes)
        if _MARCA_DE_REFORMULACION in completo:
            return Decision(str(mensajes[-1].content))
        with self._candado:
            self.consultas += 1
            paso = self.secuencia.pop(0) if self.secuencia else _DEL_MODO
            modo, texto, retener = self.modo, self.texto, self.retener_tras
        if paso is not _DEL_MODO:
            if paso is None:
                raise ConnectionError(TEXTO_DE_FALLO_DE_CONEXION)
            return Decision(paso, retener)
        if modo == "conexion":
            raise ConnectionError(TEXTO_DE_FALLO_DE_CONEXION)
        if modo == "sin_datos":
            return Decision("", 0)
        return Decision(texto if modo == "texto" else respuesta_con_citas(completo), retener)


_clases: Dict[str, type] = {}


def clase_motor_programable() -> type:
    """Crea (una sola vez) el LLM simulado de la suite con el control del motor: es de verdad un `BaseChatModel` y sigue
    siendo un `_Simulado`, así que `comprobar_simulados` lo reconoce. Sustituye a `_generate` y `_stream`."""
    if "motor" in _clases:
        return _clases["motor"]

    from langchain_core.messages import AIMessage, AIMessageChunk
    from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
    from pydantic import Field

    class MotorProgramable(simulados._clase_llm_simulado()):
        estado: Any = Field(default=None)

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            self._registrar(messages)
            decision = self.estado.decidir(messages)
            if decision.retener_tras is not None:
                self.estado.compuerta.esperar()
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=decision.texto))])

        def _stream(self, messages, stop=None, run_manager=None, **kwargs):
            self._registrar(messages)
            decision = self.estado.decidir(messages)
            retener, detenido = decision.retener_tras, False
            for numero, trozo in enumerate(simulados._trozos(decision.texto)):
                if retener is not None and not detenido and numero >= retener:
                    self.estado.compuerta.esperar()
                    detenido = True
                yield ChatGenerationChunk(message=AIMessageChunk(content=trozo))
            if retener is not None and not detenido:
                self.estado.compuerta.esperar()

    _clases["motor"] = MotorProgramable
    return MotorProgramable


def _validar_nombres(nombres: Sequence[str], que: str) -> List[str]:
    if not isinstance(nombres, (list, tuple)) or len(nombres) > MAXIMO_ELEMENTOS:
        raise ValueError(f"{que}: hasta {MAXIMO_ELEMENTOS} nombres de archivo")
    if any((not isinstance(n, str)) or not n.strip() or len(n) > MAXIMO_NOMBRE for n in nombres):
        raise ValueError(f"{que}: cada nombre debe ser un texto de 1 a {MAXIMO_NOMBRE} caracteres")
    return list(nombres)


class EstadoIngesta:
    """La ingesta dentro del proceso (RF-18.40): la carga por la API encola en un solo hilo de la propia instancia, sin worker,
    con HTR y audio simulados. Se puede hacer fallar o retener el procesamiento de un archivo por su nombre, en la etapa de
    extracción del texto (con el progreso ya iniciado y sin documento todavía)."""

    def __init__(self, htr, audio, plazo: float = PLAZO_RETENCION_SEGUNDOS, esperar_inactiva: float = 60.0):
        self.htr, self.audio = htr, audio
        self._htr_texto, self._audio_texto = htr.texto, audio.texto
        self.compuerta = Retencion(plazo)
        self.fallar: List[str] = []
        self.retener: List[str] = []
        self._espera_maxima = esperar_inactiva
        self._condicion = threading.Condition()
        self._pendientes = 0
        self._numero = itertools.count(1)
        self._ejecutor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingesta-e2e")
        self.procesar: Callable[[str, str, dict, str], None] = self._procesar_con_celery

    def configurar(self, fallar: Sequence[str] = (), retener: Sequence[str] = (), htr_texto: Optional[str] = None,
                   htr_falla: bool = False, audio_texto: Optional[str] = None, audio_falla: bool = False) -> None:
        """Reemplaza la programación entera (lo omitido vuelve a su valor por omisión)."""
        fallar, retener = _validar_nombres(fallar, "fallar"), _validar_nombres(retener, "retener")
        for texto in (htr_texto, audio_texto):
            if texto is not None and len(texto) > MAXIMO_TEXTO:
                raise ValueError(f"Los textos simulados no pueden pasar de {MAXIMO_TEXTO} caracteres")
        self.fallar, self.retener = fallar, retener
        self.htr.responder(self._htr_texto if htr_texto is None else htr_texto)
        self.audio.responder(self._audio_texto if audio_texto is None else audio_texto)
        if htr_falla:
            self.htr.fallar()
        if audio_falla:
            self.audio.fallar()
        if retener:
            self.compuerta.retener()
        else:
            self.compuerta.liberar()

    def liberar(self) -> None:
        self.retener = []
        self.compuerta.liberar()

    def esperar_inactiva(self) -> bool:
        """Espera a que no quede ninguna tarea en curso; False si pasó el plazo."""
        with self._condicion:
            return self._condicion.wait_for(lambda: self._pendientes == 0, self._espera_maxima)

    def restablecer(self) -> None:
        """Suelta lo retenido, quita los fallos programados, espera a que termine lo que estaba en curso y vacía los registros."""
        self.configurar()
        if not self.esperar_inactiva():
            raise AbortoPruebas(
                f"La ingesta de la instancia sigue ocupada tras {self._espera_maxima:g} segundos; no se puede limpiar con seguridad.")
        self.htr.llamadas.clear()
        self.audio.llamadas.clear()

    def cerrar(self) -> None:
        """Al apagar la instancia: suelta lo retenido y espera a que el hilo de la ingesta termine lo que tiene en curso."""
        self.configurar()
        self._ejecutor.shutdown(wait=True, cancel_futures=True)

    def estado(self) -> dict:
        return {"fallar": list(self.fallar), "retener": list(self.retener), "retenida": self.compuerta.retenida,
                "esperando": self.compuerta.esperando, "pendientes": self._pendientes,
                "htr_falla": self.htr.error is not None, "audio_falla": self.audio.error is not None,
                "htr_llamadas": list(self.htr.llamadas), "audio_llamadas": list(self.audio.llamadas)}

    # Reemplazo de `procesar_archivo_celery.delay`: guarda la tarea en el hilo de la instancia, fuera del bucle de la petición.
    def encolar(self, tema, archivo_info, usuario):
        identificador = f"PRUEBA-tarea-{next(self._numero)}"
        with self._condicion:
            self._pendientes += 1
        try:
            self._ejecutor.submit(self._correr, identificador, tema, dict(archivo_info), usuario)
        except BaseException:
            with self._condicion:
                self._pendientes -= 1
                self._condicion.notify_all()
            raise
        return type("TareaEnElProceso", (), {"id": identificador})()

    def _procesar_con_celery(self, identificador, tema, archivo_info, usuario) -> None:
        from app.services.ingesta.async_processing.celery_tasks import procesar_archivo_celery

        procesar_archivo_celery.apply(args=(tema, archivo_info, usuario), task_id=identificador, throw=False)

    def _correr(self, identificador, tema, archivo_info, usuario) -> None:
        try:
            self.procesar(identificador, tema, archivo_info, usuario)
        except Exception as error:
            logger.error("La tarea de ingesta %s terminó con un error inesperado (%s)", identificador, type(error).__name__)
        finally:
            with self._condicion:
                self._pendientes -= 1
                self._condicion.notify_all()

    def envolver_extraccion(self, original: Callable) -> Callable:
        """La extracción de texto del sistema, con la retención y el fallo por nombre de archivo delante."""
        estado = self

        async def extraer(content, filename, content_type, progress_tracker=None, cancel_check=None):
            if filename in estado.retener:
                await estado.compuerta.esperar_async()
            if filename in estado.fallar:
                raise ValueError(f"Error extrayendo texto de {filename}: fallo programado por el control de pruebas (PRUEBA)")
            return await original(content, filename, content_type, progress_tracker, cancel_check)

        return extraer


class EstadoNotebooks:
    """Dos retenciones y un fallo en las acciones de un notebook: la entrega del archivo de la vista previa (RF-18.40) y la
    eliminación de un documento (RF-19.41, RF-19.42), que además puede fallar como lo haría un error al borrar."""

    def __init__(self, plazo: float = PLAZO_RETENCION_SEGUNDOS):
        self.vista_previa = Retencion(plazo)
        self.quitar = Retencion(plazo)
        self.fallar_quitar = False

    def configurar(self, retener_vista_previa: bool = False, retener_quitar: bool = False, fallar_quitar: bool = False) -> None:
        for compuerta, cerrar in ((self.vista_previa, retener_vista_previa), (self.quitar, retener_quitar)):
            if cerrar:
                compuerta.retener()
            else:
                compuerta.liberar()
        self.fallar_quitar = fallar_quitar

    def liberar(self) -> None:
        self.vista_previa.liberar()
        self.quitar.liberar()

    def restablecer(self) -> None:
        self.configurar()

    def estado(self) -> dict:
        return {"retener_vista_previa": self.vista_previa.retenida, "retener_quitar": self.quitar.retenida,
                "fallar_quitar": self.fallar_quitar, "esperando_vista_previa": self.vista_previa.esperando,
                "esperando_quitar": self.quitar.esperando}

    def instalar(self, servicio, parches: "pytest.MonkeyPatch") -> None:
        """Envuelve DOS métodos de la instancia del servicio de notebooks de las rutas (no de la clase)."""
        from app.services.notebook_service import ErrorAlQuitar

        original_archivo, original_quitar = servicio.obtener_archivo_de_documento, servicio.quitar_documento
        estado = self

        async def obtener_archivo_de_documento(db, notebook_id, documento_id, usuario_id):
            # Primero lo que decide el servicio (un ajeno recibe de inmediato su 404): solo se retiene lo que se entrega.
            resultado = await original_archivo(db, notebook_id, documento_id, usuario_id)
            await estado.vista_previa.esperar_async()
            return resultado

        async def quitar_documento(db, notebook_id, documento_id, usuario_id):
            await estado.quitar.esperar_async()
            if estado.fallar_quitar:
                notebook = await servicio._notebook_o_no_disponible(db, notebook_id, usuario_id)
                documento = servicio._documento_del_notebook(db, notebook, documento_id)
                try:
                    raise RuntimeError("Fallo programado por el control de pruebas (PRUEBA)")
                except RuntimeError as causa:
                    raise ErrorAlQuitar(notebook.clave_interna, documento.CN_Id_documento, causa)
            return await original_quitar(db, notebook_id, documento_id, usuario_id)

        parches.setattr(servicio, "obtener_archivo_de_documento", obtener_archivo_de_documento)
        parches.setattr(servicio, "quitar_documento", quitar_documento)


@dataclass
class Controles:
    """Los tres controles de la T6 juntos: lo que la limpieza total restablece y lo que el router del control consulta."""

    motor: Optional[EstadoMotor] = None
    ingesta: Optional[EstadoIngesta] = None
    notebooks: Optional[EstadoNotebooks] = None

    def restablecer(self) -> None:
        """Libera todo lo retenido y deja cada control como recién arrancado; un paso que falla no impide los demás."""
        errores = []
        for nombre, pieza in (("motor", self.motor), ("notebooks", self.notebooks), ("ingesta", self.ingesta)):
            if pieza is None:
                continue
            try:
                pieza.restablecer()
            except Exception as error:
                errores.append(f"{nombre} ({type(error).__name__}: {str(error)[:200]})")
        if errores:
            raise AbortoPruebas("No se pudieron restablecer los controles: " + "; ".join(errores))

    def cerrar(self) -> None:
        """Al apagar la instancia: nada queda retenido y el hilo de la ingesta termina (si no, el proceso no podría salir)."""
        if self.motor is not None:
            self.motor.liberar()
        if self.notebooks is not None:
            self.notebooks.liberar()
        if self.ingesta is not None:
            self.ingesta.cerrar()


def instalar_controles(piezas: Dict[str, object]) -> Controles:
    """Instala la ingesta en el proceso y las retenciones de notebooks, y reúne el motor con ellas.

    Parchea INSTANCIAS (la tarea `procesar_archivo_celery`, el servicio de notebooks de las rutas, el módulo del procesador de
    documentos y el gestor de progreso), nunca clases. Requiere `app` importable (después de `import main`).
    """
    from celery_app import celery_app

    from app.routes.notebooks import notebook_service
    from app.services.ingesta.async_processing.celery_tasks import procesar_archivo_celery
    from app.services.ingesta.async_processing.progress_tracker import progress_manager
    from app.services.ingesta.file_management import document_processor

    parches = piezas["parches"]
    # `check_if_cancelled` consulta a Celery: broker y resultados en memoria, sin tocar ningún Redis (como `celery_inmediato`).
    simulados.fijar_celery_inmediato(celery_app)
    ingesta = EstadoIngesta(piezas["htr"], piezas["audio"])
    notebooks = EstadoNotebooks()
    parches.setattr(procesar_archivo_celery, "delay", ingesta.encolar)
    # La limpieza programada de cada tarea duerme minutos en un hilo: no se programa (la limpieza total borra el progreso).
    parches.setattr(progress_manager, "schedule_task_cleanup", lambda *argumentos, **opciones: None)
    parches.setattr(document_processor, "extract_text_from_file", ingesta.envolver_extraccion(document_processor.extract_text_from_file))
    notebooks.instalar(notebook_service, parches)
    return Controles(motor=piezas["ollama"].estado, ingesta=ingesta, notebooks=notebooks)
