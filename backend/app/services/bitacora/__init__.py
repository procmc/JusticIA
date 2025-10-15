"""
Módulo de servicios de bitácora (auditoría).

Contiene:
- bitacora_service: Servicio GENERAL (base) para registro genérico (WRITE)
- bitacora_stats_service: Servicio de estadísticas y reportes (READ)
- *_audit_service: Servicios ESPECIALIZADOS para cada módulo

Arquitectura:
    Servicio General (bitacora_service.py) - WRITE operations
         ↓ usado por
    Servicios Especializados (auth_audit, ingesta_audit, etc.)
         ↓ llamados desde
    Routes (auth.py, ingesta.py, etc.)
    
    Servicio de Stats (bitacora_stats_service.py) - READ operations
         ↓ usado por
    Routes de consulta (bitacora.py)
         ↓ llamados desde
    Frontend (Bitacora.jsx, DashboardEstadisticas.jsx, etc.)
"""

# Servicio General (Write)
from .bitacora_service import bitacora_service, BitacoraService

# Servicio de Estadísticas (Read)
from .bitacora_stats_service import bitacora_stats_service, BitacoraStatsService

# Servicios Especializados (Audit)
from .auth_audit_service import auth_audit_service, AuthAuditService
from .ingesta_audit_service import ingesta_audit_service, IngestaAuditService
from .similarity_audit_service import similarity_audit_service, SimilarityAuditService
from .usuarios_audit_service import usuarios_audit_service, UsuariosAuditService

__all__ = [
    # General (Write)
    "bitacora_service",
    "BitacoraService",
    # Estadísticas (Read)
    "bitacora_stats_service",
    "BitacoraStatsService",
    # Especializados (Audit)
    "auth_audit_service",
    "AuthAuditService",
    "ingesta_audit_service",
    "IngestaAuditService",
    "similarity_audit_service",
    "SimilarityAuditService",
    "usuarios_audit_service",
    "UsuariosAuditService",
]
