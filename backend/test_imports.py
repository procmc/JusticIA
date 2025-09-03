"""
Test simple para verificar imports
"""

try:
    print("1. Probando pydantic...")
    from pydantic import BaseModel
    print("✓ Pydantic OK")
    
    print("2. Probando typing...")
    from typing import Optional
    print("✓ Typing OK")
    
    print("3. Probando schemas...")
    from app.schemas.usuario_schemas import RolInfo, EstadoInfo, UsuarioRespuesta
    print("✓ Schemas OK")
    
    print("4. Probando servicio...")
    from app.services.usuario_service import UsuarioService
    print("✓ Servicio OK")
    
    print("¡Todo OK!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
