"""Inventario de las rutas de la API y su clasificación (spec 004, T2; RA-02.12). Base de T3 (RNF-07.5) y T4 (RF-02.3).

Qué hay aquí:
- `rutas_registradas(app)`: el conjunto de `(método, plantilla)` que la aplicación registra de verdad (rutas de la API,
  montajes y las rutas del propio framework para la documentación).
- `CLASIFICACION`: la tabla a mano, una `Clasificacion` por ruta. Sale de la tabla aprobada de la spec 004 («Clasificación
  de las rutas»), no de lo que hoy hace el código: donde el código difiere (una ruta sin sesión que debería exigirla), la
  entrada lleva su `estado_actual` y la prueba que la recorre se marca `xfail`.
- `exigir_tabla_completa(app)`: falla nombrando cada ruta que sobra o falta (RA-02.12). Una ruta nueva sin clasificar, o una
  clasificada que ya no existe, rompe la suite hasta que se actualice la tabla.

Reglas de la tabla:
- `clase`: una de `CLASES`. `PUBLICA` no pide sesión; `PUBLICA_DELIBERADA` (los avatares, RF-04.20 y RNF-07.22) es la única
  excepción documentada a RNF-07.5 y T3 no la recorre; `CUALQUIER_SESION` pide sesión de cualquier rol y toca solo la cuenta
  propia; `ADMINISTRADOR` y `USUARIO_GUBERNAMENTAL` piden ese rol; `PROTEGIDA` pide sesión sin más precisión (la documentación
  automática, decisión 5 de la spec).
- `flujo_critico`: según las «Definiciones» de la spec (alcance de RF-02.3). T4 solo lo usa en las entradas de clase
  `ADMINISTRADOR` o `USUARIO_GUBERNAMENTAL`: las de sesión (renovar, cerrar, cambio obligatorio) admiten a cualquier rol.
- `estado_actual`: la etiqueta del `xfail` de RNF-07.5 cuando el código aún no exige sesión; `None` si ya la exige. Es una
  etiqueta («<requisito> · <módulo>»), nunca la ruta: así la lista de rutas con fallo la produce la prueba y no se copia
  en documentos.
- `ejemplo`: datos válidos y inventados (`PRUEBA`) para llamar a la ruta con su método: `parametros` (valores de la
  plantilla), `consulta` (parámetros de consulta), `json` (cuerpo JSON), `formulario` (campos de formulario) y `archivos`
  (campo → `(nombre, contenido, tipo)`). Ningún valor es una contraseña o un identificador reales.
- `id`: identificador neutro `<grupo>-<n>` para nombrar los casos parametrizados sin escribir rutas.

Este módulo no importa `app` ni `main` al cargarse (regla de la suite): recibe la aplicación como argumento.
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Mapping, Optional, Tuple

from fastapi.routing import APIRoute
from starlette.routing import Mount, Route

PUBLICA = "pública"
PUBLICA_DELIBERADA = "pública deliberada"
CUALQUIER_SESION = "cualquier sesión"
ADMINISTRADOR = "Administrador"
USUARIO_GUBERNAMENTAL = "Usuario Gubernamental"
PROTEGIDA = "protegida"
CLASES = (PUBLICA, PUBLICA_DELIBERADA, CUALQUIER_SESION, ADMINISTRADOR, USUARIO_GUBERNAMENTAL, PROTEGIDA)

# Etiqueta del `xfail` estricto de RNF-07.5 para lo que hoy responde sin sesión (spec 004, «Estado actual»).
ETIQUETA_AUTENTICACION = "RNF-07.5 · autenticación"

Clave = Tuple[str, str]


@dataclass(frozen=True)
class Clasificacion:
    """La clasificación de una ruta. `id` lo asigna `_tabla` por orden dentro de su grupo."""

    id: str
    clase: str
    grupo: str
    flujo_critico: bool
    ejemplo: Mapping[str, Any] = field(default_factory=dict)
    estado_actual: Optional[str] = None


def rutas_registradas(app) -> FrozenSet[Clave]:
    """Los `(método, plantilla)` que la aplicación registra, sin los `HEAD` y `OPTIONS` implícitos.

    Starlette agrega `HEAD` a toda ruta `GET` del framework (documentación) y CORS atiende `OPTIONS` por su cuenta: ninguno
    es una ruta propia. El `HEAD` de los avatares sí cuenta, porque su ruta lo declara. Un montaje (`Mount`) se registra
    como `("MONTAJE", prefijo)`: hoy no hay ninguno, y aparecería como ruta sin clasificar.
    """
    rutas = set()
    for ruta in app.routes:
        if isinstance(ruta, APIRoute):
            rutas.update((metodo, ruta.path) for metodo in ruta.methods)
        elif isinstance(ruta, Mount):
            rutas.add(("MONTAJE", ruta.path))
        elif isinstance(ruta, Route):
            metodos = set(ruta.methods or ())
            if "GET" in metodos:
                metodos.discard("HEAD")
            metodos.discard("OPTIONS")
            rutas.update((metodo, ruta.path) for metodo in metodos)
        else:
            rutas.add((type(ruta).__name__.upper(), getattr(ruta, "path", "?")))
    return frozenset(rutas)


def _tabla(*grupos: Tuple[str, list]) -> Dict[Clave, Clasificacion]:
    """Arma la tabla numerando las entradas de cada grupo (`<grupo>-<n>`) en el orden en que se escriben."""
    tabla: Dict[Clave, Clasificacion] = {}
    for grupo, entradas in grupos:
        for numero, (metodo, plantilla, clase, critico, ejemplo, estado) in enumerate(entradas, start=1):
            tabla[(metodo, plantilla)] = Clasificacion(
                id=f"{grupo}-{numero}", clase=clase, grupo=grupo, flujo_critico=critico,
                ejemplo=ejemplo, estado_actual=estado,
            )
    return tabla


_AUTH = ETIQUETA_AUTENTICACION
_U = {"usuario_id": "PRUEBA-usuario"}
_N = {"notebook_id": "1", "documento_id": "1"}
_S = {"session_id": "PRUEBA-sesion"}
_TEMA = "PRUEBA-tema"
_ARCHIVO = ("PRUEBA_ejemplo.txt", b"PRUEBA contenido de ejemplo", "text/plain")

CLASIFICACION: Dict[Clave, Clasificacion] = _tabla(
    # (método, plantilla, clase, flujo_critico, ejemplo, estado_actual)
    ("salud", [
        ("GET", "/", PUBLICA, False, {}, None),
    ]),
    ("documentacion", [
        ("GET", "/openapi.json", PROTEGIDA, False, {}, _AUTH),
        ("GET", "/docs", PROTEGIDA, False, {}, _AUTH),
        ("GET", "/docs/oauth2-redirect", PROTEGIDA, False, {}, _AUTH),
        ("GET", "/redoc", PROTEGIDA, False, {}, _AUTH),
    ]),
    ("avatares", [
        ("GET", "/uploads/profiles/{nombre}", PUBLICA_DELIBERADA, False, {"parametros": {"nombre": "PRUEBA.png"}}, None),
        ("HEAD", "/uploads/profiles/{nombre}", PUBLICA_DELIBERADA, False, {"parametros": {"nombre": "PRUEBA.png"}}, None),
    ]),
    ("recuperacion", [
        ("POST", "/auth/login", PUBLICA, False, {"json": {"email": "prueba@example.org", "password": "PRUEBA-no-valida"}}, None),
        ("POST", "/auth/solicitar-recuperacion", PUBLICA, False, {"json": {"email": "prueba@example.org"}}, None),
        ("POST", "/auth/verificar-codigo", PUBLICA, False, {"json": {"token": "PRUEBA-token", "codigo": "000000"}}, None),
        ("POST", "/auth/cambiar-contrasenna-recuperacion", PUBLICA, False,
         {"json": {"verificationToken": "PRUEBA-token", "nuevaContrasenna": "PRUEBA-no-valida"}}, None),
    ]),
    ("sesion", [
        ("POST", "/auth/logout", CUALQUIER_SESION, True,
         {"json": {"usuario_id": "PRUEBA-usuario", "email": "prueba@example.org"}}, _AUTH),
        ("POST", "/auth/refresh-token", CUALQUIER_SESION, True, {}, None),
        ("PUT", "/auth/cambiar-contrasenna", CUALQUIER_SESION, True,
         {"json": {"cedula_usuario": "PRUEBA-cedula", "contrasenna_actual": "PRUEBA-no-valida",
                   "nueva_contrasenna": "PRUEBA-no-valida-2"}}, _AUTH),
    ]),
    ("cuenta", [
        ("POST", "/usuarios/{usuario_id}/avatar/upload", CUALQUIER_SESION, False,
         {"parametros": _U, "archivos": {"file": ("PRUEBA.png", b"PRUEBA", "image/png")}}, None),
        ("PUT", "/usuarios/{usuario_id}/avatar/tipo", CUALQUIER_SESION, False,
         {"parametros": _U, "json": {"avatar_tipo": "neutral"}}, None),
        ("DELETE", "/usuarios/{usuario_id}/avatar", CUALQUIER_SESION, False, {"parametros": _U}, None),
    ]),
    ("usuarios", [
        ("GET", "/usuarios/", ADMINISTRADOR, True, {}, None),
        ("GET", "/usuarios/{usuario_id}", ADMINISTRADOR, True, {"parametros": _U}, None),
        ("POST", "/usuarios/", ADMINISTRADOR, True,
         {"json": {"cedula": "PRUEBA-cedula", "nombre_usuario": "PRUEBA usuario", "nombre": "PRUEBA",
                   "apellido_uno": "Uno", "apellido_dos": "Dos", "correo": "prueba@example.org", "id_rol": 2}}, None),
        ("PUT", "/usuarios/{usuario_id}", ADMINISTRADOR, True,
         {"parametros": _U,
          "json": {"nombre_usuario": "PRUEBA usuario", "nombre": "PRUEBA", "apellido_uno": "Uno", "apellido_dos": "Dos",
                   "correo": "prueba@example.org", "id_rol": 2, "id_estado": 1}}, None),
        ("PATCH", "/usuarios/{usuario_id}/ultimo-acceso", ADMINISTRADOR, True, {"parametros": _U}, None),
        ("POST", "/usuarios/{usuario_id}/resetear-contrasenna", ADMINISTRADOR, True, {"parametros": _U}, None),
    ]),
    ("correo", [
        ("POST", "/email/test-email", ADMINISTRADOR, False,
         {"json": {"email": "prueba@example.org", "password": "PRUEBA-no-valida"}}, None),
        ("GET", "/email/email-config", ADMINISTRADOR, False, {}, None),
    ]),
    ("bitacora", [
        ("GET", "/bitacora/registros", ADMINISTRADOR, False, {"consulta": {"limite": 1}}, None),
        ("GET", "/bitacora/estadisticas", ADMINISTRADOR, False, {"consulta": {"dias": 1}}, None),
        ("GET", "/bitacora/estadisticas-rag", ADMINISTRADOR, False, {"consulta": {"dias": 1}}, None),
        ("GET", "/bitacora/mi-historial", USUARIO_GUBERNAMENTAL, False, {"consulta": {"limite": 1}}, None),
        # La spec lo clasifica «Solo Administrador (RF-22)»; hoy el código admite al Usuario Gubernamental. No es flujo
        # crítico, así que RF-02.3 no lo recorre (decisión 7-B); queda para la retroactiva de autenticación.
        ("GET", "/bitacora/expediente/{expediente_numero}", ADMINISTRADOR, False,
         {"parametros": {"expediente_numero": _TEMA}, "consulta": {"limite": 1}}, None),
        ("POST", "/bitacora/registrar-exportacion", ADMINISTRADOR, False, {}, None),
    ]),
    ("ingesta", [
        ("GET", "/ingesta/progress/{task_id}", USUARIO_GUBERNAMENTAL, True, {"parametros": {"task_id": "PRUEBA-tarea"}}, None),
        ("GET", "/ingesta/stats", USUARIO_GUBERNAMENTAL, False, {}, None),
        ("POST", "/ingesta/archivos", USUARIO_GUBERNAMENTAL, True,
         {"formulario": {"CT_Num_expediente": _TEMA}, "archivos": {"files": _ARCHIVO}}, None),
        ("POST", "/ingesta/cancel/{task_id}", USUARIO_GUBERNAMENTAL, False, {"parametros": {"task_id": "PRUEBA-tarea"}}, None),
    ]),
    ("chat", [
        ("POST", "/rag/consulta-con-historial-stream", USUARIO_GUBERNAMENTAL, True,
         {"json": {"query": "PRUEBA pregunta", "session_id": "PRUEBA-sesion", "expediente_number": _TEMA}}, None),
        ("POST", "/rag/update-expediente-context", USUARIO_GUBERNAMENTAL, False,
         {"json": {"session_id": "PRUEBA-sesion", "expediente_number": _TEMA, "action": "set"}}, None),
        ("GET", "/rag/conversations", USUARIO_GUBERNAMENTAL, False, {}, None),
        ("GET", "/rag/conversations/{session_id}", USUARIO_GUBERNAMENTAL, False, {"parametros": _S}, None),
        ("DELETE", "/rag/conversations/{session_id}", USUARIO_GUBERNAMENTAL, False, {"parametros": _S}, None),
        ("POST", "/rag/conversations/{session_id}/restore", USUARIO_GUBERNAMENTAL, False, {"parametros": _S}, None),
        ("GET", "/rag/conversations-stats", USUARIO_GUBERNAMENTAL, False, {}, None),
        ("GET", "/rag/health/redis", USUARIO_GUBERNAMENTAL, False, {}, None),
    ]),
    ("similares", [
        ("POST", "/similarity/search", USUARIO_GUBERNAMENTAL, False,
         {"json": {"modo_busqueda": "descripcion", "texto_consulta": "PRUEBA consulta"}}, None),
        ("POST", "/similarity/generate-summary", USUARIO_GUBERNAMENTAL, False, {"json": {"numero_expediente": _TEMA}}, None),
    ]),
    ("archivos", [
        ("GET", "/archivos/expediente/{expediente_numero}/archivos", USUARIO_GUBERNAMENTAL, False,
         {"parametros": {"expediente_numero": _TEMA}}, None),
        ("GET", "/archivos/expediente/{expediente_numero}/archivo/{nombre_archivo}", USUARIO_GUBERNAMENTAL, False,
         {"parametros": {"expediente_numero": _TEMA, "nombre_archivo": "PRUEBA_ejemplo.txt"}}, None),
        # La descarga del documento citado en el chat (RF-12.1): flujo crítico.
        ("GET", "/archivos/download", USUARIO_GUBERNAMENTAL, True, {"consulta": {"ruta_archivo": "PRUEBA/PRUEBA_ejemplo.txt"}}, None),
    ]),
    ("notebooks", [
        ("POST", "/notebooks", USUARIO_GUBERNAMENTAL, True, {"json": {"nombre": "PRUEBA notebook"}}, None),
        ("GET", "/notebooks", USUARIO_GUBERNAMENTAL, True, {}, None),
        ("GET", "/notebooks/{notebook_id}/documentos", USUARIO_GUBERNAMENTAL, True, {"parametros": _N}, None),
        ("GET", "/notebooks/{notebook_id}/documentos/{documento_id}/archivo", USUARIO_GUBERNAMENTAL, True, {"parametros": _N}, None),
        ("DELETE", "/notebooks/{notebook_id}/documentos/{documento_id}", USUARIO_GUBERNAMENTAL, True, {"parametros": _N}, None),
    ]),
)


def ruta_de_ejemplo(clave: Clave, clasificacion: Mapping[Clave, Clasificacion] = CLASIFICACION) -> str:
    """La ruta concreta de la entrada: su plantilla con los valores `PRUEBA` de `ejemplo["parametros"]`, sin consulta."""
    entrada = clasificacion[clave]
    valores = entrada.ejemplo.get("parametros", {})
    return re.sub(r"{(\w+)}", lambda parametro: str(valores[parametro.group(1)]), clave[1])


def exigir_tabla_completa(app, clasificacion: Mapping[Clave, Clasificacion] = CLASIFICACION) -> None:
    """RA-02.12: falla (`AssertionError`) nombrando las rutas registradas sin clasificar y las clasificadas que ya no existen."""
    registradas = rutas_registradas(app)
    clasificadas = set(clasificacion)
    sin_clasificar = sorted(registradas - clasificadas)
    inexistentes = sorted(clasificadas - registradas)

    problemas = []
    if sin_clasificar:
        problemas.append("Rutas registradas sin clasificar (agréguelas a la tabla): " + "; ".join(
            f"{metodo} {plantilla}" for metodo, plantilla in sin_clasificar))
    if inexistentes:
        problemas.append("Rutas clasificadas que ya no existen en la aplicación (quítelas de la tabla): " + "; ".join(
            f"{metodo} {plantilla}" for metodo, plantilla in inexistentes))
    assert not problemas, " | ".join(problemas)
