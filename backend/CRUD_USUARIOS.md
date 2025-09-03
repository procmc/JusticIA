# CRUD de Usuarios - JusticIA API

## Descripción
Este módulo implementa un sistema completo de gestión de usuarios (CRUD) para la aplicación JusticIA. En lugar de implementar eliminación física de registros, se utiliza un sistema de cambio de estado para mantener la integridad de los datos.

## Estructura del Sistema

### Modelos de Base de Datos
- **T_Usuario**: Tabla principal de usuarios
- **T_Estado**: Estados disponibles para usuarios (Activo, Inactivo, Suspendido, Pendiente)
- **T_Rol**: Roles del sistema (Administrador, Usuario, Analista, Supervisor)

### Componentes Implementados

#### 1. Schemas (`app/schemas/usuario_schemas.py`)
- `UsuarioBase`: Esquema base con validaciones
- `UsuarioCrear`: Para crear nuevos usuarios
- `UsuarioActualizar`: Para actualizar usuarios existentes
- `UsuarioCambiarEstado`: Para cambiar el estado del usuario
- `UsuarioRespuesta`: Respuesta completa con relaciones
- `UsuarioLista`: Lista paginada de usuarios

#### 2. Repository (`app/repositories/usuario_repository.py`)
- Operaciones CRUD en la base de datos
- Encriptación de contraseñas con bcrypt
- Validaciones de unicidad
- Búsquedas con filtros y paginación

#### 3. Service (`app/services/usuario_service.py`)
- Lógica de negocio
- Validaciones de integridad
- Manejo de errores y excepciones
- Autenticación de usuarios

#### 4. Routes (`app/routes/usuarios.py`)
- Endpoints REST API
- Documentación automática con FastAPI
- Validación de parámetros

## Endpoints Disponibles

### Gestión de Usuarios

#### `GET /usuarios/`
Obtiene una lista paginada de usuarios con filtros opcionales.

**Parámetros de consulta:**
- `pagina`: Número de página (mínimo 1)
- `tamaño_pagina`: Usuarios por página (1-100)
- `filtro_busqueda`: Búsqueda por nombre o correo
- `id_estado`: Filtrar por estado específico
- `id_rol`: Filtrar por rol específico

**Ejemplo:**
```
GET /usuarios/?pagina=1&tamaño_pagina=10&filtro_busqueda=juan&id_estado=1
```

#### `GET /usuarios/{usuario_id}`
Obtiene un usuario específico por su ID.

#### `POST /usuarios/`
Crea un nuevo usuario.

**Body ejemplo:**
```json
{
  "nombre_usuario": "juan.perez",
  "correo": "juan.perez@justicia.gob.co",
  "contrasenna": "password123",
  "id_rol": 2,
  "id_estado": 1
}
```

#### `PUT /usuarios/{usuario_id}`
Actualiza un usuario existente.

**Body ejemplo:**
```json
{
  "nombre_usuario": "juan.perez.nuevo",
  "correo": "juan.nuevo@justicia.gob.co",
  "id_rol": 3
}
```

#### `PATCH /usuarios/{usuario_id}/estado`
Cambia el estado de un usuario (alternativa a eliminación).

**Body ejemplo:**
```json
{
  "id_estado": 2
}
```

### Catálogos

#### `GET /usuarios/catalogo/roles`
Obtiene todos los roles disponibles.

#### `GET /usuarios/catalogo/estados`
Obtiene todos los estados disponibles.

### Autenticación

#### `POST /usuarios/autenticar`
Autentica un usuario con correo y contraseña.

### Información Adicional

#### `GET /usuarios/{usuario_id}/estado`
Obtiene el estado actual de un usuario.

#### `GET /usuarios/{usuario_id}/rol`
Obtiene el rol actual de un usuario.

## Estados del Sistema

1. **Activo (ID: 1)**: Usuario habilitado para usar el sistema
2. **Inactivo (ID: 2)**: Usuario temporalmente deshabilitado
3. **Suspendido (ID: 3)**: Usuario suspendido por violaciones
4. **Pendiente (ID: 4)**: Usuario en proceso de activación

## Roles del Sistema

1. **Administrador (ID: 1)**: Acceso completo al sistema
2. **Usuario (ID: 2)**: Acceso básico para consultas
3. **Analista (ID: 3)**: Acceso para análisis de datos
4. **Supervisor (ID: 4)**: Acceso para supervisión y reportes

## Seguridad

- **Encriptación**: Las contraseñas se encriptan usando bcrypt
- **Validaciones**: Correo y nombre de usuario únicos
- **Estados**: En lugar de eliminar usuarios, se cambia su estado
- **Validación de datos**: Schemas de Pydantic con validaciones

## Instalación de Dependencias

Asegúrate de tener instaladas las siguientes dependencias:

```bash
pip install fastapi
pip install sqlalchemy
pip install pydantic[email]
pip install passlib[bcrypt]
```

## Uso

1. **Insertar datos iniciales:**
```bash
python insertar_datos_iniciales.py
```

2. **Iniciar el servidor:**
```bash
uvicorn main:app --reload
```

3. **Acceder a la documentación:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Ejemplos de Uso

### Crear un usuario administrador
```bash
curl -X POST "http://localhost:8000/usuarios/" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre_usuario": "admin",
    "correo": "admin@justicia.gob.co",
    "contrasenna": "admin123",
    "id_rol": 1,
    "id_estado": 1
  }'
```

### Buscar usuarios activos
```bash
curl "http://localhost:8000/usuarios/?id_estado=1&pagina=1&tamaño_pagina=10"
```

### Desactivar un usuario (en lugar de eliminarlo)
```bash
curl -X PATCH "http://localhost:8000/usuarios/1/estado" \
  -H "Content-Type: application/json" \
  -d '{"id_estado": 2}'
```

## Notas Importantes

- **No hay eliminación física**: Los usuarios se desactivan cambiando su estado
- **Unicidad**: Correo y nombre de usuario deben ser únicos
- **Paginación**: Todos los listados están paginados para mejorar rendimiento
- **Filtros**: Se pueden combinar múltiples filtros en las búsquedas
- **Relaciones**: Los usuarios siempre incluyen información de rol y estado
