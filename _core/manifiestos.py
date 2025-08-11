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
    def intentar_guardado():
        # print(f"Intentando guardar manifiesto {codigo}...")
        guardar_id = "dnn_ctr396_CumplirManifiesto_btGuardar"
        nuevo_id = "dnn_ctr396_CumplirManifiestoNew_btNuevo"

        try:
            boton_guardar = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, guardar_id))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", boton_guardar)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", boton_guardar)
            # print("✅ Click ejecutado en el botón guardar")
        except Exception as e:
            # print(f"⚠️ No se pudo hacer clic en el botón guardar: {e}")
            driver.save_screenshot("error_click_guardar.png")
            return "Botón guardar no clickeable"

        # 1. Esperar si aparece una alerta
        try:
            WebDriverWait(driver, 3).until(EC.alert_is_present())
            alerta = driver.switch_to.alert
            texto = alerta.text
            alerta.accept()
            # print(f"⚠️ Alerta detectada: {texto}")
            return texto
        except TimeoutException:
            print("⏱ No hubo alerta después del clic")

        # 2. Esperar si se redirige correctamente (aparece botón "Nuevo")
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, nuevo_id))
            )
            # print("✅ Redirección detectada (botón Nuevo encontrado)")
            return "GUARDADO_OK"
        except TimeoutException:
            # print("❌ No hubo alerta ni redirección después del clic")
            driver.save_screenshot("no_alerta_ni_redireccion.png")
            return "Error: No hubo alerta ni redirección (no se guardó)"

    def reescribir_campos(campos_actualizados):
        return

    def manejar_cma045_cma145():
        # print(f"Error CMA045/CMA145 detectado en manifiesto {codigo}. Intentando corregir...")
        try:
            actualizar_estado_callback(f"⏳ Error CMA045 en {codigo}. Reintentando aumentando flete...")
            # print(f"⏳ Error CMA045 en {codigo}. Reintentando aumentando flete...")
            flete_id = "dnn_ctr396_CumplirManifiesto_VALORADICIONALFLETE"
            motivo_flete_id = "dnn_ctr396_CumplirManifiesto_NOMMOTIVOVALORADICIONAL"
            motivo_flete_value = "R"
            incremento_flete = 100_000
            max_intentos = 20

            for intento in range(max_intentos):
                try:
                    flete_elemento = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.ID, flete_id))
                    )
                    driver.execute_script("arguments[0].scrollIntoView(true);", flete_elemento)
                    time.sleep(0.3)

                    # Asegurarse de que el campo sea interactuable
                    WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.ID, flete_id))
                    )

                    flete_actual = int(flete_elemento.get_attribute("value").replace(".", "").replace(",", "") or "0")
                    nuevo_flete = flete_actual + incremento_flete
                    flete_elemento.clear()
                    flete_elemento.send_keys(str(nuevo_flete))
                    flete_elemento.send_keys(Keys.TAB)
                    time.sleep(0.5)  # Esperar que el cambio se registre antes de seguir


                    # print(f"Manifiesto {codigo}. incrementando a {nuevo_flete} en intento {intento + 1} de {max_intentos}...")

                    Select(driver.find_element(By.ID, motivo_flete_id)).select_by_value(motivo_flete_value)

                    # Actualizar campos
                    actualizado = False
                    for i, (nombre, _) in enumerate(campos):
                        if nombre == "VALORADICIONALFLETE":
                            campos[i] = ("VALORADICIONALFLETE", str(nuevo_flete))
                            actualizado = True
                            break
                    if not actualizado:
                        campos.append(("VALORADICIONALFLETE", str(nuevo_flete)))

                    texto_alerta = intentar_guardado()
                    # print(f"Texto de alerta tras incremento: {texto_alerta}")
                    # Verificamos si se completó
                    try:
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirManifiestoNew_btNuevo"))
                        )
                        actualizar_estado_callback(f"✅ Manifiesto {codigo} completado con flete {nuevo_flete}.")
                        # print(f"Manifiesto {codigo} completado con flete {nuevo_flete}.")
                        registrar_log_remesa(codigo, "Guardado exitoso tras CMA045", campos)
                        return
                    except Exception:
                        # Si no aparece el botón, asumimos que falló y reintentamos
                        registrar_log_remesa(codigo, texto_alerta or "Sin alerta y sin confirmación", campos)
                        # print("Sin confirmación de guardado, reintentando...")
                        # time.sleep(1)
                        continue

                except Exception as e:
                    # print(f"Error en intento {intento + 1}: {e}")
                    registrar_log_remesa(codigo, f"Error en intento {intento + 1}: {e}", campos)
                    # time.sleep(1)

            # Si se llega al final sin éxito
            actualizar_estado_callback(f"❌ Manifiesto {codigo} no pudo completarse tras {max_intentos} intentos de incremento de flete.")
            registrar_log_remesa(codigo, "Fallo tras múltiples intentos por CMA045/CMA145", campos)

        except Exception as e:
            # print(f"Error general al actualizar estado: {e}")
            registrar_log_remesa(codigo, f"Fallo en reintento CMA045/CMA145: {e}", campos)


    # Flujo principal:

    texto_alerta = intentar_guardado()

    if texto_alerta is None:
        # print(f"Manifiesto {codigo} guardado sin alertas.")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirManifiestoNew_btNuevo"))
        )
        actualizar_estado_callback(f"✅ Manifiesto {codigo} completado correctamente.")
        return

    registrar_log_remesa(codigo, texto_alerta, campos)

    if "CMA045" in texto_alerta or "CMA145" in texto_alerta:
        manejar_cma045_cma145()
    else:
        actualizar_estado_callback(f"❌ Manifiesto {codigo} falló: {texto_alerta}")


def ejecutar_manifiestos(driver, codigos, actualizar_estado_callback):
    try:
        hacer_login(driver)
        navegar_a_formulario(driver)

        for codigo in codigos:
            actualizar_estado_callback(f"Procesando manifiesto {codigo}...")
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
