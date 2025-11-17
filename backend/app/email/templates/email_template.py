"""
Plantilla HTML/CSS para correos electrónicos
Extraída del servicio para separar presentación de lógica
"""
from typing import Dict, Any, Optional

class EmailTemplate:
    """Manejador de plantillas HTML para correos electrónicos"""
    
    def obtener_estilos_css(self) -> str:
        """
        Estilos CSS para los correos electrónicos
        Extraídos del email_service.py original
        """
        return """
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 20px; border-radius: 8px; }
        .header { background: #2563eb; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
        .content { background: white; padding: 30px; border-radius: 0 0 8px 8px; }
        .password { background: #f3f4f6; padding: 15px; border-radius: 4px; font-family: monospace; font-size: 18px; font-weight: bold; text-align: center; margin: 20px 0; }
        .footer { text-align: center; color: #666; margin-top: 20px; }
        .info-box { background: #f8f9fc; border: 1px solid #e1e5e9; border-radius: 6px; padding: 20px; margin: 25px 0; }
        .credential-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #eee; }
        .credential-row:last-child { border-bottom: none; }
        .credential-label { font-weight: 600; color: #666; }
        .credential-value { font-family: 'Courier New', monospace; background-color: #e9ecef; padding: 4px 8px; border-radius: 4px; font-size: 14px; }
        .alert { background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 6px; margin: 20px 0; }
        """
    
    @staticmethod
    def obtener_plantilla_base() -> str:
        """
        Estructura HTML base extraída del email_service.py
        """
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                {estilos}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{titulo_sistema}</h1>
                </div>
                <div class="content">
                    {contenido}
                </div>
                <div class="footer">
                    <p>Este es un mensaje automático, no responder a este correo.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def generar_correo_credenciales(
        self,
        usuario_nombre: str,
        password: str,
        titulo_sistema: str = "JusticIA"
    ) -> str:
        """
        Genera el HTML completo para correos de credenciales
        Usando la estructura original del email_service.py
        """
        estilos = self.obtener_estilos_css()
        
        contenido = f"""
        <h2>Hola {usuario_nombre},</h2>
        <p>Se ha creado tu cuenta en el sistema JusticIA. Tu contraseña de acceso es:</p>
        
        <div class="password">{password}</div>
        
        <p><strong>Importante:</strong></p>
        <ul>
            <li>Guarda esta contraseña en un lugar seguro</li>
            <li>Se recomienda cambiarla después del primer acceso</li>
            <li>No compartas esta información con terceros</li>
        </ul>
        
        <p>Puedes acceder al sistema usando tu email y esta contraseña.</p>
        """
        
        plantilla_base = EmailTemplate.obtener_plantilla_base()
        
        return plantilla_base.format(
            estilos=estilos,
            titulo_sistema=titulo_sistema,
            contenido=contenido
        )
    
    def generar_correo_universal(
        self,
        asunto: str,
        titulo: str,
        mensaje: str,
        datos_adicionales: Optional[Dict[str, Any]] = None,
        mostrar_credenciales: bool = False,
        credenciales: Optional[Dict[str, str]] = None,
        titulo_sistema: str = "JusticIA"
    ) -> str:
        """
        Genera HTML para cualquier tipo de correo usando la misma plantilla base
        """
        estilos = self.obtener_estilos_css()
        
        # Contenido principal
        contenido = f"""
        <h2>{titulo}</h2>
        <p>{mensaje}</p>
        """
        
        # Sección de credenciales (opcional)
        if mostrar_credenciales and credenciales:
            contenido += """
            <div class="info-box">
                <h3>Información de Acceso</h3>
            """
            for label, valor in credenciales.items():
                contenido += f"""
                <div class="credential-row">
                    <span class="credential-label">{label}:</span>
                    <span class="credential-value">{valor}</span>
                </div>
                """
            contenido += "</div>"
        
        # Datos adicionales (opcional)
        if datos_adicionales:
            contenido += """
            <div class="info-box">
                <h3>Información Adicional</h3>
            """
            for label, valor in datos_adicionales.items():
                contenido += f"""
                <div class="credential-row">
                    <span class="credential-label">{label}:</span>
                    <span class="credential-value">{valor}</span>
                </div>
                """
            contenido += "</div>"
        
        plantilla_base = EmailTemplate.obtener_plantilla_base()
        
        return plantilla_base.format(
            estilos=estilos,
            titulo_sistema=titulo_sistema,
            contenido=contenido
        )
    
    def obtener_texto_plano_credenciales(self, usuario_nombre: str, password: str) -> str:
        """
        Versión texto plano para correos de credenciales
        Extraída del email_service.py original
        """
        return f"""
        Hola {usuario_nombre},

        Se ha creado tu cuenta en el sistema JusticIA.
        Tu contraseña de acceso es: {password}

        Importante:
        - Guarda esta contraseña en un lugar seguro
        - Se recomienda cambiarla después del primer acceso
        - No compartas esta información con terceros

        Puedes acceder al sistema usando tu email y esta contraseña.

        --
        Sistema JusticIA
        """
