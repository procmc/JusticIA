#!/usr/bin/env python3
"""
Script para verificar que las tablas se crearon correctamente en la base de datos
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import urllib.parse

# Cargar variables de entorno
load_dotenv()

def verificar_tablas():
    # Construir URL de conexión
    sql_server_host = os.getenv("SQL_SERVER_HOST")
    sql_server_port = os.getenv("SQL_SERVER_PORT", "1433")
    sql_server_database = os.getenv("SQL_SERVER_DATABASE")
    sql_server_user = os.getenv("SQL_SERVER_USER")
    sql_server_password = os.getenv("SQL_SERVER_PASSWORD")
    sql_server_driver = os.getenv("SQL_SERVER_DRIVER", "ODBC Driver 18 for SQL Server")
    
    # Codificar el driver para la URL
    driver_encoded = urllib.parse.quote_plus(sql_server_driver)
    
    database_url = f"mssql+pyodbc://{sql_server_user}:{sql_server_password}@{sql_server_host}:{sql_server_port}/{sql_server_database}?driver={driver_encoded}&TrustServerCertificate=yes"
    
    try:
        # Crear engine y conectar
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            print("CONEXIÓN A SQL SERVER EXITOSA")
            
            # Consultar tablas del usuario
            result = connection.execute(text("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE = 'BASE TABLE' 
                AND TABLE_NAME LIKE 'T_%'
                ORDER BY TABLE_NAME
            """))
            
            tablas = result.fetchall()
            
            print(f"\nTablas creadas en la base de datos ({len(tablas)} encontradas):")
            for tabla in tablas:
                print(f"  ✅ {tabla[0]}")
                
            # Verificar tabla alembic_version
            result = connection.execute(text("""
                SELECT version_num 
                FROM alembic_version
            """))
            
            version = result.fetchone()
            if version:
                print(f"\nVersión actual de Alembic: {version[0]}")
            else:
                print("\n⚠️  No se encontró información de versión de Alembic")
                
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")

if __name__ == "__main__":
    verificar_tablas()
