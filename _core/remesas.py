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
# CONSTANTES ESPECÍFICAS DE REMESAS
# ============================================================================
# Mensajes de error conocidos
ERROR_REMESA_NO_EMITIDA = "no ha sido emitida o ya está cerrada"
ERROR_CRE064 = "CRE064"  # Ya completada
ERROR_CRE080 = "CRE080"  # Antigüedad de fecha de llegada al cargue
ERROR_CRE100 = "CRE100"  # Antigüedad de fecha de entrada al cargue
ERROR_CRE130 = "CRE130"  # Antigüedad de fecha de salida al cargue
ERROR_CRE141 = "CRE141"  # Hora entrada > hora salida en cargue
ERROR_CRE230 = "CRE230"  # Formato incorrecto hora salida descargue
ERROR_CRE250 = "CRE250"  # Error de fechas
ERROR_CRE270 = "CRE270"  # Error de fechas respecto a expedición
ERROR_CRE308 = "CRE308"  # Error de fechas en descargue
ERROR_CRE309 = "CRE309"  # Error de tiempos en descargue

# Obtener logger para remesas
logger = obtener_logger(TipoProceso.REMESA)


# ============================================================================
# FUNCIONES DE VALIDACIÓN
# ============================================================================
def validar_hora_formato(hora_str):
    """
    Valida que una hora tenga el formato correcto y no esté vacía.
    
    Args:
        hora_str: String con la hora
    
    Returns:
        tuple: (bool: es_valida, str: hora_corregida)
    """
    if not hora_str or hora_str.strip() == "":
        return False, "00:00"
    
    try:
        # Intentar parsear la hora
        datetime.strptime(hora_str.strip(), "%H:%M")
        return True, hora_str.strip()
    except ValueError:
        # Si falla, intentar corregir formatos comunes
        hora_limpia = hora_str.strip()
        
        # Caso: hora sin ceros a la izquierda (ej: "9:30" -> "09:30")
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
# FUNCIONES DE CÁLCULO DE FECHAS Y HORAS
# ============================================================================
def calcular_hora_salida(hora_entrada_str, minutos_adicionales=60):
    """
    Calcula la hora de salida sumando minutos a una hora de entrada.
    Maneja casos de horas vacías o inválidas.
    
    Args:
        hora_entrada_str: Hora en formato "HH:MM"
        minutos_adicionales: Minutos a sumar (default: 60)
    
    Returns:
        str: Hora de salida en formato "HH:MM"
    """
    es_valida, hora_corregida = validar_hora_formato(hora_entrada_str)
    
    if not es_valida:
        logger.registrar_error(
            "SISTEMA",
            f"Hora de entrada inválida: '{hora_entrada_str}', usando '{hora_corregida}'",
            codigo_error="HORA_INVALIDA"
        )
    
    hora_entrada = datetime.strptime(hora_corregida, "%H:%M")
    hora_salida = hora_entrada + timedelta(minutes=minutos_adicionales)
    return hora_salida.strftime("%H:%M")


def ajustar_hora_descargue(hora_descargue_str, hora_salida_cargue_str):
    """
    Ajusta la hora de descargue si es muy cercana a la salida de cargue.
    Debe haber al menos 16 minutos de diferencia.
    
    Args:
        hora_descargue_str: Hora de descargue en formato "HH:MM"
        hora_salida_cargue_str: Hora de salida de cargue en formato "HH:MM"
    
    Returns:
        str: Hora de descargue ajustada en formato "HH:MM"
    """
    # Validar ambas horas
    es_valida_desc, hora_desc_corregida = validar_hora_formato(hora_descargue_str)
    es_valida_salida, hora_salida_corregida = validar_hora_formato(hora_salida_cargue_str)
    
    if not es_valida_desc or not es_valida_salida:
        logger.registrar_error(
            "SISTEMA",
            f"Horas inválidas - Descargue: '{hora_descargue_str}', Salida: '{hora_salida_cargue_str}'",
            codigo_error="HORA_INVALIDA"
        )
    
    hora_descargue = datetime.strptime(hora_desc_corregida, "%H:%M")
    hora_salida_cargue = datetime.strptime(hora_salida_corregida, "%H:%M")
    
    if hora_descargue <= hora_salida_cargue + timedelta(minutes=15):
        hora_descargue = hora_salida_cargue + timedelta(minutes=16)
    
    return hora_descargue.strftime("%H:%M")


def calcular_fecha_salida_descargue(fecha_descargue_str, hora_llegada_str):
    """
    Calcula la fecha de salida del descargue sumando 60 minutos a la llegada.
    
    Args:
        fecha_descargue_str: Fecha en formato "dd/mm/YYYY"
        hora_llegada_str: Hora en formato "HH:MM"
    
    Returns:
        str: Fecha de salida en formato "dd/mm/YYYY"
    """
    es_valida, hora_corregida = validar_hora_formato(hora_llegada_str)
    
    fecha_hora_llegada = datetime.strptime(
        f"{fecha_descargue_str} {hora_corregida}", 
        "%d/%m/%Y %H:%M"
    )
    fecha_salida = fecha_hora_llegada + timedelta(minutes=60)
    return fecha_salida.strftime("%d/%m/%Y")


# ============================================================================
# FUNCIONES DE LLENADO DE FORMULARIO
# ============================================================================
def llenar_formulario_remesa(driver, remesa_id):
    """
    Llena el formulario de remesa con los datos calculados.
    Incluye validaciones para campos vacíos y formatos incorrectos.
    
    Args:
        driver: WebDriver de Selenium
        remesa_id: Código/ID de la remesa
    
    Returns:
        list: Lista de tuplas (campo_id, valor) con los campos utilizados
    
    Raises:
        ValueError: Si la remesa no está emitida, ya cerrada, o tiene fecha futura
    """
    # Ingresar código de remesa
    campo_remesa = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA")
    campo_remesa.clear()
    campo_remesa.send_keys(remesa_id)
    campo_remesa.send_keys("\t")
    time.sleep(1)
    
    # Verificar mensajes del sistema
    mensaje_sistema = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_MENSAJE").get_attribute("value")
    if ERROR_REMESA_NO_EMITIDA in mensaje_sistema:
        logger.registrar_error(remesa_id, "Remesa no emitida o ya cerrada", codigo_error="NO_EMITIDA")
        raise ValueError("REMESA_NO_EMITIDA_O_YA_CERRADA")
    
    # Seleccionar tipo de cumplimiento
    Select(driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_NOMTIPOCUMPLIDOREMESA")).select_by_visible_text("Cumplido Normal")
    
    # Copiar cantidad cargada a cantidad entregada
    cantidad_cargada = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CANTIDADCARGADA").get_attribute("value")
    campo_entregada = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CANTIDADENTREGADA")
    campo_entregada.clear()
    campo_entregada.send_keys(cantidad_cargada)
    
    # Obtener datos de cargue con validación
    fecha_cargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHACITAPACTADACARGUE").get_attribute("value")
    hora_cargue_raw = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORACITAPACTADACARGUE").get_attribute("value")
    
    # Validar hora de cargue
    es_valida_cargue, hora_cargue = validar_hora_formato(hora_cargue_raw)
    if not es_valida_cargue:
        logger.registrar_error(
            remesa_id,
            f"Hora de cargue inválida o vacía: '{hora_cargue_raw}', usando '{hora_cargue}'",
            codigo_error="HORA_CARGUE_INVALIDA"
        )
    
    hora_salida_cargue = calcular_hora_salida(hora_cargue, 60)
    
    # Obtener datos de descargue con validación
    fecha_descargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHACITAPACTADADESCARGUE").get_attribute("value")
    hora_descargue_raw = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORACITAPACTADADESCARGUEREMESA").get_attribute("value")
    
    # Validar hora de descargue
    es_valida_desc, hora_descargue_original = validar_hora_formato(hora_descargue_raw)
    if not es_valida_desc:
        logger.registrar_error(
            remesa_id,
            f"Hora de descargue inválida o vacía: '{hora_descargue_raw}', usando '{hora_descargue_original}'",
            codigo_error="HORA_DESCARGUE_INVALIDA"
        )
    
    # Validar que la fecha de descargue no sea futura
    if datetime.strptime(fecha_descargue, "%d/%m/%Y").date() > datetime.today().date():
        logger.registrar_error(remesa_id, "Fecha de descargue es futura", codigo_error="FECHA_FUTURA")
        raise ValueError("REMESA_FECHA_DESCARGUE_FUTURA")
    
    # Ajustar hora de llegada al descargue si es necesario
    hora_llegada_descargue = ajustar_hora_descargue(hora_descargue_original, hora_salida_cargue)
    hora_salida_descargue = calcular_hora_salida(hora_llegada_descargue, 60)
    fecha_salida_descargue = calcular_fecha_salida_descargue(fecha_descargue, hora_llegada_descargue)
    
    # Definir todos los campos a llenar
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
    
    # Llenar todos los campos
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
# FUNCIONES DE GUARDADO Y MANEJO DE ALERTAS
# ============================================================================
def intentar_guardado(driver):
    """
    Intenta guardar el formulario y captura alertas si existen.
    
    Returns:
        str or None: Texto de la alerta si existe, None si no hay alerta
    """
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
    """
    Reescribe los campos del formulario con valores actualizados.
    
    Args:
        driver: WebDriver de Selenium
        campos_actualizados: Lista de tuplas (sufijo_id, valor)
    """
    for id_suffix, value in campos_actualizados:
        campo_id = f"dnn_ctr396_CumplirRemesa_{id_suffix}"
        elementos = driver.find_elements(By.ID, campo_id)
        if elementos:
            elementos[0].clear()
            elementos[0].send_keys(value)


def manejar_error_cre230(driver, codigo, campos, actualizar_estado_callback):
    """
    Maneja el error CRE230 (formato de hora de salida descargue incorrecto).
    Intenta corregir el formato de la hora.
    
    Args:
        driver: WebDriver de Selenium
        codigo: Código de la remesa
        campos: Lista de campos originales
        actualizar_estado_callback: Función para actualizar estado en GUI
    
    Returns:
        bool: True si el reintento fue exitoso, False en caso contrario
    """
    try:
        actualizar_estado_callback(
            f"⏳ Error CRE230 en {codigo}. Corrigiendo formato de hora de salida descargue..."
        )
        
        logger.registrar_reintento(codigo, 1, "Corrigiendo formato CRE230 (hora salida descargue)", codigo_error=ERROR_CRE230)
        
        # Asegurar formato correcto de hora de salida
        hora_salida_desc = campos[11][1]  # HORASALIDADESCARGUECUMPLIDO
        es_valida, hora_corregida = validar_hora_formato(hora_salida_desc)
        
        if not es_valida:
            # Si la hora no es válida, usar una hora calculada
            hora_llegada_desc = campos[9][1]
            hora_corregida = calcular_hora_salida(hora_llegada_desc, 60)
        
        # Crear campos modificados
        campos_modificados = [
            (id_campo, hora_corregida if "HORASALIDADESCARGUECUMPLIDO" in id_campo else valor)
            for id_campo, valor in campos
        ]
        
        reescribir_campos(driver, campos_modificados)
        
        # Intentar guardar nuevamente
        texto_alerta_reintento = intentar_guardado(driver)
        
        if texto_alerta_reintento is None:
            WebDriverWait(driver, TIMEOUT_MEDIO).until(
                EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo"))
            )
            logger.registrar_exito(codigo, "Reintento exitoso tras corregir CRE230")
            registrar_log_remesa(codigo, "Reintento exitoso tras CRE230", campos_modificados)
            actualizar_estado_callback(f"✅ Remesa {codigo} completada tras corregir formato de hora.")
            return True
        else:
            logger.registrar_alerta(codigo, "CRE230_RETRY_FAILED", f"Reintento fallido: {texto_alerta_reintento}")
            registrar_log_remesa(codigo, f"Reintento fallido CRE230: {texto_alerta_reintento}", campos_modificados)
            actualizar_estado_callback(
                f"❌ Remesa {codigo} falló incluso tras reintento: {texto_alerta_reintento}"
            )
            return False
            
    except Exception as e:
        logger.registrar_excepcion(codigo, e, "Error en reintento CRE230")
        actualizar_estado_callback(f"❌ Error al reintentar remesa {codigo}: {e}")
        registrar_log_remesa(codigo, f"Fallo en reintento CRE230: {e}", campos)
        return False


def manejar_error_cre141(driver, codigo, campos, actualizar_estado_callback):
    """
    Maneja el error CRE141 (hora entrada cargue > hora salida cargue).
    Ajusta las horas para que haya al menos 1 minuto de diferencia.
    
    Args:
        driver: WebDriver de Selenium
        codigo: Código de la remesa
        campos: Lista de campos originales
        actualizar_estado_callback: Función para actualizar estado en GUI
    
    Returns:
        bool: True si el reintento fue exitoso, False en caso contrario
    """
    try:
        actualizar_estado_callback(
            f"⏳ Error CRE141 en {codigo}. Ajustando horas de cargue..."
        )
        
        logger.registrar_reintento(codigo, 1, "Ajustando horas por CRE141", codigo_error=ERROR_CRE141)
        
        # Ajustar hora de salida para que sea mayor que la de entrada
        hora_entrada_cargue = campos[4][1]  # HORAENTRADACARGUEREMESA
        nueva_hora_salida = calcular_hora_salida(hora_entrada_cargue, 1)  # +1 minuto
        
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
            logger.registrar_exito(codigo, "Reintento exitoso tras ajustar CRE141")
            registrar_log_remesa(codigo, "Reintento exitoso tras CRE141", campos_modificados)
            actualizar_estado_callback(f"✅ Remesa {codigo} completada tras ajustar horas de cargue.")
            return True
        else:
            logger.registrar_alerta(codigo, "CRE141_RETRY_FAILED", f"Reintento fallido: {texto_alerta_reintento}")
            registrar_log_remesa(codigo, f"Reintento fallido CRE141: {texto_alerta_reintento}", campos_modificados)
            actualizar_estado_callback(
                f"❌ Remesa {codigo} falló incluso tras reintento: {texto_alerta_reintento}"
            )
            return False
            
    except Exception as e:
        logger.registrar_excepcion(codigo, e, "Error en reintento CRE141")
        actualizar_estado_callback(f"❌ Error al reintentar CRE141 en remesa {codigo}: {e}")
        registrar_log_remesa(codigo, f"Fallo en reintento CRE141: {e}", campos)
        return False


def manejar_errores_antiguedad(driver, codigo, campos, actualizar_estado_callback):
    """
    Maneja errores CRE080, CRE100, CRE130 (antigüedad de fechas excesiva).
    Usa la fecha de expedición como base para todas las fechas.
    
    Args:
        driver: WebDriver de Selenium
        codigo: Código de la remesa
        campos: Lista de campos originales
        actualizar_estado_callback: Función para actualizar estado en GUI
    
    Returns:
        bool: True si el reintento fue exitoso, False en caso contrario
    """
    try:
        actualizar_estado_callback(
            f"⏳ Error de antigüedad en {codigo}. Usando fecha de expedición..."
        )
        
        logger.registrar_reintento(codigo, 1, "Ajustando por antigüedad de fechas", codigo_error="CRE_ANTIGUEDAD")
        
        # Obtener fecha de expedición
        fecha_expedicion_element = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHAEMISION")
        fecha_expedicion_str = fecha_expedicion_element.get_attribute("value")
        fecha_expedicion = datetime.strptime(fecha_expedicion_str, "%d/%m/%Y")
        
        # Calcular fechas basadas en expedición
        fecha_cargue = fecha_expedicion.strftime("%d/%m/%Y")
        fecha_descargue = (fecha_expedicion + timedelta(days=1)).strftime("%d/%m/%Y")
        fecha_salida_descargue = fecha_descargue
        
        # Mantener las horas originales
        hora_cargue = campos[3][1]
        hora_salida_cargue = campos[5][1]
        hora_llegada_descargue = campos[9][1]
        hora_salida_descargue = campos[11][1]
        
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
        
        reescribir_campos(driver, campos_modificados)
        
        texto_alerta_reintento = intentar_guardado(driver)
        
        if texto_alerta_reintento is None:
            WebDriverWait(driver, TIMEOUT_MEDIO).until(
                EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo"))
            )
            logger.registrar_exito(codigo, "Reintento exitoso tras corregir antigüedad")
            registrar_log_remesa(codigo, "Reintento exitoso tras corregir antigüedad", campos_modificados)
            actualizar_estado_callback(f"✅ Remesa {codigo} completada tras ajustar fechas.")
            return True
        else:
            logger.registrar_alerta(codigo, "ANTIGUEDAD_RETRY_FAILED", f"Reintento fallido: {texto_alerta_reintento}")
            registrar_log_remesa(codigo, f"Reintento fallido antigüedad: {texto_alerta_reintento}", campos_modificados)
            actualizar_estado_callback(
                f"❌ Remesa {codigo} falló incluso tras reintento: {texto_alerta_reintento}"
            )
            return False
            
    except Exception as e:
        logger.registrar_excepcion(codigo, e, "Error en reintento por antigüedad")
        actualizar_estado_callback(f"❌ Error al reintentar remesa {codigo}: {e}")
        registrar_log_remesa(codigo, f"Fallo en reintento por antigüedad: {e}", campos)
        return False


# [Continúa con las funciones existentes: manejar_error_cre308, manejar_error_cre309, manejar_error_cre270...]
# (Por brevedad, no las incluyo de nuevo, pero deben estar en el archivo completo)

def guardar_y_manejar_alertas(driver, codigo, actualizar_estado_callback, campos):
    """
    Guarda el formulario y maneja todas las alertas posibles con sus reintentos.
    Incluye manejo de nuevos errores identificados en el log.
    
    Args:
        driver: WebDriver de Selenium
        codigo: Código de la remesa
        actualizar_estado_callback: Función para actualizar estado en GUI
        campos: Lista de campos utilizados
    
    Returns:
        bool: True si se guardó exitosamente, False en caso contrario
    """
    texto_alerta = intentar_guardado(driver)
    
    # Sin alerta = éxito
    if texto_alerta is None:
        WebDriverWait(driver, TIMEOUT_MEDIO).until(
            EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo"))
        )
        logger.registrar_exito(codigo, "Remesa completada correctamente")
        actualizar_estado_callback(f"✅ Remesa {codigo} completada correctamente.")
        return True
    
    # Registrar alerta
    logger.registrar_alerta(codigo, texto_alerta.split()[0] if texto_alerta else "UNKNOWN", texto_alerta)
    registrar_log_remesa(codigo, texto_alerta, campos)
    
    # Manejo según tipo de error
    if ERROR_CRE064 in texto_alerta:
        logger.registrar_exito(codigo, "Remesa ya completada anteriormente", codigo_error=ERROR_CRE064)
        actualizar_estado_callback(f"✅ Remesa {codigo} ya había sido completada anteriormente.")
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


# [La función ejecutar_remesas permanece igual que en la versión anterior]
# (Incluirla completa en el archivo final)