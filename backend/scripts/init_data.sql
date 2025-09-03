-- Script de inicialización de datos básicos para JusticIA
-- Base de datos: SQL Server
-- Fecha: 2025-09-03

-- ============================================
-- TABLA: T_Estado_procesamiento
-- ============================================
INSERT INTO T_Estado_procesamiento (CT_Nombre_estado) VALUES 
('Pendiente'),
('Procesado'), 
('Error');

-- ============================================
-- TABLA: T_Rol
-- ============================================
INSERT INTO T_Rol (CT_Nombre_rol) VALUES 
('Administrador'),
('Usuario Judicial');

-- ============================================
-- TABLA: T_Estado
-- ============================================
INSERT INTO T_Estado (CT_Nombre_estado) VALUES 
('Activo'),
('Inactivo');

-- ============================================
-- TABLA: T_Tipo_accion
-- ============================================
INSERT INTO T_Tipo_accion (CT_Nombre_tipo_accion) VALUES 
('Consulta'),
('Carga Documentos'),
('Busqueda Similares'),
('Login'),
('Crear_Usuario'),
('Editar_Usuario'),
('Consultar_Bitacora'),
('Exportar Bitacora');

-- ============================================
-- VERIFICACIÓN DE DATOS INSERTADOS
-- ============================================

-- Verificar T_Estado_procesamiento
SELECT 'T_Estado_procesamiento' as Tabla, COUNT(*) as Total_Registros FROM T_Estado_procesamiento
UNION ALL
-- Verificar T_Rol
SELECT 'T_Rol' as Tabla, COUNT(*) as Total_Registros FROM T_Rol
UNION ALL
-- Verificar T_Estado
SELECT 'T_Estado' as Tabla, COUNT(*) as Total_Registros FROM T_Estado
UNION ALL
-- Verificar T_Tipo_accion
SELECT 'T_Tipo_accion' as Tabla, COUNT(*) as Total_Registros FROM T_Tipo_accion;

-- Fin del script
