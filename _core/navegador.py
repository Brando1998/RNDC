import os
import platform
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

def crear_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)
    driver_path = os.path.join(".", "drivers", "chromedriver.exe") if platform.system() == "Windows" else os.path.join(".", "drivers", "chromedriver")
    service = Service(driver_path)
    return webdriver.Chrome(service=service, options=chrome_options)
