"""
Módulo común para funcionalidades compartidas de RNDC.
Contiene constantes, funciones de login y navegación comunes.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from _utils.config import obtener_credenciales


# ============================================================================
# CONSTANTES GLOBALES
# ============================================================================
URL_LOGIN = "https://rndc.mintransporte.gov.co/MenuPrincipal/tabid/204/language/es-MX/Default.aspx?returnurl=%2fMenuPrincipal%2ftabid%2f204%2flanguage%2fes-MX%2fDefault.aspx"
URL_FORMULARIO_REMESAS = "https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirRemesa/mid/396/procesoid/5/default.aspx"
URL_FORMULARIO_MANIFIESTOS = "https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirManifiesto/mid/396/procesoid/6/default.aspx"

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
    try:
        # Obtener credenciales desde variables de entorno
        USUARIO, CONTRASENA = obtener_credenciales()
        
        driver.get(URL_LOGIN)
        WebDriverWait(driver, TIMEOUT_MEDIO).until(
            EC.presence_of_element_located((By.ID, "dnn_ctr580_FormLogIn_edUsername"))
        )
        
        driver.find_element(By.ID, "dnn_ctr580_FormLogIn_edUsername").send_keys(USUARIO)
        driver.find_element(By.ID, "dnn_ctr580_FormLogIn_edPassword").send_keys(CONTRASENA)
        driver.find_element(By.ID, "dnn_ctr580_FormLogIn_btIngresar").click()
        
        # Esperar a que el login sea exitoso (verificando presencia del menú)
        WebDriverWait(driver, TIMEOUT_MEDIO).until(
            EC.presence_of_element_located((By.ID, "tddnn_dnnSOLPARTMENU_ctldnnSOLPARTMENU120"))
        )
        
    except Exception as e:
        raise Exception(f"Error en login: {str(e)}")


def limpiar_almacenamiento(driver):
    """
    Limpia el almacenamiento local y de sesión del navegador.
    Esto ayuda a evitar problemas con datos cacheados.
    
    Args:
        driver: WebDriver de Selenium
    """
    try:
        driver.execute_script("window.localStorage.clear();")
        driver.execute_script("window.sessionStorage.clear();")
    except Exception:
        # Si falla la limpieza, continuar de todas formas
        pass


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