"""
Script para verificar la creación de usuarios y datos básicos de la BD
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db
from app.db.models.usuario import T_Usuario
from app.db.models.estado import T_Estado
from app.db.models.rol import T_Rol
from app.repositories.usuario_repository import UsuarioRepository

def verificar_datos_basicos():
    """Verifica que existan datos básicos en la BD"""
    db = next(get_db())
    
    print("=== Verificando Estados ===")
    estados = db.query(T_Estado).all()
    for estado in estados:
        print(f"ID: {estado.CN_Id_estado}, Nombre: {estado.CT_Nombre_estado}")
    
    print("\n=== Verificando Roles ===")
    roles = db.query(T_Rol).all()
    for rol in roles:
        print(f"ID: {rol.CN_Id_rol}, Nombre: {rol.CT_Nombre_rol}")
    
    print("\n=== Verificando Usuarios Existentes ===")
    usuarios = db.query(T_Usuario).all()
    print(f"Total usuarios: {len(usuarios)}")
    for usuario in usuarios:
        print(f"ID: {usuario.CN_Id_usuario}, Usuario: {usuario.CT_Nombre_usuario}, Email: {usuario.CT_Correo}")
    
    db.close()

def probar_crear_usuario():
    """Prueba crear un usuario"""
    db = next(get_db())
    repo = UsuarioRepository()
    
    try:
        print("\n=== Intentando crear usuario de prueba ===")
        usuario = repo.crear_usuario(
            db, 
            nombre_usuario="test_user", 
            correo="test@test.com", 
            contrasenna="test123", 
            id_rol=1
        )
        print(f"Usuario creado exitosamente: {usuario.CT_Nombre_usuario}")
        return True
    except Exception as e:
        print(f"Error al crear usuario: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("Verificando base de datos...")
    verificar_datos_basicos()
    probar_crear_usuario()
