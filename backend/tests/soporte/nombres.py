"""Constantes de la suite de pruebas (spec 002, RA-02.3 y RA-02.7).

Sin importaciones: otros módulos de `tests/soporte/` las usan antes de importar nada del sistema.
"""

# Nombre de la base de datos y de la colección de Qdrant de pruebas. Se compara por igualdad
# exacta (distingue mayúsculas): ningún otro nombre pasa la protección de `proteccion.py`.
NOMBRE_PRUEBAS = "servia_pruebas"

# Prefijo de los datos que crea una prueba (usuarios, notebooks, archivos); permite encontrarlos
# y contarlos como residuos (RA-02.7).
PREFIJO_DATOS = "PRUEBA"

# Tiempo máximo que la suite espera a SQL Server, Qdrant y Tika antes de abortar (RA-02.4).
ESPERA_SERVICIOS_SEGUNDOS = 60
