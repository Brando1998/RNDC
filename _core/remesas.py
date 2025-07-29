from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, TimeoutException
from datetime import datetime, timedelta
import time
from _utils.logger import registrar_log_remesa


def navegar_a_formulario(driver):
    # Limpiar localStorage y sessionStorage (esto NO afecta la sesión en la mayoría de sitios)
    driver.execute_script("window.localStorage.clear();")
    driver.execute_script("window.sessionStorage.clear();")

    # Recargar el formulario
    driver.get("https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirRemesa/mid/396/procesoid/5/default.aspx")

    # Esperar que el campo esté disponible
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA"))
    )


def llenar_formulario_remesa(driver, codigo):
    # Buscar remesa
    input_remesa = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA")
    input_remesa.clear()
    input_remesa.send_keys(codigo)
    input_remesa.send_keys("\t")
    time.sleep(2)

    # Verificar si hay mensaje de remesa inexistente o cerrada
    mensaje = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_MENSAJE").get_attribute("value")
    if "no ha sido emitida o ya está cerrada" in mensaje:
        raise ValueError("REMESA_NO_EMITIDA_O_YA_CERRADA")

    # Seleccionar cumplido
    Select(driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_NOMTIPOCUMPLIDOREMESA")).select_by_visible_text("Cumplido Normal")

    # Cantidad
    cantidad = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CANTIDADCARGADA").get_attribute("value")
    driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CANTIDADENTREGADA").clear()
    driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CANTIDADENTREGADA").send_keys(cantidad)

    # Fechas
    fecha_cargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHACITAPACTADACARGUE").get_attribute("value")
    hora_cargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORACITAPACTADACARGUE").get_attribute("value")
    hora_salida_dt = datetime.strptime(hora_cargue, "%H:%M") + timedelta(minutes=60)
    hora_salida = hora_salida_dt.strftime("%H:%M")

    fecha_descargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHACITAPACTADADESCARGUE").get_attribute("value")
    hora_descargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORACITAPACTADADESCARGUEREMESA").get_attribute("value")
    hora_llegada_dt = datetime.strptime(hora_descargue, "%H:%M") + timedelta(minutes=60)

    # Validar conflicto entre hora_salida y hora_llegada
    if hora_llegada_dt <= hora_salida_dt:
        hora_llegada_dt = hora_salida_dt + timedelta(minutes=15)

    hora_llegada = hora_llegada_dt.strftime("%H:%M")


    # Validar si la fecha de descargue es mayor a hoy
    fecha_descargue_dt = datetime.strptime(fecha_descargue, "%d/%m/%Y").date()
    if fecha_descargue_dt > datetime.today().date():
        raise ValueError("REMESA_FECHA_DESCARGUE_FUTURA")


    campos = [
        ("FECHALLEGADACARGUE", fecha_cargue),
        ("FECHAENTRADACARGUE", fecha_cargue),
        ("FECHASALIDACARGUE", fecha_cargue),
        ("HORALLEGADACARGUEREMESA", hora_cargue),
        ("HORAENTRADACARGUEREMESA", hora_cargue),
        ("HORASALIDACARGUEREMESA", hora_salida),
        ("FECHALLEGADADESCARGUE", fecha_descargue),
        ("FECHAENTRADADESCARGUE", fecha_descargue),
        ("FECHASALIDADESCARGUE", fecha_descargue),
        ("HORALLEGADADESCARGUECUMPLIDO", hora_descargue),
        ("HORAENTRADADESCARGUECUMPLIDO", hora_descargue),
        ("HORASALIDADESCARGUECUMPLIDO", hora_llegada),
    ]

    for id_suffix, value in campos:
        campo_id = f"dnn_ctr396_CumplirRemesa_{id_suffix}"
        elementos = driver.find_elements(By.ID, campo_id)
        if elementos:
            elementos[0].clear()
            elementos[0].send_keys(value)
        else:
            raise ValueError(f"CAMPOS_REMESA_INCOMPLETOS: Falta campo '{campo_id}'")
    return campos 

def guardar_y_manejar_alertas(driver, codigo, actualizar_estado_callback, campos):
    def intentar_guardado():
        driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_btGuardar").click()
        try:
            WebDriverWait(driver, 3).until(EC.alert_is_present())
            alerta = driver.switch_to.alert
            texto = alerta.text
            alerta.accept()
            return texto
        except TimeoutException:
            return None

    texto_alerta = intentar_guardado()
    
    # Si no hubo alerta, se guarda correctamente
    if texto_alerta is None:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo"))
        )
        actualizar_estado_callback(f"✅ Remesa {codigo} completada correctamente.")
        return

    # Registrar intento fallido
    registrar_log_remesa(codigo, texto_alerta, campos)

    # Casos especiales
    if "CRE064" in texto_alerta:
        actualizar_estado_callback(f"✅ Remesa {codigo} ya había sido completada anteriormente.")
        return
    if "CRE250" in texto_alerta:
        actualizar_estado_callback(f"⚠ Remesa {codigo} con error de fechas.")
        return

    # Manejo del error CRE308
    if "CRE308" in texto_alerta:
        try:
            actualizar_estado_callback(f"⏳ Error CRE308 en {codigo}. Reintentando con fecha de descargue +5 días...")

            # Aumentar 3 días a la fecha de descargue en los campos y recargar en el formulario
            nueva_fecha = (datetime.strptime(campos[6][1], "%d/%m/%Y") + timedelta(days=5)).strftime("%d/%m/%Y")
            for i, (campo_id, valor) in enumerate(campos):
                if "FECHALLEGADADESCARGUE" in campo_id or "FECHAENTRADADESCARGUE" in campo_id or "FECHASALIDADESCARGUE" in campo_id:
                    campos[i] = (campo_id, nueva_fecha)

            # Reescribir campos en el formulario
            for id_suffix, value in campos:
                campo_id = f"dnn_ctr396_CumplirRemesa_{id_suffix}"
                elementos = driver.find_elements(By.ID, campo_id)
                if elementos:
                    elementos[0].clear()
                    elementos[0].send_keys(value)

            texto_alerta_reintento = intentar_guardado()
            if texto_alerta_reintento is None:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo"))
                )
                registrar_log_remesa(codigo, "Reintento exitoso con fecha +3 días", campos)
                actualizar_estado_callback(f"✅ Remesa {codigo} completada correctamente tras reintento.")
                return
            else:
                registrar_log_remesa(codigo, f"Reintento fallido: {texto_alerta_reintento}", campos)
                actualizar_estado_callback(f"❌ Remesa {codigo} falló incluso tras reintento: {texto_alerta_reintento}")
                return

        except Exception as e:
            actualizar_estado_callback(f"❌ Error al reintentar remesa {codigo}: {e}")
            registrar_log_remesa(codigo, f"Fallo en reintento CRE308: {e}", campos)
            return

    # Otros errores
    actualizar_estado_callback(f"❌ Remesa {codigo} falló: {texto_alerta}")


def ejecutar_remesas(driver, codigos, actualizar_estado_callback):
    try:
        driver.get("https://rndc.mintransporte.gov.co/MenuPrincipal/tabid/204/language/es-MX/Default.aspx?returnurl=%2fMenuPrincipal%2ftabid%2f204%2flanguage%2fes-MX%2fDefault.aspx")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "dnn_ctr580_FormLogIn_edUsername"))
        )
        driver.find_element(By.ID, "dnn_ctr580_FormLogIn_edUsername").send_keys("Sotranscolombianos1@0341")
        driver.find_element(By.ID, "dnn_ctr580_FormLogIn_edPassword").send_keys("053EPA746**")
        driver.find_element(By.ID, "dnn_ctr580_FormLogIn_btIngresar").click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "tddnn_dnnSOLPARTMENU_ctldnnSOLPARTMENU120"))
        )

        navegar_a_formulario(driver)

        for codigo in codigos:
            actualizar_estado_callback(f"Procesando remesa {codigo}...")
            navegar_a_formulario(driver)
            try:
                campos = llenar_formulario_remesa(driver, codigo)
                guardar_y_manejar_alertas(driver, codigo, actualizar_estado_callback, campos)
            except Exception as e:
                actualizar_estado_callback(f"❌ Error procesando remesa {codigo}: {e}")
                registrar_log_remesa(codigo, f"Excepción: {e}", campos if 'campos' in locals() else[])
                # ⏸️ Aquí pausamos si el error no es conocido
                # if not any(s in str(e) for s in ["REMESA_FECHA_DESCARGUE_FUTURA", "CRE064", "REMESA_NO_ENCONTRADA"]):
                #     print(f"\n⏸️  Pausado por error desconocido en remesa {codigo}.")
                #     print(f"🔍 Excepción completa: {e}")
                #     input("🔧 Presiona Enter para continuar...")
                navegar_a_formulario(driver)
                continue

        actualizar_estado_callback("✅ Todas las remesas completadas.")
    except Exception as e:
        actualizar_estado_callback(f"❌ Error general llenando remesas: {e}")