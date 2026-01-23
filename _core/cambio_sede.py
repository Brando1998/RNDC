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
from datetime import datetime


# ============================================================================
# CONSTANTES
# ============================================================================
URL_CAMBIO_SEDE = "https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CambioMasivoRemesas/mid/396/procesoid/4/default.aspx"
NIT_EMPRESA = "8600537463"
SEDE_DESTINO = "+020"  # Código de BOGOTA específico solicitado
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
        columnas_requeridas = ['NUMIDPROPIETARIO', 'REM_ORIG', 'CONSECUTIVOREMESA']
        for col in columnas_requeridas:
            if col not in df.columns:
                raise ValueError(f"Columna requerida '{col}' no encontrada en el Excel")
        
        # Extraer datos conservando toda la fila original
        datos = []
        for idx, row in df.iterrows():
            # Obtener diccionario con todos los datos originales
            fila_data = row.to_dict()
            
            # Procesar datos específicos para el bot
            nit_generador = str(int(row['NUMIDPROPIETARIO']))  # Convertir a string sin decimales
            sede_origen = str(row['REM_ORIG']).strip()
            consecutivo = str(row['CONSECUTIVOREMESA']).strip()
            # Si consecutivo tiene decimales (ej 123.0), quitarlo
            if consecutivo.endswith('.0'):
                consecutivo = consecutivo[:-2]
            
            # Agregar datos procesados al diccionario
            fila_data['nit_generador'] = nit_generador
            fila_data['sede_origen'] = sede_origen
            fila_data['consecutivo'] = consecutivo
            fila_data['fila'] = idx + 2  # +2 porque Excel empieza en 1 y tiene header
            
            datos.append(fila_data)
        
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


def buscar_codigo_sede(driver, texto_sede, element_id, usar_fallback=True):
    """
    Busca el código de una sede en el select con búsqueda inteligente.
    
    Estrategias de búsqueda (en orden):
    1. Coincidencia exacta (normalizada)
    2. Una cadena contiene a la otra
    3. Todas las palabras de búsqueda están presentes
    4. FALLBACK: Si no encuentra nada y usar_fallback=True, busca BOGOTA
    
    Args:
        driver: WebDriver de Selenium
        texto_sede: Texto a buscar (ej: "MEDELLIN ANTIOQUIA")
        element_id: ID del elemento Select en el HTML
        usar_fallback: Si True, busca BOGOTA cuando no encuentra la sede
    
    Returns:
        tuple: (codigo_sede, es_fallback)
               - codigo_sede: Código de la sede encontrada o None
               - es_fallback: True si se usó BOGOTA como fallback
    """
    try:
        select_element = driver.find_element(By.ID, element_id)
        options = select_element.find_elements(By.TAG_NAME, "option")
        
        # Normalizar texto de búsqueda
        texto_busqueda = normalizar_texto(texto_sede)
        palabras_busqueda = texto_busqueda.split()
        
        print(f"🔍 Buscando sede: '{texto_sede}' (normalizado: '{texto_busqueda}') en {element_id}")
        
        mejores_coincidencias = []
        
        for option in options:
            if option.get_attribute('value') == '0' or not option.get_attribute('value'):  # Saltar opción por defecto
                continue
                
            texto_option = normalizar_texto(option.text)
            
            # Estrategia 1: Coincidencia exacta
            if texto_busqueda == texto_option:
                print(f"   ✅ Coincidencia EXACTA: '{option.text}'")
                return option.get_attribute('value'), False
            
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
            return mejor[0].get_attribute('value'), False
        
        # No se encontró nada - INTENTAR FALLBACK A BOGOTA
        if usar_fallback:
            print(f"   ⚠️  No se encontró '{texto_sede}', buscando BOGOTA como fallback...")
            
            # Buscar BOGOTA en las opciones
            for option in options:
                if option.get_attribute('value') == '0' or not option.get_attribute('value'):
                    continue
                
                texto_option = normalizar_texto(option.text)
                
                # Buscar opciones que contengan BOGOTA
                if 'BOGOTA' in texto_option:
                    print(f"   🔄 Usando FALLBACK: '{option.text}'")
                    return option.get_attribute('value'), True
            
            print(f"   ❌ No se encontró ni '{texto_sede}' ni BOGOTA como fallback")
        else:
            print(f"   ❌ No se encontró coincidencia para '{texto_sede}'")
        
        print(f"   📋 Algunas sedes disponibles:")
        for option in options[:10]:  # Mostrar primeras 10 opciones
            if option.get_attribute('value') and option.get_attribute('value') != '0':
                print(f"      • {option.text}")
        
        return None, False
    
    except Exception as e:
        print(f"❌ Error buscando sede '{texto_sede}': {str(e)}")
        return None, False


# ============================================================================
# FUNCIONES DE LLENADO DE FORMULARIO
# ============================================================================
def llenar_formulario_cambio_sede(driver, datos_fila):
    """
    Llena el formulario de cambio de sede con los datos de una fila.
    
    Args:
        driver: WebDriver de Selenium
        datos_fila: Diccionario con 'nit_generador', 'sede_origen', y 'consecutivo'
    
    Returns:
        bool: True si se llenó correctamente, False si hubo error
    """
    try:
        nit_generador = datos_fila['nit_generador']
        sede_origen = datos_fila['sede_origen']
        consecutivo = datos_fila['consecutivo']
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
        
        # 3. Buscar y seleccionar la sede de origen (con fallback a BOGOTA)
        id_sede_origen = "dnn_ctr396_CambioMasivoRemesas_SEDEPROPIETARIO_ANT"
        codigo_sede_origen, es_fallback = buscar_codigo_sede(driver, sede_origen, id_sede_origen, usar_fallback=True)
        
        if not codigo_sede_origen:
            print(f"❌ Fila {fila}: No se encontró la sede '{sede_origen}' ni BOGOTA para NIT {nit_generador}")
            registrar_log_remesa(
                f"Fila {fila}",
                f"Sede no encontrada: '{sede_origen}' (sin fallback disponible)",
                []
            )
            return False
        
        if es_fallback:
            print(f"🔄 Fila {fila}: Usando BOGOTA en lugar de '{sede_origen}' para NIT {nit_generador}")
            registrar_log_remesa(
                f"Fila {fila}",
                f"Usando BOGOTA como fallback para '{sede_origen}'",
                []
            )
        
        select_sede_element_ant = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_SEDEPROPIETARIO_ANT")
        select_sede_ant = Select(select_sede_element_ant)
        select_sede_ant.select_by_value(codigo_sede_origen)
        # TAB para disparar evento
        select_sede_element_ant.send_keys(Keys.TAB)
        
        # Esperar a que se carguen los datos
        time.sleep(2)
        
        # 4. Ingresar CONSECUTIVO DE REMESA (Columna K)
        # Este paso faltaba y es crucial según las instrucciones
        try:
            input_consecutivo = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_CONSECUTIVOREMESA")
            input_consecutivo.clear()
            input_consecutivo.send_keys(consecutivo)
            input_consecutivo.send_keys(Keys.TAB)
            print(f"   📝 Ingresando consecutivo: {consecutivo}")
        except Exception as e:
            print(f"   ⚠️ No se pudo ingresar el consecutivo: {str(e)}")

        # Esperar un momento después del consecutivo
        time.sleep(2)
        
        # 5. Verificar cuántas remesas se encontraron
        try:
            remesas_encontradas = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_REMESAS").get_attribute("value")
            
            if not remesas_encontradas or remesas_encontradas == "0":
                print(f"⚠️ Fila {fila}: No se encontraron remesas para NIT {nit_generador} sede '{sede_origen}' consecutivo {consecutivo}")
                return False
            
            print(f"✅ Fila {fila}: Encontradas {remesas_encontradas} remesas para NIT {nit_generador}")
        
        except Exception:
            pass  # Continuar si no se puede leer
        
        # 6. Seleccionar tipo de identificación NUEVO (NIT)
        select_element_nuevo = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_TIPOIDPROPIETARIO")
        select_tipo_nuevo = Select(select_element_nuevo)
        select_tipo_nuevo.select_by_value("N")
        # TAB para disparar evento
        select_element_nuevo.send_keys(Keys.TAB)
        time.sleep(0.5)
        
        # 7. Ingresar NIT de la empresa (hardcoded)
        input_nit_nuevo = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_NUMIDPROPIETARIO")
        input_nit_nuevo.clear()
        input_nit_nuevo.send_keys(NIT_EMPRESA)
        input_nit_nuevo.send_keys(Keys.TAB)
        
        # Esperar a que se carguen las sedes
        time.sleep(3)
        
        # 8. Seleccionar sede destino (BOGOTA)
        id_sede_destino = "dnn_ctr396_CambioMasivoRemesas_SEDEPROPIETARIOLISTA"
        select_sede_element_nuevo = driver.find_element(By.ID, id_sede_destino)
        select_sede_nuevo = Select(select_sede_element_nuevo)
        select_sede_nuevo.select_by_value(SEDE_DESTINO)
        # TAB para disparar evento
        select_sede_element_nuevo.send_keys(Keys.TAB)
        time.sleep(1)
        
        # 9. Ingresar observaciones
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
        tuple: (exito, radicado, mensaje)
    """
    fila = datos_fila['fila']
    nit_generador = datos_fila['nit_generador']
    
    try:
        # Click en el botón de guardar
        boton_guardar = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_btGuardar")
        driver.execute_script("arguments[0].click();", boton_guardar)
        
        # Esperar la alerta de confirmación
        try:
            WebDriverWait(driver, 30).until(EC.alert_is_present())
            alerta = driver.switch_to.alert
            texto_alerta = alerta.text
            alerta.accept()
            time.sleep(2)  # Esperar un momento a que se cierre la alerta
            
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
                return True, radicado, texto_alerta
            else:
                # Alerta con otro mensaje
                print(f"⚠️ Fila {fila} - Alerta: {texto_alerta}")
                registrar_log_remesa(
                    f"Fila {fila}",
                    f"Alerta: {texto_alerta}",
                    [("NIT", nit_generador)]
                )
                actualizar_estado_callback(f"⚠️ Fila {fila} - {texto_alerta[:50]}")
                return False, None, texto_alerta
        
        except TimeoutException:
            # No apareció alerta
            print(f"❌ Fila {fila} - Sin alerta de confirmación")
            registrar_log_remesa(
                f"Fila {fila}",
                "Error: Sin alerta de confirmación",
                [("NIT", nit_generador)]
            )
            actualizar_estado_callback(f"❌ Fila {fila} - Sin alerta de confirmación")
            return False, None, "No apareció alerta de confirmación"
    
    except Exception as e:
        print(f"❌ Error guardando fila {fila}: {str(e)}")
        registrar_log_remesa(
            f"Fila {fila}",
            f"Error guardando: {str(e)}",
            [("NIT", nit_generador)]
        )
        actualizar_estado_callback(f"❌ Fila {fila} - Error: {str(e)[:50]}")
        return False, None, f"Error excepción: {str(e)}"


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
        reporte_data = [] # Lista para almacenar el reporte completo
        
        for idx, datos_fila in enumerate(datos, 1):
            # Inicializar tracking de la fila actual
            # Copiar todos los datos originales
            fila_reporte = datos_fila.copy()
            
            # Agregar datos de operación
            fila_reporte['FECHA_PROCESO'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fila_reporte['NIT_NUEVO_USADO'] = NIT_EMPRESA
            fila_reporte['SEDE_NUEVA_USADA'] = "BOGOTA (" + SEDE_DESTINO + ")"
            fila_reporte['OBSERVACIONES_USADAS'] = OBSERVACIONES
            
            # Verificar cancelación
            if cancelar_func():
                actualizar_estado_callback("⛔ Proceso cancelado por el usuario")
                fila_reporte['RESULTADO_PROCESO'] = "CANCELADO POR USUARIO"
                fila_reporte['MENSAJE_PROCESO'] = "Proceso detenido manualmente"
                reporte_data.append(fila_reporte)
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
                fila_reporte['RESULTADO_PROCESO'] = "FALLIDO"
                fila_reporte['MENSAJE_PROCESO'] = "No se pudo llenar el formulario (posiblemente no se encontró sede o remesas)"
                fila_reporte['RADICADO_GENERADO'] = ""
                reporte_data.append(fila_reporte)
                
                navegar_a_formulario(driver)
                continue
            
            # Guardar y obtener radicado
            exito, radicado, mensaje = guardar_y_capturar_radicado(driver, datos_fila, actualizar_estado_callback)
            
            fila_reporte['MENSAJE_PROCESO'] = mensaje if mensaje else "Error desconocido"
            
            if exito:
                exitosos += 1
                fila_reporte['RESULTADO_PROCESO'] = "EXITOSO"
                fila_reporte['RADICADO_GENERADO'] = radicado if radicado else ""
            else:
                fallidos += 1
                fila_reporte['RESULTADO_PROCESO'] = "FALLIDO"
                fila_reporte['RADICADO_GENERADO'] = ""
            
            reporte_data.append(fila_reporte)
            
            # Recargar formulario para siguiente registro
            navegar_a_formulario(driver)
            time.sleep(1)
        
        # Resumen final
        mensaje_final = f"✅ Proceso completado | Exitosos: {exitosos} | Fallidos: {fallidos}"
        actualizar_estado_callback(mensaje_final)
        print(f"\n{mensaje_final}")
        
        # Generar Reporte Excel Detallado
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_reporte = f"reporte_cambio_sede_{timestamp}.xlsx"
        
        try:
            actualizar_estado_callback(f"📊 Generando reporte detallado: {nombre_reporte}")
            df_reporte = pd.DataFrame(reporte_data)
            
            # Asegurarse que fila, nit, etc. no queden duplicados si ya venían del excel
            # Pandas se encarga, pero ordenemos las columas importantes al inicio si es posible
            cols_prioridad = ['fila', 'nit_generador', 'RESULTADO_PROCESO', 'RADICADO_GENERADO', 'MENSAJE_PROCESO']
            cols = list(df_reporte.columns)
            
            # Reordenar para poner prioridad al inicio, resto después
            cols_final = [c for c in cols_prioridad if c in cols] + [c for c in cols if c not in cols_prioridad]
            df_reporte = df_reporte[cols_final]
            
            df_reporte.to_excel(nombre_reporte, index=False)
            print(f"✅ Reporte guardado en: {nombre_reporte}")
            actualizar_estado_callback(f"✅ Reporte guardado: {nombre_reporte}")
            
        except Exception as e:
            print(f"❌ Error generando reporte Excel: {str(e)}")
            actualizar_estado_callback(f"❌ Error generando reporte: {str(e)}")
        
    except Exception as e:
        error_msg = f"❌ Error general: {str(e)}"
        print(error_msg)
        actualizar_estado_callback(error_msg)
        registrar_log_remesa("SISTEMA", f"Error general: {str(e)}", [])
    
    finally:
        driver.quit()