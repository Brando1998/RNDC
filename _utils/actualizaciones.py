"""
Módulo para verificar actualizaciones de la aplicación al inicio.
"""
import requests
import json
import os
from packaging import version
from tkinter import messagebox

# Versión actual de tu aplicación
VERSION_ACTUAL = "1.0.0"  # Actualiza esto con cada release

# URL del último release en GitHub
GITHUB_API_URL = "https://api.github.com/repos/Brando1998/RNDC/releases/latest"

def verificar_actualizacion():
    """
    Verifica si hay una nueva versión disponible en GitHub.
    Retorna: (hay_actualizacion, version_nueva, url_descarga)
    """
    try:
        response = requests.get(GITHUB_API_URL, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            version_remota = data.get("tag_name", "").replace("v", "")
            
            # Comparar versiones
            if version.parse(version_remota) > version.parse(VERSION_ACTUAL):
                # Buscar el asset del ejecutable
                assets = data.get("assets", [])
                for asset in assets:
                    if asset["name"].endswith(".zip") or asset["name"].endswith(".exe"):
                        return True, version_remota, asset["browser_download_url"]
                
                return True, version_remota, data.get("html_url")
            
        return False, None, None
    
    except Exception as e:
        print(f"Error verificando actualizaciones: {e}")
        return False, None, None


def mostrar_notificacion_actualizacion(version_nueva, url_descarga):
    """
    Muestra un diálogo informando sobre la nueva versión.
    """
    mensaje = f"¡Hay una nueva versión disponible!\n\n"
    mensaje += f"Versión actual: {VERSION_ACTUAL}\n"
    mensaje += f"Nueva versión: {version_nueva}\n\n"
    mensaje += "¿Deseas descargar la actualización?"
    
    respuesta = messagebox.askyesno(
        "Actualización Disponible",
        mensaje,
        icon='info'
    )
    
    if respuesta:
        import webbrowser
        webbrowser.open(url_descarga)
        return True
    
    return False


def verificar_al_iniciar(mostrar_si_actualizado=False):
    """
    Verifica actualizaciones al iniciar la aplicación.
    
    Args:
        mostrar_si_actualizado: Si es True, muestra mensaje aunque esté actualizado
    """
    hay_actualizacion, version_nueva, url_descarga = verificar_actualizacion()
    
    if hay_actualizacion:
        mostrar_notificacion_actualizacion(version_nueva, url_descarga)
    elif mostrar_si_actualizado:
        messagebox.showinfo(
            "Sin Actualizaciones",
            f"Tu aplicación está actualizada.\nVersión: {VERSION_ACTUAL}"
        )


def obtener_version_chromedriver_local():
    """
    Obtiene la versión del ChromeDriver local.
    """
    try:
        import subprocess
        driver_path = os.path.join(".", "drivers", "chromedriver.exe")
        
        if os.path.exists(driver_path):
            result = subprocess.run(
                [driver_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Output típico: "ChromeDriver 120.0.6099.109 (...)"
            output = result.stdout.strip()
            version_str = output.split()[1] if len(output.split()) > 1 else "Unknown"
            return version_str
    except Exception as e:
        print(f"Error obteniendo versión de ChromeDriver: {e}")
    
    return "Unknown"


if __name__ == "__main__":
    # Test
    print(f"Versión actual: {VERSION_ACTUAL}")
    print(f"ChromeDriver local: {obtener_version_chromedriver_local()}")
    verificar_al_iniciar(mostrar_si_actualizado=True)