"""
Script para insertar datos iniciales necesarios para el sistema de usuarios
"""
from sqlalchemy.orm import Session
from app.db.database import get_db, engine
from app.db.models.estado import T_Estado
from app.db.models.rol import T_Rol


def insertar_estados_iniciales(db: Session):
    """Inserta los estados básicos del sistema"""
    estados_iniciales = [
        {"nombre": "Activo"},
        {"nombre": "Inactivo"},
        {"nombre": "Suspendido"},
        {"nombre": "Pendiente"}
    ]
    
    print("Insertando estados iniciales...")
    for estado_data in estados_iniciales:
        # Verificar si el estado ya existe
        estado_existente = db.query(T_Estado).filter(
            T_Estado.CT_Nombre_estado == estado_data["nombre"]
        ).first()
        
        if not estado_existente:
            nuevo_estado = T_Estado(CT_Nombre_estado=estado_data["nombre"])
            db.add(nuevo_estado)
            print(f"  - Estado '{estado_data['nombre']}' agregado")
        else:
            print(f"  - Estado '{estado_data['nombre']}' ya existe")
    
    db.commit()


def insertar_roles_iniciales(db: Session):
    """Inserta los roles básicos del sistema"""
    roles_iniciales = [
        {"nombre": "Administrador"},
        {"nombre": "Usuario"},
        {"nombre": "Analista"},
        {"nombre": "Supervisor"}
    ]
    
    print("Insertando roles iniciales...")
    for rol_data in roles_iniciales:
        # Verificar si el rol ya existe
        rol_existente = db.query(T_Rol).filter(
            T_Rol.CT_Nombre_rol == rol_data["nombre"]
        ).first()
        
        if not rol_existente:
            nuevo_rol = T_Rol(CT_Nombre_rol=rol_data["nombre"])
            db.add(nuevo_rol)
            print(f"  - Rol '{rol_data['nombre']}' agregado")
        else:
            print(f"  - Rol '{rol_data['nombre']}' ya existe")
    
    db.commit()


def main():
    """Función principal para insertar datos iniciales"""
    print("🔄 Insertando datos iniciales para el sistema de usuarios...")
    
    # Crear sesión de base de datos
    db = next(get_db())
    
    try:
        # Insertar estados iniciales
        insertar_estados_iniciales(db)
        
        # Insertar roles iniciales
        insertar_roles_iniciales(db)
        
        print("✅ Datos iniciales insertados correctamente")
        
        # Mostrar resumen
        total_estados = db.query(T_Estado).count()
        total_roles = db.query(T_Rol).count()
        
        print(f"\n📊 Resumen:")
        print(f"  - Total de estados: {total_estados}")
        print(f"  - Total de roles: {total_roles}")
        
    except Exception as e:
        print(f"❌ Error al insertar datos iniciales: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
