#!/usr/bin/env python3
"""
Script para probar que los modelos se cargan correctamente
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Importar Base y todos los modelos
from app.db.models import Base, T_Usuario, T_Expediente, T_Documento, T_Bitacora, T_Rol, T_Estado, T_Estado_procesamiento, T_Tipo_accion, T_Usuario_Expediente, T_Expediente_Documento

def main():
    print("Modelos importados correctamente")
    print(f"Base metadata tables: {list(Base.metadata.tables.keys())}")
    print(f"Total de tablas: {len(Base.metadata.tables)}")
    
    # Listar todas las tablas detectadas
    for table_name, table in Base.metadata.tables.items():
        print(f"- {table_name}: {len(table.columns)} columnas")

if __name__ == "__main__":
    main()
