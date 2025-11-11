import os
import sys
import platform
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
from tkinter import messagebox

def resource_path(relative_path):
    # ✅ Detecta si está corriendo como .exe (PyInstaller)
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def crear_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)

    if platform.system() == "Windows":
        driver_path = resource_path("drivers/chromedriver.exe")
    else:
        driver_path = resource_path("drivers/chromedriver")

    service = Service(driver_path)
    
    try:
        return webdriver.Chrome(service=service, options=chrome_options)
    except SessionNotCreatedException as e:
        error_msg = str(e).lower()
        
        # Detectar si es porque Chrome no está instalado
        if "cannot find chrome binary" in error_msg or "chrome binary" in error_msg:
            messagebox.showerror(
                "Chrome No Encontrado",
                "❌ No se pudo encontrar Google Chrome instalado en tu computadora.\n\n"
                "Para usar esta aplicación necesitas:\n\n"
                "1️⃣ Instalar Google Chrome desde:\n"
                "   https://www.google.com/chrome/\n\n"
                "2️⃣ Reiniciar esta aplicación\n\n"
                "Si ya tienes Chrome instalado, puede estar en una ubicación no estándar.\n"
                "Contacta al desarrollador para configurar la ruta personalizada."
            )
            raise SystemExit("Chrome no instalado")
        else:
            # Otro error de sesión
            messagebox.showerror(
                "Error al Iniciar Chrome",
                f"❌ No se pudo iniciar Chrome.\n\n"
                f"Error: {str(e)[:200]}\n\n"
                f"Posibles soluciones:\n"
                f"• Cierra todas las ventanas de Chrome\n"
                f"• Reinicia tu computadora\n"
                f"• Reinstala Google Chrome"
            )
            raise
    except WebDriverException as e:
        messagebox.showerror(
            "Error de ChromeDriver",
            f"❌ Error al iniciar el navegador.\n\n"
            f"Error: {str(e)[:200]}\n\n"
            f"Posibles causas:\n"
            f"• ChromeDriver no compatible con tu versión de Chrome\n"
            f"• ChromeDriver corrupto o bloqueado por antivirus\n"
            f"• Permisos insuficientes"
        )
        raise