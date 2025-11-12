"""
Módulo de configuración para credenciales RNDC.
Lee desde variables de entorno, archivo .env o credenciales embebidas.
"""

import os
import sys
import base64

def obtener_credenciales():
    """
    Obtiene las credenciales RNDC desde el entorno, .env o embebidas en el ejecutable.
    """
    usuario = os.getenv("RNDC_USUARIO")
    contrasena = os.getenv("RNDC_CONTRASENA")

    # Si no hay entorno, intentar cargar .env (solo desarrollo)
    if not usuario or not contrasena:
        if os.path.exists(".env"):
            try:
                from dotenv import load_dotenv
                load_dotenv()
                usuario = os.getenv("RNDC_USUARIO")
                contrasena = os.getenv("RNDC_CONTRASENA")
            except ImportError:
                pass

    # Si aún no hay credenciales, intentar leer las embebidas
    if (not usuario or not contrasena) and getattr(sys, 'frozen', False):
        try:
            from _utils import credenciales_embed
            usuario = base64.b64decode(credenciales_embed.USUARIO_EMBEBIDO).decode("utf-8")
            contrasena = base64.b64decode(credenciales_embed.CONTRASENA_EMBEBIDA).decode("utf-8")
        except Exception:
            raise RuntimeError("⚠️ No se pudieron cargar las credenciales embebidas en el ejecutable.")

    # Validar al final
    if not usuario or not contrasena:
        raise RuntimeError("⚠️ No se encontraron credenciales RNDC válidas.")

    return usuario, contrasena
