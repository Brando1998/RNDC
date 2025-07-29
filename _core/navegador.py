import os
import sys
import platform
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

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
    return webdriver.Chrome(service=service, options=chrome_options)