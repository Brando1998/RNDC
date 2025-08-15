from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, TimeoutException
from datetime import datetime, timedelta
import time
from _utils.logger import registrar_log_remesa
from selenium.webdriver.common.keys import Keys



def hacer_login(driver):
    driver.get("https://rndc.mintransporte.gov.co/MenuPrincipal/tabid/204/language/es-MX/Default.aspx?returnurl=%2fMenuPrincipal%2ftabid%2f204%2flanguage%2fes-MX%2fDefault.aspx")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "dnn_ctr580_FormLogIn_edUsername")))

    usuario = "Sotranscolombianos1@0341"
    contrasena = "053EPA746**"

    driver.find_element(By.ID, "dnn_ctr580_FormLogIn_edUsername").send_keys(usuario)
    driver.find_element(By.ID, "dnn_ctr580_FormLogIn_edPassword").send_keys(contrasena)
    driver.find_element(By.ID, "dnn_ctr580_FormLogIn_btIngresar").click()

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "tddnn_dnnSOLPARTMENU_ctldnnSOLPARTMENU120")))


def navegar_a_formulario(driver):
    driver.execute_script("window.localStorage.clear();")
    driver.execute_script("window.sessionStorage.clear();")

    driver.get("https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirManifiesto/mid/396/procesoid/6/default.aspx")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirManifiesto_NUMMANIFIESTOCARGA")))


def llenar_formulario_manifiesto(driver, codigo):
    campos_utilizados = []

    input_codigo = driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_NUMMANIFIESTOCARGA")
    input_codigo.clear()
    input_codigo.send_keys(codigo)
    input_codigo.send_keys("\t")
    time.sleep(0.5)

    mensaje_error = driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_MSGERROR").get_attribute("value").strip()
    if mensaje_error:
        raise Exception(mensaje_error)

    # Tipo de cumplimiento
    Select(driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_NOMTIPOCUMPLIDOMANIFIESTO")).select_by_visible_text("Cumplido Normal")
    campos_utilizados.append(("NOMTIPOCUMPLIDOMANIFIESTO", "Cumplido Normal"))

    # Campos con cero
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

    # Obtener fecha expedición
    id_fecha_expedicion = "dnn_ctr396_CumplirManifiesto_FECHAEXPEDICIONMANIFIESTO"
    WebDriverWait(driver, 10).until(lambda d: d.find_element(By.ID, id_fecha_expedicion).get_attribute("value").strip() != "")
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
        raise Exception(f"No se pudo calcular fecha de entrega: {e}")

    # time.sleep(1)
    return campos_utilizados

def guardar_y_manejar_alertas(driver, codigo, actualizar_estado_callback, campos):
    MAX_REINTENTOS = 18
    INCREMENTO_FLETE = 100000
    valor_flete_actual = 0  # Empieza en 0

    def modificar_flete_y_motivo(valor):
        flete_id = "dnn_ctr396_CumplirManifiesto_VALORADICIONALFLETE"
        motivo_flete_id = "dnn_ctr396_CumplirManifiesto_NOMMOTIVOVALORADICIONAL"
        
        try:
            # Esperar a que la página esté lista
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete")
            
            navegar_a_formulario(driver)
            campos = llenar_formulario_manifiesto(driver, codigo)

            # Esperar a que la página esté lista
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete")
            
            # Actualizar valor flete
            flete_elemento = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, flete_id)))
            flete_elemento.clear()
            flete_elemento.send_keys(str(valor))
            flete_elemento.send_keys(Keys.TAB)  # Forzar actualización
            
            # Pequeña pausa para estabilización
            time.sleep(0.5)
            
            # Solo establecer motivo si el valor > 0
            if valor > 0:
                # Esperar y seleccionar el motivo
                motivo_elemento = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, motivo_flete_id)))
                Select(motivo_elemento).select_by_value("R")
                motivo_elemento.send_keys(Keys.TAB)
                # Pequeña pausa para estabilización
                time.sleep(0.5)
                
            # # Actualizar registro de campos
            # for i, (nombre, _) in enumerate(campos):
            #     if nombre == "VALORADICIONALFLETE":
            #         campos[i] = (nombre, str(valor))
            #         break
                    
            return True
        except Exception as e:
            registrar_log_remesa(codigo, f"Error al modificar flete/motivo (valor={valor}): {str(e)}", campos)
            return False

    for reintento in range(MAX_REINTENTOS + 1):
        try:
            # Solo modificar flete en reintentos > 0
            if reintento > 0:
                valor_flete_actual += INCREMENTO_FLETE
                if not modificar_flete_y_motivo(valor_flete_actual):
                    continue
                
                actualizar_estado_callback(f"🔄 Reintento {reintento} para {codigo} | Flete: ${valor_flete_actual:,}")

            # Intentar guardar
            max_click_attempts = 3
            for attempt in range(max_click_attempts):
                try:
                    guardar_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "dnn_ctr396_CumplirManifiesto_btGuardar")))
                    driver.execute_script("arguments[0].click();", guardar_btn)
                    time.sleep(1)
                    break  # Si no hay excepción, sal del bucle
                except Exception as e:
                    if attempt == max_click_attempts - 1:
                        raise
                    print(f"Reintento {attempt + 1} de click fallido. Volviendo a intentar...")
            # Esperar un momento para posibles alertas
            time.sleep(1)
            
            # Manejar posibles alertas
            try:
                alerta = WebDriverWait(driver, 3).until(EC.alert_is_present())
                texto_alerta = alerta.text
                alerta.accept()
                
                # Pequeña pausa después de aceptar alerta
                time.sleep(2)
                
                registrar_log_remesa(codigo, texto_alerta, campos)
                
                # Si es un error que podemos manejar, continuamos
                if "CMA045" in texto_alerta or "CMA145" in texto_alerta:
                    continue
                else:
                    actualizar_estado_callback(f"❌ Error no manejable en {codigo}: {texto_alerta}")
                    return False
                    
            except TimeoutException:
                # No hubo alerta - verificar si se guardó correctamente
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirManifiestoNew_btNuevo")))
                    actualizar_estado_callback(f"✅ {codigo} completado | Flete: ${valor_flete_actual:,}")
                    return True
                except TimeoutException:
                    # --- INICIO: PAUSA PARA REVISIÓN MANUAL ---
                    print(f"\n⚠️ PAUSA MANUAL - Reintento {reintento} para {codigo}")
                    print("Motivo: No hubo alerta, pero el guardado no se completó.")
                    registrar_log_remesa(codigo, "Error: Sin alerta pero no se completó", campos)
                    input("Presiona ENTER para continuar con el siguiente reintento...")

                    continue

        except Exception as e:
            registrar_log_remesa(codigo, f"Error en reintento {reintento}: {str(e)}", campos)
            continue

    # Si se agotan los reintentos
    actualizar_estado_callback(f"❌ Fallo definitivo en {codigo} | Último flete: ${valor_flete_actual:,}")
    return False

def ejecutar_manifiestos(driver, codigos, actualizar_estado_callback, pausa_event, cancelar_func):
    try:
        hacer_login(driver)
        navegar_a_formulario(driver)

        for codigo in codigos:
            if cancelar_func():
                driver.quit()
                actualizar_estado_callback("⛔ Proceso cancelado por el usuario.")
                break
                
            actualizar_estado_callback(f"Procesando manifiesto {codigo}...")
            pausa_event.wait()  # Espera si el proceso está pausado
            
            navegar_a_formulario(driver)
            try:
                campos = llenar_formulario_manifiesto(driver, codigo)
                guardar_y_manejar_alertas(driver, codigo, actualizar_estado_callback, campos)
            except Exception as e:
                registrar_log_remesa(codigo, f"Excepción: {e}", campos if 'campos' in locals() else [])
                actualizar_estado_callback(f"❌ Error en manifiesto {codigo}: {e}")
                navegar_a_formulario(driver)
                continue

        actualizar_estado_callback("✅ Todos los manifiestos completados.")
    except Exception as e:
        actualizar_estado_callback(f"❌ Error general llenando manifiestos: {e}")
    finally:
        driver.quit()
        if not cancelar_func():
            messagebox.showinfo(
                "Proceso completado",
                "Los manifiestos fueron procesados. Revisa el log de errores para más detalles."
            )