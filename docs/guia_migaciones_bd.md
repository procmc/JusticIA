# Guía de Migraciones de Base de Datos

## Descripción General

Este documento describe el procedimiento para realizar migraciones de base de datos en el sistema JusticIA utilizando Alembic. Se presenta un ejemplo práctico de agregar un nuevo campo a una tabla existente, siguiendo las mejores prácticas de desarrollo backend.

## Alcance

Esta guía cubre únicamente los cambios del lado del backend. No incluye modificaciones en el frontend.

---

## Ejemplo: Agregar Campo "Estado del Proceso" a Expediente

El siguiente ejemplo ilustra el proceso completo para agregar un nuevo campo llamado "Estado del Proceso" a la tabla de expedientes.

---

## Paso 1: Modificar el Modelo

**Archivo:** `backend/app/db/models/expediente.py`

Agregar la nueva columna utilizando la sintaxis moderna de SQLAlchemy 2.0:

```python
from typing import Optional
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

class T_Expediente(Base):
    # ... campos existentes
    
    # Nuevo campo agregado
    CT_Estado_proceso: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
```

**Explicación de la sintaxis:**

- `Mapped[Optional[str]]`: Type hint que indica el tipo de dato Python (`str` o `None`)
- `mapped_column()`: Función moderna de SQLAlchemy 2.0 que reemplaza `Column()`
- `String(100)`: Tipo de dato en la base de datos (VARCHAR con longitud máxima)
- `nullable=True`: Permite valores NULL en la base de datos

**Correspondencia de tipos comunes:**

| Tipo Python | Tipo SQLAlchemy | nullable |
|-------------|-----------------|----------|
| `Mapped[str]` | `String(n)` | `False` |
| `Mapped[Optional[str]]` | `String(n)` | `True` |
| `Mapped[int]` | `Integer` o `BigInteger` | `False` |
| `Mapped[Optional[int]]` | `Integer` o `BigInteger` | `True` |
| `Mapped[datetime]` | `DateTime` | `False` |
| `Mapped[Optional[datetime]]` | `DateTime` | `True` |
| `Mapped[bool]` | `Boolean` | `False` |

**Nota:** Para campos obligatorios use `Mapped[tipo]` sin `Optional`, y `nullable=False` en `mapped_column()`.

---

## Paso 2: Crear Migración

Desde la carpeta `backend/`:

```bash
# Con Docker
docker-compose exec backend alembic revision --autogenerate -m "Agregar campo estado_proceso"

# Sin Docker
alembic revision --autogenerate -m "Agregar campo estado_proceso"
```

---

## Paso 3: Aplicar Migración

```bash
# Con Docker
docker-compose exec backend alembic upgrade head

# Sin Docker
alembic upgrade head
```

---

## Paso 4: Actualizar Schema

**Archivo:** `backend/app/schemas/expediente_schemas.py`

```python
class ExpedienteBase(BaseModel):
    # ... campos existentes
    estado_proceso: Optional[str] = None  # Nuevo campo
```

---

## Paso 5: Actualizar Repository

**Archivo:** `backend/app/repositories/expediente_repository.py`

```python
def crear_expediente(self, db, numero, descripcion, usuario_id, estado_proceso=None):
    expediente = T_Expediente(
        # ... campos existentes
        CT_Estado_proceso=estado_proceso  # Nuevo campo
    )
    db.add(expediente)
    db.commit()
    return expediente
```

---

## Paso 6: Actualizar Service

**Archivo:** `backend/app/services/expediente_service.py`

```python
def _mapear_expediente_respuesta(self, expediente):
    return ExpedienteRespuesta(
        # ... campos existentes
        estado_proceso=expediente.CT_Estado_proceso  # Nuevo campo
    )
```

---

## Paso 7: Actualizar Endpoint

**Archivo:** `backend/app/routes/expedientes.py`

```python
@router.post("/")
async def crear_expediente(
    expediente: ExpedienteCrear,  # Ya incluye el nuevo campo del schema
    db: Session = Depends(get_db)
):
    return service.crear_expediente(
        db,
        expediente.numero_expediente,
        expediente.descripcion,
        usuario_id,
        expediente.estado_proceso  # Nuevo parámetro
    )
```

---

## Verificación de Cambios

**Opción 1: Swagger UI**

1. Acceder a la documentación interactiva: `http://localhost:8000/docs`
2. Localizar el endpoint correspondiente
3. Probar la funcionalidad incluyendo el nuevo campo

**Opción 2: Curl**
```bash
curl -X POST "http://localhost:8000/expedientes" \
  -H "Content-Type: application/json" \
  -d '{
    "numero_expediente": "01-000001-0001-LA",
    "descripcion": "Test",
    "estado_proceso": "En Trámite"
  }'
```

---

## Reversión de Cambios

### Opción 1: Deshacer última migración

```bash
# Con Docker
docker-compose exec backend alembic downgrade -1

# Sin Docker
alembic downgrade -1
```

Este comando revierte la última migración aplicada, eliminando automáticamente el campo de la base de datos.

### Opción 2: Volver a una migración específica

```bash
# Ver historial de migraciones
alembic history

# Volver a una migración específica
alembic downgrade <revision_id>
```

### Opción 3: Eliminación manual de archivos

**ADVERTENCIA:** Esta opción NO es recomendada para entornos de producción.

Solo aplicable si la migración no ha sido ejecutada en producción:

1. Eliminar el archivo de migración: `backend/alembic/versions/xxxx_agregar_campo.py`
2. Revertir cambios en el código utilizando Git

**IMPORTANTE:** Esta opción solo debe utilizarse en entornos de desarrollo y si la migración no ha sido aplicada en ningún ambiente productivo.

---

## Comandos de Referencia

```bash
# Ver todas las migraciones
alembic history

# Ver migración actual
alembic current

# Deshacer última migración
alembic downgrade -1

# Volver al inicio (vaciar BD)
alembic downgrade base

# Ver SQL sin ejecutar
alembic upgrade head --sql
```