from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchWindowException,
    InvalidSessionIdException
)
from datetime import datetime, timedelta
from tkinter import messagebox
import time
import os
from _utils.logger import registrar_log_remesa, obtener_logger, TipoProceso
from _core.common import hacer_login, navegar_a_remesas, TIMEOUT_CORTO, TIMEOUT_MEDIO

from _utils.esperas import (
    esperar_pagina_cargada,
    esperar_elemento_interactivo,
    esperar_valor_campo_cargado,
    esperar_ajax_completo,
    esperar_campo_editable
)


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

TIEMPO_REINTENTO_SERVIDOR = 60  # 1 minuto
MAX_REINTENTOS_SERVIDOR = 60  # 1 hora máximo

logger = obtener_logger(TipoProceso.REMESA)


# ============================================================================
# RECUPERACIÓN AUTOMÁTICA
# ============================================================================
def es_error_servidor(excepcion):
    """Detecta si es un error recuperable del servidor."""
    errores_recuperables = [
        TimeoutException,
        WebDriverException,
        NoSuchWindowException,
        InvalidSessionIdException
    ]
    
    if type(excepcion) in errores_recuperables:
        return True
    
    mensaje = str(excepcion).lower()
    patrones = ["timeout", "connection", "no such window", "invalid session", "chrome not reachable"]
    return any(p in mensaje for p in patrones)


def verificar_servidor_disponible(crear_driver_func):
    """Verifica si el servidor RNDC está disponible."""
    driver = None
    try:
        driver = crear_driver_func()
        driver.get("https://rndc.mintransporte.gov.co")
        esperar_pagina_cargada(driver, timeout=10)
        
        if "rndc" in driver.current_url.lower():
            return True, driver
        return False, driver
    except:
        if driver:
            try:
                driver.quit()
            except:
                pass
        return False, None


def esperar_recuperacion_servidor(crear_driver_func, actualizar_estado_callback):
    """Espera a que el servidor RNDC se recupere."""
    logger.registrar_error("SERVIDOR", "Servidor RNDC caído. Iniciando espera de recuperación", codigo_error="SERVIDOR_CAIDO")
    actualizar_estado_callback("Servidor RNDC caído. Esperando recuperación...")
    
    for intento in range(1, MAX_REINTENTOS_SERVIDOR + 1):
        minutos = intento * TIEMPO_REINTENTO_SERVIDOR // 60
        actualizar_estado_callback(
            f"Reintento {intento}/{MAX_REINTENTOS_SERVIDOR} - Esperando {TIEMPO_REINTENTO_SERVIDOR}s (Total: {minutos} min)"
        )
        
        time.sleep(TIEMPO_REINTENTO_SERVIDOR)
        
        disponible, driver = verificar_servidor_disponible(crear_driver_func)
        if disponible:
            logger.registrar_exito("SERVIDOR", f"Servidor recuperado tras {intento} intentos ({minutos} min)")
            actualizar_estado_callback("Servidor recuperado. Reanudando proceso...")
            return driver
    
    logger.registrar_error("SERVIDOR", "Servidor no recuperado tras 1 hora", codigo_error="SERVIDOR_NO_RECUPERADO")
    actualizar_estado_callback("Servidor no se recuperó tras 1 hora. Proceso detenido.")
    return None


class CheckpointManager:
    """Gestiona el progreso para reanudar después de caídas."""
    
    def __init__(self, archivo="checkpoint_remesas.txt"):
        self.archivo = os.path.join("logs", archivo)
        os.makedirs("logs", exist_ok=True)
        self.procesados = set()
        self.cargar()
    
    def cargar(self):
        try:
            with open(self.archivo, 'r') as f:
                self.procesados = set(line.strip() for line in f if line.strip())
        except FileNotFoundError:
            pass
    
    def marcar_procesado(self, codigo):
        self.procesados.add(codigo)
        with open(self.archivo, 'a') as f:
            f.write(f"{codigo}\n")
    
    def esta_procesado(self, codigo):
        return codigo in self.procesados
    
    def obtener_pendientes(self, codigos):
        return [c for c in codigos if not self.esta_procesado(c)]
    
    def limpiar(self):
        try:
            os.remove(self.archivo)
            self.procesados.clear()
        except FileNotFoundError:
            pass


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


def validar_fecha_formato(fecha_str):
    """Valida que una fecha no esté vacía y tenga formato correcto."""
    if not fecha_str or fecha_str.strip() == "":
        return False
    try:
        datetime.strptime(fecha_str.strip(), "%d/%m/%Y")
        return True
    except ValueError:
        return False


# ============================================================================
# CÁLCULOS
# ============================================================================
def calcular_hora_salida(hora_entrada_str, minutos_adicionales=60):
    """
    Calcula hora de salida evitando cruzar medianoche.
    Si la hora resultante cruza las 00:00, usa 23:59 en su lugar.
    """
    es_valida, hora_corregida = validar_hora_formato(hora_entrada_str)
    if not es_valida:
        logger.registrar_error("SISTEMA", f"Hora inválida: '{hora_entrada_str}'", codigo_error="HORA_INVALIDA")
    
    hora_entrada = datetime.strptime(hora_corregida, "%H:%M")
    hora_salida = hora_entrada + timedelta(minutes=minutos_adicionales)
    
    # Si cruza medianoche (hora >= 00:00 del día siguiente), usar 23:59
    if hora_salida.hour < hora_entrada.hour or hora_salida.day > hora_entrada.day:
        return "23:59"
    
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
    """
    Calcula fecha de salida considerando que la hora nunca cruza medianoche.
    """
    es_valida, hora_corregida = validar_hora_formato(hora_llegada_str)
    
    # La hora de salida será calculada con calcular_hora_salida que ya evita cruzar medianoche
    hora_salida = calcular_hora_salida(hora_corregida, 60)
    
    # Si la hora de salida es menor que la de llegada, significa que cruzó medianoche
    # pero calcular_hora_salida la ajustó a 23:59, entonces NO incrementamos el día
    hora_llegada_dt = datetime.strptime(hora_corregida, "%H:%M")
    hora_salida_dt = datetime.strptime(hora_salida, "%H:%M")
    
    fecha_descargue_dt = datetime.strptime(fecha_descargue_str, "%d/%m/%Y")
    
    # Solo incrementar día si realmente hay un cruce (pero esto no debería pasar con 23:59 como límite)
    if hora_salida == "23:59" and hora_llegada_dt.hour == 23:
        # Caso especial: llegada tardía, salida al límite del día
        return fecha_descargue_dt.strftime("%d/%m/%Y")
    
    return fecha_descargue_dt.strftime("%d/%m/%Y")


# ============================================================================
# INTERACCIÓN CON ELEMENTOS (CON ESPERAS)
# ============================================================================
def llenar_campo_seguro(driver, campo_id, valor, timeout=5):
    """Llena un campo esperando a que sea interactuable."""
    try:
        elemento = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, campo_id))
        )
        elemento.clear()
        esperar_ajax_completo(driver, timeout=1)
        elemento.send_keys(valor)
        return True
    except Exception as e:
        logger.registrar_error("SISTEMA", f"Error llenando campo {campo_id}: {e}", codigo_error="CAMPO_NO_INTERACTUABLE")
        return False


# ============================================================================
# LLENADO DE FORMULARIO
# ============================================================================
def esperar_formulario_cargado(driver, remesa_id, max_intentos=3):
    """
    Espera a que el formulario esté completamente cargado con todos los campos visibles.
    
    Returns:
        bool: True si el formulario está listo, False si no se pudo cargar
    """
    for intento in range(max_intentos):
        try:
            # Verificar que los campos críticos existan y estén visibles
            campos_criticos = [
                "dnn_ctr396_CumplirRemesa_FECHALLEGADADESCARGUE",
                "dnn_ctr396_CumplirRemesa_HORALLEGADADESCARGUECUMPLIDO",
                "dnn_ctr396_CumplirRemesa_FECHASALIDADESCARGUE",
                "dnn_ctr396_CumplirRemesa_HORASALIDADESCARGUECUMPLIDO"
            ]
            
            todos_visibles = True
            for campo_id in campos_criticos:
                elemento = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.ID, campo_id))
                )
                if not elemento.is_displayed() or not elemento.is_enabled():
                    todos_visibles = False
                    break
            
            if todos_visibles:
                return True
            
            # Si no están todos visibles, recargar
            logger.registrar_error(remesa_id, f"Formulario incompleto, intento {intento + 1}/{max_intentos}", codigo_error="FORMULARIO_INCOMPLETO")
            navegar_a_remesas(driver)
            
            # Reingresar código
            campo_remesa = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA")
            campo_remesa.clear()
            campo_remesa.send_keys(remesa_id)
            campo_remesa.send_keys("\t")
            time.sleep(2)
            
        except Exception as e:
            logger.registrar_error(remesa_id, f"Error verificando formulario: {e}", codigo_error="ERROR_VERIFICACION")
            if intento < max_intentos - 1:
                navegar_a_remesas(driver)
                time.sleep(1)
            continue
    
    return False


def llenar_formulario_remesa(driver, remesa_id):
    campo_remesa = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA")
    campo_remesa.clear()
    campo_remesa.send_keys(remesa_id)
    campo_remesa.send_keys("\t")
    esperar_ajax_completo(driver, timeout=5)
    
    mensaje_sistema = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_MENSAJE").get_attribute("value")
    if ERROR_REMESA_NO_EMITIDA in mensaje_sistema:
        logger.registrar_error(remesa_id, "Remesa no emitida o ya cerrada", codigo_error="NO_EMITIDA")
        raise ValueError("REMESA_NO_EMITIDA_O_YA_CERRADA")
    
    # VERIFICAR QUE EL FORMULARIO ESTÉ COMPLETAMENTE CARGADO
    if not esperar_formulario_cargado(driver, remesa_id):
        logger.registrar_error(remesa_id, "Formulario no cargó correctamente tras reintentos", codigo_error="FORMULARIO_NO_CARGO")
        raise ValueError("FORMULARIO_NO_CARGO")
    
    Select(driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_NOMTIPOCUMPLIDOREMESA")).select_by_visible_text("Cumplido Normal")
    
    cantidad_cargada = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CANTIDADCARGADA").get_attribute("value")
    campo_entregada = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CANTIDADENTREGADA")
    campo_entregada.clear()
    campo_entregada.send_keys(cantidad_cargada)
    
    # VALIDAR FECHAS ANTES DE USAR
    fecha_cargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHACITAPACTADACARGUE").get_attribute("value")
    fecha_descargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHACITAPACTADADESCARGUE").get_attribute("value")
    
    # Si fecha_cargue está vacía, usar fecha de expedición
    if not validar_fecha_formato(fecha_cargue):
        logger.registrar_error(remesa_id, f"Fecha cargue inválida: '{fecha_cargue}', intentando usar fecha expedición", codigo_error="FECHA_CARGUE_INVALIDA")
        try:
            fecha_expedicion_element = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHAEMISION")
            fecha_cargue = fecha_expedicion_element.get_attribute("value")
            if not validar_fecha_formato(fecha_cargue):
                # Si tampoco tiene fecha de expedición, usar fecha actual
                logger.registrar_error(remesa_id, "Fecha expedición también inválida, usando fecha actual", codigo_error="USANDO_FECHA_ACTUAL")
                fecha_cargue = datetime.today().strftime("%d/%m/%Y")
        except Exception:
            # Último recurso: fecha actual
            fecha_cargue = datetime.today().strftime("%d/%m/%Y")
            logger.registrar_error(remesa_id, "Usando fecha actual como último recurso", codigo_error="FECHA_ACTUAL_FALLBACK")
    
    if not validar_fecha_formato(fecha_descargue):
        logger.registrar_error(remesa_id, f"Fecha descargue inválida: '{fecha_descargue}'", codigo_error="FECHA_DESCARGUE_INVALIDA")
        # Usar fecha cargue + 1 día como fallback
        fecha_cargue_dt = datetime.strptime(fecha_cargue, "%d/%m/%Y")
        fecha_descargue = (fecha_cargue_dt + timedelta(days=1)).strftime("%d/%m/%Y")
        logger.registrar_error(remesa_id, f"Usando fecha cargue + 1 día: {fecha_descargue}", codigo_error="FECHA_DESCARGUE_CALCULADA")
    
    # Validar que fecha descargue no sea futura
    if datetime.strptime(fecha_descargue, "%d/%m/%Y").date() > datetime.today().date():
        logger.registrar_error(remesa_id, "Fecha de descargue es futura", codigo_error="FECHA_FUTURA")
        raise ValueError("REMESA_FECHA_DESCARGUE_FUTURA")
    
    # Obtener y validar horas
    hora_cargue_raw = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORACITAPACTADACARGUE").get_attribute("value")
    es_valida_cargue, hora_cargue = validar_hora_formato(hora_cargue_raw)
    
    if not es_valida_cargue:
        logger.registrar_error(remesa_id, f"Hora cargue inválida: '{hora_cargue_raw}'", codigo_error="HORA_CARGUE_INVALIDA")
    
    hora_salida_cargue = calcular_hora_salida(hora_cargue, 60)
    
    hora_descargue_raw = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORACITAPACTADADESCARGUEREMESA").get_attribute("value")
    es_valida_desc, hora_descargue_original = validar_hora_formato(hora_descargue_raw)
    
    if not es_valida_desc:
        logger.registrar_error(remesa_id, f"Hora descargue inválida: '{hora_descargue_raw}'", codigo_error="HORA_DESCARGUE_INVALIDA")
    
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
    
    # Llenar con esperas
    for sufijo_id, valor in campos_remesa:
        campo_id = f"dnn_ctr396_CumplirRemesa_{sufijo_id}"
        if not llenar_campo_seguro(driver, campo_id, valor):
            logger.registrar_error(remesa_id, f"No se pudo llenar campo '{campo_id}'", codigo_error="CAMPO_NO_LLENADO")
    
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
        llenar_campo_seguro(driver, campo_id, value)


def manejar_error_cre230(driver, codigo, campos, actualizar_estado_callback):
    """CRE230: Omitir campo de hora salida descargue problemático."""
    try:
        actualizar_estado_callback(f"⏳ Error CRE230 en {codigo}. Omitiendo hora salida...")
        logger.registrar_reintento(codigo, 1, "Omitiendo hora salida CRE230", codigo_error=ERROR_CRE230)
        
        # Dejar el campo de hora salida VACÍO
        campos_modificados = [
            (id_campo, "" if "HORASALIDADESCARGUECUMPLIDO" in id_campo else valor)
            for id_campo, valor in campos
        ]
        
        reescribir_campos(driver, campos_modificados)
        texto_alerta_reintento = intentar_guardado(driver)
        
        if texto_alerta_reintento is None:
            WebDriverWait(driver, TIMEOUT_MEDIO).until(EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo")))
            logger.registrar_exito(codigo, "Reintento exitoso omitiendo CRE230")
            actualizar_estado_callback(f"✅ Remesa {codigo} completada.")
            return True
        else:
            logger.registrar_alerta(codigo, "CRE230_RETRY_FAILED", f"Falló: {texto_alerta_reintento}")
            actualizar_estado_callback(f"❌ Remesa {codigo} - CRE230 no resoluble")
            return False
    except Exception as e:
        logger.registrar_excepcion(codigo, e, "Error en reintento CRE230")
        return False


def manejar_error_cre141(driver, codigo, campos, actualizar_estado_callback):
    """CRE141: Ajustar con tiempo mínimo de 30 minutos."""
    try:
        actualizar_estado_callback(f"⏳ Error CRE141 en {codigo}. Ajustando +30 min...")
        logger.registrar_reintento(codigo, 1, "Ajustando CRE141 (+30 min)", codigo_error=ERROR_CRE141)
        
        hora_entrada_cargue = campos[4][1]
        nueva_hora_salida = calcular_hora_salida(hora_entrada_cargue, 30)  # 30 minutos mínimo
        
        campos_modificados = [
            (id_campo, nueva_hora_salida if "HORASALIDACARGUEREMESA" in id_campo else valor)
            for id_campo, valor in campos
        ]
        reescribir_campos(driver, campos_modificados)
        texto_alerta_reintento = intentar_guardado(driver)
        
        if texto_alerta_reintento is None:
            WebDriverWait(driver, TIMEOUT_MEDIO).until(EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo")))
            logger.registrar_exito(codigo, "Reintento exitoso CRE141")
            actualizar_estado_callback(f"✅ Remesa {codigo} completada.")
            return True
        else:
            logger.registrar_alerta(codigo, "CRE141_RETRY_FAILED", f"Falló: {texto_alerta_reintento}")
            return False
    except Exception as e:
        logger.registrar_excepcion(codigo, e, "Error en reintento CRE141")
        return False


def manejar_errores_antiguedad(driver, codigo, campos, actualizar_estado_callback):
    try:
        actualizar_estado_callback(f"⏳ Antigüedad en {codigo}. Usando fecha expedición...")
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
            WebDriverWait(driver, TIMEOUT_MEDIO).until(EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo")))
            logger.registrar_exito(codigo, "Reintento exitoso antigüedad")
            actualizar_estado_callback(f"✅ Remesa {codigo} completada.")
            return True
        else:
            logger.registrar_alerta(codigo, "ANTIGUEDAD_RETRY_FAILED", f"Falló: {texto_alerta_reintento}")
            return False
    except Exception as e:
        logger.registrar_excepcion(codigo, e, "Error antigüedad")
        return False


def manejar_error_cre308(driver, codigo, campos, actualizar_estado_callback):
    try:
        actualizar_estado_callback(f"⏳ CRE308 en {codigo}. +5 días...")
        logger.registrar_reintento(codigo, 1, "Ajustando CRE308", codigo_error=ERROR_CRE308)
        
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
            logger.registrar_alerta(codigo, "CRE308_RETRY_FAILED", f"Falló: {texto_alerta_reintento}")
            return False
    except Exception as e:
        logger.registrar_excepcion(codigo, e, "Error CRE308")
        return False


def manejar_error_cre309(driver, codigo, campos, actualizar_estado_callback):
    try:
        actualizar_estado_callback(f"⏳ CRE309 en {codigo}. +3 días +3 horas...")
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
            logger.registrar_alerta(codigo, "CRE309_RETRY_FAILED", f"Falló: {texto_alerta_reintento}")
            return False
    except Exception as e:
        logger.registrar_excepcion(codigo, e, "Error CRE309")
        return False


def manejar_error_cre270(driver, codigo, campos, actualizar_estado_callback):
    try:
        actualizar_estado_callback(f"⏳ CRE270 en {codigo}. Fecha expedición...")
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
            logger.registrar_alerta(codigo, "CRE270_RETRY_FAILED", f"Falló: {texto_alerta_reintento}")
            return False
    except Exception as e:
        logger.registrar_excepcion(codigo, e, "Error CRE270")
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
# FUNCIÓN PRINCIPAL CON RECUPERACIÓN
# ============================================================================
def ejecutar_remesas(driver, codigos, actualizar_estado_callback, pausa_event, cancelar_func):
    """
    Función principal con sistema de recuperación automática.
    """
    # Importar crear_driver desde navegador
    from _core.navegador import crear_driver
    
    # Inicializar checkpoint
    checkpoint = CheckpointManager()
    codigos_pendientes = checkpoint.obtener_pendientes(codigos)
    
    if len(codigos_pendientes) < len(codigos):
        procesados = len(codigos) - len(codigos_pendientes)
        actualizar_estado_callback(f"Reanudando proceso. {procesados} remesas ya procesadas.")
    
    def procesar_remesa_seguro(driver_actual, codigo):
        """Wrapper que maneja errores del servidor."""
        max_intentos = 3
        
        for intento in range(max_intentos):
            try:
                navegar_a_remesas(driver_actual)
                campos = llenar_formulario_remesa(driver_actual, codigo)
                exito = guardar_y_manejar_alertas(driver_actual, codigo, actualizar_estado_callback, campos)
                
                if exito:
                    checkpoint.marcar_procesado(codigo)
                
                return True, driver_actual
                
            except Exception as e:
                # Verificar si es error del servidor
                if es_error_servidor(e):
                    logger.registrar_error("SISTEMA", f"Error servidor en {codigo}: {str(e)[:200]}", codigo_error="ERROR_SERVIDOR")
                    
                    # Intentar recuperación
                    driver_recuperado = esperar_recuperacion_servidor(crear_driver, actualizar_estado_callback)
                    
                    if driver_recuperado:
                        # Cerrar driver viejo si existe
                        try:
                            if driver_actual:
                                driver_actual.quit()
                        except:
                            pass
                        
                        driver_actual = driver_recuperado
                        
                        # Reiniciar sesión
                        try:
                            hacer_login(driver_actual)
                            navegar_a_remesas(driver_actual)
                        except Exception as login_err:
                            logger.registrar_excepcion("SISTEMA", login_err, "Error en login tras recuperación")
                            continue
                        
                        # Reintentar con servidor recuperado
                        continue
                    else:
                        # No se recuperó el servidor
                        return False, None
                
                # Error no recuperable
                if "REMESA_NO_EMITIDA" in str(e):
                    actualizar_estado_callback(f"Remesa {codigo} no disponible.")
                    checkpoint.marcar_procesado(codigo)  # Marcar como procesada para no reintentarla
                    return True, driver_actual
                elif "FORMULARIO_NO_CARGO" in str(e):
                    actualizar_estado_callback(f"Formulario de {codigo} no cargó. Saltando...")
                    return True, driver_actual
                else:
                    logger.registrar_excepcion(codigo, e, "Error procesando remesa")
                    actualizar_estado_callback(f"Error en remesa {codigo}: {e}")
                    return True, driver_actual
        
        return True, driver_actual
    
    try:
        hacer_login(driver)
        navegar_a_remesas(driver)
        
        for codigo in codigos_pendientes:
            if cancelar_func():
                driver.quit()
                actualizar_estado_callback("Proceso cancelado por el usuario.")
                break
            
            actualizar_estado_callback(f"Procesando remesa {codigo}...")
            pausa_event.wait()
            
            # Procesar con recuperación automática
            exito, driver = procesar_remesa_seguro(driver, codigo)
            
            if not exito or driver is None:
                # Servidor no se recuperó
                actualizar_estado_callback("Proceso detenido. Servidor no disponible.")
                break
        
        else:
            # Completado exitosamente
            actualizar_estado_callback("Todas las remesas completadas.")
            checkpoint.limpiar()  # Limpiar checkpoint al terminar
        
        reporte = logger.generar_reporte()
        print(reporte)
        
    except Exception as e:
        actualizar_estado_callback(f"Error general: {e}")
        logger.registrar_excepcion("SISTEMA", e, "Error general en ejecución")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
        
        if not cancelar_func():
            messagebox.showinfo("Proceso completado", f"El proceso ha finalizado.\n\n{logger.generar_reporte()}")