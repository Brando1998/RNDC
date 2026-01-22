"""
Módulo para cambio masivo de sede en remesas RNDC.
Lee datos desde Excel y realiza cambios de generador/sede en el sistema.
VERSIÓN MEJORADA con búsqueda inteligente de sedes.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
from selenium.webdriver.common.keys import Keys
import time
import pandas as pd
import unicodedata
from _utils.logger import registrar_log_remesa
from _core.common import hacer_login


# ============================================================================
# CONSTANTES
# ============================================================================
URL_CAMBIO_SEDE = "https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CambioMasivoRemesas/mid/396/procesoid/4/default.aspx"
NIT_EMPRESA = "8600537463"
SEDE_DESTINO = "10"  # Código de BOGOTA
OBSERVACIONES = "error de digitacion"


# ============================================================================
# FUNCIONES DE NAVEGACIÓN
# ============================================================================
def navegar_a_formulario(driver):
    """Navega al formulario de cambio masivo de remesas."""
    driver.get(URL_CAMBIO_SEDE)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "dnn_ctr396_CambioMasivoRemesas_TIPOIDPROPIETARIO_ANT"))
    )


# ============================================================================
# FUNCIONES DE LECTURA DE EXCEL
# ============================================================================
def cargar_datos_excel(ruta_archivo):
    """
    Carga los datos del Excel y extrae la información necesaria.
    
    Returns:
        list: Lista de diccionarios con los datos de cada fila
    """
    try:
        df = pd.read_excel(ruta_archivo)
        
        # Validar columnas necesarias
        columnas_requeridas = ['NUMIDPROPIETARIO', 'REM_ORIG']
        for col in columnas_requeridas:
            if col not in df.columns:
                raise ValueError(f"Columna requerida '{col}' no encontrada en el Excel")
        
        # Extraer datos
        datos = []
        for idx, row in df.iterrows():
            nit_generador = str(int(row['NUMIDPROPIETARIO']))  # Convertir a string sin decimales
            sede_origen = str(row['REM_ORIG']).strip()
            
            datos.append({
                'nit_generador': nit_generador,
                'sede_origen': sede_origen,
                'fila': idx + 2  # +2 porque Excel empieza en 1 y tiene header
            })
        
        return datos
    
    except Exception as e:
        raise Exception(f"Error leyendo Excel: {str(e)}")


def normalizar_texto(texto):
    """
    Normaliza texto removiendo tildes, espacios extras y caracteres especiales.
    
    Args:
        texto: Texto a normalizar
    
    Returns:
        str: Texto normalizado
    """
    # Convertir a mayúsculas
    texto = texto.upper()
    
    # Remover tildes/acentos
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    
    # Remover caracteres especiales (guiones, puntos, etc.) y espacios extras
    texto = ' '.join(texto.replace('-', ' ').replace('.', ' ').split())
    
    return texto


def buscar_codigo_sede(driver, texto_sede):
    """
    Busca el código de una sede en el select con búsqueda inteligente.
    
    Estrategias de búsqueda (en orden):
    1. Coincidencia exacta (normalizada)
    2. Una cadena contiene a la otra
    3. Todas las palabras de búsqueda están presentes
    
    Args:
        driver: WebDriver de Selenium
        texto_sede: Texto a buscar (ej: "MEDELLIN ANTIOQUIA")
    
    Returns:
        str: Código de la sede encontrada o None
    """
    try:
        select_element = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_SEDEPROPIETARIO_ANT")
        options = select_element.find_elements(By.TAG_NAME, "option")
        
        # Normalizar texto de búsqueda
        texto_busqueda = normalizar_texto(texto_sede)
        palabras_busqueda = texto_busqueda.split()
        
        print(f"🔍 Buscando sede: '{texto_sede}' (normalizado: '{texto_busqueda}')")
        
        mejores_coincidencias = []
        
        for option in options:
            if option.get_attribute('value') == '0':  # Saltar opción por defecto
                continue
                
            texto_option = normalizar_texto(option.text)
            
            # Estrategia 1: Coincidencia exacta
            if texto_busqueda == texto_option:
                print(f"   ✅ Coincidencia EXACTA: '{option.text}'")
                return option.get_attribute('value')
            
            # Estrategia 2: Una opción contiene a la otra
            if texto_busqueda in texto_option:
                score = len(texto_busqueda) / len(texto_option)  # Mientras más parecidos, mejor
                mejores_coincidencias.append((option, score, "CONTIENE", option.text))
            elif texto_option in texto_busqueda:
                score = len(texto_option) / len(texto_busqueda)
                mejores_coincidencias.append((option, score, "CONTENIDO", option.text))
            
            # Estrategia 3: Todas las palabras de búsqueda están en la opción
            else:
                palabras_option = texto_option.split()
                palabras_encontradas = sum(1 for palabra in palabras_busqueda if palabra in palabras_option)
                
                if palabras_encontradas == len(palabras_busqueda):
                    score = palabras_encontradas / len(palabras_option)
                    mejores_coincidencias.append((option, score, "PALABRAS", option.text))
        
        # Si hay coincidencias, usar la mejor
        if mejores_coincidencias:
            mejores_coincidencias.sort(key=lambda x: x[1], reverse=True)
            mejor = mejores_coincidencias[0]
            print(f"   ✅ Coincidencia {mejor[2]} (score={mejor[1]:.2f}): '{mejor[3]}'")
            return mejor[0].get_attribute('value')
        
        # No se encontró nada
        print(f"   ❌ No se encontró coincidencia para '{texto_sede}'")
        print(f"   📋 Algunas sedes disponibles:")
        for option in options[:10]:  # Mostrar primeras 10 opciones
            if option.get_attribute('value') != '0':
                print(f"      • {option.text}")
        
        return None
    
    except Exception as e:
        print(f"❌ Error buscando sede '{texto_sede}': {str(e)}")
        return None


# ============================================================================
# FUNCIONES DE LLENADO DE FORMULARIO
# ============================================================================
def llenar_formulario_cambio_sede(driver, datos_fila):
    """
    Llena el formulario de cambio de sede con los datos de una fila.
    
    Args:
        driver: WebDriver de Selenium
        datos_fila: Diccionario con 'nit_generador' y 'sede_origen'
    
    Returns:
        bool: True si se llenó correctamente, False si hubo error
    """
    try:
        nit_generador = datos_fila['nit_generador']
        sede_origen = datos_fila['sede_origen']
        fila = datos_fila['fila']
        
        # 1. Seleccionar tipo de identificación ANTERIOR (NIT)
        select_element_ant = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_TIPOIDPROPIETARIO_ANT")
        select_tipo_ant = Select(select_element_ant)
        select_tipo_ant.select_by_value("N")
        # TAB para disparar evento
        select_element_ant.send_keys(Keys.TAB)
        time.sleep(0.5)
        
        # 2. Ingresar NIT del generador anterior
        input_nit_ant = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_NUMIDPROPIETARIO_ANT")
        input_nit_ant.clear()
        input_nit_ant.send_keys(nit_generador)
        input_nit_ant.send_keys(Keys.TAB)
        
        # Esperar a que se carguen las sedes
        time.sleep(3)
        
        # 3. Buscar y seleccionar la sede de origen
        codigo_sede_origen = buscar_codigo_sede(driver, sede_origen)
        
        if not codigo_sede_origen:
            print(f"⚠️ Fila {fila}: No se encontró la sede '{sede_origen}' para NIT {nit_generador}")
            registrar_log_remesa(
                f"Fila {fila}",
                f"Sede no encontrada: '{sede_origen}'",
                []
            )
            return False
        
        select_sede_element_ant = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_SEDEPROPIETARIO_ANT")
        select_sede_ant = Select(select_sede_element_ant)
        select_sede_ant.select_by_value(codigo_sede_origen)
        # TAB para disparar evento
        select_sede_element_ant.send_keys(Keys.TAB)
        
        # Esperar a que se carguen los datos y las fechas
        time.sleep(3)
        
        # 4. Verificar cuántas remesas se encontraron
        try:
            remesas_encontradas = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_REMESAS").get_attribute("value")
            
            if not remesas_encontradas or remesas_encontradas == "0":
                print(f"⚠️ Fila {fila}: No se encontraron remesas para NIT {nit_generador} sede '{sede_origen}'")
                return False
            
            print(f"✅ Fila {fila}: Encontradas {remesas_encontradas} remesas para NIT {nit_generador}")
        
        except Exception:
            pass  # Continuar si no se puede leer
        
        # 5. Seleccionar tipo de identificación NUEVO (NIT)
        select_element_nuevo = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_TIPOIDPROPIETARIO")
        select_tipo_nuevo = Select(select_element_nuevo)
        select_tipo_nuevo.select_by_value("N")
        # TAB para disparar evento
        select_element_nuevo.send_keys(Keys.TAB)
        time.sleep(0.5)
        
        # 6. Ingresar NIT de la empresa (hardcoded)
        input_nit_nuevo = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_NUMIDPROPIETARIO")
        input_nit_nuevo.clear()
        input_nit_nuevo.send_keys(NIT_EMPRESA)
        input_nit_nuevo.send_keys(Keys.TAB)
        
        # Esperar a que se carguen las sedes
        time.sleep(3)
        
        # 7. Seleccionar sede destino (BOGOTA)
        select_sede_element_nuevo = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_SEDEPROPIETARIOLISTA")
        select_sede_nuevo = Select(select_sede_element_nuevo)
        select_sede_nuevo.select_by_value(SEDE_DESTINO)
        # TAB para disparar evento
        select_sede_element_nuevo.send_keys(Keys.TAB)
        time.sleep(1)
        
        # 8. Ingresar observaciones
        input_obs = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_OBSERVACIONES")
        input_obs.clear()
        input_obs.send_keys(OBSERVACIONES)
        # TAB final
        input_obs.send_keys(Keys.TAB)
        time.sleep(0.5)
        
        return True
    
    except Exception as e:
        print(f"❌ Error llenando formulario fila {datos_fila.get('fila', '?')}: {str(e)}")
        registrar_log_remesa(
            f"Fila {datos_fila.get('fila', '?')}",
            f"Error: {str(e)}",
            []
        )
        return False


# ============================================================================
# FUNCIONES DE GUARDADO Y MANEJO DE ALERTAS
# ============================================================================
def guardar_y_capturar_radicado(driver, datos_fila, actualizar_estado_callback):
    """
    Guarda el formulario y captura el número de radicado.
    
    Returns:
        tuple: (exito, radicado)
    """
    fila = datos_fila['fila']
    nit_generador = datos_fila['nit_generador']
    
    try:
        # Click en el botón de guardar
        boton_guardar = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_btGuardar")
        driver.execute_script("arguments[0].click();", boton_guardar)
        
        # Esperar la alerta de confirmación
        try:
            WebDriverWait(driver, 10).until(EC.alert_is_present())
            alerta = driver.switch_to.alert
            texto_alerta = alerta.text
            alerta.accept()
            
            # Extraer número de radicado
            # Formato: "Ha sido creado el Cambio Masivo de Generador en Remesas con el radicado:1324357"
            if "radicado:" in texto_alerta:
                radicado = texto_alerta.split("radicado:")[-1].strip()
                print(f"✅ Fila {fila} - Radicado: {radicado}")
                registrar_log_remesa(
                    f"Fila {fila}",
                    f"Éxito - Radicado: {radicado}",
                    [("NIT", nit_generador)]
                )
                actualizar_estado_callback(f"✅ Fila {fila} - Radicado: {radicado}")
                return True, radicado
            else:
                # Alerta con otro mensaje
                print(f"⚠️ Fila {fila} - Alerta: {texto_alerta}")
                registrar_log_remesa(
                    f"Fila {fila}",
                    f"Alerta: {texto_alerta}",
                    [("NIT", nit_generador)]
                )
                actualizar_estado_callback(f"⚠️ Fila {fila} - {texto_alerta[:50]}")
                return False, None
        
        except TimeoutException:
            # No apareció alerta
            print(f"❌ Fila {fila} - Sin alerta de confirmación")
            registrar_log_remesa(
                f"Fila {fila}",
                "Error: Sin alerta de confirmación",
                [("NIT", nit_generador)]
            )
            actualizar_estado_callback(f"❌ Fila {fila} - Sin alerta de confirmación")
            return False, None
    
    except Exception as e:
        print(f"❌ Error guardando fila {fila}: {str(e)}")
        registrar_log_remesa(
            f"Fila {fila}",
            f"Error guardando: {str(e)}",
            [("NIT", nit_generador)]
        )
        actualizar_estado_callback(f"❌ Fila {fila} - Error: {str(e)[:50]}")
        return False, None


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================
def ejecutar_cambio_sede(driver, ruta_excel, actualizar_estado_callback, pausa_event, cancelar_func):
    """
    Función principal que ejecuta el proceso de cambio masivo de sede.
    
    Args:
        driver: WebDriver de Selenium
        ruta_excel: Ruta del archivo Excel con los datos
        actualizar_estado_callback: Función para actualizar estado en GUI
        pausa_event: Evento de threading para pausar
        cancelar_func: Función para verificar cancelación
    """
    try:
        # Cargar datos del Excel
        actualizar_estado_callback("📂 Cargando datos del Excel...")
        datos = cargar_datos_excel(ruta_excel)
        
        total = len(datos)
        actualizar_estado_callback(f"✅ Se cargaron {total} registros del Excel")
        
        # Login
        actualizar_estado_callback("🔐 Iniciando sesión...")
        hacer_login(driver)
        
        # Navegar al formulario
        actualizar_estado_callback("📋 Navegando al formulario...")
        navegar_a_formulario(driver)
        
        # Procesar cada fila
        exitosos = 0
        fallidos = 0
        radicados = []
        
        for idx, datos_fila in enumerate(datos, 1):
            # Verificar cancelación
            if cancelar_func():
                actualizar_estado_callback("⛔ Proceso cancelado por el usuario")
                break
            
            # Verificar pausa
            pausa_event.wait()
            
            fila = datos_fila['fila']
            nit = datos_fila['nit_generador']
            sede = datos_fila['sede_origen']
            
            actualizar_estado_callback(
                f"📝 Procesando {idx}/{total} - Fila {fila} | NIT: {nit} | Sede: {sede[:30]}"
            )
            
            # Llenar formulario
            if not llenar_formulario_cambio_sede(driver, datos_fila):
                actualizar_estado_callback(f"❌ Fila {fila} - Error llenando formulario")
                fallidos += 1
                navegar_a_formulario(driver)
                continue
            
            # Guardar y obtener radicado
            exito, radicado = guardar_y_capturar_radicado(driver, datos_fila, actualizar_estado_callback)
            
            if exito:
                exitosos += 1
                if radicado:
                    radicados.append({'fila': fila, 'nit': nit, 'radicado': radicado})
            else:
                fallidos += 1
            
            # Recargar formulario para siguiente registro
            navegar_a_formulario(driver)
            time.sleep(1)
        
        # Resumen final
        mensaje_final = f"✅ Proceso completado | Exitosos: {exitosos} | Fallidos: {fallidos}"
        actualizar_estado_callback(mensaje_final)
        print(f"\n{mensaje_final}")
        
        # Generar reporte de radicados
        if radicados:
            reporte = "\n=== RADICADOS GENERADOS ===\n"
            for r in radicados:
                reporte += f"Fila {r['fila']} | NIT: {r['nit']} | Radicado: {r['radicado']}\n"
            print(reporte)
        
    except Exception as e:
        error_msg = f"❌ Error general: {str(e)}"
        print(error_msg)
        actualizar_estado_callback(error_msg)
        registrar_log_remesa("SISTEMA", f"Error general: {str(e)}", [])
    
    finally:
        driver.quit()