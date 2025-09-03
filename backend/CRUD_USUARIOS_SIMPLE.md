# CRUD de Usuarios Simplificado

## Descripción
Este CRUD contiene las funciones básicas para manejar usuarios en el sistema JusticIA.

## Funciones Disponibles

### 1. Obtener Todos los Usuarios
- **Ruta:** `GET /usuarios/`
- **Descripción:** Obtiene una lista de todos los usuarios del sistema
- **Respuesta:** Lista de usuarios con sus datos básicos

### 2. Obtener Usuario por ID
- **Ruta:** `GET /usuarios/{usuario_id}`
- **Descripción:** Obtiene un usuario específico por su ID
- **Parámetros:** `usuario_id` (entero)
- **Respuesta:** Datos del usuario o error 404 si no existe

### 3. Crear Usuario
- **Ruta:** `POST /usuarios/`
- **Descripción:** Crea un nuevo usuario en el sistema
- **Body:** 
  ```json
  {
    "nombre_usuario": "string",
    "correo": "string",
    "contrasenna": "string",
    "id_rol": integer
  }
  ```
- **Respuesta:** Usuario creado con todos sus datos

### 4. Editar Usuario
- **Ruta:** `PUT /usuarios/{usuario_id}`
- **Descripción:** Edita los datos básicos de un usuario
- **Parámetros:** `usuario_id` (entero)
- **Body:** 
  ```json
  {
    "nombre_usuario": "string",
    "correo": "string", 
    "id_rol": integer
  }
  ```
- **Respuesta:** Usuario actualizado o error 404 si no existe

### 5. Deshabilitar Usuario
- **Ruta:** `PATCH /usuarios/{usuario_id}/deshabilitar`
- **Descripción:** Deshabilita un usuario cambiando su estado a "Inactivo"
- **Parámetros:** `usuario_id` (entero)
- **Respuesta:** Mensaje de confirmación o error 404 si no existe

## Estructura de Datos

### Usuario
```json
{
  "CN_Id_usuario": integer,
  "CT_Nombre_usuario": "string",
  "CT_Correo": "string",
  "CN_Id_rol": integer,
  "CN_Id_estado": integer
}
```

## Notas Importantes
- En lugar de eliminar usuarios, se cambia su estado a "Inactivo"
- Los usuarios están relacionados con las tablas Estado y Rol
- Todos los endpoints requieren conexión a la base de datos SQL Server
