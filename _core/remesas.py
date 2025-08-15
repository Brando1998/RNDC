from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, TimeoutException
from datetime import datetime, timedelta
import time
from _utils.logger import registrar_log_remesa
from tkinter import messagebox


def navegar_al_formulario_remesa(driver):
    driver.execute_script("window.localStorage.clear();")
    driver.execute_script("window.sessionStorage.clear();")
    driver.get("https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirRemesa/mid/396/procesoid/5/default.aspx")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA"))
    )


def llenar_formulario_remesa(driver, remesa_id):
    campo_remesa = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA")
    campo_remesa.clear()
    campo_remesa.send_keys(remesa_id)
    campo_remesa.send_keys("\t")
    time.sleep(1)

    mensaje_sistema = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_MENSAJE").get_attribute("value")
    if "no ha sido emitida o ya está cerrada" in mensaje_sistema:
        raise ValueError("REMESA_NO_EMITIDA_O_YA_CERRADA")

    Select(driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_NOMTIPOCUMPLIDOREMESA")).select_by_visible_text("Cumplido Normal")

    cantidad_cargada = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CANTIDADCARGADA").get_attribute("value")
    campo_entregada = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CANTIDADENTREGADA")
    campo_entregada.clear()
    campo_entregada.send_keys(cantidad_cargada)

    fecha_cargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHACITAPACTADACARGUE").get_attribute("value")
    hora_cargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORACITAPACTADACARGUE").get_attribute("value")
    hora_salida_cargue_dt = datetime.strptime(hora_cargue, "%H:%M") + timedelta(minutes=60)
    hora_salida_cargue = hora_salida_cargue_dt.strftime("%H:%M")

    fecha_descargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHACITAPACTADADESCARGUE").get_attribute("value")
    hora_descargue_original = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORACITAPACTADADESCARGUEREMESA").get_attribute("value")
    hora_llegada_descargue_dt = datetime.strptime(hora_descargue_original, "%H:%M")

    if hora_llegada_descargue_dt <= hora_salida_cargue_dt + timedelta(minutes=15):
        hora_llegada_descargue_dt = hora_salida_cargue_dt + timedelta(minutes=16)

    hora_llegada_descargue = hora_llegada_descargue_dt.strftime("%H:%M")
    hora_salida_descargue_dt = hora_llegada_descargue_dt + timedelta(minutes=60)
    hora_salida_descargue = hora_salida_descargue_dt.strftime("%H:%M")

    fecha_salida_descargue_dt = datetime.strptime(fecha_descargue + " " + hora_llegada_descargue, "%d/%m/%Y %H:%M") + timedelta(minutes=60)
    fecha_salida_descargue = fecha_salida_descargue_dt.strftime("%d/%m/%Y")

    if datetime.strptime(fecha_descargue, "%d/%m/%Y").date() > datetime.today().date():
        raise ValueError("REMESA_FECHA_DESCARGUE_FUTURA")

    campos_remesa = [
        ("FECHALLEGADACARGUE", fecha_cargue),
        ("FECHAENTRADACARGUE", fecha_cargue),
        ("FECHASALIDACARGUE", fecha_cargue),
        ("HORALLEGADACARGUEREMESA", hora_cargue),
        ("HORAENTRADACARGUEREMESA", hora_cargue),
        ("HORASALIDACARGUEREMESA", hora_salida_cargue),
        ("FECHALLEGADADESCARGUE", fecha_descargue),
        ("FECHAENTRADADESCARGUE", fecha_descargue),
        ("FECHASALIDADESCARGUE", fecha_salida_descargue),
        ("HORALLEGADADESCARGUECUMPLIDO", hora_llegada_descargue),
        ("HORAENTRADADESCARGUECUMPLIDO", hora_llegada_descargue),
        ("HORASALIDADESCARGUECUMPLIDO", hora_salida_descargue),
    ]

    for sufijo_id, valor in campos_remesa:
        campo_id = f"dnn_ctr396_CumplirRemesa_{sufijo_id}"
        elementos = driver.find_elements(By.ID, campo_id)
        if elementos:
            elementos[0].clear()
            elementos[0].send_keys(valor)
        else:
            raise ValueError(f"CAMPOS_REMESA_INCOMPLETOS: Falta campo '{campo_id}'")

    return campos_remesa

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

    def reescribir_campos(campos_actualizados):
        for id_suffix, value in campos_actualizados:
            campo_id = f"dnn_ctr396_CumplirRemesa_{id_suffix}"
            elementos = driver.find_elements(By.ID, campo_id)
            if elementos:
                elementos[0].clear()
                elementos[0].send_keys(value)

    def manejar_cre308():
        try:
            actualizar_estado_callback(f"⏳ Error CRE308 en {codigo}. Reintentando con fecha descargue +5 días...")

            nueva_fecha = (datetime.strptime(campos[6][1], "%d/%m/%Y") + timedelta(days=5)).strftime("%d/%m/%Y")
            campos_modificados = [
                (id_campo, nueva_fecha if "FECHALLEGADADESCARGUE" in id_campo or 
                                           "FECHAENTRADADESCARGUE" in id_campo or 
                                           "FECHASALIDADESCARGUE" in id_campo 
                 else valor)
                for id_campo, valor in campos
            ]

            reescribir_campos(campos_modificados)

            texto_alerta_reintento = intentar_guardado()
            if texto_alerta_reintento is None:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo"))
                )
                registrar_log_remesa(codigo, "Reintento exitoso con fecha +5 días", campos_modificados)
                actualizar_estado_callback(f"✅ Remesa {codigo} completada correctamente tras reintento.")
            else:
                registrar_log_remesa(codigo, f"Reintento fallido: {texto_alerta_reintento}", campos_modificados)
                actualizar_estado_callback(f"❌ Remesa {codigo} falló incluso tras reintento: {texto_alerta_reintento}")
        except Exception as e:
            actualizar_estado_callback(f"❌ Error al reintentar remesa {codigo}: {e}")
            registrar_log_remesa(codigo, f"Fallo en reintento CRE308: {e}", campos)

    def manejar_cre309():
        try:
            actualizar_estado_callback(f"⏳ Error CRE309 en {codigo}. Reintentando con +3 días y +3 horas en descargue...")

            nueva_fecha = (datetime.strptime(campos[6][1], "%d/%m/%Y") + timedelta(days=3)).strftime("%d/%m/%Y")

            campos_modificados = []
            for id_campo, valor in campos:
                if "FECHALLEGADADESCARGUE" in id_campo or "FECHAENTRADADESCARGUE" in id_campo or "FECHASALIDADESCARGUE" in id_campo:
                    campos_modificados.append((id_campo, nueva_fecha))
                elif "HORALLEGADADESCARGUECUMPLIDO" in id_campo or "HORAENTRADADESCARGUECUMPLIDO" in id_campo or "HORASALIDADESCARGUECUMPLIDO" in id_campo:
                    hora_original = datetime.strptime(valor, "%H:%M")
                    nueva_hora = (hora_original + timedelta(hours=3)).strftime("%H:%M")
                    campos_modificados.append((id_campo, nueva_hora))
                else:
                    campos_modificados.append((id_campo, valor))

            reescribir_campos(campos_modificados)

            texto_alerta_reintento = intentar_guardado()
            if texto_alerta_reintento is None:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo"))
                )
                registrar_log_remesa(codigo, "Reintento exitoso tras CRE309", campos_modificados)
                actualizar_estado_callback(f"✅ Remesa {codigo} completada correctamente tras reintento CRE309.")
            else:
                registrar_log_remesa(codigo, f"Reintento fallido CRE309: {texto_alerta_reintento}", campos_modificados)
                actualizar_estado_callback(f"❌ Remesa {codigo} falló incluso tras reintento CRE309: {texto_alerta_reintento}")
        except Exception as e:
            actualizar_estado_callback(f"❌ Error al reintentar CRE309 en remesa {codigo}: {e}")
            registrar_log_remesa(codigo, f"Fallo en reintento CRE309: {e}", campos)
    
    def manejar_cre270():
        try:
            actualizar_estado_callback(f"⏳ Error CRE270 en {codigo}. Reintentando con fechas basadas en fecha de expedición...")
            
            # Obtener la fecha de expedición del formulario
            fecha_expedicion_element = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHAEMISION")
            fecha_expedicion_str = fecha_expedicion_element.get_attribute("value")
            
            # Parsear la fecha de expedición
            fecha_expedicion = datetime.strptime(fecha_expedicion_str, "%d/%m/%Y")
            
            # Calcular fechas para cargue (misma fecha de expedición)
            fecha_cargue = fecha_expedicion.strftime("%d/%m/%Y")
            
            # Calcular fechas para descargue (3 días después de expedición)
            fecha_descargue = (fecha_expedicion + timedelta(days=3)).strftime("%d/%m/%Y")
            
            # Calcular fecha de salida descargue (1 hora después de llegada descargue)
            fecha_salida_descargue = fecha_descargue  # Misma fecha en este caso
            
            # Mantener las horas originales de los campos
            hora_cargue = campos[3][1]  # HORALLEGADACARGUEREMESA
            hora_salida_cargue = campos[5][1]  # HORASALIDACARGUEREMESA
            hora_llegada_descargue = campos[9][1]  # HORALLEGADADESCARGUECUMPLIDO
            hora_salida_descargue = campos[11][1]  # HORASALIDADESCARGUECUMPLIDO
            
            # Crear nuevos campos modificados
            campos_modificados = [
                ("FECHALLEGADACARGUE", fecha_cargue),
                ("FECHAENTRADACARGUE", fecha_cargue),
                ("FECHASALIDACARGUE", fecha_cargue),
                ("HORALLEGADACARGUEREMESA", hora_cargue),
                ("HORAENTRADACARGUEREMESA", hora_cargue),
                ("HORASALIDACARGUEREMESA", hora_salida_cargue),
                ("FECHALLEGADADESCARGUE", fecha_descargue),
                ("FECHAENTRADADESCARGUE", fecha_descargue),
                ("FECHASALIDADESCARGUE", fecha_salida_descargue),
                ("HORALLEGADADESCARGUECUMPLIDO", hora_llegada_descargue),
                ("HORAENTRADADESCARGUECUMPLIDO", hora_llegada_descargue),
                ("HORASALIDADESCARGUECUMPLIDO", hora_salida_descargue),
            ]
            
            reescribir_campos(campos_modificados)

            texto_alerta_reintento = intentar_guardado()
            if texto_alerta_reintento is None:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo"))
                )
                registrar_log_remesa(codigo, "Reintento exitoso tras CRE270", campos_modificados)
                actualizar_estado_callback(f"✅ Remesa {codigo} completada correctamente tras reintento CRE270.")
            else:
                registrar_log_remesa(codigo, f"Reintento fallido CRE270: {texto_alerta_reintento}", campos_modificados)
                actualizar_estado_callback(f"❌ Remesa {codigo} falló incluso tras reintento CRE270: {texto_alerta_reintento}")
        except Exception as e:
            actualizar_estado_callback(f"❌ Error al reintentar CRE270 en remesa {codigo}: {e}")
            registrar_log_remesa(codigo, f"Fallo en reintento CRE270: {e}", campos)
    # --- Proceso principal ---
    texto_alerta = intentar_guardado()

    if texto_alerta is None:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo"))
        )
        actualizar_estado_callback(f"✅ Remesa {codigo} completada correctamente.")
        return

    registrar_log_remesa(codigo, texto_alerta, campos)

    if "CRE064" in texto_alerta:
        actualizar_estado_callback(f"✅ Remesa {codigo} ya había sido completada anteriormente.")
    elif "CRE250" in texto_alerta:
        actualizar_estado_callback(f"⚠ Remesa {codigo} con error de fechas.")
    elif "CRE308" in texto_alerta:
        manejar_cre308()
    elif "CRE309" in texto_alerta:
        manejar_cre309()
    elif "CRE270" in texto_alerta:
        manejar_cre270()
    else:
        actualizar_estado_callback(f"❌ Remesa {codigo} falló: {texto_alerta}")


def ejecutar_remesas(driver, codigos, actualizar_estado_callback, pausa_event, cancelar_func):
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

        navegar_al_formulario_remesa(driver)

        for codigo in codigos:
            if cancelar_func():
                driver.quit()
                actualizar_estado_callback("⛔ Proceso cancelado por el usuario.")
                break
            actualizar_estado_callback(f"Procesando remesa {codigo}...")
            pausa_event.wait()
            navegar_al_formulario_remesa(driver)
            try:
                campos = llenar_formulario_remesa(driver, codigo)
                guardar_y_manejar_alertas(driver, codigo, actualizar_estado_callback, campos)
            except Exception as e:
                actualizar_estado_callback(f"❌ Error procesando remesa {codigo}: {e}")
                registrar_log_remesa(codigo, f"Excepción: {e}", campos if 'campos' in locals() else[])
                # ⏸️ Aquí pausamos si el error no es conocido
                # if not any(s in str(e) for s in ["REMESA_FECHA_DESCARGUE_FUTURA", "CRE064", "CRE250", "CRE308", "CRE309", "REMESA_NO_EMITIDA_O_YA_CERRADA", "CAMPOS_REMESA_INCOMPLETOS"]):
                #     print(f"\n⏸️  Pausado por error desconocido en remesa {codigo}.")
                #     print(f"🔍 Excepción completa: {e}")
                #     input("🔧 Presiona Enter para continuar...")
                navegar_al_formulario_remesa(driver)
                continue
            actualizar_estado_callback("✅ Todas las remesas completadas.")
    except Exception as e:
        actualizar_estado_callback(f"❌ Error general llenando remesas: {e}")
    finally:
        driver.quit()
        if not cancelar_func():
            messagebox.showinfo(
                "Proceso completado",
                "El proceso de llenado de remesas ha finalizado. Revisa el log de errores para más detalles."
            )
        actualizar_estado_callback("✅ Todas las remesas completadas.")