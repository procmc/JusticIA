"""Datos de prueba de la suite: usuarios `PRUEBA`, limpieza por prueba y conteo de residuos (spec 002, RA-02.7).

- Usuarios: `crear_usuario(rol)` inserta un Administrador o un Usuario Gubernamental inventado en la base de pruebas,
  con el prefijo `PRUEBA`, contraseña aleatoria de 16 caracteres guardada con el hash bcrypt del sistema real y
  `CF_Ultimo_acceso` lleno (para que no se les obligue a cambiar la contraseña). La contraseña es un `str` cuyo `repr`
  no la muestra, y nunca se escribe en archivos ni en registros.
- Registro: `Registro` guarda lo que crea una prueba (usuarios, puntos y archivos). Los archivos de prueba los escribe
  la suite DIRECTAMENTE en la carpeta temporal (no con `guardar_archivo`, que falla fuera de `/app`; decisión 7 del plan).
- Limpieza: la fixture automática `registro_de_datos` limpia, al terminar CADA prueba, lo que esa prueba creó: filas con
  el prefijo `PRUEBA` (en orden de claves foráneas), puntos de la colección de pruebas, archivos de la carpeta temporal y
  las claves del Redis simulado. NUNCA toca los catálogos de las migraciones (roles, estados, tipos de acción).
  `limpiar` se niega con un destino que no sea el de pruebas (base, colección o carpeta ajenas).
- Residuos: `contar_residuos` cuenta lo que quedó; el cierre de la sesión (`conftest.py`, `pytest_sessionfinish`) lo ejecuta
  ANTES de eliminar la colección, la carpeta y la base, y falla la corrida si no da cero.

Este módulo es también un plugin de pytest (lo declara el `conftest.py` raíz) y nunca importa `app` al cargarse: lo hace
dentro de las funciones. Las unitarias solo limpian Redis y archivos (no tienen SQL Server ni Qdrant); la integración
limpia además la base y la colección de pruebas. Solo se borran filas con el prefijo `PRUEBA` de la base `servia_pruebas`
y puntos de la colección `servia_pruebas`; el borrado de puntos NO es DDL (crear o eliminar la colección sigue siendo
solo de `proteccion.py`).
"""
import contextlib
import itertools
import os
import secrets
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional

import pytest

from tests.soporte import entorno, simulados
from tests.soporte.nombres import PREFIJO_DATOS
from tests.soporte.proteccion import AbortoPruebas, exigir_nombre_pruebas

# Roles de la base. El del Usuario Gubernamental conserva el nombre heredado «Usuario Judicial» (RT-06).
ROL_ADMINISTRADOR = "Administrador"
ROL_USUARIO_GUBERNAMENTAL = "Usuario Judicial"
_ETIQUETA_DEL_ROL = {ROL_ADMINISTRADOR: "admin", ROL_USUARIO_GUBERNAMENTAL: "usuario"}

# Las carpetas temporales de la suite se llaman así (`simulados.carpeta_temporal_de_la_sesion`).
PREFIJO_DE_CARPETA = "servia_pruebas_"

# Tema de los puntos de prueba: lleva el prefijo para poder encontrarlos por su metadato.
TEMA_DE_PRUEBA = f"{PREFIJO_DATOS}-TEMA-1"

# Catálogos que siembran las migraciones: la limpieza no los toca y el cierre comprueba que siguen completos.
CATALOGOS = ("T_Rol", "T_Estado", "T_Estado_procesamiento", "T_Tipo_accion")

_USUARIOS_DE_PRUEBA = "SELECT CN_Id_usuario FROM T_Usuario WHERE CN_Id_usuario LIKE :prefijo"
_TEMAS_DE_PRUEBA = "SELECT CN_Id_expediente FROM T_Expediente WHERE CT_Num_expediente LIKE :prefijo"
_DOCUMENTOS_DE_PRUEBA = "SELECT CN_Id_documento FROM T_Documento WHERE CT_Nombre_archivo LIKE :prefijo"

# (tabla, condición de las filas de prueba). El orden es el de borrado, por claves foráneas: lo que apunta a un
# usuario, un tema o un documento se borra antes que ellos. `:prefijo` es `PRUEBA%` y `:texto` es `%PRUEBA%`.
TABLAS_DE_PRUEBA = (
    ("T_Bitacora", f"CN_Id_usuario IN ({_USUARIOS_DE_PRUEBA}) OR CN_Id_expediente IN ({_TEMAS_DE_PRUEBA}) "
                   "OR CT_Texto LIKE :texto"),
    ("T_Notebook", f"CN_Id_usuario IN ({_USUARIOS_DE_PRUEBA}) OR CT_Nombre LIKE :prefijo"),
    ("T_Expediente_Documento", f"CN_Id_expediente IN ({_TEMAS_DE_PRUEBA}) OR CN_Id_documento IN ({_DOCUMENTOS_DE_PRUEBA})"),
    ("T_Documento", "CT_Nombre_archivo LIKE :prefijo"),
    ("T_Expediente", "CT_Num_expediente LIKE :prefijo"),
    ("T_Usuario", "CN_Id_usuario LIKE :prefijo"),
)

# Estado de la sesión: los catálogos al empezar, y lo que encontró el conteo del cierre.
_estado: Dict[str, object] = {"catalogos": None, "residuos": None, "conteo_fallido": None}

_consecutivo = itertools.count(1)


# --- La contraseña y los usuarios ------------------------------------------------------------------------------

class Contrasena(str):
    """Contraseña de prueba: sigue siendo un texto (el inicio de sesión la envía tal cual), pero su `repr` no la muestra.

    Así no aparece en los mensajes de una aserción fallida ni en el `repr` del usuario que la contiene.
    """

    def __repr__(self) -> str:
        return "'<contraseña de prueba>'"


def pytest_assertrepr_compare(config, op, left, right):
    """Gancho de pytest: una aserción fallida con una contraseña de prueba no muestra su valor.

    Sin esto, pytest compara dos textos con su propio diff (`str`, no `repr`) y la contraseña saldría en el mensaje
    aunque su `repr` esté oculto. Con otro tipo de operandos devuelve `None` y pytest explica la aserción como siempre.
    """
    if isinstance(left, Contrasena) or isinstance(right, Contrasena):
        return [f"comparación ({op}) con una contraseña de prueba: el valor se oculta"]
    return None


def generar_contrasena() -> Contrasena:
    """Una contraseña aleatoria de 16 caracteres, distinta en cada llamada (RNF-08 pide al menos 8)."""
    return Contrasena(secrets.token_urlsafe(12))


@dataclass(frozen=True)
class UsuarioPrueba:
    """Un usuario de prueba ya guardado en la base. Su `repr` no muestra la contraseña."""

    cedula: str
    nombre_usuario: str
    correo: str
    contrasena: Contrasena
    rol: str


def crear_usuario(rol: str, registro: Optional["Registro"] = None) -> UsuarioPrueba:
    """Inserta en la base de pruebas un usuario inventado con el rol indicado y lo devuelve (con su contraseña).

    `rol` es `ROL_ADMINISTRADOR` o `ROL_USUARIO_GUBERNAMENTAL`. La cédula es `PRUEBA` + consecutivo (cabe en los 20
    caracteres de la columna), el hash es el del `UsuarioRepository` (bcrypt, igual que el sistema), el estado es
    `Activo` y `CF_Ultimo_acceso` está lleno para que el inicio de sesión no exija cambiar la contraseña.
    """
    if rol not in _ETIQUETA_DEL_ROL:
        raise ValueError(f"El rol {rol!r} no es válido: use {ROL_ADMINISTRADOR!r} o {ROL_USUARIO_GUBERNAMENTAL!r}.")

    from app.db.database import SessionLocal
    from app.db.models import T_Estado, T_Rol, T_Usuario
    from app.repositories.usuario_repository import UsuarioRepository

    numero = next(_consecutivo)
    etiqueta = _ETIQUETA_DEL_ROL[rol]
    cedula = f"{PREFIJO_DATOS}{numero:06d}"
    nombre_usuario = f"{PREFIJO_DATOS}_{etiqueta}_{numero}"
    correo = f"prueba{numero}.{etiqueta}@prueba.invalid"
    contrasena = generar_contrasena()
    hash_de_la_contrasena = UsuarioRepository().pwd_context.hash(str(contrasena))

    with SessionLocal() as db:
        id_rol = db.query(T_Rol.CN_Id_rol).filter(T_Rol.CT_Nombre_rol == rol).scalar()
        id_estado = db.query(T_Estado.CN_Id_estado).filter(T_Estado.CT_Nombre_estado == "Activo").scalar()
        if id_rol is None or id_estado is None:
            raise AbortoPruebas(
                "Se aborta la suite de pruebas: la base de pruebas no tiene los catálogos de las migraciones "
                f"(rol {rol!r} o estado 'Activo')."
            )
        db.add(T_Usuario(
            CN_Id_usuario=cedula, CT_Nombre_usuario=nombre_usuario, CT_Nombre=PREFIJO_DATOS, CT_Apellido_uno=etiqueta,
            CT_Correo=correo, CT_Contrasenna=hash_de_la_contrasena, CN_Id_rol=id_rol, CN_Id_estado=id_estado,
            CF_Ultimo_acceso=datetime.now(),
        ))
        db.commit()

    if registro is not None:
        registro.registrar_usuario(cedula)
    return UsuarioPrueba(cedula=cedula, nombre_usuario=nombre_usuario, correo=correo, contrasena=contrasena, rol=rol)


def crear_punto(cliente, registro: Optional["Registro"] = None, numero_expediente: str = TEMA_DE_PRUEBA) -> str:
    """Inserta un punto inventado en la colección de pruebas (vector de `DIM` dimensiones) y devuelve su identificador.

    Valida el nombre de la colección antes de escribir. No usa el modelo de embeddings: el vector es fijo, porque
    estas pruebas no buscan por similitud. El tema (`metadata.numero_expediente`) lleva el prefijo `PRUEBA`.
    """
    coleccion = os.environ.get("QDRANT_COLLECTION_NAME")
    exigir_nombre_pruebas(coleccion, "la colección de Qdrant donde se crea el punto de prueba")

    from qdrant_client.models import PointStruct

    identificador = str(uuid.uuid4())
    dimension = int(os.environ["DIM"])
    cliente.upsert(
        collection_name=coleccion,
        points=[PointStruct(
            id=identificador,
            vector=[1.0] + [0.0] * (dimension - 1),
            payload={
                "page_content": f"{PREFIJO_DATOS}: fragmento inventado",
                "metadata": {"numero_expediente": numero_expediente, "nombre_archivo": f"{PREFIJO_DATOS}_archivo.txt"},
            },
        )],
        wait=True,
    )
    if registro is not None:
        registro.registrar_punto(identificador)
    return identificador


class Registro:
    """Lo que creó una prueba: sus usuarios (cédulas), sus puntos (identificadores) y sus archivos (rutas)."""

    def __init__(self):
        self.usuarios: List[str] = []
        self.puntos: List[object] = []
        self.archivos: List[Path] = []

    def registrar_usuario(self, cedula: str) -> None:
        self.usuarios.append(cedula)

    def registrar_punto(self, identificador: object) -> None:
        self.puntos.append(identificador)

    def registrar_archivo(self, ruta: Path) -> None:
        self.archivos.append(Path(ruta))

    def crear_archivo(self, carpeta: Path, nombre: str, contenido: bytes) -> Path:
        """Escribe un archivo inventado DIRECTAMENTE en `carpeta` (no con `guardar_archivo`) y lo registra.

        El nombre lleva el prefijo `PRUEBA` (para encontrarlo) y no puede traer subcarpetas.
        """
        if not nombre.startswith(PREFIJO_DATOS) or Path(nombre).name != nombre:
            raise ValueError(f"El nombre del archivo de prueba debe empezar por {PREFIJO_DATOS!r} y no traer carpetas: {nombre!r}.")
        ruta = Path(carpeta) / nombre
        ruta.write_bytes(contenido)
        self.registrar_archivo(ruta)
        return ruta


# --- El destino de la limpieza -------------------------------------------------------------------------------------

@dataclass
class Destino:
    """Dónde limpia y cuenta la suite. Cada parte es opcional: las unitarias solo tienen Redis y archivos.

    `borrar(sentencia, parametros)` ejecuta un DELETE y `contar(sentencia, parametros)` un SELECT COUNT en la base de
    pruebas; `qdrant` es un cliente de Qdrant; `limpiar_redis()` y `claves_redis()` vacían y cuentan el Redis simulado.
    """

    base: Optional[str] = None
    coleccion: Optional[str] = None
    carpeta: Optional[Path] = None
    borrar: Optional[Callable[[str, dict], int]] = None
    contar: Optional[Callable[[str, dict], int]] = None
    qdrant: object = None
    limpiar_redis: Optional[Callable[[], None]] = None
    claves_redis: Optional[Callable[[], int]] = None


def _carpeta_de_pruebas(carpeta: Path) -> Path:
    """La carpeta resuelta si es una carpeta temporal de la suite; si no, aborta (nunca `uploads/` ni otra ajena)."""
    resuelta = Path(carpeta).resolve()
    temporal = Path(tempfile.gettempdir()).resolve()
    if not resuelta.name.startswith(PREFIJO_DE_CARPETA) or temporal not in resuelta.parents:
        raise AbortoPruebas(
            f"Se aborta la suite de pruebas: la carpeta de la limpieza es {str(carpeta)!r} y debe ser una carpeta temporal "
            f"de la suite ('{PREFIJO_DE_CARPETA}...' dentro de {temporal}). No se borró nada."
        )
    return resuelta


def _exigir_destino_de_pruebas(destino: Destino) -> Optional[Path]:
    """Aborta, antes de tocar nada, si la base, la colección o la carpeta no son las de pruebas; devuelve la carpeta resuelta."""
    if destino.base is not None or destino.borrar is not None or destino.contar is not None:
        exigir_nombre_pruebas(destino.base, "la base de datos de la limpieza")
    if destino.qdrant is not None or destino.coleccion is not None:
        exigir_nombre_pruebas(destino.coleccion, "la colección de Qdrant de la limpieza")
    return _carpeta_de_pruebas(destino.carpeta) if destino.carpeta is not None else None


def _parametros(condicion: str) -> dict:
    parametros = {"prefijo": f"{PREFIJO_DATOS}%"}
    if ":texto" in condicion:
        parametros["texto"] = f"%{PREFIJO_DATOS}%"
    return parametros


def _ids_de_puntos_de_prueba(destino: Destino) -> List[object]:
    """Identificadores de los puntos cuyo `metadata.numero_expediente` empieza por `PRUEBA`."""
    identificadores, desplazamiento = [], None
    while True:
        puntos, desplazamiento = destino.qdrant.scroll(
            collection_name=destino.coleccion, limit=256, offset=desplazamiento, with_payload=True, with_vectors=False
        )
        for punto in puntos:
            tema = ((punto.payload or {}).get("metadata") or {}).get("numero_expediente")
            if isinstance(tema, str) and tema.startswith(PREFIJO_DATOS):
                identificadores.append(punto.id)
        if desplazamiento is None:
            return identificadores


def _borrar_puntos(destino: Destino, registro: Registro) -> None:
    identificadores = list(dict.fromkeys([*registro.puntos, *_ids_de_puntos_de_prueba(destino)]))
    if identificadores:
        from qdrant_client.models import PointIdsList

        destino.qdrant.delete(
            collection_name=destino.coleccion, points_selector=PointIdsList(points=identificadores), wait=True
        )


def limpiar(destino: Destino, registro: Registro) -> None:
    """Borra lo que creó una prueba: filas `PRUEBA`, sus puntos, sus archivos y las claves del Redis simulado.

    Primero valida TODO el destino y los archivos registrados (se niega con una base, una colección o una carpeta que no
    sean de pruebas, y con un archivo fuera de la carpeta temporal) y solo después borra. Un paso que falla no impide
    los demás: al final se lanza un `AbortoPruebas` que nombra los pasos fallidos.
    """
    carpeta = _exigir_destino_de_pruebas(destino)
    for ruta in registro.archivos:
        resuelta = Path(ruta).resolve()
        if carpeta is None or carpeta not in resuelta.parents:
            raise AbortoPruebas(
                f"Se aborta la suite de pruebas: el archivo registrado {str(ruta)!r} está fuera de la carpeta temporal "
                "de la suite. No se borró nada."
            )

    errores: List[str] = []

    def paso(nombre: str, accion: Callable[[], object]) -> None:
        try:
            accion()
        except Exception as error:
            errores.append(f"{nombre} ({type(error).__name__}: {str(error)[:200]})")

    if destino.borrar is not None:
        for tabla, condicion in TABLAS_DE_PRUEBA:
            paso(tabla, lambda t=tabla, c=condicion: destino.borrar(f"DELETE FROM {t} WHERE {c}", _parametros(c)))
    if destino.qdrant is not None:
        paso("puntos de la colección de Qdrant", lambda: _borrar_puntos(destino, registro))
    paso("archivos", lambda: [Path(ruta).unlink(missing_ok=True) for ruta in registro.archivos])
    if destino.limpiar_redis is not None:
        paso("claves del Redis simulado", destino.limpiar_redis)

    if errores:
        raise AbortoPruebas("No se pudo limpiar por completo lo que creó la prueba: " + "; ".join(errores))


# --- El conteo de residuos -------------------------------------------------------------------------------------------

@dataclass
class Residuos:
    """Lo que quedó sin limpiar: filas por tabla, puntos, archivos, claves de Redis y catálogos alterados."""

    filas: Dict[str, int] = field(default_factory=dict)
    puntos: int = 0
    archivos: List[str] = field(default_factory=list)
    claves_redis: int = 0
    catalogos: List[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(self.filas.values()) + self.puntos + len(self.archivos) + self.claves_redis

    @property
    def hay(self) -> bool:
        return self.total > 0 or bool(self.catalogos)

    def texto(self) -> str:
        """Qué quedó, en español, para el resumen de la corrida; `ninguno` si no quedó nada."""
        partes: List[str] = []
        filas = [f"{tabla}: {cantidad}" for tabla, cantidad in self.filas.items() if cantidad]
        if filas:
            partes.append("filas con el prefijo PRUEBA (" + ", ".join(filas) + ")")
        if self.puntos:
            partes.append(f"puntos de la colección de Qdrant: {self.puntos}")
        if self.archivos:
            nombres = ", ".join(Path(a).name for a in self.archivos[:5])
            partes.append(f"archivos en la carpeta temporal: {len(self.archivos)} ({nombres})")
        if self.claves_redis:
            partes.append(f"claves del Redis simulado: {self.claves_redis}")
        if self.catalogos:
            partes.append("catálogos de las migraciones alterados (" + "; ".join(self.catalogos) + ")")
        return "; ".join(partes) if partes else "ninguno"


def contar_residuos(destino: Destino) -> Residuos:
    """Cuenta lo que hay en el destino: filas `PRUEBA`, TODOS los puntos de la colección de pruebas (es de uso
    exclusivo, así que debe estar vacía), los archivos de la carpeta temporal y las claves del Redis simulado."""
    carpeta = _exigir_destino_de_pruebas(destino)
    residuos = Residuos()
    if destino.contar is not None:
        for tabla, condicion in TABLAS_DE_PRUEBA:
            residuos.filas[tabla] = int(
                destino.contar(f"SELECT COUNT(*) FROM {tabla} WHERE {condicion}", _parametros(condicion))
            )
    if destino.qdrant is not None:
        residuos.puntos = int(destino.qdrant.count(collection_name=destino.coleccion, exact=True).count)
    if carpeta is not None and carpeta.is_dir():
        residuos.archivos = sorted(str(ruta) for ruta in carpeta.rglob("*") if ruta.is_file())
    if destino.claves_redis is not None:
        residuos.claves_redis = int(destino.claves_redis())
    return residuos


def contar_catalogos(contar: Callable[[str, dict], int]) -> Dict[str, int]:
    """Cuántas filas tiene cada catálogo que siembran las migraciones (solo lectura)."""
    return {tabla: int(contar(f"SELECT COUNT(*) FROM {tabla}", {})) for tabla in CATALOGOS}


def comparar_catalogos(antes: Dict[str, int], despues: Dict[str, int]) -> List[str]:
    """Las diferencias entre dos fotos de los catálogos, una por catálogo alterado (vacía si siguen completos)."""
    return [
        f"{tabla}: {antes.get(tabla)} filas al empezar y {despues.get(tabla)} al cerrar"
        for tabla in CATALOGOS
        if antes.get(tabla) != despues.get(tabla)
    ]


def catalogos_iniciales(contar: Optional[Callable[[str, dict], int]] = None) -> Optional[Dict[str, int]]:
    """La foto de los catálogos al empezar la sesión; si todavía no hay y se da `contar`, la toma ahora."""
    if _estado["catalogos"] is None and contar is not None:
        _estado["catalogos"] = contar_catalogos(contar)
    return _estado["catalogos"]


# --- El destino real de la sesión -----------------------------------------------------------------------------------------

@contextlib.contextmanager
def destino_de_la_sesion(servicios: bool) -> Iterator[Destino]:
    """El destino real de la suite: Redis simulado y carpeta temporal siempre; con `servicios`, también la base y la colección.

    `servicios` solo vale en la integración (las unitarias no tienen SQL Server ni Qdrant). La colección entra solo si
    la sesión la creó. Cierra el cliente de Qdrant al salir.
    """
    destino = Destino(carpeta=simulados.carpeta_temporal_actual())

    servidor = simulados._estado["servidor_redis"]
    if servidor is not None:
        import redis

        destino.limpiar_redis = lambda: redis.Redis().flushall()
        destino.claves_redis = lambda: sum(len(base) for base in servidor.dbs.values())

    cliente = None
    try:
        if servicios:
            from sqlalchemy import text

            from app.db.database import engine

            if engine is None:
                raise AbortoPruebas("Se aborta la suite de pruebas: no hay conexión a la base de pruebas para limpiar.")

            def borrar(sentencia: str, parametros: dict) -> int:
                with engine.begin() as conexion:
                    return conexion.execute(text(sentencia), parametros).rowcount

            def contar(sentencia: str, parametros: dict) -> int:
                with engine.connect() as conexion:
                    return conexion.execute(text(sentencia), parametros).scalar()

            destino.base, destino.borrar, destino.contar = engine.url.database, borrar, contar
            if entorno._estado["coleccion_creada"]:
                cliente = entorno.cliente_qdrant()
                destino.qdrant, destino.coleccion = cliente, os.environ.get("QDRANT_COLLECTION_NAME")
        yield destino
    finally:
        if cliente is not None:
            cliente.close()


def contar_residuos_de_la_sesion() -> Optional[Residuos]:
    """Cuenta los residuos de la sesión (y compara los catálogos) ANTES de eliminar nada; `None` si no hubo base de pruebas.

    Lo llama `pytest_sessionfinish`. Guarda el resultado para que el resumen lo imprima; si el conteo mismo falla,
    guarda el motivo y propaga el error.
    """
    _estado["residuos"], _estado["conteo_fallido"] = None, None
    if not entorno._estado["base_creada"]:
        return None
    try:
        with destino_de_la_sesion(servicios=True) as destino:
            residuos = contar_residuos(destino)
            if _estado["catalogos"] is not None:
                residuos.catalogos = comparar_catalogos(_estado["catalogos"], contar_catalogos(destino.contar))
    except Exception as error:
        _estado["conteo_fallido"] = type(error).__name__
        raise
    _estado["residuos"] = residuos
    return residuos


def hay_problema_de_residuos() -> bool:
    """¿El cierre de la sesión encontró datos de prueba sin limpiar, o no pudo contarlos? (para el resumen)."""
    residuos: Optional[Residuos] = _estado["residuos"]
    return _estado["conteo_fallido"] is not None or (residuos is not None and residuos.hay)


def lineas_de_residuos() -> List[str]:
    """Las líneas del resumen de la corrida sobre los residuos (vacía si no se llegó a contar)."""
    if _estado["conteo_fallido"] is not None:
        return [f"FALLA: no se pudo contar los residuos de datos de prueba al cerrar la sesión ({_estado['conteo_fallido']})."]
    residuos: Optional[Residuos] = _estado["residuos"]
    if residuos is None:
        return []
    if residuos.hay:
        return [f"FALLA: quedaron datos de prueba sin limpiar al cerrar la sesión: {residuos.texto()}."]
    return ["Residuos de datos de prueba al cerrar la sesión: ninguno"]


# --- Fixtures ------------------------------------------------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def registro_de_datos(request):
    """Entrega a la prueba el registro de lo que crea y, al terminar CADA prueba, limpia lo que esa prueba creó (RA-02.7).

    Corre en todas las pruebas, cada una con su limpieza: las unitarias limpian Redis y archivos; las de integración,
    además, la base y la colección de pruebas. Ninguna prueba depende de lo que dejó otra.
    """
    registro = Registro()
    integracion = request.node.get_closest_marker("integracion") is not None
    if integracion:
        with destino_de_la_sesion(servicios=True) as destino:
            catalogos_iniciales(destino.contar)  # una sola vez por sesión, antes de que ninguna prueba cree nada
    yield registro
    with destino_de_la_sesion(servicios=integracion) as destino:
        limpiar(destino, registro)


@pytest.fixture
def destino_de_pruebas():
    """El destino real de la limpieza de la integración (base y colección de pruebas, carpeta temporal, Redis simulado).

    Crea la carpeta temporal si todavía no existe (la sesión la crea al primer uso), para que no dependa de si otra
    prueba la creó antes: lo comprobó `--orden-inverso`.
    """
    simulados.carpeta_temporal_de_la_sesion()
    with destino_de_la_sesion(servicios=True) as destino:
        yield destino


@pytest.fixture
def administrador(registro_de_datos) -> UsuarioPrueba:
    """Un Administrador `PRUEBA` ya guardado en la base de pruebas; se borra al terminar la prueba."""
    return crear_usuario(ROL_ADMINISTRADOR, registro_de_datos)


@pytest.fixture
def usuario_gubernamental(registro_de_datos) -> UsuarioPrueba:
    """Un Usuario Gubernamental `PRUEBA` (rol heredado «Usuario Judicial») ya guardado; se borra al terminar la prueba."""
    return crear_usuario(ROL_USUARIO_GUBERNAMENTAL, registro_de_datos)
