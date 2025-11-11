"""
Módulo de configuración para credenciales RNDC.
Lee desde variables de entorno o archivo .env para desarrollo.
"""
import os

def obtener_credenciales():
    """
    Obtiene las credenciales de RNDC desde variables de entorno.
    Para desarrollo, crea un archivo .env con las credenciales.
    """
    usuario = os.getenv("RNDC_USUARIO")
    contrasena = os.getenv("RNDC_CONTRASENA")
    
    # Si no hay variables de entorno, intentar cargar desde .env (solo desarrollo)
    if not usuario or not contrasena:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            usuario = os.getenv("RNDC_USUARIO")
            contrasena = os.getenv("RNDC_CONTRASENA")
        except ImportError:
            pass
    
    # Si aún no hay credenciales, mostrar error
    if not usuario or not contrasena:
        raise ValueError(
            "⚠️ No se encontraron credenciales RNDC.\n\n"
            "Para desarrollo: Crea un archivo .env con:\n"
            "RNDC_USUARIO=tu_usuario\n"
            "RNDC_CONTRASENA=tu_contraseña\n\n"
            "Para producción: Las credenciales se inyectan automáticamente desde GitHub Secrets."
        )
    
    return usuario, contrasena