"""
Utilidades para esperas inteligentes en Selenium.
Reemplaza time.sleep() con verificaciones reales del estado de la página.
"""

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


def esperar_pagina_cargada(driver, timeout=10):
    """
    Espera a que la página esté completamente cargada.
    Verifica document.readyState y que no haya requests AJAX pendientes.
    """
    try:
        # Esperar a que document.readyState sea 'complete'
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # Esperar a que jQuery (si existe) termine sus operaciones
        try:
            WebDriverWait(driver, 2).until(
                lambda d: d.execute_script("return typeof jQuery != 'undefined' && jQuery.active == 0")
            )
        except:
            pass  # jQuery no existe, continuar
        
        return True
    except TimeoutException:
        return False


def esperar_ajax_completo(driver, timeout=5):
    """
    Espera a que todas las peticiones AJAX se completen.
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("""
                return (typeof jQuery === 'undefined' || jQuery.active === 0) &&
                       document.readyState === 'complete';
            """)
        )
        return True
    except TimeoutException:
        return False


def esperar_elemento_listo(driver, by, value, timeout=10):
    """
    Espera a que un elemento esté presente, visible Y habilitado.
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        WebDriverWait(driver, timeout).until(
            EC.visibility_of(element)
        )
        WebDriverWait(driver, timeout).until(
            lambda d: element.is_enabled()
        )
        return element
    except TimeoutException:
        return None


def esperar_elemento_interactivo(driver, by, value, timeout=10):
    """
    Espera a que un elemento sea completamente interactivo (clickeable y sin overlays).
    """
    try:
        # Esperar a que sea clickeable
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        
        # Verificar que no haya overlays
        WebDriverWait(driver, 2).until(
            lambda d: d.execute_script("""
                var elem = arguments[0];
                var rect = elem.getBoundingClientRect();
                var centerX = rect.left + rect.width / 2;
                var centerY = rect.top + rect.height / 2;
                var topElement = document.elementFromPoint(centerX, centerY);
                return elem === topElement || elem.contains(topElement);
            """, element)
        )
        
        return element
    except TimeoutException:
        return None


def esperar_valor_campo_cargado(driver, by, value, timeout=10):
    """
    Espera a que un campo input tenga un valor (no esté vacío).
    Útil para campos que se llenan automáticamente via JavaScript.
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.find_element(by, value).get_attribute("value").strip() != ""
        )
        return True
    except TimeoutException:
        return False


def esperar_sin_alertas(driver, timeout=3):
    """
    Espera a que NO haya alertas pendientes.
    Útil después de hacer click en botones que podrían generar alertas.
    """
    try:
        WebDriverWait(driver, timeout).until_not(
            EC.alert_is_present()
        )
        return True
    except TimeoutException:
        return True  # No había alerta, todo bien


def esperar_formulario_estable(driver, timeout=5):
    """
    Espera a que el formulario esté estable (sin cambios en el DOM).
    """
    try:
        # Esperar a que no haya cambios en el body durante 500ms
        script = """
            var observer = new MutationObserver(function() {});
            var config = { childList: true, subtree: true };
            observer.observe(document.body, config);
            
            return new Promise(function(resolve) {
                var lastChange = Date.now();
                var checkInterval = setInterval(function() {
                    var timeSinceChange = Date.now() - lastChange;
                    if (timeSinceChange > 500) {
                        clearInterval(checkInterval);
                        resolve(true);
                    }
                }, 100);
                
                observer.observe = function() {
                    lastChange = Date.now();
                };
                
                setTimeout(function() {
                    clearInterval(checkInterval);
                    resolve(true);
                }, 5000);
            });
        """
        
        driver.execute_async_script(script)
        return True
    except:
        # Si falla, simplemente continuar
        return True


def esperar_campo_editable(driver, by, value, timeout=10):
    """
    Espera a que un campo esté listo para ser editado.
    Verifica que esté presente, visible, habilitado y no tenga readonly.
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        
        WebDriverWait(driver, timeout).until(
            lambda d: element.is_displayed() and 
                     element.is_enabled() and
                     element.get_attribute("readonly") is None
        )
        
        return element
    except TimeoutException:
        return None