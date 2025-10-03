"""
Módulo común para funcionalidades compartidas de RNDC.
Contiene constantes, funciones de login y navegación comunes.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


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
    try:
        driver.get(URL_LOGIN)
        WebDriverWait(driver, TIMEOUT_MEDIO).until(
            EC.presence_of_element_located((By.ID, "dnn_ctr580_FormLogIn_edUsername"))
        )
        
        driver.find_element(By.ID, "dnn_ctr580_FormLogIn_edUsername").send_keys(USUARIO)
        driver.find_element(By.ID, "dnn_ctr580_FormLogIn_edPassword").send_keys(CONTRASENA)
        driver.find_element(By.ID, "dnn_ctr580_FormLogIn_btIngresar").click()
        
        # Esperar a que el login sea exitoso (verificando presencia del menú)
        # Este es el ID correcto que funciona en el sistema RNDC
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


def verificar_conexion(driver):
    """
    Verifica si hay conexión con el servidor RNDC.
    
    Args:
        driver: WebDriver de Selenium
    
    Returns:
        bool: True si hay conexión, False en caso contrario
    """
    try:
        driver.get("https://rndc.mintransporte.gov.co")
        time.sleep(2)
        
        # Verificar que la página cargó correctamente
        page_source = driver.page_source.lower()
        
        # Buscar indicadores de error
        if any(error in page_source for error in [
            "server error",
            "503 service",
            "500 internal",
            "502 bad gateway",
            "504 gateway timeout"
        ]):
            return False
        
        return True
        
    except Exception:
        return False


def esperar_elemento_clickable(driver, by, value, timeout=TIMEOUT_MEDIO, descripcion="elemento"):
    """
    Espera a que un elemento sea clickeable y retorna el elemento.
    
    Args:
        driver: WebDriver de Selenium
        by: Tipo de selector (By.ID, By.XPATH, etc.)
        value: Valor del selector
        timeout: Tiempo máximo de espera en segundos
        descripcion: Descripción del elemento para mensajes de error
    
    Returns:
        WebElement: El elemento encontrado y clickeable
    
    Raises:
        TimeoutException: Si el elemento no se encuentra en el tiempo especificado
    """
    try:
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
    except Exception as e:
        raise Exception(f"No se pudo encontrar {descripcion} (selector: {value}): {str(e)}")


def esperar_presencia_elemento(driver, by, value, timeout=TIMEOUT_MEDIO, descripcion="elemento"):
    """
    Espera a que un elemento esté presente en el DOM.
    
    Args:
        driver: WebDriver de Selenium
        by: Tipo de selector (By.ID, By.XPATH, etc.)
        value: Valor del selector
        timeout: Tiempo máximo de espera en segundos
        descripcion: Descripción del elemento para mensajes de error
    
    Returns:
        WebElement: El elemento encontrado
    
    Raises:
        TimeoutException: Si el elemento no se encuentra en el tiempo especificado
    """
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    except Exception as e:
        raise Exception(f"No se pudo encontrar {descripcion} (selector: {value}): {str(e)}")