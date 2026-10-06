---
paths:
  - "backend/main.py"
  - "backend/app/routes/**/*.py"
  - "backend/app/schemas/**/*.py"
  - "frontend/services/**/*.js"
---

# Convenciones de la API

## Rutas (backend)

- Un módulo por archivo en `backend/app/routes/<modulo>.py`, con su `router = APIRouter()`, registrado en `backend/main.py` con `prefix="/<modulo>"` y `tags=["<modulo>"]`. Un módulo nuevo se refleja también en el diagrama de componentes C4.
- Rutas nuevas en español, en minúscula, con guiones y sin tildes ni ñ (`/cambiar-contrasenna`); colecciones en plural (`/notebooks/{notebook_id}/documentos`). El método indica la acción: GET consulta, POST crea, PUT/PATCH edita, DELETE quita.
- Todo endpoint exige rol con una dependencia de `app/auth/jwt_auth.py`: `require_usuario_judicial`, `require_administrador` o `require_usuario_autenticado` (nombres heredados, no se renombran — RT-06). Las únicas excepciones son el inicio de sesión y la recuperación de contraseña (`routes/auth.py`).
- El router es delgado: recibe, llama al servicio, registra en la bitácora y traduce los errores. No usa repositorios, Qdrant ni archivos directamente: eso va en el servicio. (`routes/notebooks.py` lo hace hoy; no copies ese patrón.)
- La sesión de base de datos llega como `db: Session = Depends(get_db)` y se pasa al servicio; el usuario, como `current_user["user_id"]`.
- Los recursos de un usuario (notebooks, conversaciones) se filtran siempre por `current_user["user_id"]`. Si no le pertenece, responde 404, sin revelar que existe.
- Lo pesado (extracción, transcripción, HTR, embeddings) va al Worker de Celery, no dentro de la petición.

## Esquemas (Pydantic)

- En `backend/app/schemas/<modulo>_schemas.py`, no en el archivo de rutas, con nombres en español: `<Entidad>Crear`, `<Entidad>Editar`, `<Entidad>Respuesta` (ver `usuario_schemas.py`).
- Todo endpoint declara `response_model`.
- Campos del JSON en snake_case y en español (`nombre`, `clave_interna`, `fecha_creacion`), nunca con los prefijos de las columnas (`CN_`, `CT_`, `CF_`). Fechas en ISO 8601. En lo nuevo, «tema», no «expediente».
- Para construir la respuesta desde un modelo de SQLAlchemy: `from_attributes = True`.

## Errores

- `HTTPException` con `detail` en español, pensado para el usuario: 400 datos inválidos, 401 sin sesión o token vencido, 403 rol sin permiso, 404 no existe o no le pertenece, 500 error inesperado.
- En un 500, `detail="Error interno del servidor"` y el detalle al log con `logger.exception(...)`. Nunca `detail=str(e)`: expone el funcionamiento interno.

## Bitácora (RF-21)

- Tras una acción exitosa, el router llama al servicio de auditoría de su módulo (`services/bitacora/<modulo>_audit_service.py`) con una constante de `TiposAccion` (`app/constants/tipos_accion.py`). Una acción nueva lleva su constante nueva.

## Servicios del frontend

- Un archivo por módulo en `frontend/services/<modulo>Service.js`: una clase, exportada como instancia por defecto y como clase (`export default notebookService; export { NotebookService };`).
- Siempre a través de `httpService`, que agrega el token de NextAuth y usa `NEXT_PUBLIC_API_URL`; nunca `fetch` directo.
- Cada método devuelve `{ success: true, ... }` o `{ error: true, message }`, con el mensaje en español; si `error.isNetworkError`: «Error de conexión. Verifique su red.».
