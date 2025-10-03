from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from datetime import datetime, timedelta
from tkinter import messagebox
import time
from _utils.logger import registrar_log_remesa, obtener_logger, TipoProceso
from _core.common import hacer_login, navegar_a_manifiestos, TIMEOUT_CORTO, TIMEOUT_MEDIO


# ============================================================================
# CONSTANTES ESPECÍFICAS DE MANIFIESTOS
# ============================================================================
MAX_REINTENTOS = 18
INCREMENTO_FLETE = 100000

# Obtener logger para manifiestos
logger = obtener_logger(TipoProceso.MANIFIESTO)


# ============================================================================
# FUNCIONES DE LLENADO DE FORMULARIO
# ============================================================================
def llenar_formulario_manifiesto(driver, codigo):
    """
    Llena el formulario de manifiesto con los datos básicos.
    
    Returns:
        list: Lista de tuplas (campo_id, valor) con los campos utilizados
    
    Raises:
        Exception: Si hay un error en el mensaje del sistema
    """
    campos_utilizados = []
    
    # Ingresar código de manifiesto
    input_codigo = driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_NUMMANIFIESTOCARGA")
    input_codigo.clear()
    input_codigo.send_keys(codigo)
    input_codigo.send_keys("\t")
    time.sleep(0.5)
    
    # Verificar mensajes de error del sistema
    mensaje_error = driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_MSGERROR").get_attribute("value").strip()
    if mensaje_error:
        logger.registrar_error(codigo, f"Error del sistema: {mensaje_error}")
        raise Exception(mensaje_error)
    
    # Tipo de cumplimiento
    Select(driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_NOMTIPOCUMPLIDOMANIFIESTO")).select_by_visible_text("Cumplido Normal")
    campos_utilizados.append(("NOMTIPOCUMPLIDOMANIFIESTO", "Cumplido Normal"))
    
    # Campos con valor cero
    campos_cero = [
        "VALORADICIONALHORASCARGUE",
        "VALORADICIONALHORASDESCARGUE",
        "VALORADICIONALFLETE",
        "VALORDESCUENTOFLETE",
    ]
    
    for nombre_campo in campos_cero:
        campo_id = f"dnn_ctr396_CumplirManifiesto_{nombre_campo}"
        campo_elemento = driver.find_element(By.ID, campo_id)
        campo_elemento.clear()
        campo_elemento.send_keys("0")
        campos_utilizados.append((nombre_campo, "0"))
    
    # Calcular y establecer fecha de entrega (expedición + 5 días)
    id_fecha_expedicion = "dnn_ctr396_CumplirManifiesto_FECHAEXPEDICIONMANIFIESTO"
    WebDriverWait(driver, TIMEOUT_MEDIO).until(
        lambda d: d.find_element(By.ID, id_fecha_expedicion).get_attribute("value").strip() != ""
    )
    
    fecha_expedicion_str = driver.find_element(By.ID, id_fecha_expedicion).get_attribute("value").strip()
    
    try:
        fecha_expedicion = datetime.strptime(fecha_expedicion_str, "%d/%m/%Y")
        fecha_entrega = fecha_expedicion + timedelta(days=5)
        fecha_entrega_str = fecha_entrega.strftime("%d/%m/%Y")
        
        campo_entrega = driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_FECHAENTREGADOCUMENTOS")
        campo_entrega.clear()
        campo_entrega.send_keys(fecha_entrega_str)
        
        campos_utilizados.append(("FECHAENTREGADOCUMENTOS", fecha_entrega_str))
    except Exception as e:
        logger.registrar_excepcion(codigo, e, "Error calculando fecha de entrega")
        raise Exception(f"No se pudo calcular fecha de entrega: {e}")
    
    return campos_utilizados


def modificar_flete_y_motivo(driver, codigo, valor_flete, campos):
    """
    Modifica el valor del flete adicional y su motivo en el formulario.
    
    Args:
        driver: WebDriver de Selenium
        codigo: Código del manifiesto
        valor_flete: Nuevo valor del flete adicional
        campos: Lista de campos utilizados (para logging)
    
    Returns:
        bool: True si la modificación fue exitosa, False en caso contrario
    """
    flete_id = "dnn_ctr396_CumplirManifiesto_VALORADICIONALFLETE"
    motivo_flete_id = "dnn_ctr396_CumplirManifiesto_NOMMOTIVOVALORADICIONAL"
    
    try:
        # Esperar a que la página esté lista
        WebDriverWait(driver, TIMEOUT_MEDIO).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # Recargar formulario
        navegar_a_manifiestos(driver)
        campos_actualizados = llenar_formulario_manifiesto(driver, codigo)
        
        # Esperar a que la página esté lista nuevamente
        WebDriverWait(driver, TIMEOUT_MEDIO).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # Actualizar valor flete
        flete_elemento = WebDriverWait(driver, TIMEOUT_MEDIO).until(
            EC.element_to_be_clickable((By.ID, flete_id))
        )
        flete_elemento.clear()
        flete_elemento.send_keys(str(valor_flete))
        flete_elemento.send_keys(Keys.TAB)
        
        time.sleep(0.5)
        
        # Solo establecer motivo si el valor > 0
        if valor_flete > 0:
            motivo_elemento = WebDriverWait(driver, TIMEOUT_MEDIO).until(
                EC.element_to_be_clickable((By.ID, motivo_flete_id))
            )
            Select(motivo_elemento).select_by_value("R")
            motivo_elemento.send_keys(Keys.TAB)
            time.sleep(0.5)
        
        return True
        
    except Exception as e:
        logger.registrar_error(
            codigo,
            f"Error al modificar flete/motivo (valor={valor_flete}): {str(e)}",
            valor_flete=valor_flete
        )
        registrar_log_remesa(
            codigo, 
            f"Error al modificar flete/motivo (valor={valor_flete}): {str(e)}", 
            campos
        )
        return False


# ============================================================================
# FUNCIONES DE GUARDADO Y MANEJO DE ALERTAS
# ============================================================================
def intentar_guardar_con_alertas(driver):
    """
    Intenta guardar el formulario y maneja posibles alertas.
    
    Returns:
        tuple: (bool: éxito, str: texto de alerta si existe)
    """
    max_click_attempts = 3
    
    for attempt in range(max_click_attempts):
        try:
            guardar_btn = WebDriverWait(driver, TIMEOUT_MEDIO).until(
                EC.element_to_be_clickable((By.ID, "dnn_ctr396_CumplirManifiesto_btGuardar"))
            )
            driver.execute_script("arguments[0].click();", guardar_btn)
            time.sleep(1)
            break
        except Exception as e:
            if attempt == max_click_attempts - 1:
                raise
            print(f"Reintento {attempt + 1} de click fallido. Volviendo a intentar...")
    
    time.sleep(1)
    
    # Verificar si hay alerta
    try:
        alerta = WebDriverWait(driver, TIMEOUT_CORTO).until(EC.alert_is_present())
        texto_alerta = alerta.text
        alerta.accept()
        time.sleep(2)
        return False, texto_alerta
        
    except TimeoutException:
        # No hubo alerta - verificar si se guardó correctamente
        try:
            WebDriverWait(driver, TIMEOUT_MEDIO).until(
                EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirManifiestoNew_btNuevo"))
            )
            return True, None
        except TimeoutException:
            return False, "NO_ALERT_NO_SUCCESS"


def guardar_y_manejar_alertas(driver, codigo, actualizar_estado_callback, campos):
    """
    Guarda el formulario y maneja alertas con sistema de reintentos.
    
    Args:
        driver: WebDriver de Selenium
        codigo: Código del manifiesto
        actualizar_estado_callback: Función para actualizar estado en GUI
        campos: Lista de campos utilizados
    
    Returns:
        bool: True si se guardó exitosamente, False en caso contrario
    """
    valor_flete_actual = 0
    
    for reintento in range(MAX_REINTENTOS + 1):
        try:
            # Modificar flete en reintentos > 0
            if reintento > 0:
                valor_flete_actual += INCREMENTO_FLETE
                
                logger.registrar_reintento(
                    codigo,
                    reintento,
                    f"Modificando flete a ${valor_flete_actual:,}",
                    valor_flete=valor_flete_actual
                )
                
                if not modificar_flete_y_motivo(driver, codigo, valor_flete_actual, campos):
                    continue
                
                actualizar_estado_callback(
                    f"🔄 Reintento {reintento} para {codigo} | Flete: ${valor_flete_actual:,}"
                )
            
            # Intentar guardar
            exito, texto_alerta = intentar_guardar_con_alertas(driver)
            
            if exito:
                logger.registrar_exito(
                    codigo,
                    "Manifiesto completado correctamente",
                    valor_flete=valor_flete_actual,
                    reintento=reintento
                )
                actualizar_estado_callback(
                    f"✅ {codigo} completado | Flete: ${valor_flete_actual:,}"
                )
                return True
            
            # Manejo de alertas
            if texto_alerta:
                # Extraer código de error si existe
                codigo_error = None
                if "CMA045" in texto_alerta:
                    codigo_error = "CMA045"
                elif "CMA145" in texto_alerta:
                    codigo_error = "CMA145"
                
                logger.registrar_alerta(
                    codigo,
                    codigo_error or "UNKNOWN",
                    texto_alerta,
                    valor_flete=valor_flete_actual,
                    reintento=reintento
                )
                
                registrar_log_remesa(codigo, texto_alerta, campos)
                
                # Errores que permiten reintento
                if codigo_error in ["CMA045", "CMA145"]:
                    continue
                else:
                    actualizar_estado_callback(
                        f"❌ Error no manejable en {codigo}: {texto_alerta}"
                    )
                    return False
            else:
                # Sin alerta pero sin éxito
                logger.registrar_error(
                    codigo,
                    "Sin alerta pero el guardado no se completó",
                    valor_flete=valor_flete_actual,
                    reintento=reintento
                )
                print(f"\n⚠️ PAUSA MANUAL - Reintento {reintento} para {codigo}")
                print("Motivo: No hubo alerta, pero el guardado no se completó.")
                registrar_log_remesa(codigo, "Error: Sin alerta pero no se completó", campos)
                input("Presiona ENTER para continuar con el siguiente reintento...")
                continue
        
        except Exception as e:
            logger.registrar_excepcion(
                codigo,
                e,
                f"Error en reintento {reintento}",
                valor_flete=valor_flete_actual,
                reintento=reintento
            )
            registrar_log_remesa(codigo, f"Error en reintento {reintento}: {str(e)}", campos)
            continue
    
    # Si se agotan los reintentos
    logger.registrar_error(
        codigo,
        f"Fallo definitivo tras {MAX_REINTENTOS} reintentos",
        valor_flete=valor_flete_actual
    )
    actualizar_estado_callback(
        f"❌ Fallo definitivo en {codigo} | Último flete: ${valor_flete_actual:,}"
    )
    return False


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================
def ejecutar_manifiestos(driver, codigos, actualizar_estado_callback, pausa_event, cancelar_func):
    """
    Función principal que ejecuta el proceso de llenado de manifiestos.
    
    Args:
        driver: WebDriver de Selenium
        codigos: Lista de códigos de manifiestos a procesar
        actualizar_estado_callback: Función para actualizar estado en GUI
        pausa_event: Evento de threading para pausar el proceso
        cancelar_func: Función que retorna True si se debe cancelar
    """
    try:
        hacer_login(driver)
        navegar_a_manifiestos(driver)
        
        for codigo in codigos:
            # Verificar cancelación
            if cancelar_func():
                driver.quit()
                actualizar_estado_callback("⛔ Proceso cancelado por el usuario.")
                break
            
            actualizar_estado_callback(f"Procesando manifiesto {codigo}...")
            pausa_event.wait()  # Espera si el proceso está pausado
            
            navegar_a_manifiestos(driver)
            
            try:
                campos = llenar_formulario_manifiesto(driver, codigo)
                guardar_y_manejar_alertas(driver, codigo, actualizar_estado_callback, campos)
                
            except Exception as e:
                logger.registrar_excepcion(codigo, e, "Error procesando manifiesto")
                registrar_log_remesa(
                    codigo, 
                    f"Excepción: {e}", 
                    campos if 'campos' in locals() else []
                )
                actualizar_estado_callback(f"❌ Error en manifiesto {codigo}: {e}")
                navegar_a_manifiestos(driver)
                continue
        
        actualizar_estado_callback("✅ Todos los manifiestos completados.")
        
        # Mostrar reporte final
        reporte = logger.generar_reporte()
        print(reporte)
        
    except Exception as e:
        actualizar_estado_callback(f"❌ Error general llenando manifiestos: {e}")
        logger.registrar_excepcion("SISTEMA", e, "Error general en ejecución")
        
    finally:
        driver.quit()
        if not cancelar_func():
            messagebox.showinfo(
                "Proceso completado",
                f"Los manifiestos fueron procesados.\n\n{logger.generar_reporte()}"
            )