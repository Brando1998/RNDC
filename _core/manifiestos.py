"""
Módulo para el procesamiento automatizado de manifiestos en RNDC.
Versión mejorada con mejoras conservadoras sobre la versión original.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from datetime import datetime, timedelta
from tkinter import messagebox
import time
import os
import json
from _utils.logger import registrar_log_remesa, obtener_logger, TipoProceso
from _core.navegador import crear_driver


# ============================================================================
# CONSTANTES
# ============================================================================
MAX_REINTENTOS = 18
INCREMENTO_FLETE = 100000

# Obtener logger para manifiestos
logger = obtener_logger(TipoProceso.MANIFIESTO)

# Archivo de checkpoint
CHECKPOINT_FILE = "_logs/manifiestos_checkpoint.json"


# ============================================================================
# SISTEMA DE CHECKPOINT (Opcional)
# ============================================================================
def guardar_checkpoint(codigos_procesados):
    """Guarda el progreso actual en un archivo de checkpoint."""
    try:
        checkpoint = {
            "fecha": datetime.now().isoformat(),
            "procesados": codigos_procesados
        }
        os.makedirs("_logs", exist_ok=True)
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump(checkpoint, f, indent=2)
    except Exception:
        pass  # Si falla el checkpoint, continuar de todas formas


def cargar_checkpoint():
    """Carga el checkpoint si existe."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def limpiar_checkpoint():
    """Elimina el archivo de checkpoint."""
    try:
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
    except Exception:
        pass


# ============================================================================
# FUNCIONES DE NAVEGACIÓN (Basadas en la versión original)
# ============================================================================
def hacer_login(driver):
    """Realiza el login en el sistema RNDC."""
    driver.get("https://rndc.mintransporte.gov.co/MenuPrincipal/tabid/204/language/es-MX/Default.aspx?returnurl=%2fMenuPrincipal%2ftabid%2f204%2flanguage%2fes-MX%2fDefault.aspx")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "dnn_ctr580_FormLogIn_edUsername"))
    )

    usuario = "Sotranscolombianos1@0341"
    contrasena = "053EPA746**"

    driver.find_element(By.ID, "dnn_ctr580_FormLogIn_edUsername").send_keys(usuario)
    driver.find_element(By.ID, "dnn_ctr580_FormLogIn_edPassword").send_keys(contrasena)
    driver.find_element(By.ID, "dnn_ctr580_FormLogIn_btIngresar").click()

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "tddnn_dnnSOLPARTMENU_ctldnnSOLPARTMENU120"))
    )


def navegar_a_formulario(driver):
    """Navega al formulario de manifiestos."""
    driver.execute_script("window.localStorage.clear();")
    driver.execute_script("window.sessionStorage.clear();")

    driver.get("https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirManifiesto/mid/396/procesoid/6/default.aspx")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirManifiesto_NUMMANIFIESTOCARGA"))
    )


# ============================================================================
# FUNCIONES DE LLENADO DE FORMULARIO CON FALLBACKS MEJORADOS
# ============================================================================
def calcular_fecha_entrega_con_fallbacks(driver, codigo):
    """
    Calcula la fecha de entrega con múltiples estrategias de fallback.
    MEJORA: Añade robustez cuando la fecha de expedición está vacía.
    """
    id_fecha_expedicion = "dnn_ctr396_CumplirManifiesto_FECHAEXPEDICIONMANIFIESTO"
    
    # Estrategia 1: Esperar a que la fecha se llene automáticamente (original)
    try:
        WebDriverWait(driver, 10).until(
            lambda d: d.find_element(By.ID, id_fecha_expedicion).get_attribute("value").strip() != ""
        )
        fecha_expedicion_str = driver.find_element(By.ID, id_fecha_expedicion).get_attribute("value").strip()
        
        if fecha_expedicion_str:
            fecha_expedicion = datetime.strptime(fecha_expedicion_str, "%d/%m/%Y")
            fecha_entrega = fecha_expedicion + timedelta(days=5)
            return fecha_entrega.strftime("%d/%m/%Y")
    except (TimeoutException, ValueError):
        pass
    
    # Estrategia 2: FALLBACK - Usar fecha actual como último recurso
    logger.registrar_log(
        codigo,
        "⚠️ No se pudo obtener fecha de expedición, usando fecha actual"
    )
    fecha_actual = datetime.now()
    fecha_entrega = fecha_actual + timedelta(days=5)
    return fecha_entrega.strftime("%d/%m/%Y")


def llenar_formulario_manifiesto(driver, codigo):
    """Llena el formulario de manifiesto con los datos básicos."""
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

    # MEJORA: Calcular fecha con sistema de fallbacks
    fecha_entrega_str = calcular_fecha_entrega_con_fallbacks(driver, codigo)
    
    campo_entrega = driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_FECHAENTREGADOCUMENTOS")
    campo_entrega.clear()
    campo_entrega.send_keys(fecha_entrega_str)
    campos_utilizados.append(("FECHAENTREGADOCUMENTOS", fecha_entrega_str))

    return campos_utilizados


# ============================================================================
# FUNCIONES DE GUARDADO Y MANEJO DE ALERTAS (Basadas en original)
# ============================================================================
def guardar_y_manejar_alertas(driver, codigo, actualizar_estado_callback, campos):
    """Guarda el formulario y maneja alertas con sistema de reintentos."""
    valor_flete_actual = 0

    def modificar_flete_y_motivo(valor):
        """Modifica el valor del flete adicional y su motivo."""
        flete_id = "dnn_ctr396_CumplirManifiesto_VALORADICIONALFLETE"
        motivo_flete_id = "dnn_ctr396_CumplirManifiesto_NOMMOTIVOVALORADICIONAL"
        
        try:
            # Esperar a que la página esté lista
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            navegar_a_formulario(driver)
            campos = llenar_formulario_manifiesto(driver, codigo)

            # Esperar a que la página esté lista
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # Actualizar valor flete
            flete_elemento = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, flete_id))
            )
            flete_elemento.clear()
            flete_elemento.send_keys(str(valor))
            flete_elemento.send_keys(Keys.TAB)
            
            time.sleep(0.5)
            
            # Solo establecer motivo si el valor > 0
            if valor > 0:
                motivo_elemento = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, motivo_flete_id))
                )
                Select(motivo_elemento).select_by_value("R")
                motivo_elemento.send_keys(Keys.TAB)
                time.sleep(0.5)
                    
            return True
        except Exception as e:
            logger.registrar_error(
                codigo,
                f"Error al modificar flete/motivo (valor={valor}): {str(e)}"
            )
            registrar_log_remesa(codigo, f"Error al modificar flete/motivo (valor={valor}): {str(e)}", campos)
            return False

    for reintento in range(MAX_REINTENTOS + 1):
        try:
            # Solo modificar flete en reintentos > 0
            if reintento > 0:
                valor_flete_actual += INCREMENTO_FLETE
                
                logger.registrar_reintento(
                    codigo,
                    reintento,
                    f"Modificando flete a ${valor_flete_actual:,}",
                    valor_flete=valor_flete_actual
                )
                
                if not modificar_flete_y_motivo(valor_flete_actual):
                    continue
                
                actualizar_estado_callback(
                    f"🔄 Reintento {reintento} para {codigo} | Flete: ${valor_flete_actual:,}"
                )

            # Intentar guardar con múltiples intentos de click
            max_click_attempts = 3
            for attempt in range(max_click_attempts):
                try:
                    guardar_btn = WebDriverWait(driver, 10).until(
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
            
            # Manejar posibles alertas
            try:
                alerta = WebDriverWait(driver, 3).until(EC.alert_is_present())
                texto_alerta = alerta.text
                alerta.accept()
                time.sleep(2)
                
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
                
                # Si es un error que podemos manejar con reintentos
                if codigo_error in ["CMA045", "CMA145"]:
                    continue
                else:
                    actualizar_estado_callback(f"❌ Error no manejable en {codigo}: {texto_alerta}")
                    return False
                    
            except TimeoutException:
                # No hubo alerta - verificar si se guardó correctamente
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirManifiestoNew_btNuevo"))
                    )
                    
                    logger.registrar_exito(
                        codigo,
                        "Manifiesto completado correctamente",
                        valor_flete=valor_flete_actual,
                        reintento=reintento
                    )
                    actualizar_estado_callback(f"✅ {codigo} completado | Flete: ${valor_flete_actual:,}")
                    return True
                    
                except TimeoutException:
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
    actualizar_estado_callback(f"❌ Fallo definitivo en {codigo} | Último flete: ${valor_flete_actual:,}")
    return False


# ============================================================================
# FUNCIÓN PRINCIPAL CON CHECKPOINT
# ============================================================================
def ejecutar_manifiestos(driver, codigos, actualizar_estado_callback, pausa_event, cancelar_func):
    """
    Función principal que ejecuta el proceso de llenado de manifiestos.
    MEJORA: Añade sistema de checkpoint para reanudar proceso.
    """
    codigos_procesados = []
    
    # MEJORA: Verificar si hay un checkpoint previo
    checkpoint = cargar_checkpoint()
    if checkpoint:
        codigos_previos = checkpoint.get("procesados", [])
        if codigos_previos:
            codigos_procesados = codigos_previos
            actualizar_estado_callback(
                f"🔄 Reanudando proceso. {len(codigos_procesados)} manifiestos ya procesados."
            )
            # Filtrar los códigos ya procesados
            codigos = [c for c in codigos if c not in codigos_procesados]
    
    try:
        hacer_login(driver)
        navegar_a_formulario(driver)

        for codigo in codigos:
            # Verificar cancelación
            if cancelar_func():
                driver.quit()
                actualizar_estado_callback("⛔ Proceso cancelado por el usuario.")
                break
                
            actualizar_estado_callback(f"Procesando manifiesto {codigo}...")
            pausa_event.wait()  # Espera si el proceso está pausado
            
            navegar_a_formulario(driver)
            
            try:
                campos = llenar_formulario_manifiesto(driver, codigo)
                exito = guardar_y_manejar_alertas(driver, codigo, actualizar_estado_callback, campos)
                
                # MEJORA: Guardar checkpoint si fue exitoso
                if exito:
                    codigos_procesados.append(codigo)
                    guardar_checkpoint(codigos_procesados)
                    
            except Exception as e:
                logger.registrar_excepcion(codigo, e, "Error procesando manifiesto")
                registrar_log_remesa(codigo, f"Excepción: {e}", campos if 'campos' in locals() else [])
                actualizar_estado_callback(f"❌ Error en manifiesto {codigo}: {e}")
                navegar_a_formulario(driver)
                continue

        # MEJORA: Limpiar checkpoint al finalizar exitosamente
        limpiar_checkpoint()
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