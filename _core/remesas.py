from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from datetime import datetime, timedelta
from tkinter import messagebox
import time
from _utils.logger import registrar_log_remesa, obtener_logger, TipoProceso
from _core.common import hacer_login, navegar_a_remesas, TIMEOUT_CORTO, TIMEOUT_MEDIO


# ============================================================================
# CONSTANTES Y LOGGER
# ============================================================================
ERROR_REMESA_NO_EMITIDA = "no ha sido emitida o ya está cerrada"
ERROR_CRE064 = "CRE064"
ERROR_CRE080 = "CRE080"
ERROR_CRE100 = "CRE100"
ERROR_CRE130 = "CRE130"
ERROR_CRE141 = "CRE141"
ERROR_CRE230 = "CRE230"
ERROR_CRE250 = "CRE250"
ERROR_CRE270 = "CRE270"
ERROR_CRE308 = "CRE308"
ERROR_CRE309 = "CRE309"

logger = obtener_logger(TipoProceso.REMESA)


# ============================================================================
# VALIDACIÓN
# ============================================================================
def validar_hora_formato(hora_str):
    if not hora_str or hora_str.strip() == "":
        return False, "00:00"
    try:
        datetime.strptime(hora_str.strip(), "%H:%M")
        return True, hora_str.strip()
    except ValueError:
        hora_limpia = hora_str.strip()
        if ":" in hora_limpia:
            partes = hora_limpia.split(":")
            if len(partes) == 2:
                try:
                    hora = int(partes[0])
                    minuto = int(partes[1])
                    if 0 <= hora <= 23 and 0 <= minuto <= 59:
                        return True, f"{hora:02d}:{minuto:02d}"
                except ValueError:
                    pass
        return False, "00:00"


# ============================================================================
# CÁLCULOS
# ============================================================================
def calcular_hora_salida(hora_entrada_str, minutos_adicionales=60):
    es_valida, hora_corregida = validar_hora_formato(hora_entrada_str)
    if not es_valida:
        logger.registrar_error("SISTEMA", f"Hora inválida: '{hora_entrada_str}'", codigo_error="HORA_INVALIDA")
    hora_entrada = datetime.strptime(hora_corregida, "%H:%M")
    hora_salida = hora_entrada + timedelta(minutes=minutos_adicionales)
    return hora_salida.strftime("%H:%M")


def ajustar_hora_descargue(hora_descargue_str, hora_salida_cargue_str):
    es_valida_desc, hora_desc_corregida = validar_hora_formato(hora_descargue_str)
    es_valida_salida, hora_salida_corregida = validar_hora_formato(hora_salida_cargue_str)
    
    hora_descargue = datetime.strptime(hora_desc_corregida, "%H:%M")
    hora_salida_cargue = datetime.strptime(hora_salida_corregida, "%H:%M")
    
    if hora_descargue <= hora_salida_cargue + timedelta(minutes=15):
        hora_descargue = hora_salida_cargue + timedelta(minutes=16)
    
    return hora_descargue.strftime("%H:%M")


def calcular_fecha_salida_descargue(fecha_descargue_str, hora_llegada_str):
    es_valida, hora_corregida = validar_hora_formato(hora_llegada_str)
    fecha_hora_llegada = datetime.strptime(f"{fecha_descargue_str} {hora_corregida}", "%d/%m/%Y %H:%M")
    fecha_salida = fecha_hora_llegada + timedelta(minutes=60)
    return fecha_salida.strftime("%d/%m/%Y")


# ============================================================================
# LLENADO DE FORMULARIO
# ============================================================================
def llenar_formulario_remesa(driver, remesa_id):
    campo_remesa = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA")
    campo_remesa.clear()
    campo_remesa.send_keys(remesa_id)
    campo_remesa.send_keys("\t")
    time.sleep(1)
    
    mensaje_sistema = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_MENSAJE").get_attribute("value")
    if ERROR_REMESA_NO_EMITIDA in mensaje_sistema:
        logger.registrar_error(remesa_id, "Remesa no emitida o ya cerrada", codigo_error="NO_EMITIDA")
        raise ValueError("REMESA_NO_EMITIDA_O_YA_CERRADA")
    
    Select(driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_NOMTIPOCUMPLIDOREMESA")).select_by_visible_text("Cumplido Normal")
    
    cantidad_cargada = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CANTIDADCARGADA").get_attribute("value")
    campo_entregada = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CANTIDADENTREGADA")
    campo_entregada.clear()
    campo_entregada.send_keys(cantidad_cargada)
    
    fecha_cargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHACITAPACTADACARGUE").get_attribute("value")
    hora_cargue_raw = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORACITAPACTADACARGUE").get_attribute("value")
    es_valida_cargue, hora_cargue = validar_hora_formato(hora_cargue_raw)
    
    if not es_valida_cargue:
        logger.registrar_error(remesa_id, f"Hora cargue inválida: '{hora_cargue_raw}'", codigo_error="HORA_CARGUE_INVALIDA")
    
    hora_salida_cargue = calcular_hora_salida(hora_cargue, 60)
    
    fecha_descargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHACITAPACTADADESCARGUE").get_attribute("value")
    hora_descargue_raw = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORACITAPACTADADESCARGUEREMESA").get_attribute("value")
    es_valida_desc, hora_descargue_original = validar_hora_formato(hora_descargue_raw)
    
    if not es_valida_desc:
        logger.registrar_error(remesa_id, f"Hora descargue inválida: '{hora_descargue_raw}'", codigo_error="HORA_DESCARGUE_INVALIDA")
    
    if datetime.strptime(fecha_descargue, "%d/%m/%Y").date() > datetime.today().date():
        logger.registrar_error(remesa_id, "Fecha de descargue es futura", codigo_error="FECHA_FUTURA")
        raise ValueError("REMESA_FECHA_DESCARGUE_FUTURA")
    
    hora_llegada_descargue = ajustar_hora_descargue(hora_descargue_original, hora_salida_cargue)
    hora_salida_descargue = calcular_hora_salida(hora_llegada_descargue, 60)
    fecha_salida_descargue = calcular_fecha_salida_descargue(fecha_descargue, hora_llegada_descargue)
    
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
            logger.registrar_error(remesa_id, f"Falta campo '{campo_id}'", codigo_error="CAMPO_FALTANTE")
            raise ValueError(f"CAMPOS_REMESA_INCOMPLETOS: Falta campo '{campo_id}'")
    
    return campos_remesa


# ============================================================================
# GUARDADO Y ALERTAS
# ============================================================================
def intentar_guardado(driver):
    driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_btGuardar").click()
    try:
        WebDriverWait(driver, TIMEOUT_CORTO).until(EC.alert_is_present())
        alerta = driver.switch_to.alert
        texto = alerta.text
        alerta.accept()
        return texto
    except TimeoutException:
        return None


def reescribir_campos(driver, campos_actualizados):
    for id_suffix, value in campos_actualizados:
        campo_id = f"dnn_ctr396_CumplirRemesa_{id_suffix}"
        elementos = driver.find_elements(By.ID, campo_id)
        if elementos:
            elementos[0].clear()
            elementos[0].send_keys(value)


def manejar_error_cre230(driver, codigo, campos, actualizar_estado_callback):
    try:
        actualizar_estado_callback(f"⏳ Error CRE230 en {codigo}. Corrigiendo formato...")
        logger.registrar_reintento(codigo, 1, "Corrigiendo CRE230", codigo_error=ERROR_CRE230)
        
        hora_salida_desc = campos[11][1]
        es_valida, hora_corregida = validar_hora_formato(hora_salida_desc)
        if not es_valida:
            hora_llegada_desc = campos[9][1]
            hora_corregida = calcular_hora_salida(hora_llegada_desc, 60)
        
        campos_modificados = [
            (id_campo, hora_corregida if "HORASALIDADESCARGUECUMPLIDO" in id_campo else valor)
            for id_campo, valor in campos
        ]
        reescribir_campos(driver, campos_modificados)
        texto_alerta_reintento = intentar_guardado(driver)
        
        if texto_alerta_reintento is None:
            WebDriverWait(driver, TIMEOUT_MEDIO).until(
                EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo"))
            )
            logger.registrar_exito(codigo, "Reintento exitoso tras CRE230")
            actualizar_estado_callback(f"✅ Remesa {codigo} completada tras corregir formato.")
            return True
        else:
            logger.registrar_alerta(codigo, "CRE230_RETRY_FAILED", f"Reintento fallido: {texto_alerta_reintento}")
            return False
    except Exception as e:
        logger.registrar_excepcion(codigo, e, "Error en reintento CRE230")
        return False


def manejar_error_cre141(driver, codigo, campos, actualizar_estado_callback):
    try:
        actualizar_estado_callback(f"⏳ Error CRE141 en {codigo}. Ajustando horas...")
        logger.registrar_reintento(codigo, 1, "Ajustando CRE141", codigo_error=ERROR_CRE141)
        
        hora_entrada_cargue = campos[4][1]
        nueva_hora_salida = calcular_hora_salida(hora_entrada_cargue, 1)
        
        campos_modificados = [
            (id_campo, nueva_hora_salida if "HORASALIDACARGUEREMESA" in id_campo else valor)
            for id_campo, valor in campos
        ]
        reescribir_campos(driver, campos_modificados)
        texto_alerta_reintento = intentar_guardado(driver)
        
        if texto_alerta_reintento is None:
            WebDriverWait(driver, TIMEOUT_MEDIO).until(
                EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo"))
            )
            logger.registrar_exito(codigo, "Reintento exitoso tras CRE141")
            actualizar_estado_callback(f"✅ Remesa {codigo} completada tras ajustar horas.")
            return True
        else:
            logger.registrar_alerta(codigo, "CRE141_RETRY_FAILED", f"Reintento fallido: {texto_alerta_reintento}")
            return False
    except Exception as e:
        logger.registrar_excepcion(codigo, e, "Error en reintento CRE141")
        return False


def manejar_errores_antiguedad(driver, codigo, campos, actualizar_estado_callback):
    try:
        actualizar_estado_callback(f"⏳ Error de antigüedad en {codigo}. Usando fecha expedición...")
        logger.registrar_reintento(codigo, 1, "Ajustando antigüedad", codigo_error="CRE_ANTIGUEDAD")
        
        fecha_expedicion_element = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHAEMISION")
        fecha_expedicion_str = fecha_expedicion_element.get_attribute("value")
        fecha_expedicion = datetime.strptime(fecha_expedicion_str, "%d/%m/%Y")
        
        fecha_cargue = fecha_expedicion.strftime("%d/%m/%Y")
        fecha_descargue = (fecha_expedicion + timedelta(days=1)).strftime("%d/%m/%Y")
        
        campos_modificados = [
            ("FECHALLEGADACARGUE", fecha_cargue),
            ("FECHAENTRADACARGUE", fecha_cargue),
            ("FECHASALIDACARGUE", fecha_cargue),
            ("HORALLEGADACARGUEREMESA", campos[3][1]),
            ("HORAENTRADACARGUEREMESA", campos[3][1]),
            ("HORASALIDACARGUEREMESA", campos[5][1]),
            ("FECHALLEGADADESCARGUE", fecha_descargue),
            ("FECHAENTRADADESCARGUE", fecha_descargue),
            ("FECHASALIDADESCARGUE", fecha_descargue),
            ("HORALLEGADADESCARGUECUMPLIDO", campos[9][1]),
            ("HORAENTRADADESCARGUECUMPLIDO", campos[9][1]),
            ("HORASALIDADESCARGUECUMPLIDO", campos[11][1]),
        ]
        reescribir_campos(driver, campos_modificados)
        texto_alerta_reintento = intentar_guardado(driver)
        
        if texto_alerta_reintento is None:
            WebDriverWait(driver, TIMEOUT_MEDIO).until(
                EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo"))
            )
            logger.registrar_exito(codigo, "Reintento exitoso tras antigüedad")
            actualizar_estado_callback(f"✅ Remesa {codigo} completada tras ajustar fechas.")
            return True
        else:
            logger.registrar_alerta(codigo, "ANTIGUEDAD_RETRY_FAILED", f"Reintento fallido: {texto_alerta_reintento}")
            return False
    except Exception as e:
        logger.registrar_excepcion(codigo, e, "Error en reintento antigüedad")
        return False


def manejar_error_cre308(driver, codigo, campos, actualizar_estado_callback):
    try:
        actualizar_estado_callback(f"⏳ Error CRE308 en {codigo}. +5 días...")
        logger.registrar_reintento(codigo, 1, "Ajustando CRE308 (+5 días)", codigo_error=ERROR_CRE308)
        
        nueva_fecha = (datetime.strptime(campos[6][1], "%d/%m/%Y") + timedelta(days=5)).strftime("%d/%m/%Y")
        campos_modificados = [
            (id_campo, nueva_fecha if any(x in id_campo for x in ["FECHALLEGADADESCARGUE", "FECHAENTRADADESCARGUE", "FECHASALIDADESCARGUE"]) else valor)
            for id_campo, valor in campos
        ]
        reescribir_campos(driver, campos_modificados)
        texto_alerta_reintento = intentar_guardado(driver)
        
        if texto_alerta_reintento is None:
            WebDriverWait(driver, TIMEOUT_MEDIO).until(EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo")))
            logger.registrar_exito(codigo, "Reintento exitoso CRE308")
            actualizar_estado_callback(f"✅ Remesa {codigo} completada.")
            return True
        else:
            logger.registrar_alerta(codigo, "CRE308_RETRY_FAILED", f"Reintento fallido: {texto_alerta_reintento}")
            return False
    except Exception as e:
        logger.registrar_excepcion(codigo, e, "Error en reintento CRE308")
        return False


def manejar_error_cre309(driver, codigo, campos, actualizar_estado_callback):
    try:
        actualizar_estado_callback(f"⏳ Error CRE309 en {codigo}. +3 días y +3 horas...")
        logger.registrar_reintento(codigo, 1, "Ajustando CRE309", codigo_error=ERROR_CRE309)
        
        nueva_fecha = (datetime.strptime(campos[6][1], "%d/%m/%Y") + timedelta(days=3)).strftime("%d/%m/%Y")
        campos_modificados = []
        for id_campo, valor in campos:
            if any(x in id_campo for x in ["FECHALLEGADADESCARGUE", "FECHAENTRADADESCARGUE", "FECHASALIDADESCARGUE"]):
                campos_modificados.append((id_campo, nueva_fecha))
            elif any(x in id_campo for x in ["HORALLEGADADESCARGUECUMPLIDO", "HORAENTRADADESCARGUECUMPLIDO", "HORASALIDADESCARGUECUMPLIDO"]):
                hora_original = datetime.strptime(valor, "%H:%M")
                nueva_hora = (hora_original + timedelta(hours=3)).strftime("%H:%M")
                campos_modificados.append((id_campo, nueva_hora))
            else:
                campos_modificados.append((id_campo, valor))
        
        reescribir_campos(driver, campos_modificados)
        texto_alerta_reintento = intentar_guardado(driver)
        
        if texto_alerta_reintento is None:
            WebDriverWait(driver, TIMEOUT_MEDIO).until(EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo")))
            logger.registrar_exito(codigo, "Reintento exitoso CRE309")
            actualizar_estado_callback(f"✅ Remesa {codigo} completada.")
            return True
        else:
            logger.registrar_alerta(codigo, "CRE309_RETRY_FAILED", f"Reintento fallido: {texto_alerta_reintento}")
            return False
    except Exception as e:
        logger.registrar_excepcion(codigo, e, "Error en reintento CRE309")
        return False


def manejar_error_cre270(driver, codigo, campos, actualizar_estado_callback):
    try:
        actualizar_estado_callback(f"⏳ Error CRE270 en {codigo}. Usando fecha expedición...")
        logger.registrar_reintento(codigo, 1, "Ajustando CRE270", codigo_error=ERROR_CRE270)
        
        fecha_expedicion_element = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHAEMISION")
        fecha_expedicion_str = fecha_expedicion_element.get_attribute("value")
        fecha_expedicion = datetime.strptime(fecha_expedicion_str, "%d/%m/%Y")
        
        fecha_cargue = fecha_expedicion.strftime("%d/%m/%Y")
        fecha_descargue = (fecha_expedicion + timedelta(days=3)).strftime("%d/%m/%Y")
        
        campos_modificados = [
            ("FECHALLEGADACARGUE", fecha_cargue),
            ("FECHAENTRADACARGUE", fecha_cargue),
            ("FECHASALIDACARGUE", fecha_cargue),
            ("HORALLEGADACARGUEREMESA", campos[3][1]),
            ("HORAENTRADACARGUEREMESA", campos[3][1]),
            ("HORASALIDACARGUEREMESA", campos[5][1]),
            ("FECHALLEGADADESCARGUE", fecha_descargue),
            ("FECHAENTRADADESCARGUE", fecha_descargue),
            ("FECHASALIDADESCARGUE", fecha_descargue),
            ("HORALLEGADADESCARGUECUMPLIDO", campos[9][1]),
            ("HORAENTRADADESCARGUECUMPLIDO", campos[9][1]),
            ("HORASALIDADESCARGUECUMPLIDO", campos[11][1]),
        ]
        reescribir_campos(driver, campos_modificados)
        texto_alerta_reintento = intentar_guardado(driver)
        
        if texto_alerta_reintento is None:
            WebDriverWait(driver, TIMEOUT_MEDIO).until(EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo")))
            logger.registrar_exito(codigo, "Reintento exitoso CRE270")
            actualizar_estado_callback(f"✅ Remesa {codigo} completada.")
            return True
        else:
            logger.registrar_alerta(codigo, "CRE270_RETRY_FAILED", f"Reintento fallido: {texto_alerta_reintento}")
            return False
    except Exception as e:
        logger.registrar_excepcion(codigo, e, "Error en reintento CRE270")
        return False


def guardar_y_manejar_alertas(driver, codigo, actualizar_estado_callback, campos):
    texto_alerta = intentar_guardado(driver)
    
    if texto_alerta is None:
        WebDriverWait(driver, TIMEOUT_MEDIO).until(EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo")))
        logger.registrar_exito(codigo, "Remesa completada correctamente")
        actualizar_estado_callback(f"✅ Remesa {codigo} completada correctamente.")
        return True
    
    logger.registrar_alerta(codigo, texto_alerta.split()[0] if texto_alerta else "UNKNOWN", texto_alerta)
    registrar_log_remesa(codigo, texto_alerta, campos)
    
    if ERROR_CRE064 in texto_alerta:
        logger.registrar_exito(codigo, "Remesa ya completada", codigo_error=ERROR_CRE064)
        actualizar_estado_callback(f"✅ Remesa {codigo} ya completada anteriormente.")
        return True
    elif ERROR_CRE230 in texto_alerta:
        return manejar_error_cre230(driver, codigo, campos, actualizar_estado_callback)
    elif ERROR_CRE141 in texto_alerta:
        return manejar_error_cre141(driver, codigo, campos, actualizar_estado_callback)
    elif any(err in texto_alerta for err in [ERROR_CRE080, ERROR_CRE100, ERROR_CRE130]):
        return manejar_errores_antiguedad(driver, codigo, campos, actualizar_estado_callback)
    elif ERROR_CRE250 in texto_alerta:
        actualizar_estado_callback(f"⚠ Remesa {codigo} con error de fechas.")
        return False
    elif ERROR_CRE308 in texto_alerta:
        return manejar_error_cre308(driver, codigo, campos, actualizar_estado_callback)
    elif ERROR_CRE309 in texto_alerta:
        return manejar_error_cre309(driver, codigo, campos, actualizar_estado_callback)
    elif ERROR_CRE270 in texto_alerta:
        return manejar_error_cre270(driver, codigo, campos, actualizar_estado_callback)
    else:
        logger.registrar_error(codigo, f"Error no manejado: {texto_alerta}")
        actualizar_estado_callback(f"❌ Remesa {codigo} falló: {texto_alerta}")
        return False


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================
def ejecutar_remesas(driver, codigos, actualizar_estado_callback, pausa_event, cancelar_func):
    try:
        hacer_login(driver)
        navegar_a_remesas(driver)
        
        for codigo in codigos:
            if cancelar_func():
                driver.quit()
                actualizar_estado_callback("⛔ Proceso cancelado por el usuario.")
                break
            
            actualizar_estado_callback(f"Procesando remesa {codigo}...")
            pausa_event.wait()
            navegar_a_remesas(driver)
            
            try:
                campos = llenar_formulario_remesa(driver, codigo)
                guardar_y_manejar_alertas(driver, codigo, actualizar_estado_callback, campos)
            except Exception as e:
                logger.registrar_excepcion(codigo, e, "Error procesando remesa")
                actualizar_estado_callback(f"❌ Error procesando remesa {codigo}: {e}")
                registrar_log_remesa(codigo, f"Excepción: {e}", campos if 'campos' in locals() else [])
                navegar_a_remesas(driver)
                continue
        
        actualizar_estado_callback("✅ Todas las remesas completadas.")
        reporte = logger.generar_reporte()
        print(reporte)
        
    except Exception as e:
        actualizar_estado_callback(f"❌ Error general llenando remesas: {e}")
        logger.registrar_excepcion("SISTEMA", e, "Error general en ejecución")
    finally:
        driver.quit()
        if not cancelar_func():
            messagebox.showinfo("Proceso completado", f"El proceso ha finalizado.\n\n{logger.generar_reporte()}")