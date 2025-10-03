"""
Módulo común para funcionalidades compartidas de RNDC.
Contiene constantes, funciones de login y navegación comunes.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ============================================================================
# CONSTANTES GLOBALES
# ============================================================================
URL_LOGIN = "https://rndc.mintransporte.gov.co/MenuPrincipal/tabid/204/language/es-MX/Default.aspx?returnurl=%2fMenuPrincipal%2ftabid%2f204%2flanguage%2fes-MX%2fDefault.aspx"
URL_FORMULARIO_REMESAS = "https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirRemesa/mid/396/procesoid/5/default.aspx"
URL_FORMULARIO_MANIFIESTOS = "https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirManifiesto/mid/396/procesoid/6/default.aspx"

USUARIO = "Sotranscolombianos1@0341"
CONTRASENA = "053EPA746**"

TIMEOUT_CORTO = 3
TIMEOUT_MEDIO = 10


# ============================================================================
# FUNCIONES COMUNES
# ============================================================================
def hacer_login(driver):
    """
    Realiza el login en el sistema RNDC.
    Esta función es compartida por remesas y manifiestos.
    
    Args:
        driver: WebDriver de Selenium
    """
    driver.get(URL_LOGIN)
    WebDriverWait(driver, TIMEOUT_MEDIO).until(
        EC.presence_of_element_located((By.ID, "dnn_ctr580_FormLogIn_edUsername"))
    )
    
    driver.find_element(By.ID, "dnn_ctr580_FormLogIn_edUsername").send_keys(USUARIO)
    driver.find_element(By.ID, "dnn_ctr580_FormLogIn_edPassword").send_keys(CONTRASENA)
    driver.find_element(By.ID, "dnn_ctr580_FormLogIn_btIngresar").click()
    
    WebDriverWait(driver, TIMEOUT_MEDIO).until(
        EC.presence_of_element_located((By.ID, "tddnn_dnnSOLPARTMENU_ctldnnSOLPARTMENU120"))
    )


def limpiar_almacenamiento(driver):
    """
    Limpia el almacenamiento local y de sesión del navegador.
    
    Args:
        driver: WebDriver de Selenium
    """
    driver.execute_script("window.localStorage.clear();")
    driver.execute_script("window.sessionStorage.clear();")


def navegar_a_remesas(driver):
    """
    Limpia el almacenamiento y navega al formulario de remesas.
    
    Args:
        driver: WebDriver de Selenium
    """
    limpiar_almacenamiento(driver)
    driver.get(URL_FORMULARIO_REMESAS)
    WebDriverWait(driver, TIMEOUT_MEDIO).until(
        EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA"))
    )


def navegar_a_manifiestos(driver):
    """
    Limpia el almacenamiento y navega al formulario de manifiestos.
    
    Args:
        driver: WebDriver de Selenium
    """
    limpiar_almacenamiento(driver)
    driver.get(URL_FORMULARIO_MANIFIESTOS)
    WebDriverWait(driver, TIMEOUT_MEDIO).until(
        EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirManifiesto_NUMMANIFIESTOCARGA"))
    )