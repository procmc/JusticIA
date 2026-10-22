"""Control de la instancia de extremo a extremo (spec 005a, RA-02.49).

Router `/pruebas-e2e` que el lanzador (`__main__.py`) monta sobre la aplicación real solo en este proceso: `main.py` no lo
incluye, así que el backend de desarrollo responde 404. Todo POST exige el token de la corrida en la cabecera
`X-Control-Pruebas` (la red interna de Compose alcanza el puerto 8100); `GET /estado` es de solo lectura. T1 trae `estado` y
`apagar`; T3 suma usuarios y limpieza, T5 correo, almacén, reloj y bitácora, y T6 motor, ingesta y notebooks. No importa `app` al
cargarse: lo hace dentro de las funciones, para poder probarlo sin base de datos.
"""
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from tests.instancia_e2e import simulados_e2e
from tests.instancia_e2e.simulados_e2e import DestinoE2E, RegistroContrasenas, Vigilante, estado_de_simulados
from tests.soporte.proteccion import AbortoPruebas, nombre_activo

CABECERA_TOKEN = "X-Control-Pruebas"


@dataclass
class Contexto:
    """Lo que el control necesita de la instancia: su token, cómo apagarla y el vigilante de inactividad."""

    token: str
    apagar: Callable[[], None]
    vigilante: Vigilante
    contrasenas: RegistroContrasenas = field(default_factory=RegistroContrasenas)
    registro: Optional[Path] = None  # el registro de la instancia, donde no debe aparecer ninguna contraseña
    destino: Optional[DestinoE2E] = None  # dónde limpia y cuenta la instancia (la base, la colección y las carpetas)
    correo: Any = None  # el correo simulado (T5): de ahí se lee el código y se programa su fallo
    almacen: Any = None  # el Redis controlable de la recuperación (T5): puede dejar de responder y avanzar el tiempo
    controles: Any = None  # el motor, la ingesta y los notebooks controlables (T6): `simulados_e2e.Controles`


_contexto: Optional[Contexto] = None


def configurar(contexto: Contexto) -> None:
    """Lo llama el lanzador antes de arrancar el servidor."""
    global _contexto
    _contexto = contexto


def exigir_token(contexto: Contexto, recibido: Optional[str]) -> None:
    """403 si la cabecera no trae exactamente el token de la corrida (comparación de tiempo constante)."""
    if not recibido or not secrets.compare_digest(recibido.encode("utf-8"), contexto.token.encode("utf-8")):
        raise HTTPException(status_code=403, detail="Token de control inválido")


def _tocar() -> None:
    """Toda petición al control reinicia la cuenta del vigilante de inactividad."""
    if _contexto is not None:
        _contexto.vigilante.tocar()


def _con_token(token: Optional[str] = Header(None, alias=CABECERA_TOKEN)) -> Contexto:
    if _contexto is None:
        raise HTTPException(status_code=503, detail="La instancia todavía no está configurada")
    exigir_token(_contexto, token)
    return _contexto


router = APIRouter(prefix="/pruebas-e2e", dependencies=[Depends(_tocar)])


@router.get("/estado")
def estado() -> dict:
    """Base, colección y simulados que la instancia usa hoy. No abre conexiones nuevas ni modifica nada."""
    import fakeredis
    import redis

    import app.config.config as config_del_sistema
    from app.db import database

    simulados_activos = estado_de_simulados()
    return {
        "listo": True,
        "nombre_activo": nombre_activo(),
        "base": database.engine.url.database if database.engine is not None else None,
        "coleccion": config_del_sistema.QDRANT_COLLECTION_NAME,
        "redis_simulado": issubclass(redis.Redis, fakeredis.FakeRedis),
        "simulados": simulados_activos,
        "todos_simulados": all(simulados_activos.values()),
        "pid": os.getpid(),
    }


@router.post("/apagar")
def apagar(contexto: Contexto = Depends(_con_token)) -> dict:
    """Pide al servidor que termine; el lanzador elimina la base, la colección y la carpeta temporal al salir.

    Devuelve cuántas veces aparecen en el registro de la instancia las contraseñas que recibió (RA-02.43): solo el número.
    """
    try:
        texto = contexto.registro.read_text(errors="replace") if contexto.registro else ""
    except OSError:
        texto = ""
    coincidencias = contexto.contrasenas.contar_en(texto)
    contexto.apagar()
    return {"apagando": True, "coincidencias_en_registro": coincidencias}


# --- Usuarios, residuos y limpieza (T3, RA-02.42) ----------------------------------------------------------------

# Los roles que el control acepta y el nombre que tienen en la base (el del Usuario Gubernamental conserva el heredado, RT-06).
ROLES = {"administrador": "Administrador", "usuario": "Usuario Judicial"}


class CuerpoUsuario(BaseModel):
    """Un usuario `PRUEBA` a crear: su rol, la contraseña que genera la suite y si entra con contraseña temporal o Inactivo."""

    rol: str
    contrasena: str
    temporal: bool = False
    inactivo: bool = False


def crear_usuario_e2e(rol: str, contrasena: str, temporal: bool, inactivo: bool):
    """Inserta el usuario con la misma función de la suite de pytest (cédula `PRUEBA` + consecutivo, hash bcrypt real)."""
    from tests.soporte import datos

    return datos.crear_usuario(
        ROLES[rol], contrasena=contrasena, temporal=temporal, estado="Inactivo" if inactivo else "Activo"
    )


@router.post("/usuarios")
def usuarios(cuerpo: CuerpoUsuario, contexto: Contexto = Depends(_con_token)) -> dict:
    """Crea un usuario `PRUEBA` con la contraseña recibida. Responde sin ella: la guarda solo en memoria (RA-02.43)."""
    if cuerpo.rol not in ROLES:
        raise HTTPException(status_code=400, detail=f"Rol inválido: use {', '.join(sorted(ROLES))}")
    if not cuerpo.contrasena:
        raise HTTPException(status_code=400, detail="La contraseña no puede estar vacía")
    contexto.contrasenas.recordar(cuerpo.contrasena)
    usuario = crear_usuario_e2e(cuerpo.rol, cuerpo.contrasena, cuerpo.temporal, cuerpo.inactivo)
    return {
        "cedula": usuario.cedula,
        "nombre_usuario": usuario.nombre_usuario,
        "correo": usuario.correo,
        "rol": usuario.rol,
        "temporal": cuerpo.temporal,
        "inactivo": cuerpo.inactivo,
    }


def _destino(contexto: Contexto) -> DestinoE2E:
    if contexto.destino is None:
        raise HTTPException(status_code=503, detail="La instancia todavía no tiene destino de limpieza")
    return contexto.destino


@router.get("/residuos")
def residuos(contexto: Contexto = Depends(_con_token)) -> dict:
    """Lo que hay en el entorno aislado (filas, puntos, archivos, Redis, conversaciones, buzón), sin catálogos ni sembrados."""
    return simulados_e2e.contar_residuos_e2e(_destino(contexto))


@router.post("/limpiar")
def limpiar(contexto: Contexto = Depends(_con_token)) -> dict:
    """Deja el entorno aislado como recién arrancado y devuelve los residuos que quedan (deben ser cero)."""
    destino = _destino(contexto)
    try:
        simulados_e2e.limpiar_todo(destino)
    except AbortoPruebas as aborto:  # el motivo (en español, sin secretos) llega a quien llamó
        raise HTTPException(status_code=500, detail=str(aborto)[:500])
    return simulados_e2e.contar_residuos_e2e(destino)


# --- Recuperación y bitácora (T5, RA-02.49) ------------------------------------------------------------------------------

LIMITE_RELOJ_SEGUNDOS = 24 * 60 * 60  # un día: más no hace falta para vencer un código de 15 minutos ni un bloqueo


class CuerpoCorreo(BaseModel):
    """Programa el servidor de correo simulado: `falla=True` hace que cada envío falle hasta restablecerlo."""

    falla: bool = True


class CuerpoAlmacen(BaseModel):
    """Programa el almacén temporal de la recuperación: `disponible=False` lo deja sin responder (conexión o tiempo agotado)."""

    disponible: bool
    tipo: str = "conexion"


class CuerpoReloj(BaseModel):
    """Segundos de tiempo virtual que pasan para el almacén temporal (vencen los códigos, sin esperar tiempo real)."""

    segundos: float


class CuerpoBitacora(BaseModel):
    """Una fila de bitácora de un `tipo` del catálogo del control, a nombre de un usuario ya creado."""

    cedula: str
    tipo: str
    tema: Optional[str] = None


def _pieza(contexto: Contexto, nombre: str):
    pieza = getattr(contexto, nombre)
    if pieza is None:
        raise HTTPException(status_code=503, detail=f"La instancia todavía no tiene {nombre}")
    return pieza


@router.get("/correo/codigo")
def leer_codigo(a: str, contexto: Contexto = Depends(_con_token)) -> dict:
    """El código de 6 dígitos del último correo enviado a `a`. Solo el código: nunca el contenido del correo (RF-03.41)."""
    try:
        return {"codigo": simulados_e2e.codigo_del_correo(_pieza(contexto, "correo"), a)}
    except LookupError:
        raise HTTPException(status_code=404, detail="No hay un correo con código de verificación para ese destinatario")


@router.post("/correo")
def programar_correo(cuerpo: CuerpoCorreo, contexto: Contexto = Depends(_con_token)) -> dict:
    """Hace que los envíos de correo fallen (o vuelvan a la normalidad); no toca los intentos ya registrados."""
    correo = _pieza(contexto, "correo")
    if cuerpo.falla:
        correo.fallar()
    else:
        correo.responder_bien()
    return {"correo_en_fallo": cuerpo.falla}


@router.post("/almacen")
def programar_almacen(cuerpo: CuerpoAlmacen, contexto: Contexto = Depends(_con_token)) -> dict:
    """Deja el almacén temporal sin responder (`conexion` o `tiempo`) o lo restablece."""
    if cuerpo.tipo not in ("conexion", "tiempo"):
        raise HTTPException(status_code=400, detail="El tipo de fallo debe ser «conexion» o «tiempo»")
    almacen = _pieza(contexto, "almacen")
    if cuerpo.disponible:
        almacen.responder_bien()
    else:
        almacen.no_responde(cuerpo.tipo)
    return {"almacen_no_disponible": not cuerpo.disponible}


@router.post("/reloj")
def avanzar_reloj(cuerpo: CuerpoReloj, contexto: Contexto = Depends(_con_token)) -> dict:
    """Avanza el tiempo virtual del almacén temporal: caducan las claves cuyo plazo se cumple."""
    if not 0 < cuerpo.segundos <= LIMITE_RELOJ_SEGUNDOS:
        raise HTTPException(status_code=400, detail=f"Los segundos deben estar entre 0 (sin incluir) y {LIMITE_RELOJ_SEGUNDOS}")
    _pieza(contexto, "almacen").avanzar(cuerpo.segundos)
    return {"avanzado": cuerpo.segundos}


@router.post("/bitacora")
def crear_fila_de_bitacora(cuerpo: CuerpoBitacora, contexto: Contexto = Depends(_con_token)) -> dict:
    """Escribe una fila de bitácora del tipo pedido con el servicio de auditoría real y devuelve su id."""
    if cuerpo.tipo not in simulados_e2e.TIPOS_DE_BITACORA:
        raise HTTPException(status_code=400, detail=f"Tipo inválido: use uno de {', '.join(simulados_e2e.TIPOS_DE_BITACORA)}")
    if not cuerpo.cedula.strip():
        raise HTTPException(status_code=400, detail="La cédula no puede estar vacía")
    try:
        identificador = simulados_e2e.registrar_fila_de_bitacora(cuerpo.tipo, cuerpo.cedula.strip(), cuerpo.tema)
    except AbortoPruebas as aborto:
        raise HTTPException(status_code=500, detail=str(aborto)[:500])
    return {"id": identificador, "tipo": cuerpo.tipo}


@router.get("/capacidades")
def capacidades(contexto: Contexto = Depends(_con_token)) -> dict:
    """Lo que está programado hoy (correo en fallo, almacén caído) y cuántos correos recibió el buzón simulado."""
    return {
        "correo_en_fallo": getattr(_pieza(contexto, "correo"), "_error", None) is not None,
        "almacen_no_disponible": simulados_e2e.almacen_no_disponible(_pieza(contexto, "almacen")),
        "correos_enviados": len(_pieza(contexto, "correo").intentos),
    }


# --- Motor, ingesta y notebooks (T6, RA-02.49) -----------------------------------------------------------------------------
# Cada POST reemplaza la programación entera (lo omitido vuelve a su valor por omisión); `liberar` abre la retención sin cambiar
# lo demás; los GET devuelven el estado. La limpieza total (`/limpiar`) lo restablece todo.

class CuerpoMotor(BaseModel):
    """Programa el motor de lenguaje: `modo` (cita, texto, conexion, sin_datos), una `secuencia` de respuestas que se consume
    antes del modo (texto vacío: respuesta vacía; null: fallo de conexión) y `retener_tras` fragmentos antes de detenerse."""

    modo: str = "cita"
    texto: Optional[str] = None
    secuencia: List[Optional[str]] = []
    retener_tras: Optional[int] = None


class CuerpoIngesta(BaseModel):
    """Programa la ingesta en el proceso: archivos (por nombre) que fallan o se retienen al extraer su texto, y el texto o el
    fallo del HTR y del audio simulados."""

    fallar: List[str] = []
    retener: List[str] = []
    htr_texto: Optional[str] = None
    htr_falla: bool = False
    audio_texto: Optional[str] = None
    audio_falla: bool = False


class CuerpoNotebooks(BaseModel):
    """Programa las acciones de un notebook: retener la entrega del archivo de la vista previa, retener la eliminación de un
    documento y hacerla fallar."""

    retener_vista_previa: bool = False
    retener_quitar: bool = False
    fallar_quitar: bool = False


def _control(contexto: Contexto, nombre: str):
    """Una de las piezas de `controles` (motor, ingesta, notebooks); 503 si la instancia todavía no la tiene."""
    controles = _pieza(contexto, "controles")
    pieza = getattr(controles, nombre)
    if pieza is None:
        raise HTTPException(status_code=503, detail=f"La instancia todavía no tiene {nombre}")
    return pieza


def _programar(pieza, **valores) -> dict:
    try:
        pieza.configurar(**valores)
    except ValueError as error:  # el motivo es de la suite, en español y sin secretos
        raise HTTPException(status_code=400, detail=str(error)[:300])
    return pieza.estado()


@router.get("/motor")
def leer_motor(contexto: Contexto = Depends(_con_token)) -> dict:
    return _control(contexto, "motor").estado()


@router.post("/motor")
def programar_motor(cuerpo: CuerpoMotor, contexto: Contexto = Depends(_con_token)) -> dict:
    """Programa el motor de lenguaje simulado (RF-11.40 a RF-11.43, RF-16.40)."""
    return _programar(_control(contexto, "motor"), modo=cuerpo.modo, texto=cuerpo.texto, secuencia=cuerpo.secuencia,
                      retener_tras=cuerpo.retener_tras)


@router.post("/motor/liberar")
def liberar_motor(contexto: Contexto = Depends(_con_token)) -> dict:
    motor = _control(contexto, "motor")
    motor.liberar()
    return motor.estado()


@router.get("/ingesta")
def leer_ingesta(contexto: Contexto = Depends(_con_token)) -> dict:
    return _control(contexto, "ingesta").estado()


@router.post("/ingesta")
def programar_ingesta(cuerpo: CuerpoIngesta, contexto: Contexto = Depends(_con_token)) -> dict:
    """Programa la ingesta en el proceso: fallos y retenciones por nombre, HTR y audio simulados (RF-18.40)."""
    return _programar(_control(contexto, "ingesta"), fallar=cuerpo.fallar, retener=cuerpo.retener, htr_texto=cuerpo.htr_texto,
                      htr_falla=cuerpo.htr_falla, audio_texto=cuerpo.audio_texto, audio_falla=cuerpo.audio_falla)


@router.post("/ingesta/liberar")
def liberar_ingesta(contexto: Contexto = Depends(_con_token)) -> dict:
    ingesta = _control(contexto, "ingesta")
    ingesta.liberar()
    return ingesta.estado()


@router.get("/notebooks")
def leer_notebooks(contexto: Contexto = Depends(_con_token)) -> dict:
    return _control(contexto, "notebooks").estado()


@router.post("/notebooks")
def programar_notebooks(cuerpo: CuerpoNotebooks, contexto: Contexto = Depends(_con_token)) -> dict:
    """Programa la retención de la vista previa y de la eliminación de un documento, y el fallo de esta (RF-18.40, RF-19.41, RF-19.42)."""
    return _programar(_control(contexto, "notebooks"), retener_vista_previa=cuerpo.retener_vista_previa,
                      retener_quitar=cuerpo.retener_quitar, fallar_quitar=cuerpo.fallar_quitar)


@router.post("/notebooks/liberar")
def liberar_notebooks(contexto: Contexto = Depends(_con_token)) -> dict:
    notebooks = _control(contexto, "notebooks")
    notebooks.liberar()
    return notebooks.estado()
