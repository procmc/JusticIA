"""
Script para insertar datos iniciales básicos en la base de datos
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db
from app.db.models.estado import T_Estado
from app.db.models.rol import T_Rol

def insertar_estados():
    """Inserta los estados básicos"""
    db = next(get_db())
    
    try:
        # Verificar si ya existen estados
        if db.query(T_Estado).count() > 0:
            print("Los estados ya existen")
            return
        
        estados = [
            T_Estado(CT_Nombre_estado="Activo", CT_Descripcion="Usuario activo en el sistema"),
            T_Estado(CT_Nombre_estado="Inactivo", CT_Descripcion="Usuario inactivo"),
            T_Estado(CT_Nombre_estado="Suspendido", CT_Descripcion="Usuario suspendido temporalmente")
        ]
        
        for estado in estados:
            db.add(estado)
        
        db.commit()
        print("Estados insertados correctamente")
        
    except Exception as e:
        db.rollback()
        print(f"Error al insertar estados: {e}")
    finally:
        db.close()

def insertar_roles():
    """Inserta los roles básicos"""
    db = next(get_db())
    
    try:
        # Verificar si ya existen roles
        if db.query(T_Rol).count() > 0:
            print("Los roles ya existen")
            return
        
        roles = [
            T_Rol(CT_Nombre_rol="Administrador", CT_Descripcion="Acceso completo al sistema"),
            T_Rol(CT_Nombre_rol="Usuario", CT_Descripcion="Usuario estándar del sistema"),
            T_Rol(CT_Nombre_rol="Consultor", CT_Descripcion="Solo puede consultar información")
        ]
        
        for rol in roles:
            db.add(rol)
        
        db.commit()
        print("Roles insertados correctamente")
        
    except Exception as e:
        db.rollback()
        print(f"Error al insertar roles: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Insertando datos iniciales...")
    insertar_estados()
    insertar_roles()
    print("Proceso completado")
